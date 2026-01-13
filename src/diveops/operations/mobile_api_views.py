"""Mobile API views for the staff chat Android app.

These endpoints power the mobile app with:
- Authentication via token
- FCM device registration
- Conversations list
- Chat messages
- Send message functionality
- App version checking (in-app updates)
- Customer bookings
- Location tracking and sharing preferences
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django_parties.models import Person
from django_communication.models import (
    Conversation,
    ConversationStatus,
    FCMDevice,
    Message,
)

from .models import (
    AppVersion,
    Booking,
    LocationSharingPreference,
    LocationUpdate,
)

logger = logging.getLogger(__name__)


def require_auth_token(view_func):
    """Decorator to require Bearer token authentication (staff only)."""
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization required"}, status=401)

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Look up the token
        from rest_framework.authtoken.models import Token
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            if not token_obj.user.is_active or not token_obj.user.is_staff:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            request.user = token_obj.user
        except Token.DoesNotExist:
            return JsonResponse({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper


def require_auth_token_any(view_func):
    """Decorator to require Bearer token authentication (any active user)."""
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Authorization required"}, status=401)

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Look up the token
        from rest_framework.authtoken.models import Token
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            if not token_obj.user.is_active:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            request.user = token_obj.user
        except Token.DoesNotExist:
            return JsonResponse({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper


@method_decorator(csrf_exempt, name="dispatch")
class MobileLoginView(View):
    """Login endpoint for mobile app.

    POST /api/mobile/login/
    {
        "email": "user@example.com",
        "password": "secret"
    }

    Returns auth token for subsequent requests.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)

        # Authenticate
        user = authenticate(request, username=email, password=password)

        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not user.is_staff:
            return JsonResponse({"error": "Staff access required"}, status=403)

        # Get or create auth token
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        return JsonResponse({
            "token": token.key,
            "user": {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        })


@method_decorator(csrf_exempt, name="dispatch")
class FCMRegisterView(View):
    """Register FCM device token.

    POST /api/mobile/fcm/register/
    Headers: Authorization: Bearer <token>
    {
        "registration_id": "fcm-device-token",
        "platform": "android",
        "device_id": "unique-device-id",
        "device_name": "Pixel 7 Pro",
        "app_version": "1.0.0"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        registration_id = data.get("registration_id", "").strip()
        if not registration_id:
            return JsonResponse({"error": "registration_id required"}, status=400)

        # Create or update device
        device, created = FCMDevice.objects.update_or_create(
            user=request.user,
            registration_id=registration_id,
            defaults={
                "platform": data.get("platform", "android"),
                "device_id": data.get("device_id", ""),
                "device_name": data.get("device_name", ""),
                "app_version": data.get("app_version", ""),
                "is_active": True,
                "failure_count": 0,
                "deleted_at": None,
            },
        )

        return JsonResponse({
            "status": "registered" if created else "updated",
            "device_id": str(device.pk),
        })


@method_decorator(csrf_exempt, name="dispatch")
class FCMUnregisterView(View):
    """Unregister FCM device token.

    POST /api/mobile/fcm/unregister/
    Headers: Authorization: Bearer <token>
    {
        "registration_id": "fcm-device-token"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        registration_id = data.get("registration_id", "").strip()
        if not registration_id:
            return JsonResponse({"error": "registration_id required"}, status=400)

        # Deactivate device
        updated = FCMDevice.objects.filter(
            user=request.user,
            registration_id=registration_id,
        ).update(is_active=False)

        return JsonResponse({
            "status": "unregistered" if updated else "not_found",
        })


@method_decorator(csrf_exempt, name="dispatch")
class MobileConversationsView(View):
    """List conversations for mobile app.

    GET /api/mobile/conversations/
    Headers: Authorization: Bearer <token>

    Returns list of conversations with last message and unread count.
    """

    @method_decorator(require_auth_token)
    def get(self, request):
        from django_communication.models import ConversationParticipant

        # Get all active conversations (not filtered by content type)
        # This includes conversations for leads, divers, bookings, etc.
        conversations = (
            Conversation.objects.filter(deleted_at__isnull=True)
            .exclude(status=ConversationStatus.CLOSED)
            .select_related("related_content_type")
            .prefetch_related("participants__person")
            .order_by("-updated_at")[:100]
        )

        result = []
        for conv in conversations:
            # Find the customer participant (the person we're chatting with)
            customer_participant = conv.participants.filter(
                role="customer",
                person__deleted_at__isnull=True,
            ).select_related("person").first()

            if not customer_participant:
                # Fallback: try to get person from related_object if it's a Person
                person_ct = ContentType.objects.get_for_model(Person)
                if conv.related_content_type == person_ct:
                    person = Person.objects.filter(
                        pk=conv.related_object_id,
                        deleted_at__isnull=True,
                    ).first()
                else:
                    continue
            else:
                person = customer_participant.person

            if not person:
                continue

            # Get last message
            last_msg = (
                Message.objects.filter(conversation=conv)
                .order_by("-created_at")
                .first()
            )

            # Count unread (inbound messages not marked as read)
            unread_count = Message.objects.filter(
                conversation=conv,
                direction="inbound",
            ).exclude(status="read").count()

            # Needs reply if last message was inbound
            needs_reply = last_msg and last_msg.direction == "inbound"

            result.append({
                "id": str(conv.pk),
                "person_id": str(person.pk),
                "name": f"{person.first_name} {person.last_name}".strip() or person.email or "Unknown",
                "email": person.email or "",
                "initials": _get_initials(person),
                "last_message": last_msg.body_text[:100] if last_msg else "",
                "last_message_time": last_msg.created_at.isoformat() if last_msg else None,
                "needs_reply": needs_reply,
                "unread_count": unread_count,
                "status": conv.status,
            })

        return JsonResponse({"conversations": result})


@method_decorator(csrf_exempt, name="dispatch")
class MobileMessagesView(View):
    """Get messages for a conversation.

    GET /api/mobile/conversations/<conversation_id>/messages/
    Headers: Authorization: Bearer <token>

    Returns messages in chronological order.
    """

    @method_decorator(require_auth_token)
    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(
                pk=conversation_id,
                deleted_at__isnull=True,
            )
        except Conversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        messages = (
            Message.objects.filter(conversation=conversation)
            .order_by("created_at")[:200]
        )

        # Mark inbound messages as read
        from django.utils import timezone
        Message.objects.filter(
            conversation=conversation,
            direction="inbound",
        ).exclude(status="read").update(
            status="read",
            read_at=timezone.now(),
        )

        result = []
        for msg in messages:
            result.append({
                "id": str(msg.pk),
                "body": msg.body_text or "",  # Ensure never None
                "direction": msg.direction or "inbound",
                "status": msg.status or "sent",
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "sender_name": _get_sender_name(msg),
            })

        return JsonResponse({"messages": result})


@method_decorator(csrf_exempt, name="dispatch")
class MobileSendMessageView(View):
    """Send a message in a conversation.

    POST /api/mobile/conversations/<conversation_id>/send/
    Headers: Authorization: Bearer <token>
    {
        "message": "Hello, how can I help?"
    }
    """

    @method_decorator(require_auth_token)
    def post(self, request, conversation_id):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message_text = data.get("message", "").strip()
        if not message_text:
            return JsonResponse({"error": "Message required"}, status=400)

        try:
            conversation = Conversation.objects.get(
                pk=conversation_id,
                deleted_at__isnull=True,
            )
        except Conversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)

        # Get the person for this conversation
        person_ct = ContentType.objects.get_for_model(Person)
        if conversation.related_content_type != person_ct:
            return JsonResponse({"error": "Invalid conversation type"}, status=400)

        try:
            person = Person.objects.get(pk=conversation.related_object_id)
        except Person.DoesNotExist:
            return JsonResponse({"error": "Person not found"}, status=404)

        # Create the message
        from django.utils import timezone

        msg = Message.objects.create(
            conversation=conversation,
            sender_person=None,  # Staff message, no Person sender
            direction="outbound",
            channel="in_app",
            from_address=request.user.email,
            to_address=person.email or "",
            body_text=message_text,
            status="sent",
            sent_at=timezone.now(),
        )

        # Update conversation timestamp
        conversation.last_outbound_at = timezone.now()
        conversation.save(update_fields=["last_outbound_at", "updated_at"])

        # Broadcast via WebSocket
        from .crm.services import broadcast_chat_message
        broadcast_chat_message(
            person_id=str(person.pk),
            visitor_id=person.visitor_id,
            conversation_id=str(conversation.pk),
            message_id=str(msg.pk),
            message_text=message_text,
            direction="outbound",
            status=msg.status,
            created_at=msg.created_at.isoformat(),
        )

        # Send email notification
        from .crm.services import send_lead_notification_email
        send_lead_notification_email(
            person=person,
            message=message_text,
            staff_user=request.user,
            message_obj=msg,
        )

        return JsonResponse({
            "status": "sent",
            "message_id": str(msg.pk),
        })


def _get_initials(person):
    """Get initials from person name."""
    initials = ""
    if person.first_name:
        initials += person.first_name[0].upper()
    if person.last_name:
        initials += person.last_name[0].upper()
    return initials or "?"


def _get_sender_name(msg):
    """Get sender name for a message."""
    if msg.direction == "inbound":
        if msg.sender_person:
            name = f"{msg.sender_person.first_name} {msg.sender_person.last_name}".strip()
            return name or msg.sender_person.email or "Visitor"
        return "Visitor"
    else:
        # Outbound - from staff
        return "Staff"


# =============================================================================
# App Version Check (In-App Updates)
# =============================================================================


@method_decorator(csrf_exempt, name="dispatch")
class VersionCheckView(View):
    """Check for app updates.

    GET /api/mobile/version/check/?platform=android&current_version=1

    No authentication required (app needs to check before login).

    Returns:
    {
        "update_available": true,
        "force_update": true,
        "latest_version": {
            "version_code": 2,
            "version_name": "1.1.0",
            "download_url": "https://...",
            "release_notes": "Bug fixes..."
        }
    }
    """

    def get(self, request):
        platform = request.GET.get("platform", "").strip().lower()
        current_version_str = request.GET.get("current_version", "0")

        if not platform:
            return JsonResponse({"error": "platform parameter required"}, status=400)

        try:
            current_version = int(current_version_str)
        except (ValueError, TypeError):
            current_version = 0

        # Get latest version for this platform
        latest = (
            AppVersion.objects
            .filter(platform=platform, deleted_at__isnull=True)
            .order_by("-version_code")
            .first()
        )

        if not latest:
            return JsonResponse({
                "update_available": False,
                "force_update": False,
            })

        update_available = latest.version_code > current_version
        force_update = (
            update_available and
            (latest.is_force_update or current_version < latest.min_supported_version)
        )

        response = {
            "update_available": update_available,
            "force_update": force_update,
        }

        if update_available:
            response["latest_version"] = {
                "version_code": latest.version_code,
                "version_name": latest.version_name,
                "download_url": latest.download_url,
                "release_notes": latest.release_notes,
            }

        return JsonResponse(response)


# =============================================================================
# Customer Login
# =============================================================================


@method_decorator(csrf_exempt, name="dispatch")
class CustomerLoginView(View):
    """Login endpoint for customer mobile app.

    POST /api/mobile/customer/login/
    {
        "email": "user@example.com",
        "password": "secret"
    }

    Returns auth token and is_staff flag for role-based UI.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)

        # Authenticate
        user = authenticate(request, username=email, password=password)

        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        if not user.is_active:
            return JsonResponse({"error": "Account disabled"}, status=403)

        # Get Person record (required for customer features)
        try:
            person = Person.objects.get(user=user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found for this user"}, status=403)

        # Get or create auth token
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=user)

        return JsonResponse({
            "token": token.key,
            "user": {
                "id": user.pk,
                "person_id": str(person.pk),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            },
        })


# =============================================================================
# Customer Bookings
# =============================================================================


@method_decorator(csrf_exempt, name="dispatch")
class CustomerBookingsView(View):
    """List customer's dive bookings.

    GET /api/mobile/customer/bookings/
    Headers: Authorization: Bearer <token>

    Returns:
    {
        "upcoming": [...],
        "past": [...]
    }
    """

    @method_decorator(require_auth_token_any)
    def get(self, request):
        # Get person for this user
        try:
            person = Person.objects.get(user=request.user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found"}, status=404)

        # Get diver profile
        from .models import DiverProfile
        try:
            diver = DiverProfile.objects.get(person=person, deleted_at__isnull=True)
        except DiverProfile.DoesNotExist:
            # No diver profile means no bookings
            return JsonResponse({"upcoming": [], "past": []})

        today = timezone.now().date()

        # Get all bookings for this diver
        bookings = (
            Booking.objects
            .filter(diver=diver, deleted_at__isnull=True)
            .select_related("excursion")
            .order_by("excursion__departure_date", "excursion__departure_time")
        )

        upcoming = []
        past = []

        for booking in bookings:
            excursion = booking.excursion
            if not excursion or excursion.deleted_at:
                continue

            booking_data = {
                "id": str(booking.pk),
                "excursion_id": str(excursion.pk),
                "excursion_name": excursion.name,
                "departure_date": excursion.departure_date.isoformat() if excursion.departure_date else None,
                "departure_time": excursion.departure_time.isoformat() if excursion.departure_time else None,
                "status": booking.status,
            }

            if excursion.departure_date and excursion.departure_date >= today:
                upcoming.append(booking_data)
            else:
                past.append(booking_data)

        # Sort: upcoming by nearest first, past by most recent first
        past.reverse()

        return JsonResponse({"upcoming": upcoming, "past": past})


# =============================================================================
# Location Update
# =============================================================================


@method_decorator(csrf_exempt, name="dispatch")
class LocationUpdateView(View):
    """Submit a location update.

    POST /api/mobile/location/
    Headers: Authorization: Bearer <token>
    {
        "latitude": 20.508895,
        "longitude": -87.376305,
        "accuracy_meters": 10.5,
        "altitude_meters": 5.0,
        "source": "gps",
        "recorded_at": "2024-01-13T10:30:00Z"
    }
    """

    @method_decorator(require_auth_token_any)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Get person for this user
        try:
            person = Person.objects.get(user=request.user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found"}, status=404)

        # Parse and validate coordinates
        try:
            latitude = Decimal(str(data.get("latitude", "")))
            longitude = Decimal(str(data.get("longitude", "")))
        except (InvalidOperation, TypeError):
            return JsonResponse({"error": "Invalid coordinates"}, status=400)

        if not (-90 <= latitude <= 90):
            return JsonResponse({"error": "Latitude must be between -90 and 90"}, status=400)
        if not (-180 <= longitude <= 180):
            return JsonResponse({"error": "Longitude must be between -180 and 180"}, status=400)

        # Parse optional fields
        accuracy_meters = None
        if data.get("accuracy_meters"):
            try:
                accuracy_meters = Decimal(str(data["accuracy_meters"]))
            except (InvalidOperation, TypeError):
                pass

        altitude_meters = None
        if data.get("altitude_meters"):
            try:
                altitude_meters = Decimal(str(data["altitude_meters"]))
            except (InvalidOperation, TypeError):
                pass

        source = data.get("source", "fused")
        if source not in ["gps", "network", "fused", "manual"]:
            source = "fused"

        # Parse recorded_at or use current time
        recorded_at_str = data.get("recorded_at")
        if recorded_at_str:
            from django.utils.dateparse import parse_datetime
            recorded_at = parse_datetime(recorded_at_str)
            if not recorded_at:
                recorded_at = timezone.now()
        else:
            recorded_at = timezone.now()

        # Create location update
        location = LocationUpdate.objects.create(
            person=person,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=accuracy_meters,
            altitude_meters=altitude_meters,
            source=source,
            recorded_at=recorded_at,
        )

        return JsonResponse({"id": str(location.pk)}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class LocationBatchUpdateView(View):
    """Submit multiple location updates at once.

    POST /api/mobile/location/batch/
    Headers: Authorization: Bearer <token>
    {
        "updates": [
            {"latitude": 20.5, "longitude": -87.3, "recorded_at": "..."},
            ...
        ]
    }
    """

    @method_decorator(require_auth_token_any)
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        updates = data.get("updates", [])
        if not isinstance(updates, list):
            return JsonResponse({"error": "updates must be an array"}, status=400)

        # Get person for this user
        try:
            person = Person.objects.get(user=request.user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found"}, status=404)

        created_count = 0
        from django.utils.dateparse import parse_datetime

        for update in updates:
            try:
                latitude = Decimal(str(update.get("latitude", "")))
                longitude = Decimal(str(update.get("longitude", "")))

                if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                    continue

                accuracy_meters = None
                if update.get("accuracy_meters"):
                    try:
                        accuracy_meters = Decimal(str(update["accuracy_meters"]))
                    except (InvalidOperation, TypeError):
                        pass

                altitude_meters = None
                if update.get("altitude_meters"):
                    try:
                        altitude_meters = Decimal(str(update["altitude_meters"]))
                    except (InvalidOperation, TypeError):
                        pass

                source = update.get("source", "fused")
                if source not in ["gps", "network", "fused", "manual"]:
                    source = "fused"

                recorded_at_str = update.get("recorded_at")
                recorded_at = parse_datetime(recorded_at_str) if recorded_at_str else timezone.now()
                if not recorded_at:
                    recorded_at = timezone.now()

                LocationUpdate.objects.create(
                    person=person,
                    latitude=latitude,
                    longitude=longitude,
                    accuracy_meters=accuracy_meters,
                    altitude_meters=altitude_meters,
                    source=source,
                    recorded_at=recorded_at,
                )
                created_count += 1

            except (InvalidOperation, TypeError):
                continue

        return JsonResponse({"created": created_count}, status=201)


# =============================================================================
# Location Settings
# =============================================================================


@method_decorator(csrf_exempt, name="dispatch")
class LocationSettingsView(View):
    """Get or update location sharing preferences.

    GET /api/mobile/location/settings/
    Headers: Authorization: Bearer <token>

    PUT /api/mobile/location/settings/
    Headers: Authorization: Bearer <token>
    {
        "visibility": "staff",
        "is_tracking_enabled": true,
        "tracking_interval_seconds": 60
    }
    """

    @method_decorator(require_auth_token_any)
    def get(self, request):
        # Get person for this user
        try:
            person = Person.objects.get(user=request.user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found"}, status=404)

        # Get or create preferences
        pref, created = LocationSharingPreference.objects.get_or_create(
            person=person,
            defaults={
                "visibility": "private",
                "is_tracking_enabled": False,
                "tracking_interval_seconds": 60,
            }
        )

        return JsonResponse({
            "visibility": pref.visibility,
            "is_tracking_enabled": pref.is_tracking_enabled,
            "tracking_interval_seconds": pref.tracking_interval_seconds,
        })

    @method_decorator(require_auth_token_any)
    def put(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Get person for this user
        try:
            person = Person.objects.get(user=request.user, deleted_at__isnull=True)
        except Person.DoesNotExist:
            return JsonResponse({"error": "No profile found"}, status=404)

        # Get or create preferences
        pref, created = LocationSharingPreference.objects.get_or_create(
            person=person,
            defaults={
                "visibility": "private",
                "is_tracking_enabled": False,
                "tracking_interval_seconds": 60,
            }
        )

        # Update visibility
        visibility = data.get("visibility")
        if visibility is not None:
            valid_choices = ["private", "staff", "trip", "buddies", "public"]
            if visibility not in valid_choices:
                return JsonResponse(
                    {"error": f"visibility must be one of: {', '.join(valid_choices)}"},
                    status=400,
                )
            pref.visibility = visibility

        # Update tracking enabled
        is_tracking_enabled = data.get("is_tracking_enabled")
        if is_tracking_enabled is not None:
            pref.is_tracking_enabled = bool(is_tracking_enabled)

        # Update tracking interval
        tracking_interval = data.get("tracking_interval_seconds")
        if tracking_interval is not None:
            try:
                interval = int(tracking_interval)
                if interval < 10:
                    interval = 10  # Minimum 10 seconds
                elif interval > 3600:
                    interval = 3600  # Maximum 1 hour
                pref.tracking_interval_seconds = interval
            except (ValueError, TypeError):
                pass

        pref.save()

        return JsonResponse({
            "visibility": pref.visibility,
            "is_tracking_enabled": pref.is_tracking_enabled,
            "tracking_interval_seconds": pref.tracking_interval_seconds,
        })
