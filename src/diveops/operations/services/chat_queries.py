"""Optimized chat query services.

This module provides N+1-safe query services for conversation and message
retrieval. All chat interfaces (staff, customer, public, mobile) should use
these instead of writing their own queries.

The key optimization is using Subquery annotations to fetch related data
(last message, unread counts, etc.) in a single query instead of looping.
"""

from datetime import datetime
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone

from django_communication.models import (
    Conversation,
    ConversationParticipant,
    ConversationStatus,
    Message,
    MessageDirection,
    MessageStatus,
)
from django_parties.models import Person


class ConversationQueryService:
    """Optimized conversation list queries.

    Kills N+1 queries by using Subquery to annotate each conversation with:
    - last_message_preview
    - last_message_at
    - last_message_direction
    - unread_count (where applicable)
    - customer/lead name

    Usage:
        # Get lead-linked conversations (public chat, staff chat widget)
        conversations = ConversationQueryService.list_for_leads(
            status="active",
            limit=100,
        )

        # Get conversations for a staff user
        conversations = ConversationQueryService.list_for_staff(
            user=request.user,
            status="active",
            scope="mine",
        )

        # Get conversations for a customer
        conversations = ConversationQueryService.list_for_customer(
            person=customer_person,
        )
    """

    @staticmethod
    def list_for_leads(
        status: str = "active",
        limit: int = 100,
        exclude_closed: bool = True,
    ) -> models.QuerySet:
        """Get conversations linked to Person records (lead chat pattern).

        Returns annotated queryset with:
        - last_message_preview (first 100 chars of last message)
        - last_message_at
        - last_message_direction
        - needs_reply (bool: last message was inbound)
        - person_id (related Person's ID)

        Args:
            status: Filter by status (active, archived, closed, all)
            limit: Maximum conversations to return
            exclude_closed: If True and status not specified, exclude closed

        Returns:
            QuerySet of Conversation with annotations
        """
        person_ct = ContentType.objects.get_for_model(Person)

        # Base queryset: conversations linked to Person records
        qs = Conversation.objects.filter(
            related_content_type=person_ct,
            deleted_at__isnull=True,
        )

        # Apply status filter
        if status == "active":
            qs = qs.filter(status=ConversationStatus.ACTIVE)
        elif status == "archived":
            qs = qs.filter(status=ConversationStatus.ARCHIVED)
        elif status == "closed":
            qs = qs.filter(status=ConversationStatus.CLOSED)
        elif status == "all":
            pass  # No filter
        elif exclude_closed:
            # Default: exclude closed
            qs = qs.exclude(status=ConversationStatus.CLOSED)

        # Subquery for last message fields
        latest_message = Message.objects.filter(
            conversation=OuterRef("pk")
        ).order_by("-created_at")

        qs = qs.annotate(
            last_message_preview=Subquery(latest_message.values("body_text")[:1]),
            last_message_at_annotated=Subquery(latest_message.values("created_at")[:1]),
            last_message_direction=Subquery(latest_message.values("direction")[:1]),
        )

        # Annotate needs_reply (last message was inbound)
        qs = qs.annotate(
            needs_reply=Q(last_message_direction=MessageDirection.INBOUND)
        )

        # Order by most recent activity
        qs = qs.order_by("-last_message_at", "-updated_at")

        # Apply limit
        if limit:
            qs = qs[:limit]

        return qs

    @staticmethod
    def list_for_staff(
        user: "User",
        status: str = "active",
        scope: str = "mine",
        limit: int = 100,
    ) -> models.QuerySet:
        """Get conversations for staff CRM inbox.

        Wraps django_communication's get_staff_inbox with additional controls.

        Args:
            user: Staff user
            status: Filter by status (active, archived, closed, all)
            scope: Filter scope (mine, unassigned, all)
            limit: Maximum conversations to return

        Returns:
            QuerySet of Conversation with annotations
        """
        from django_communication.services.conversations import get_staff_inbox

        qs = get_staff_inbox(user=user, status=status, scope=scope)

        if limit:
            qs = qs[:limit]

        return qs

    @staticmethod
    def list_for_customer(
        person: "Person",
        limit: int = 50,
    ) -> models.QuerySet:
        """Get conversations for customer portal.

        Wraps django_communication's get_customer_inbox.

        Args:
            person: Customer Person instance
            limit: Maximum conversations to return

        Returns:
            QuerySet of Conversation with annotations
        """
        from django_communication.services.conversations import get_customer_inbox

        qs = get_customer_inbox(person=person)

        if limit:
            qs = qs[:limit]

        return qs

    @staticmethod
    def list_for_mobile(
        user: "User",
        limit: int = 100,
    ) -> models.QuerySet:
        """Get conversations for mobile app (staff).

        Returns conversations with unread counts and needs-reply indicators.

        Args:
            user: Staff user
            limit: Maximum conversations to return

        Returns:
            QuerySet of Conversation with annotations
        """
        person_ct = ContentType.objects.get_for_model(Person)

        # Exclude closed conversations
        qs = Conversation.objects.filter(
            related_content_type=person_ct,
            deleted_at__isnull=True,
        ).exclude(status=ConversationStatus.CLOSED)

        # Subquery for last message
        latest_message = Message.objects.filter(
            conversation=OuterRef("pk")
        ).order_by("-created_at")

        qs = qs.annotate(
            last_message_preview=Subquery(latest_message.values("body_text")[:1]),
            last_message_at_annotated=Subquery(latest_message.values("created_at")[:1]),
            last_message_direction=Subquery(latest_message.values("direction")[:1]),
            last_message_sender_id=Subquery(latest_message.values("sender_person_id")[:1]),
        )

        # Count unread inbound messages
        unread_messages = Message.objects.filter(
            conversation=OuterRef("pk"),
            direction=MessageDirection.INBOUND,
            status__in=[
                MessageStatus.QUEUED,
                MessageStatus.SENDING,
                MessageStatus.SENT,
                MessageStatus.DELIVERED,
            ],
        )

        qs = qs.annotate(
            unread_count=Coalesce(
                Subquery(
                    unread_messages.values("conversation").annotate(
                        cnt=Count("id")
                    ).values("cnt")[:1]
                ),
                Value(0),
            )
        )

        # Needs reply: last message was inbound
        qs = qs.annotate(
            needs_reply=Q(last_message_direction=MessageDirection.INBOUND)
        )

        # Order by most recent
        qs = qs.order_by("-last_message_at", "-updated_at")

        if limit:
            qs = qs[:limit]

        return qs


