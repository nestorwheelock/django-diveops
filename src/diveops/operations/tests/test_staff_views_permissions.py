"""Permission tests for staff views.

Tests that all staff POST endpoints:
1. Require authentication (anonymous users redirected to login)
2. Require staff status (non-staff users get 403)
3. Allow staff users access
"""

import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone


@pytest.fixture
def anonymous_client(client):
    """Return an unauthenticated client."""
    return client


@pytest.fixture
def regular_user(db):
    """Create a regular (non-staff) user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="testpass123",
        is_staff=False,
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def dive_shop(db):
    """Create a dive shop organization."""
    from django_parties.models import Organization
    return Organization.objects.create(
        name="Test Dive Shop",
        org_type="dive_shop",
    )


@pytest.fixture
def person(db):
    """Create a person for the diver."""
    from django_parties.models import Person
    return Person.objects.create(
        first_name="Test",
        last_name="Diver",
        email="diver@example.com",
    )


@pytest.fixture
def diver(person):
    """Create a diver profile."""
    from diveops.operations.models import DiverProfile
    return DiverProfile.objects.create(person=person)


@pytest.fixture
def excursion_type(db):
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
def excursion(dive_shop, excursion_type):
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
def booking(excursion, diver, staff_user):
    """Create a confirmed booking."""
    from diveops.operations.models import Booking
    return Booking.objects.create(
        excursion=excursion,
        diver=diver,
        status="confirmed",
        booked_by=staff_user,
    )


@pytest.fixture
def dive_site(dive_shop):
    """Create a dive site."""
    from diveops.operations.models import DiveSite
    return DiveSite.objects.create(
        name="Test Reef",
        dive_shop=dive_shop,
        max_depth_m=30,
    )


@pytest.fixture
def certification_level(db):
    """Create a certification level."""
    from diveops.operations.models import CertificationLevel
    return CertificationLevel.objects.create(
        name="Open Water",
        agency="PADI",
        level=1,
    )


@pytest.fixture
def certification(diver, certification_level, staff_user):
    """Create a diver certification."""
    from diveops.operations.models import DiverCertification
    return DiverCertification.objects.create(
        diver=diver,
        certification=certification_level,
        certification_number="12345",
        certification_date=timezone.now().date(),
        added_by=staff_user,
    )


# =============================================================================
# CheckInView Tests
# =============================================================================


@pytest.mark.django_db
class TestCheckInViewPermissions:
    """Permission tests for CheckInView."""

    def test_anonymous_redirected_to_login(self, anonymous_client, booking):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:check-in", kwargs={"pk": booking.pk})
        response = anonymous_client.post(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user, booking):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:check-in", kwargs={"pk": booking.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user, booking):
        """Staff users can check in."""
        client.force_login(staff_user)
        url = reverse("diveops:check-in", kwargs={"pk": booking.pk})
        response = client.post(url)
        # Should redirect to excursion detail on success
        assert response.status_code == 302
        assert "excursion" in response.url


# =============================================================================
# StartExcursionView Tests
# =============================================================================


@pytest.mark.django_db
class TestStartExcursionViewPermissions:
    """Permission tests for StartExcursionView."""

    def test_anonymous_redirected_to_login(self, anonymous_client, excursion):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:start-excursion", kwargs={"pk": excursion.pk})
        response = anonymous_client.post(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user, excursion):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:start-excursion", kwargs={"pk": excursion.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user, excursion):
        """Staff users can start excursion."""
        client.force_login(staff_user)
        url = reverse("diveops:start-excursion", kwargs={"pk": excursion.pk})
        response = client.post(url)
        # Should redirect to excursion detail on success
        assert response.status_code == 302


# =============================================================================
# CompleteExcursionView Tests
# =============================================================================


@pytest.mark.django_db
class TestCompleteExcursionViewPermissions:
    """Permission tests for CompleteExcursionView."""

    @pytest.fixture
    def in_progress_excursion(self, excursion):
        """Create an in-progress excursion."""
        excursion.status = "in_progress"
        excursion.save()
        return excursion

    def test_anonymous_redirected_to_login(self, anonymous_client, in_progress_excursion):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:complete-excursion", kwargs={"pk": in_progress_excursion.pk})
        response = anonymous_client.post(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user, in_progress_excursion):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:complete-excursion", kwargs={"pk": in_progress_excursion.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user, in_progress_excursion):
        """Staff users can complete excursion."""
        client.force_login(staff_user)
        url = reverse("diveops:complete-excursion", kwargs={"pk": in_progress_excursion.pk})
        response = client.post(url)
        # Should redirect to excursion detail on success
        assert response.status_code == 302


# =============================================================================
# DiverListView Tests
# =============================================================================


@pytest.mark.django_db
class TestDiverListViewPermissions:
    """Permission tests for DiverListView."""

    def test_anonymous_redirected_to_login(self, anonymous_client):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:diver-list")
        response = anonymous_client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:diver-list")
        response = client.get(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user):
        """Staff users can view diver list."""
        client.force_login(staff_user)
        url = reverse("diveops:diver-list")
        response = client.get(url)
        assert response.status_code == 200


# =============================================================================
# ExcursionListView Tests
# =============================================================================


@pytest.mark.django_db
class TestExcursionListViewPermissions:
    """Permission tests for ExcursionListView."""

    def test_anonymous_redirected_to_login(self, anonymous_client):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:excursion-list")
        response = anonymous_client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:excursion-list")
        response = client.get(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user):
        """Staff users can view excursion list."""
        client.force_login(staff_user)
        url = reverse("diveops:excursion-list")
        response = client.get(url)
        assert response.status_code == 200


# =============================================================================
# DiveSiteListView Tests
# =============================================================================


@pytest.mark.django_db
class TestDiveSiteListViewPermissions:
    """Permission tests for DiveSiteListView."""

    def test_anonymous_redirected_to_login(self, anonymous_client):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:dive-site-list")
        response = anonymous_client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:dive-site-list")
        response = client.get(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user):
        """Staff users can view dive site list."""
        client.force_login(staff_user)
        url = reverse("diveops:dive-site-list")
        response = client.get(url)
        assert response.status_code == 200


# =============================================================================
# DashboardView Tests
# =============================================================================


@pytest.mark.django_db
class TestDashboardViewPermissions:
    """Permission tests for DashboardView."""

    def test_anonymous_redirected_to_login(self, anonymous_client):
        """Anonymous users are redirected to login."""
        url = reverse("diveops:dashboard")
        response = anonymous_client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url or "/accounts/login/" in response.url

    def test_non_staff_forbidden(self, client, regular_user):
        """Non-staff users get 403."""
        client.force_login(regular_user)
        url = reverse("diveops:dashboard")
        response = client.get(url)
        assert response.status_code == 403

    def test_staff_allowed(self, client, staff_user):
        """Staff users can view dashboard."""
        client.force_login(staff_user)
        url = reverse("diveops:dashboard")
        response = client.get(url)
        assert response.status_code == 200


# =============================================================================
# Method Safety Tests (GET-only views reject POST)
# =============================================================================


@pytest.mark.django_db
class TestMethodSafety:
    """Test that read-only views reject unsafe methods."""

    def test_diver_list_rejects_post(self, client, staff_user):
        """DiverListView rejects POST requests."""
        client.force_login(staff_user)
        url = reverse("diveops:diver-list")
        response = client.post(url)
        assert response.status_code == 405

    def test_excursion_list_rejects_post(self, client, staff_user):
        """ExcursionListView rejects POST requests."""
        client.force_login(staff_user)
        url = reverse("diveops:excursion-list")
        response = client.post(url)
        assert response.status_code == 405

    def test_dashboard_rejects_post(self, client, staff_user):
        """DashboardView rejects POST requests."""
        client.force_login(staff_user)
        url = reverse("diveops:dashboard")
        response = client.post(url)
        assert response.status_code == 405


# =============================================================================
# POST-only views reject GET
# =============================================================================


@pytest.mark.django_db
class TestPOSTOnlyViews:
    """Test that POST-only views reject GET requests."""

    def test_check_in_rejects_get(self, client, staff_user, booking):
        """CheckInView rejects GET requests."""
        client.force_login(staff_user)
        url = reverse("diveops:check-in", kwargs={"pk": booking.pk})
        response = client.get(url)
        assert response.status_code == 405

    def test_start_excursion_rejects_get(self, client, staff_user, excursion):
        """StartExcursionView rejects GET requests."""
        client.force_login(staff_user)
        url = reverse("diveops:start-excursion", kwargs={"pk": excursion.pk})
        response = client.get(url)
        assert response.status_code == 405

    def test_complete_excursion_rejects_get(self, client, staff_user, excursion):
        """CompleteExcursionView rejects GET requests."""
        client.force_login(staff_user)
        url = reverse("diveops:complete-excursion", kwargs={"pk": excursion.pk})
        response = client.get(url)
        assert response.status_code == 405
