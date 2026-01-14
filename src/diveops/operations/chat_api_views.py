"""Staff chat widget API views.

These endpoints power the floating chat widget and chat PWA in the staff portal.
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.timesince import timesince
from django.views import View
from django.views.generic import TemplateView

from diveops.core.mixins import ImpersonationAwareStaffMixin as StaffPortalMixin

from django_parties.models import Person
from django_communication.models import MessageDirection, MessageStatus

from .services.chat_queries import ConversationQueryService, MessageQueryService


class ChatInboxView(StaffPortalMixin, TemplateView):
    """Mobile-first chat inbox for staff."""

    template_name = "diveops/staff/chat/inbox.html"


class ChatThreadView(StaffPortalMixin, View):
    """Mobile-first chat thread for a specific lead."""

    def get(self, request, person_id):
        person = get_object_or_404(Person, pk=person_id, deleted_at__isnull=True)

        return render(request, "diveops/staff/chat/thread.html", {
            "person": person,
        })


class StaffChatConversationsAPIView(StaffPortalMixin, View):
    """List conversations with leads for the staff chat widget.

    Uses ConversationQueryService to avoid N+1 queries - all conversation
    data including last message is fetched in a single optimized query.
    """

    def get(self, request):
        # Get status filter from query params (default: show active and archived)
        status_filter = request.GET.get("status", "").lower() or "default"

        # Get limit from query params (default 100, max 200)
        try:
            limit = min(int(request.GET.get("limit", 100)), 200)
        except (ValueError, TypeError):
            limit = 100

        # Use optimized service - single query with Subquery annotations
        # This replaces the N+1 pattern where each conversation fetched last_msg separately
        conversations = ConversationQueryService.list_for_leads(
            status=status_filter if status_filter != "default" else "all",
            limit=limit,
            exclude_closed=(status_filter == "default"),
        )

        # Batch fetch all persons to avoid N+1 queries for person data
        person_ids = [conv.related_object_id for conv in conversations]
        persons_by_id = {
            str(p.pk): p
            for p in Person.objects.filter(
                pk__in=person_ids,
                deleted_at__isnull=True,
            ).select_related("diver_profile")
        }

        result = []
        now = timezone.now()

        for conv in conversations:
            # Get the Person for this conversation
            person = persons_by_id.get(conv.related_object_id)
            if not person:
                continue

            # Use annotated fields from the optimized query (no additional queries!)
            last_message_preview = conv.last_message_preview or ""
            last_message_at = conv.last_message_at_annotated
            needs_reply = conv.last_message_direction == MessageDirection.INBOUND

            # Format time from annotated timestamp
            if last_message_at:
                time_str = timesince(last_message_at, now)
                time_str = time_str.split(",")[0] + " ago"
            else:
                time_str = ""

            # Get initials
            initials = ""
            if person.first_name:
                initials += person.first_name[0].upper()
            if person.last_name:
                initials += person.last_name[0].upper()
            if not initials:
                initials = "?"

            # Check if person is a diver (select_related already fetched this)
            try:
                is_diver = person.diver_profile is not None
            except Exception:
                is_diver = False

            # Truncate preview
            if len(last_message_preview) > 50:
                last_message_preview = last_message_preview[:50] + "..."

            result.append({
                "person_id": str(person.pk),
                "conversation_id": str(conv.pk),
                "name": f"{person.first_name} {person.last_name}".strip() or person.email or "Unknown",
                "email": person.email or "",
                "initials": initials,
                "last_message": last_message_preview,
                "last_message_time": time_str,
                "needs_reply": needs_reply,
                "lead_status": person.lead_status,
                "conversation_status": conv.status,
                "is_diver": is_diver,
            })

        return JsonResponse({"conversations": result})


class StaffChatMessagesAPIView(StaffPortalMixin, View):
    """Get messages for a specific lead conversation.

    Uses MessageQueryService for consistent message retrieval.
    """

    def get(self, request, person_id):
        # Use service to get messages - handles conversation lookup
        conversation, messages = MessageQueryService.get_messages_for_lead(
            person_id=person_id,
            limit=MessageQueryService.DEFAULT_LIMIT_STAFF,
        )

        if not conversation:
            return JsonResponse({"messages": []})

        now = timezone.now()
        result = []

        for msg in messages:
            time_str = timesince(msg.created_at, now)
            time_str = time_str.split(",")[0] + " ago"

            result.append({
                "id": str(msg.pk),
                "body": msg.body_text,
                "direction": msg.direction,
                "status": msg.status,
                "time": time_str,
                "created_at": msg.created_at.isoformat(),
                "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
                "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
                "read_at": msg.read_at.isoformat() if msg.read_at else None,
            })

        return JsonResponse({"messages": result})


class MarkMessagesReadAPIView(StaffPortalMixin, View):
    """Mark messages as read when viewed by staff.

    Uses MessageQueryService.mark_inbound_read for consistent status handling.
    """

    def post(self, request, person_id):
        # Get conversation for this lead
        conversation, _ = MessageQueryService.get_messages_for_lead(
            person_id=person_id,
            limit=1,  # Just need to find the conversation
        )

        if not conversation:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        # Mark all inbound messages as read using service
        updated = MessageQueryService.mark_inbound_read(conversation)

        return JsonResponse({"marked_read": updated})
