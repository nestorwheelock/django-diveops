"""Tests for booking flow services.

Tests for book_excursion, cancel_booking, and related booking operations.
"""

import pytest
from decimal import Decimal

from django.utils import timezone


@pytest.mark.django_db
class TestBookExcursion:
    """Tests for book_excursion service."""

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
        return DiverProfile.objects.create(person=person)

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
        """Create an excursion with capacity."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    def test_creates_booking(self, excursion, diver, user):
        """book_excursion creates a confirmed booking."""
        from diveops.operations._services import book_excursion
        from diveops.operations.models import Booking

        booking = book_excursion(
            excursion, diver, user, skip_eligibility_check=True
        )

        assert booking is not None
        assert booking.excursion == excursion
        assert booking.diver == diver
        assert booking.status == "confirmed"
        assert booking.booked_by == user
        assert Booking.objects.count() == 1

    def test_rejects_duplicate_booking(self, excursion, diver, user):
        """Cannot book same diver twice on same excursion."""
        from diveops.operations._services import book_excursion
        from diveops.operations.exceptions import BookingError

        book_excursion(excursion, diver, user, skip_eligibility_check=True)

        with pytest.raises(BookingError, match="already has an active booking"):
            book_excursion(excursion, diver, user, skip_eligibility_check=True)

    def test_allows_rebooking_after_cancellation(self, excursion, diver, user):
        """Can book again after cancellation."""
        from diveops.operations._services import book_excursion, cancel_booking
        from diveops.operations.models import Booking

        booking1 = book_excursion(excursion, diver, user, skip_eligibility_check=True)
        cancel_booking(booking1, user)

        booking2 = book_excursion(excursion, diver, user, skip_eligibility_check=True)

        assert booking2.pk != booking1.pk
        assert booking2.status == "confirmed"
        assert Booking.objects.filter(status="confirmed").count() == 1


@pytest.mark.django_db
class TestCancelBooking:
    """Tests for cancel_booking service."""

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
        return DiverProfile.objects.create(person=person)

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

    def test_cancels_booking(self, booking, user):
        """cancel_booking sets status to cancelled."""
        from diveops.operations._services import cancel_booking

        result = cancel_booking(booking, user)

        booking.refresh_from_db()
        assert booking.status == "cancelled"
        assert booking.cancelled_at is not None
        assert result.booking == booking

    def test_rejects_already_cancelled(self, booking, user):
        """Cannot cancel an already cancelled booking."""
        from diveops.operations._services import cancel_booking
        from diveops.operations.exceptions import BookingError

        cancel_booking(booking, user)

        with pytest.raises(BookingError, match="already cancelled"):
            cancel_booking(booking, user)

    def test_rejects_checked_in_booking(self, booking, user):
        """Cannot cancel a checked-in booking."""
        from diveops.operations._services import cancel_booking
        from diveops.operations.exceptions import BookingError

        booking.status = "checked_in"
        booking.save()

        with pytest.raises(BookingError, match="checked-in booking"):
            cancel_booking(booking, user)


@pytest.mark.django_db
class TestStartExcursion:
    """Tests for start_excursion service."""

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
        """Create a scheduled excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=12,
            status="scheduled",
        )

    def test_starts_excursion(self, excursion, user):
        """start_excursion transitions to in_progress."""
        from diveops.operations._services import start_excursion

        result = start_excursion(excursion, user)

        excursion.refresh_from_db()
        assert excursion.status == "in_progress"
        assert result == excursion


@pytest.mark.django_db
class TestCompleteExcursion:
    """Tests for complete_excursion service."""

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
    def in_progress_excursion(self, dive_shop, excursion_type):
        """Create an in-progress excursion."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() - timezone.timedelta(hours=2),
            capacity=12,
            status="in_progress",
        )

    def test_completes_excursion(self, in_progress_excursion, user):
        """complete_excursion transitions to completed."""
        from diveops.operations._services import complete_excursion

        result = complete_excursion(in_progress_excursion, user)

        in_progress_excursion.refresh_from_db()
        assert in_progress_excursion.status == "completed"
        assert result == in_progress_excursion


@pytest.mark.django_db(transaction=True)
class TestBookingConcurrency:
    """Concurrency tests for booking services."""

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
        return DiverProfile.objects.create(person=person)

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
        """Create an excursion with limited capacity."""
        from diveops.operations.models import Excursion
        return Excursion.objects.create(
            dive_shop=dive_shop,
            excursion_type=excursion_type,
            departure_time=timezone.now() + timezone.timedelta(days=1),
            capacity=1,  # Only 1 spot
            status="scheduled",
        )

    def test_concurrent_bookings_only_one_succeeds(self, excursion, diver, user):
        """Two concurrent booking attempts for same diver should only create one.

        The select_for_update() lock prevents duplicates.
        """
        from diveops.operations._services import book_excursion
        from diveops.operations.models import Booking
        from diveops.operations.exceptions import BookingError
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        results = []
        errors = []
        barrier = threading.Barrier(2)

        def attempt_booking():
            try:
                barrier.wait(timeout=5)
                result = book_excursion(
                    excursion, diver, user, skip_eligibility_check=True
                )
                results.append(result)
            except BookingError as e:
                errors.append(e)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(attempt_booking) for _ in range(2)]
            for future in as_completed(futures):
                pass

        # One should succeed, one should fail with BookingError
        assert len(results) == 1
        assert len(errors) == 1
        assert "already has an active booking" in str(errors[0])
        # Only one booking should exist
        assert Booking.objects.filter(status="confirmed").count() == 1