class MessageQueryService:
    """Optimized message retrieval queries.

    Provides consistent message retrieval with cursor pagination support.

    Usage:
        # Get messages for a conversation
        messages = MessageQueryService.get_messages(
            conversation=conv,
            limit=50,
            before=cursor_timestamp,
        )

        # Get messages for a lead (by person_id)
        messages = MessageQueryService.get_messages_for_lead(
            person_id=person_id,
            limit=100,
        )
    """

    # Default limits per interface
    DEFAULT_LIMIT_STAFF = 100
    DEFAULT_LIMIT_MOBILE = 200
    DEFAULT_LIMIT_PUBLIC = 50
    DEFAULT_LIMIT_CUSTOMER = 100

    @staticmethod
    def get_messages(
        conversation: Conversation,
        limit: int = 100,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        mark_read_for: Optional["Person"] = None,
    ) -> models.QuerySet:
        """Get messages for a conversation with cursor pagination.

        Args:
            conversation: Conversation to get messages from
            limit: Maximum messages to return
            before: Only messages before this timestamp (cursor)
            after: Only messages after this timestamp
            mark_read_for: If provided, mark messages as read for this person

        Returns:
            QuerySet of Message in chronological order
        """
        qs = Message.objects.filter(
            conversation=conversation
        ).select_related("sender_person", "template")

        if before:
            qs = qs.filter(created_at__lt=before)

        if after:
            qs = qs.filter(created_at__gt=after)

        # Order chronologically
        qs = qs.order_by("created_at")

        if limit:
            # Get latest N messages in chronological order
            # Subquery approach to maintain chronological order
            latest_ids = Message.objects.filter(
                conversation=conversation
            )
            if before:
                latest_ids = latest_ids.filter(created_at__lt=before)
            if after:
                latest_ids = latest_ids.filter(created_at__gt=after)

            latest_ids = latest_ids.order_by("-created_at").values("pk")[:limit]
            qs = qs.filter(pk__in=latest_ids).order_by("created_at")

        # Optionally mark as read
        if mark_read_for:
            conversation.mark_read_for(mark_read_for)

        return qs

    @staticmethod
    def get_messages_for_lead(
        person_id: str,
        limit: int = 100,
        before: Optional[datetime] = None,
    ) -> tuple[Optional[Conversation], models.QuerySet]:
        """Get messages for a lead-linked conversation.

        Args:
            person_id: Person UUID
            limit: Maximum messages to return
            before: Only messages before this timestamp

        Returns:
            Tuple of (Conversation or None, QuerySet of Message)
        """
        person_ct = ContentType.objects.get_for_model(Person)

        conversation = Conversation.objects.filter(
            related_content_type=person_ct,
            related_object_id=str(person_id),
            deleted_at__isnull=True,
        ).first()

        if not conversation:
            return None, Message.objects.none()

        messages = MessageQueryService.get_messages(
            conversation=conversation,
            limit=limit,
            before=before,
        )

        return conversation, messages

    @staticmethod
    def mark_inbound_read(
        conversation: Conversation,
    ) -> int:
        """Mark all inbound messages as read.

        Args:
            conversation: Conversation to mark read

        Returns:
            Number of messages updated
        """
        return Message.objects.filter(
            conversation=conversation,
            direction=MessageDirection.INBOUND,
            status__in=[
                MessageStatus.QUEUED,
                MessageStatus.SENDING,
                MessageStatus.SENT,
                MessageStatus.DELIVERED,
            ],
        ).update(
            status=MessageStatus.READ,
            read_at=timezone.now(),
        )
