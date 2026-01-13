"""WebSocket consumers for real-time chat and WebRTC signaling."""

import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


# =============================================================================
# WebRTC Signaling Consumer
# =============================================================================


class WebRTCConsumer(WebsocketConsumer):
    """WebSocket consumer for WebRTC signaling.

    Handles peer-to-peer video/audio call signaling:
    - Offer/Answer SDP exchange
    - ICE candidate exchange
    - Call state (calling, answered, rejected, ended)

    Connection: /ws/call/<user_id>/
    """

    # Track connected users for call routing
    connected_users = {}

    def connect(self):
        """Handle WebSocket connection."""
        route_kwargs = self.scope.get("url_route", {}).get("kwargs", {})
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("Unauthenticated WebRTC connection attempt")
            self.close()
            return

        self.user_id = str(user.pk)
        self.room_group_name = f"webrtc_user_{self.user_id}"

        # Join personal room for receiving calls
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        # Track this connection
        WebRTCConsumer.connected_users[self.user_id] = self.channel_name

        self.accept()
        logger.info(f"WebRTC connected: user {self.user_id}")

        self.send(text_data=json.dumps({
            "type": "connected",
            "user_id": self.user_id,
        }))

    def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, "room_group_name"):
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name
            )

        if hasattr(self, "user_id") and self.user_id in WebRTCConsumer.connected_users:
            del WebRTCConsumer.connected_users[self.user_id]

        logger.info(f"WebRTC disconnected: user {getattr(self, 'user_id', 'unknown')}")

    def receive(self, text_data):
        """Handle incoming signaling message."""
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "call":
                self.handle_call(data)
            elif msg_type == "offer":
                self.handle_offer(data)
            elif msg_type == "answer":
                self.handle_answer(data)
            elif msg_type == "ice_candidate":
                self.handle_ice_candidate(data)
            elif msg_type == "hangup":
                self.handle_hangup(data)
            elif msg_type == "reject":
                self.handle_reject(data)
            else:
                logger.warning(f"Unknown WebRTC message type: {msg_type}")

        except json.JSONDecodeError:
            logger.warning("Invalid JSON in WebRTC message")
        except Exception as e:
            logger.exception(f"Error handling WebRTC message: {e}")

    def handle_call(self, data):
        """Initiate a call to another user."""
        target_user_id = data.get("target_user_id")
        call_type = data.get("call_type", "video")  # video or audio

        if not target_user_id:
            self.send(text_data=json.dumps({
                "type": "error",
                "message": "target_user_id required",
            }))
            return

        # Check if target is online
        if target_user_id not in WebRTCConsumer.connected_users:
            self.send(text_data=json.dumps({
                "type": "user_offline",
                "target_user_id": target_user_id,
            }))
            return

        # Notify target user of incoming call
        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "incoming_call",
                "caller_id": self.user_id,
                "call_type": call_type,
            }
        )

        logger.info(f"Call initiated: {self.user_id} -> {target_user_id}")

    def handle_offer(self, data):
        """Forward SDP offer to target user."""
        target_user_id = data.get("target_user_id")
        sdp = data.get("sdp")

        if not target_user_id or not sdp:
            return

        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "webrtc_offer",
                "caller_id": self.user_id,
                "sdp": sdp,
            }
        )

    def handle_answer(self, data):
        """Forward SDP answer to caller."""
        target_user_id = data.get("target_user_id")
        sdp = data.get("sdp")

        if not target_user_id or not sdp:
            return

        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "webrtc_answer",
                "answerer_id": self.user_id,
                "sdp": sdp,
            }
        )

    def handle_ice_candidate(self, data):
        """Forward ICE candidate to peer."""
        target_user_id = data.get("target_user_id")
        candidate = data.get("candidate")

        if not target_user_id or not candidate:
            return

        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "ice_candidate",
                "sender_id": self.user_id,
                "candidate": candidate,
            }
        )

    def handle_hangup(self, data):
        """End the call."""
        target_user_id = data.get("target_user_id")

        if not target_user_id:
            return

        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "call_ended",
                "ended_by": self.user_id,
            }
        )

    def handle_reject(self, data):
        """Reject incoming call."""
        target_user_id = data.get("target_user_id")

        if not target_user_id:
            return

        target_room = f"webrtc_user_{target_user_id}"
        async_to_sync(self.channel_layer.group_send)(
            target_room,
            {
                "type": "call_rejected",
                "rejected_by": self.user_id,
            }
        )

    # Channel layer message handlers

    def incoming_call(self, event):
        """Notify user of incoming call."""
        self.send(text_data=json.dumps({
            "type": "incoming_call",
            "caller_id": event["caller_id"],
            "call_type": event["call_type"],
        }))

    def webrtc_offer(self, event):
        """Forward offer to user."""
        self.send(text_data=json.dumps({
            "type": "offer",
            "caller_id": event["caller_id"],
            "sdp": event["sdp"],
        }))

    def webrtc_answer(self, event):
        """Forward answer to user."""
        self.send(text_data=json.dumps({
            "type": "answer",
            "answerer_id": event["answerer_id"],
            "sdp": event["sdp"],
        }))

    def ice_candidate(self, event):
        """Forward ICE candidate to user."""
        self.send(text_data=json.dumps({
            "type": "ice_candidate",
            "sender_id": event["sender_id"],
            "candidate": event["candidate"],
        }))

    def call_ended(self, event):
        """Notify user call ended."""
        self.send(text_data=json.dumps({
            "type": "hangup",
            "ended_by": event["ended_by"],
        }))

    def call_rejected(self, event):
        """Notify user call was rejected."""
        self.send(text_data=json.dumps({
            "type": "rejected",
            "rejected_by": event["rejected_by"],
        }))


