"""Tests for WebRTC signaling consumer.

TDD tests for:
- WebRTC WebSocket connection
- Call initiation signaling
- Offer/Answer SDP exchange
- ICE candidate exchange
- Call hangup/reject
"""

import asyncio

import pytest
from channels.testing import WebsocketCommunicator

from diveops.operations.consumers import WebRTCConsumer


class MockUser:
    """Mock user for testing."""

    def __init__(self, pk, is_authenticated=True):
        self.pk = pk
        self.is_authenticated = is_authenticated


async def create_authenticated_communicator(user):
    """Create a WebSocket communicator with authenticated user."""
    communicator = WebsocketCommunicator(
        WebRTCConsumer.as_asgi(),
        "/ws/call/",
    )
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {}}
    return communicator


# =============================================================================
# Connection Tests
# =============================================================================


@pytest.mark.asyncio
class TestWebRTCConnection:
    """Tests for WebRTC WebSocket connection."""

    async def test_connect_authenticated_user(self):
        """Authenticated user can connect to WebRTC endpoint."""
        user = MockUser(pk=123, is_authenticated=True)
        communicator = await create_authenticated_communicator(user)

        connected, _ = await communicator.connect()

        assert connected is True

        # Should receive connected confirmation
        response = await communicator.receive_json_from()
        assert response["type"] == "connected"
        assert response["user_id"] == "123"

        await communicator.disconnect()

    async def test_connect_unauthenticated_rejected(self):
        """Unauthenticated connection is rejected."""
        user = MockUser(pk=456, is_authenticated=False)
        communicator = await create_authenticated_communicator(user)

        connected, close_code = await communicator.connect()

        # Should be rejected
        assert connected is False

    async def test_disconnect_clears_user_tracking(self):
        """Disconnecting removes user from connected users tracking."""
        user = MockUser(pk=789, is_authenticated=True)

        # Clear any existing state
        WebRTCConsumer.connected_users.clear()

        communicator = await create_authenticated_communicator(user)

        await communicator.connect()
        await communicator.receive_json_from()  # Connected message

        user_id = "789"
        assert user_id in WebRTCConsumer.connected_users

        await communicator.disconnect()

        assert user_id not in WebRTCConsumer.connected_users


# =============================================================================
# Call Initiation Tests
# =============================================================================


@pytest.mark.asyncio
class TestCallInitiation:
    """Tests for initiating calls."""

    async def test_call_online_user(self):
        """Can initiate call to online user."""
        caller = MockUser(pk=100, is_authenticated=True)
        callee = MockUser(pk=200, is_authenticated=True)

        # Clear state
        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)
        callee_comm = await create_authenticated_communicator(callee)

        await caller_comm.connect()
        await callee_comm.connect()

        await caller_comm.receive_json_from()  # Skip connected message
        await callee_comm.receive_json_from()  # Skip connected message

        # Caller initiates call
        await caller_comm.send_json_to({
            "type": "call",
            "target_user_id": "200",
            "call_type": "video",
        })

        # Callee should receive incoming call notification
        response = await callee_comm.receive_json_from()
        assert response["type"] == "incoming_call"
        assert response["caller_id"] == "100"
        assert response["call_type"] == "video"

        await caller_comm.disconnect()
        await callee_comm.disconnect()

    async def test_call_offline_user(self):
        """Calling offline user returns user_offline message."""
        caller = MockUser(pk=101, is_authenticated=True)

        # Clear state - no users connected
        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)

        await caller_comm.connect()
        await caller_comm.receive_json_from()

        # Try to call offline user (id 999 not connected)
        await caller_comm.send_json_to({
            "type": "call",
            "target_user_id": "999",
            "call_type": "video",
        })

        response = await caller_comm.receive_json_from()
        assert response["type"] == "user_offline"
        assert response["target_user_id"] == "999"

        await caller_comm.disconnect()

    async def test_call_without_target_returns_error(self):
        """Call without target_user_id returns error."""
        caller = MockUser(pk=102, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)

        await caller_comm.connect()
        await caller_comm.receive_json_from()

        await caller_comm.send_json_to({
            "type": "call",
            "call_type": "video",
        })

        response = await caller_comm.receive_json_from()
        assert response["type"] == "error"
        assert "target_user_id" in response["message"]

        await caller_comm.disconnect()


# =============================================================================
# SDP Exchange Tests
# =============================================================================


