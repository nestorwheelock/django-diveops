"""Tests for settlement services.

Tests for create_revenue_settlement and create_refund_settlement,
including concurrency/race condition tests.
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.db import connection, transaction
from django.utils import timezone


@pytest.mark.django_db
class TestCreateRevenueSettlement:
    """Tests for create_revenue_settlement service."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="teststaff",
            email="teststaff@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def dive_shop(self):
        """Create a dive shop organization."""
        from django_parties.models import Organization
        return Organization.objects.create(
            name="Test Dive Shop",
            org_type="dive_shop",
        )

    @pytest.fixture
    def person(self):
        """Create a person for the diver."""
        from django_parties.models import Person
        return Person.objects.create(
            first_name="Test",
            last_name="Diver",
            email="diver@example.com",
        )

    @pytest.fixture
    def diver(self, person):
        """Create a diver profile."""
        from diveops.operations.models import DiverProfile
        return DiverProfile.objects.create(
            person=person,
        )

    @pytest.fixture
    def excursion_type(self):
        """Create an excursion type."""
        from diveops.operations.models import ExcursionType
        return ExcursionType.objects.create(
            name="Morning 2-Tank",
            slug="morning-2-tank",
            dive_mode="boat",
            time_of_day="day",
            base_price=Decimal("150.00"),
        )

    @pytest.fixture
    def excursion(self, dive_shop, excursion_type):
        """Create an excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    @pytest.fixture
    def booking(self, excursion, diver, user):
        """Create a booking with price snapshot."""
        from diveops.operations.models import Booking
        return Booking.objects.create(
            excursion=excursion,
            diver=diver,
            status="confirmed",
            booked_by=user,
            price_amount=Decimal("150.00"),
            price_currency="USD",
            price_snapshot={"amount": "150.00", "currency": "USD"},
        )

    def test_creates_settlement_record(self, booking, user):
        """create_revenue_settlement creates a SettlementRecord."""
        from diveops.operations._services import create_revenue_settlement
        from diveops.operations.models import SettlementRecord

        settlement = create_revenue_settlement(booking, processed_by=user)

        assert settlement is not None
        assert settlement.booking == booking
        assert settlement.settlement_type == "revenue"
        assert settlement.amount == Decimal("150.00")
        assert settlement.processed_by == user
        assert SettlementRecord.objects.count() == 1

    def test_idempotent_returns_existing(self, booking, user):
        """Calling twice returns existing settlement (idempotent)."""
        from diveops.operations._services import create_revenue_settlement

        settlement1 = create_revenue_settlement(booking, processed_by=user)
        settlement2 = create_revenue_settlement(booking, processed_by=user)

        assert settlement1.pk == settlement2.pk

    def test_rejects_cancelled_booking(self, booking, user):
        """Cannot settle a cancelled booking."""
        from diveops.operations._services import create_revenue_settlement

        booking.status = "cancelled"
        booking.save()

        with pytest.raises(ValueError, match="booking is cancelled"):
            create_revenue_settlement(booking, processed_by=user)

    def test_rejects_booking_without_price(self, booking, user):
        """Cannot settle a booking without price_amount."""
        from diveops.operations._services import create_revenue_settlement

        booking.price_amount = None
        booking.save()

        with pytest.raises(ValueError, match="no price_amount"):
            create_revenue_settlement(booking, processed_by=user)


@pytest.mark.django_db
class TestCreateRefundSettlement:
    """Tests for create_refund_settlement service."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="teststaff",
            email="teststaff@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def dive_shop(self):
        """Create a dive shop organization."""
        from django_parties.models import Organization
        return Organization.objects.create(
            name="Test Dive Shop",
            org_type="dive_shop",
        )

    @pytest.fixture
    def person(self):
        """Create a person for the diver."""
        from django_parties.models import Person
        return Person.objects.create(
            first_name="Test",
            last_name="Diver",
            email="diver@example.com",
        )

    @pytest.fixture
    def diver(self, person):
        """Create a diver profile."""
        from diveops.operations.models import DiverProfile
        return DiverProfile.objects.create(
            person=person,
        )

    @pytest.fixture
    def excursion_type(self):
        """Create an excursion type."""
        from diveops.operations.models import ExcursionType
        return ExcursionType.objects.create(
            name="Morning 2-Tank",
            slug="morning-2-tank",
            dive_mode="boat",
            time_of_day="day",
            base_price=Decimal("150.00"),
        )

    @pytest.fixture
    def excursion(self, dive_shop, excursion_type):
        """Create an excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    @pytest.fixture
    def cancelled_booking(self, excursion, diver, user):
        """Create a cancelled booking with price snapshot."""
        from diveops.operations.models import Booking
        return Booking.objects.create(
            excursion=excursion,
            diver=diver,
            status="cancelled",
            booked_by=user,
            price_amount=Decimal("150.00"),
            price_currency="USD",
            price_snapshot={"amount": "150.00", "currency": "USD"},
            cancelled_at=timezone.now(),
        )

    @pytest.fixture
    def refund_decision(self):
        """Create a refund decision."""
        from diveops.operations.cancellation_policy import RefundDecision
        return RefundDecision(
            refund_amount=Decimal("150.00"),
            refund_percent=100,
            original_amount=Decimal("150.00"),
            currency="USD",
            reason="Full refund - cancelled in time",
        )

    def test_creates_refund_settlement(self, cancelled_booking, refund_decision, user):
        """create_refund_settlement creates a SettlementRecord."""
        from diveops.operations._services import create_refund_settlement
        from diveops.operations.models import SettlementRecord

        settlement = create_refund_settlement(
            cancelled_booking, refund_decision, processed_by=user
        )

        assert settlement is not None
        assert settlement.booking == cancelled_booking
        assert settlement.settlement_type == "refund"
        assert settlement.amount == Decimal("150.00")
        assert SettlementRecord.objects.count() == 1

    def test_idempotent_returns_existing(self, cancelled_booking, refund_decision, user):
        """Calling twice returns existing refund settlement."""
        from diveops.operations._services import create_refund_settlement

        settlement1 = create_refund_settlement(
            cancelled_booking, refund_decision, processed_by=user
        )
        settlement2 = create_refund_settlement(
            cancelled_booking, refund_decision, processed_by=user
        )

        assert settlement1.pk == settlement2.pk

    def test_returns_none_for_zero_refund(self, cancelled_booking, user):
        """Returns None when refund amount is zero."""
        from diveops.operations._services import create_refund_settlement
        from diveops.operations.cancellation_policy import RefundDecision

        zero_refund = RefundDecision(
            refund_amount=Decimal("0.00"),
            refund_percent=0,
            original_amount=Decimal("150.00"),
            currency="USD",
            reason="No refund - cancelled too late",
        )

        result = create_refund_settlement(
            cancelled_booking, zero_refund, processed_by=user
        )

        assert result is None

    def test_rejects_non_cancelled_booking(self, cancelled_booking, refund_decision, user):
        """Cannot refund a non-cancelled booking."""
        from diveops.operations._services import create_refund_settlement

        cancelled_booking.status = "confirmed"
        cancelled_booking.save()

        with pytest.raises(ValueError, match="not cancelled"):
            create_refund_settlement(
                cancelled_booking, refund_decision, processed_by=user
            )


@pytest.mark.django_db
class TestCheckIn:
    """Tests for check_in service."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="teststaff",
            email="teststaff@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def dive_shop(self):
        """Create a dive shop organization."""
        from django_parties.models import Organization
        return Organization.objects.create(
            name="Test Dive Shop",
            org_type="dive_shop",
        )

    @pytest.fixture
    def person(self):
        """Create a person for the diver."""
        from django_parties.models import Person
        return Person.objects.create(
            first_name="Test",
            last_name="Diver",
            email="diver@example.com",
        )

    @pytest.fixture
    def diver(self, person):
        """Create a diver profile."""
        from diveops.operations.models import DiverProfile
        return DiverProfile.objects.create(
            person=person,
        )

    @pytest.fixture
    def excursion_type(self):
        """Create an excursion type."""
        from diveops.operations.models import ExcursionType
        return ExcursionType.objects.create(
            name="Morning 2-Tank",
            slug="morning-2-tank",
            dive_mode="boat",
            time_of_day="day",
            base_price=Decimal("150.00"),
        )

    @pytest.fixture
    def excursion(self, dive_shop, excursion_type):
        """Create an excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    @pytest.fixture
    def booking(self, excursion, diver, user):
        """Create a confirmed booking."""
        from diveops.operations.models import Booking
        return Booking.objects.create(
            excursion=excursion,
            diver=diver,
            status="confirmed",
            booked_by=user,
        )

    def test_creates_roster_entry(self, booking, user):
        """check_in creates a roster entry."""
        from diveops.operations._services import check_in
        from diveops.operations.models import ExcursionRoster

        roster = check_in(booking, checked_in_by=user)

        assert roster is not None
        assert roster.diver == booking.diver
        assert roster.excursion == booking.excursion
        assert roster.booking == booking
        assert ExcursionRoster.objects.count() == 1

    def test_updates_booking_status(self, booking, user):
        """check_in updates booking status to checked_in."""
        from diveops.operations._services import check_in

        check_in(booking, checked_in_by=user)
        booking.refresh_from_db()

        assert booking.status == "checked_in"

    def test_rejects_cancelled_booking(self, booking, user):
        """Cannot check in a cancelled booking."""
        from diveops.operations._services import check_in
        from diveops.operations.exceptions import CheckInError

        booking.status = "cancelled"
        booking.save()

        with pytest.raises(CheckInError, match="cancelled booking"):
            check_in(booking, checked_in_by=user)

    def test_rejects_already_checked_in(self, booking, user):
        """Cannot check in twice."""
        from diveops.operations._services import check_in
        from diveops.operations.exceptions import CheckInError

        check_in(booking, checked_in_by=user)

        with pytest.raises(CheckInError, match="already checked in"):
            check_in(booking, checked_in_by=user)

    def test_rejects_without_waiver_when_required(self, booking, user):
        """Rejects check-in when waiver required but not signed."""
        from diveops.operations._services import check_in
        from diveops.operations.exceptions import CheckInError

        with pytest.raises(CheckInError, match="Waiver agreement"):
            check_in(booking, checked_in_by=user, require_waiver=True)


@pytest.mark.django_db(transaction=True)
class TestSettlementConcurrency:
    """Concurrency tests for settlement services.

    Uses database transaction isolation to test race conditions.
    """

    @pytest.fixture
    def user(self):
        """Create a test user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username="teststaff",
            email="teststaff@example.com",
            password="testpass123",
        )

    @pytest.fixture
    def dive_shop(self):
        """Create a dive shop organization."""
        from django_parties.models import Organization
        return Organization.objects.create(
            name="Test Dive Shop",
            org_type="dive_shop",
        )

    @pytest.fixture
    def person(self):
        """Create a person for the diver."""
        from django_parties.models import Person
        return Person.objects.create(
            first_name="Test",
            last_name="Diver",
            email="diver@example.com",
        )

    @pytest.fixture
    def diver(self, person):
        """Create a diver profile."""
        from diveops.operations.models import DiverProfile
        return DiverProfile.objects.create(
            person=person,
        )

    @pytest.fixture
    def excursion_type(self):
        """Create an excursion type."""
        from diveops.operations.models import ExcursionType
        return ExcursionType.objects.create(
            name="Morning 2-Tank",
            slug="morning-2-tank",
            dive_mode="boat",
            time_of_day="day",
            base_price=Decimal("150.00"),
        )

    @pytest.fixture
    def excursion(self, dive_shop, excursion_type):
        """Create an excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    @pytest.fixture
    def booking(self, excursion, diver, user):
        """Create a booking with price snapshot."""
        from diveops.operations.models import Booking
        return Booking.objects.create(
            excursion=excursion,
            diver=diver,
            status="confirmed",
            booked_by=user,
            price_amount=Decimal("150.00"),
            price_currency="USD",
            price_snapshot={"amount": "150.00", "currency": "USD"},
        )

    def test_concurrent_settlements_create_only_one(self, booking, user):
        """Two concurrent settlement calls should only create one record.

        This test verifies that the select_for_update() lock prevents
        duplicate settlements when two requests arrive simultaneously.
        """
        from diveops.operations._services import create_revenue_settlement
        from diveops.operations.models import SettlementRecord
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        results = []
        errors = []
        barrier = threading.Barrier(2)

        def attempt_settlement():
            try:
                barrier.wait(timeout=5)
                result = create_revenue_settlement(booking, processed_by=user)
                results.append(result)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(attempt_settlement) for _ in range(2)]
            for future in as_completed(futures):
                pass

        # Both should succeed (one creates, one returns existing)
        assert len(results) == 2
        assert len(errors) == 0
        # Both should return the same settlement
        assert results[0].pk == results[1].pk
        # Only one record should exist
        assert SettlementRecord.objects.count() == 1
