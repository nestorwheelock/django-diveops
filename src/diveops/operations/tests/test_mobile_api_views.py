"""Tests for mobile API views.

TDD tests for:
- Version check endpoint
- Customer login endpoint
- Customer bookings endpoint
- Location update endpoint
- Location settings endpoint
"""

import json
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from rest_framework.authtoken.models import Token

from django_parties.models import Person

from diveops.operations.models import (
    AppVersion,
    Booking,
    Excursion,
    LocationSharingPreference,
    LocationUpdate,
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    user = User.objects.create_user(
        username="staff@happydiving.mx",
        email="staff@happydiving.mx",
        password="testpass123",
        first_name="Staff",
        last_name="User",
        is_staff=True,
    )
    return user


@pytest.fixture
def customer_user(db):
    """Create a customer (non-staff) user."""
    user = User.objects.create_user(
        username="customer@example.com",
        email="customer@example.com",
        password="testpass123",
        first_name="John",
        last_name="Diver",
        is_staff=False,
    )
    return user


@pytest.fixture
def customer_person(db, customer_user):
    """Create a Person linked to customer user."""
    person = Person.objects.create(
        email=customer_user.email,
        first_name=customer_user.first_name,
        last_name=customer_user.last_name,
        user=customer_user,
    )
    return person


@pytest.fixture
def staff_token(db, staff_user):
    """Create auth token for staff user."""
    token, _ = Token.objects.get_or_create(user=staff_user)
    return token.key


@pytest.fixture
def customer_token(db, customer_user):
    """Create auth token for customer user."""
    token, _ = Token.objects.get_or_create(user=customer_user)
    return token.key


@pytest.fixture
def app_version(db):
    """Create an AppVersion for testing."""
    return AppVersion.objects.create(
        platform="android",
        version_code=2,
        version_name="1.1.0",
        download_url="https://happydiving.mx/static/downloads/diveops.apk",
        is_force_update=False,
        min_supported_version=1,
        release_notes="Bug fixes and improvements",
    )


@pytest.fixture
def force_update_version(db):
    """Create a force-update AppVersion."""
    return AppVersion.objects.create(
        platform="android",
        version_code=3,
        version_name="2.0.0",
        download_url="https://happydiving.mx/static/downloads/diveops.apk",
        is_force_update=True,
        min_supported_version=2,
        release_notes="Major update required",
    )


# =============================================================================
# Version Check Tests
# =============================================================================


class TestVersionCheckView:
    """Tests for GET /api/mobile/version/check/"""

    def test_version_check_no_update_needed(self, api_client, app_version):
        """No update available when current version equals latest."""
        response = api_client.get(
            "/api/mobile/version/check/",
            {"platform": "android", "current_version": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] is False
        assert data["force_update"] is False

    def test_version_check_update_available(self, api_client, app_version):
        """Update available when newer version exists."""
        response = api_client.get(
            "/api/mobile/version/check/",
            {"platform": "android", "current_version": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] is True
        assert data["force_update"] is False
        assert data["latest_version"]["version_code"] == 2
        assert data["latest_version"]["version_name"] == "1.1.0"
        assert "download_url" in data["latest_version"]

    def test_version_check_force_update_required(self, api_client, force_update_version):
        """Force update when version below min_supported_version."""
        response = api_client.get(
            "/api/mobile/version/check/",
            {"platform": "android", "current_version": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] is True
        assert data["force_update"] is True

    def test_version_check_missing_platform(self, api_client):
        """Return error when platform is missing."""
        response = api_client.get(
            "/api/mobile/version/check/",
            {"current_version": 1},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_version_check_no_versions_exist(self, api_client, db):
        """Handle case when no versions exist for platform."""
        response = api_client.get(
            "/api/mobile/version/check/",
            {"platform": "android", "current_version": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["update_available"] is False


# =============================================================================
# Customer Login Tests
# =============================================================================


class TestCustomerLoginView:
    """Tests for POST /api/mobile/customer/login/"""

    def test_customer_login_success(self, api_client, customer_user, customer_person):
        """Customer can login and receives is_staff=False."""
        response = api_client.post(
            "/api/mobile/customer/login/",
            data=json.dumps({
                "email": "customer@example.com",
                "password": "testpass123",
            }),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["is_staff"] is False
        assert data["user"]["email"] == "customer@example.com"
        assert "person_id" in data["user"]

    def test_staff_login_via_customer_endpoint(self, api_client, staff_user):
        """Staff can also login via customer endpoint."""
        # Create Person for staff
        Person.objects.create(
            email=staff_user.email,
            first_name=staff_user.first_name,
            last_name=staff_user.last_name,
            user=staff_user,
        )

        response = api_client.post(
            "/api/mobile/customer/login/",
            data=json.dumps({
                "email": "staff@happydiving.mx",
                "password": "testpass123",
            }),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["is_staff"] is True

    def test_customer_login_invalid_credentials(self, api_client, customer_user):
        """Invalid password returns 401."""
        response = api_client.post(
            "/api/mobile/customer/login/",
            data=json.dumps({
                "email": "customer@example.com",
                "password": "wrongpassword",
            }),
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_customer_login_no_person(self, api_client, customer_user):
        """Login fails if user has no Person record."""
        response = api_client.post(
            "/api/mobile/customer/login/",
            data=json.dumps({
                "email": "customer@example.com",
                "password": "testpass123",
            }),
            content_type="application/json",
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data


# =============================================================================
# Customer Bookings Tests
# =============================================================================


class TestCustomerBookingsView:
    """Tests for GET /api/mobile/customer/bookings/"""

    def test_bookings_requires_auth(self, api_client):
        """Bookings endpoint requires authentication."""
        response = api_client.get("/api/mobile/customer/bookings/")
        assert response.status_code == 401

    def test_bookings_empty_list(self, api_client, customer_token, customer_person):
        """Return empty lists when customer has no bookings."""
        response = api_client.get(
            "/api/mobile/customer/bookings/",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["upcoming"] == []
        assert data["past"] == []

    def test_bookings_with_data(self, api_client, customer_token, customer_person, db):
        """Return bookings categorized by upcoming/past."""
        from diveops.models import DiverProfile, Excursion

        # Create diver profile for customer
        diver = DiverProfile.objects.create(
            person=customer_person,
            date_of_birth=date(1990, 1, 1),
        )

        # Create excursions
        tomorrow = timezone.now().date() + timedelta(days=1)
        yesterday = timezone.now().date() - timedelta(days=1)

        upcoming_excursion = Excursion.objects.create(
            name="Reef Dive Tomorrow",
            departure_date=tomorrow,
            departure_time=time(9, 0),
            capacity=10,
        )
        past_excursion = Excursion.objects.create(
            name="Reef Dive Yesterday",
            departure_date=yesterday,
            departure_time=time(9, 0),
            capacity=10,
        )

        # Create bookings
        Booking.objects.create(
            excursion=upcoming_excursion,
            diver=diver,
            status="confirmed",
        )
        Booking.objects.create(
            excursion=past_excursion,
            diver=diver,
            status="confirmed",
        )

        response = api_client.get(
            "/api/mobile/customer/bookings/",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["upcoming"]) == 1
        assert len(data["past"]) == 1
        assert data["upcoming"][0]["excursion_name"] == "Reef Dive Tomorrow"


# =============================================================================
# Location Update Tests
# =============================================================================


class TestLocationUpdateView:
    """Tests for POST /api/mobile/location/"""

    def test_location_update_requires_auth(self, api_client):
        """Location update requires authentication."""
        response = api_client.post(
            "/api/mobile/location/",
            data=json.dumps({
                "latitude": 20.5,
                "longitude": -87.3,
            }),
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_location_update_success(self, api_client, customer_token, customer_person):
        """Create location update successfully."""
        response = api_client.post(
            "/api/mobile/location/",
            data=json.dumps({
                "latitude": 20.508895,
                "longitude": -87.376305,
                "accuracy_meters": 10.5,
                "altitude_meters": 5.0,
                "source": "gps",
                "recorded_at": timezone.now().isoformat(),
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data

        # Verify in database
        update = LocationUpdate.objects.get(pk=data["id"])
        assert update.person == customer_person
        assert update.latitude == Decimal("20.508895")
        assert update.longitude == Decimal("-87.376305")

    def test_location_update_invalid_coordinates(self, api_client, customer_token, customer_person):
        """Reject invalid coordinates."""
        response = api_client.post(
            "/api/mobile/location/",
            data=json.dumps({
                "latitude": 91.0,  # Invalid: > 90
                "longitude": -87.3,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 400

    def test_location_update_batch(self, api_client, customer_token, customer_person):
        """Accept batch of location updates."""
        now = timezone.now()
        updates = [
            {
                "latitude": 20.508895,
                "longitude": -87.376305,
                "recorded_at": (now - timedelta(minutes=2)).isoformat(),
            },
            {
                "latitude": 20.509000,
                "longitude": -87.376400,
                "recorded_at": (now - timedelta(minutes=1)).isoformat(),
            },
            {
                "latitude": 20.509100,
                "longitude": -87.376500,
                "recorded_at": now.isoformat(),
            },
        ]

        response = api_client.post(
            "/api/mobile/location/batch/",
            data=json.dumps({"updates": updates}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 3


# =============================================================================
# Location Settings Tests
# =============================================================================


class TestLocationSettingsView:
    """Tests for GET/PUT /api/mobile/location/settings/"""

    def test_settings_requires_auth(self, api_client):
        """Settings endpoint requires authentication."""
        response = api_client.get("/api/mobile/location/settings/")
        assert response.status_code == 401

    def test_get_settings_creates_default(self, api_client, customer_token, customer_person):
        """GET creates default preferences if none exist."""
        response = api_client.get(
            "/api/mobile/location/settings/",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["visibility"] == "private"
        assert data["is_tracking_enabled"] is False
        assert data["tracking_interval_seconds"] == 60

        # Verify preference was created
        assert LocationSharingPreference.objects.filter(person=customer_person).exists()

    def test_get_existing_settings(self, api_client, customer_token, customer_person):
        """GET returns existing preferences."""
        LocationSharingPreference.objects.create(
            person=customer_person,
            visibility="staff",
            is_tracking_enabled=True,
            tracking_interval_seconds=30,
        )

        response = api_client.get(
            "/api/mobile/location/settings/",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["visibility"] == "staff"
        assert data["is_tracking_enabled"] is True
        assert data["tracking_interval_seconds"] == 30

    def test_update_settings(self, api_client, customer_token, customer_person):
        """PUT updates location preferences."""
        LocationSharingPreference.objects.create(
            person=customer_person,
            visibility="private",
            is_tracking_enabled=False,
        )

        response = api_client.put(
            "/api/mobile/location/settings/",
            data=json.dumps({
                "visibility": "trip",
                "is_tracking_enabled": True,
                "tracking_interval_seconds": 120,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["visibility"] == "trip"
        assert data["is_tracking_enabled"] is True
        assert data["tracking_interval_seconds"] == 120

        # Verify in database
        pref = LocationSharingPreference.objects.get(person=customer_person)
        assert pref.visibility == "trip"

    def test_update_settings_invalid_visibility(self, api_client, customer_token, customer_person):
        """Reject invalid visibility value."""
        LocationSharingPreference.objects.create(person=customer_person)

        response = api_client.put(
            "/api/mobile/location/settings/",
            data=json.dumps({
                "visibility": "invalid_value",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {customer_token}",
        )

        assert response.status_code == 400