@pytest.mark.asyncio
class TestSDPExchange:
    """Tests for SDP offer/answer exchange."""

    async def test_offer_forwarded_to_callee(self):
        """SDP offer is forwarded to target user."""
        caller = MockUser(pk=300, is_authenticated=True)
        callee = MockUser(pk=400, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)
        callee_comm = await create_authenticated_communicator(callee)

        await caller_comm.connect()
        await callee_comm.connect()

        await caller_comm.receive_json_from()
        await callee_comm.receive_json_from()

        test_sdp = {
            "type": "offer",
            "sdp": "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\n...",
        }

        await caller_comm.send_json_to({
            "type": "offer",
            "target_user_id": "400",
            "sdp": test_sdp,
        })

        # Callee should receive the offer
        response = await callee_comm.receive_json_from()
        assert response["type"] == "offer"
        assert response["caller_id"] == "300"
        assert response["sdp"] == test_sdp

        await caller_comm.disconnect()
        await callee_comm.disconnect()

    async def test_answer_forwarded_to_caller(self):
        """SDP answer is forwarded to caller."""
        caller = MockUser(pk=500, is_authenticated=True)
        callee = MockUser(pk=600, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)
        callee_comm = await create_authenticated_communicator(callee)

        await caller_comm.connect()
        await callee_comm.connect()

        await caller_comm.receive_json_from()
        await callee_comm.receive_json_from()

        test_sdp = {
            "type": "answer",
            "sdp": "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\n...",
        }

        await callee_comm.send_json_to({
            "type": "answer",
            "target_user_id": "500",
            "sdp": test_sdp,
        })

        # Caller should receive the answer
        response = await caller_comm.receive_json_from()
        assert response["type"] == "answer"
        assert response["answerer_id"] == "600"
        assert response["sdp"] == test_sdp

        await caller_comm.disconnect()
        await callee_comm.disconnect()


# =============================================================================
# ICE Candidate Tests
# =============================================================================


@pytest.mark.asyncio
class TestICECandidateExchange:
    """Tests for ICE candidate exchange."""

    async def test_ice_candidate_forwarded(self):
        """ICE candidate is forwarded to peer."""
        peer1 = MockUser(pk=700, is_authenticated=True)
        peer2 = MockUser(pk=800, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        peer1_comm = await create_authenticated_communicator(peer1)
        peer2_comm = await create_authenticated_communicator(peer2)

        await peer1_comm.connect()
        await peer2_comm.connect()

        await peer1_comm.receive_json_from()
        await peer2_comm.receive_json_from()

        test_candidate = {
            "candidate": "candidate:1 1 UDP 2013266431 192.168.1.1 12345 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0,
        }

        await peer1_comm.send_json_to({
            "type": "ice_candidate",
            "target_user_id": "800",
            "candidate": test_candidate,
        })

        # Peer2 should receive the ICE candidate
        response = await peer2_comm.receive_json_from()
        assert response["type"] == "ice_candidate"
        assert response["sender_id"] == "700"
        assert response["candidate"] == test_candidate

        await peer1_comm.disconnect()
        await peer2_comm.disconnect()


# =============================================================================
# Call End Tests
# =============================================================================


@pytest.mark.asyncio
class TestCallEnd:
    """Tests for ending/rejecting calls."""

    async def test_hangup_notifies_peer(self):
        """Hangup message is forwarded to peer."""
        caller = MockUser(pk=900, is_authenticated=True)
        callee = MockUser(pk=1000, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)
        callee_comm = await create_authenticated_communicator(callee)

        await caller_comm.connect()
        await callee_comm.connect()

        await caller_comm.receive_json_from()
        await callee_comm.receive_json_from()

        await caller_comm.send_json_to({
            "type": "hangup",
            "target_user_id": "1000",
        })

        # Callee should receive hangup notification
        response = await callee_comm.receive_json_from()
        assert response["type"] == "hangup"
        assert response["ended_by"] == "900"

        await caller_comm.disconnect()
        await callee_comm.disconnect()

    async def test_reject_notifies_caller(self):
        """Reject message is forwarded to caller."""
        caller = MockUser(pk=1100, is_authenticated=True)
        callee = MockUser(pk=1200, is_authenticated=True)

        WebRTCConsumer.connected_users.clear()

        caller_comm = await create_authenticated_communicator(caller)
        callee_comm = await create_authenticated_communicator(callee)

        await caller_comm.connect()
        await callee_comm.connect()

        await caller_comm.receive_json_from()
        await callee_comm.receive_json_from()

        await callee_comm.send_json_to({
            "type": "reject",
            "target_user_id": "1100",
        })

        # Caller should receive rejection notification
        response = await caller_comm.receive_json_from()
        assert response["type"] == "rejected"
        assert response["rejected_by"] == "1200"

        await caller_comm.disconnect()
        await callee_comm.disconnect()
