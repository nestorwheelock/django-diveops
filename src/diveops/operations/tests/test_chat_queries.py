"""Tests for chat query services.

These tests verify:
1. Query count optimization (no N+1 queries)
2. Correct annotations and filtering
3. Cursor pagination behavior
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test.utils import CaptureQueriesContext
from django.db import connection

from django_parties.models import Person
from django_communication.models import (
    Conversation,
    ConversationStatus,
    Message,
    MessageDirection,
    MessageStatus,
)

from diveops.operations.services.chat_queries import (
    ConversationQueryService,
    MessageQueryService,
)


@pytest.fixture
def person(db):
    """Create a test person."""
    return Person.objects.create(
        first_name="Test",
        last_name="Lead",
        email="test@example.com",
        lead_status="new",
    )


@pytest.fixture
def person_ct(db):
    """Get ContentType for Person."""
    return ContentType.objects.get_for_model(Person)


@pytest.fixture
def conversation(db, person, person_ct):
    """Create a test conversation linked to person."""
    return Conversation.objects.create(
        subject="Test Conversation",
        related_content_type=person_ct,
        related_object_id=str(person.pk),
        status=ConversationStatus.ACTIVE,
    )


@pytest.fixture
def messages(db, conversation, person):
    """Create test messages in conversation."""
    msgs = []
    for i in range(10):
        direction = MessageDirection.INBOUND if i % 2 == 0 else MessageDirection.OUTBOUND
        msgs.append(
            Message.objects.create(
                conversation=conversation,
                sender_person=person if direction == MessageDirection.INBOUND else None,
                direction=direction,
                body_text=f"Test message {i}",
                status=MessageStatus.SENT,
            )
        )
    return msgs


@pytest.fixture
def multiple_conversations(db, person_ct):
    """Create multiple conversations with messages for N+1 testing."""
    conversations = []
    for i in range(5):
        person = Person.objects.create(
            first_name=f"Person{i}",
            last_name="Test",
            email=f"person{i}@example.com",
            lead_status="new",
        )
        conv = Conversation.objects.create(
            subject=f"Conversation {i}",
            related_content_type=person_ct,
            related_object_id=str(person.pk),
            status=ConversationStatus.ACTIVE,
        )
        # Create 3 messages per conversation
        for j in range(3):
            Message.objects.create(
                conversation=conv,
                sender_person=person,
                direction=MessageDirection.INBOUND,
                body_text=f"Message {j} in conv {i}",
                status=MessageStatus.SENT,
            )
        conversations.append(conv)
    return conversations


# =============================================================================
# ConversationQueryService.list_for_leads Tests
# =============================================================================


@pytest.mark.django_db
class TestConversationListForLeads:
    """Tests for ConversationQueryService.list_for_leads."""

    def test_returns_conversations_with_annotations(self, multiple_conversations):
        """Returns conversations with last_message annotations."""
        result = list(ConversationQueryService.list_for_leads(limit=10))

        assert len(result) == 5
        for conv in result:
            # Check annotations exist
            assert hasattr(conv, "last_message_preview")
            assert hasattr(conv, "last_message_at_annotated")
            assert hasattr(conv, "last_message_direction")

    def test_no_n_plus_one_queries(self, multiple_conversations):
        """Query count should be O(1), not O(n)."""
        # Warm up ContentType cache
        ContentType.objects.get_for_model(Person)

        with CaptureQueriesContext(connection) as context:
            result = list(ConversationQueryService.list_for_leads(limit=10))
            # Access annotations to ensure they don't trigger additional queries
            for conv in result:
                _ = conv.last_message_preview
                _ = conv.last_message_at_annotated
                _ = conv.last_message_direction

        # Should be a single query (plus ContentType lookup if not cached)
        # The key is that it's constant regardless of N conversations
        assert len(context) <= 3, f"Too many queries: {len(context)}"

    def test_filters_by_status_active(self, person_ct, db):
        """Filters conversations by active status."""
        # Create active and closed conversations
        p1 = Person.objects.create(first_name="A", email="a@test.com", lead_status="new")
        p2 = Person.objects.create(first_name="B", email="b@test.com", lead_status="new")

        active = Conversation.objects.create(
            subject="Active",
            related_content_type=person_ct,
            related_object_id=str(p1.pk),
            status=ConversationStatus.ACTIVE,
        )
        closed = Conversation.objects.create(
            subject="Closed",
            related_content_type=person_ct,
            related_object_id=str(p2.pk),
            status=ConversationStatus.CLOSED,
        )

        result = list(ConversationQueryService.list_for_leads(status="active"))

        conv_ids = [c.pk for c in result]
        assert active.pk in conv_ids
        assert closed.pk not in conv_ids

    def test_limit_parameter(self, multiple_conversations):
        """Respects limit parameter."""
        result = list(ConversationQueryService.list_for_leads(limit=2))
        assert len(result) == 2


# =============================================================================
# MessageQueryService.get_messages Tests
# =============================================================================


@pytest.mark.django_db
class TestMessageQueryServiceGetMessages:
    """Tests for MessageQueryService.get_messages."""

    def test_returns_messages_in_chronological_order(self, conversation, messages):
        """Returns messages in chronological order."""
        result = list(MessageQueryService.get_messages(conversation, limit=50))

        assert len(result) == 10
        # Verify chronological order
        for i in range(1, len(result)):
            assert result[i].created_at >= result[i - 1].created_at

    def test_respects_limit(self, conversation, messages):
        """Returns limited number of messages."""
        result = list(MessageQueryService.get_messages(conversation, limit=5))
        assert len(result) == 5

    def test_cursor_pagination_before(self, conversation, messages):
        """Filters messages before cursor timestamp."""
        # Get middle message timestamp
        middle_msg = messages[5]

        result = list(
            MessageQueryService.get_messages(
                conversation, limit=50, before=middle_msg.created_at
            )
        )

        # All results should be before the cursor
        for msg in result:
            assert msg.created_at < middle_msg.created_at


# =============================================================================
# MessageQueryService.get_messages_for_lead Tests
# =============================================================================


@pytest.mark.django_db
class TestMessageQueryServiceGetMessagesForLead:
    """Tests for MessageQueryService.get_messages_for_lead."""

    def test_returns_conversation_and_messages(self, person, conversation, messages):
        """Returns both conversation and messages."""
        conv, msgs = MessageQueryService.get_messages_for_lead(
            person_id=str(person.pk), limit=50
        )

        assert conv is not None
        assert conv.pk == conversation.pk
        assert len(list(msgs)) == 10

    def test_returns_none_for_nonexistent_person(self, db):
        """Returns None for person without conversation."""
        conv, msgs = MessageQueryService.get_messages_for_lead(
            person_id="00000000-0000-0000-0000-000000000000", limit=50
        )

        assert conv is None
        assert len(list(msgs)) == 0


# =============================================================================
# MessageQueryService.mark_inbound_read Tests
# =============================================================================


@pytest.mark.django_db
class TestMessageQueryServiceMarkInboundRead:
    """Tests for MessageQueryService.mark_inbound_read."""

    def test_marks_inbound_messages_as_read(self, conversation, messages):
        """Marks all inbound messages as read."""
        # Count inbound messages before
        inbound_before = Message.objects.filter(
            conversation=conversation,
            direction=MessageDirection.INBOUND,
            status__in=[
                MessageStatus.QUEUED,
                MessageStatus.SENDING,
                MessageStatus.SENT,
                MessageStatus.DELIVERED,
            ],
        ).count()

        updated = MessageQueryService.mark_inbound_read(conversation)

        # Check count matches
        assert updated == inbound_before

        # Verify all inbound are now read
        inbound_not_read = Message.objects.filter(
            conversation=conversation,
            direction=MessageDirection.INBOUND,
        ).exclude(status=MessageStatus.READ).count()

        assert inbound_not_read == 0

    def test_does_not_affect_outbound_messages(self, conversation, messages):
        """Does not change outbound message status."""
        # Get outbound statuses before
        outbound_before = list(
            Message.objects.filter(
                conversation=conversation,
                direction=MessageDirection.OUTBOUND,
            ).values_list("pk", "status")
        )

        MessageQueryService.mark_inbound_read(conversation)

        # Verify outbound unchanged
        for pk, status in outbound_before:
            msg = Message.objects.get(pk=pk)
            assert msg.status == status
