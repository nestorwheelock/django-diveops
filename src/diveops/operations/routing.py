"""WebSocket URL routing for diveops.operations."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Visitor chat (public - identified by visitor_id cookie/param)
    re_path(r"ws/chat/visitor/(?P<visitor_id>[0-9a-f-]+)/$", consumers.ChatConsumer.as_asgi()),
    # Staff chat (authenticated - viewing a specific lead)
    re_path(r"ws/chat/lead/(?P<lead_id>[0-9a-f-]+)/$", consumers.ChatConsumer.as_asgi()),
    # Portal conversation chat (authenticated user viewing their conversation)
    re_path(r"ws/chat/conversation/(?P<conversation_id>[0-9a-f-]+)/$", consumers.ChatConsumer.as_asgi()),
    # WebRTC signaling (authenticated - for video/audio calls)
    re_path(r"ws/call/$", consumers.WebRTCConsumer.as_asgi()),
]