class ChatConsumer(WebsocketConsumer):
    """WebSocket consumer for lead chat conversations.

    Supports two connection types:
    1. Visitor (public): /ws/chat/visitor/<visitor_id>/
    2. Staff (authenticated): /ws/chat/lead/<lead_id>/

    Messages are broadcast to all participants in the conversation.
    """

    def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = None
        self.room_group_name = None

        # Determine connection type from URL route
        route_name = self.scope.get("url_route", {}).get("kwargs", {})

        if "visitor_id" in route_name:
            # Public visitor connection
            self.visitor_id = route_name["visitor_id"]
            self.is_staff = False
            self.room_group_name = f"chat_visitor_{self.visitor_id}"
        elif "lead_id" in route_name:
            # Staff connection - requires authentication and staff status
            user = self.scope.get("user")
            if not user or not user.is_authenticated or not user.is_staff:
                logger.warning("Unauthorized WebSocket connection attempt")
                self.close()
                return
            self.lead_id = route_name["lead_id"]
            self.is_staff = True
            self.room_group_name = f"chat_lead_{self.lead_id}"
        elif "conversation_id" in route_name:
            # Conversation connection - authenticated users OR visitors with valid conversation
            self.conversation_id = route_name["conversation_id"]
            user = self.scope.get("user")

            if user and user.is_authenticated:
                # Authenticated user (staff or portal user)
                self.is_staff = user.is_staff
            else:
                # Anonymous visitor - verify they have access to this conversation via cookie
                # For now, allow connection (the visitor would need to know the conversation ID)
                self.is_staff = False

            self.room_group_name = f"chat_conversation_{self.conversation_id}"
        else:
            logger.warning("Invalid WebSocket route")
            self.close()
            return

        # Join room group
        try:
            async_to_sync(self.channel_layer.group_add)(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            logger.exception(f"Failed to join channel group: {e}")
            self.close()
            return

        self.accept()
        logger.info(f"WebSocket connected: {self.room_group_name}")

        # Send connection confirmation to client
        self.send(text_data=json.dumps({
            "type": "connection_established",
            "room": self.room_group_name,
        }))

    def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.room_group_name:
            async_to_sync(self.channel_layer.group_discard)(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected: {self.room_group_name}")

    def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")

            if message_type == "message":
                self.handle_message(data)
            elif message_type == "typing":
                self.handle_typing(data)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in WebSocket message")
        except Exception as e:
            logger.exception(f"Error handling WebSocket message: {e}")

    def handle_message(self, data):
        """Handle a chat message."""
        message_text = data.get("message", "").strip()
        if not message_text:
            return

        # The actual message saving is done via the HTTP API
        # This just broadcasts to the room that a new message exists
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_text,
                "direction": "outbound" if self.is_staff else "inbound",
                "sender": "staff" if self.is_staff else "visitor",
            }
        )

    def handle_typing(self, data):
        """Handle typing indicator."""
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "is_typing": data.get("is_typing", False),
                "sender": "staff" if self.is_staff else "visitor",
            }
        )

    def chat_message(self, event):
        """Send chat message to WebSocket."""
        self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"],
            "direction": event["direction"],
            "sender": event["sender"],
        }))

    def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        self.send(text_data=json.dumps({
            "type": "typing",
            "is_typing": event["is_typing"],
            "sender": event["sender"],
        }))

    def new_message(self, event):
        """Notify about a new message (sent from HTTP API)."""
        self.send(text_data=json.dumps({
            "type": "new_message",
            "message_id": event.get("message_id"),
            "message": event.get("message"),
            "direction": event.get("direction"),
            "created_at": event.get("created_at"),
        }))
