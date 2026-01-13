"""Staff chat widget API views.

These endpoints power the floating chat widget and chat PWA in the staff portal.
"""

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView

from diveops.core.mixins import ImpersonationAwareStaffMixin as StaffPortalMixin

from django_parties.models import Person
from django_communication.models import Conversation, ConversationStatus, Message


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
    """List conversations with leads for the staff chat widget."""

    def get(self, request):
        person_ct = ContentType.objects.get_for_model(Person)

        # Get status filter from query params (default: show active and archived)
        status_filter = request.GET.get("status", "").lower()

        # Build base query for conversations linked to Person records
        queryset = Conversation.objects.filter(
            related_content_type=person_ct,
            deleted_at__isnull=True,
        )

        # Apply status filter
        if status_filter == "active":
            queryset = queryset.filter(status=ConversationStatus.ACTIVE)
        elif status_filter == "archived":
            queryset = queryset.filter(status=ConversationStatus.ARCHIVED)
        elif status_filter == "closed":
            queryset = queryset.filter(status=ConversationStatus.CLOSED)
        elif status_filter == "all":
            pass  # No filter, show all statuses
        else:
            # Default: show active and archived (exclude only closed)
            queryset = queryset.exclude(status=ConversationStatus.CLOSED)

        # Get limit from query params (default 100, max 200)
        try:
            limit = min(int(request.GET.get("limit", 100)), 200)
        except (ValueError, TypeError):
            limit = 100

        conversations = (
            queryset
            .select_related("related_content_type")
            .order_by("-updated_at")[:limit]
        )

        # Batch fetch all persons to avoid N+1 queries
        person_ids = [conv.related_object_id for conv in conversations]
        persons_by_id = {
            str(p.pk): p
            for p in Person.objects.filter(
                pk__in=person_ids,
                deleted_at__isnull=True,
            ).select_related("diver_profile")
        }

        result = []
        for conv in conversations:
            # Get the Person for this conversation
            person = persons_by_id.get(conv.related_object_id)
            if not person:
                continue

            # Get last message
            last_msg = (
                Message.objects.filter(conversation=conv)
                .order_by("-created_at")
                .first()
            )

            # Check if needs reply (last message was inbound)
            needs_reply = last_msg and last_msg.direction == "inbound"

            # Format time
            if last_msg:
                from django.utils import timezone
                from django.utils.timesince import timesince

                time_str = timesince(last_msg.created_at, timezone.now())
                # Simplify "1 day, 2 hours" to "1 day"
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

            result.append({
                "person_id": str(person.pk),
                "conversation_id": str(conv.pk),
                "name": f"{person.first_name} {person.last_name}".strip() or person.email or "Unknown",
                "email": person.email or "",
                "initials": initials,
                "last_message": last_msg.body_text[:50] + "..." if last_msg and len(last_msg.body_text) > 50 else (last_msg.body_text if last_msg else ""),
                "last_message_time": time_str,
                "needs_reply": needs_reply,
                "lead_status": person.lead_status,
                "conversation_status": conv.status,
                "is_diver": is_diver,
            })

        return JsonResponse({"conversations": result})


class StaffChatMessagesAPIView(StaffPortalMixin, View):
    """Get messages for a specific lead conversation."""

    def get(self, request, person_id):
        person_ct = ContentType.objects.get_for_model(Person)

        # Find conversation for this person
        conversation = Conversation.objects.filter(
            related_content_type=person_ct,
            related_object_id=str(person_id),
            deleted_at__isnull=True,
        ).first()

        if not conversation:
            return JsonResponse({"messages": []})

        # Get messages
        messages = (
            Message.objects.filter(conversation=conversation)
            .order_by("created_at")[:100]
        )

        result = []
        for msg in messages:
            from django.utils import timezone
            from django.utils.timesince import timesince

            time_str = timesince(msg.created_at, timezone.now())
            time_str = time_str.split(",")[0] + " ago"

            result.append({
                "id": str(msg.pk),
                "body": msg.body_text,
                "direction": msg.direction,
                "time": time_str,
                "created_at": msg.created_at.isoformat(),
            })

        return JsonResponse({"messages": result})
