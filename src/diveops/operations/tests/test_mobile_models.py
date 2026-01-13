"""Tests for mobile app models.

Tests for:
- AppVersion: Version tracking and force-update
- LocationUpdate: GPS location recording
- LocationSharingPreference: Privacy controls
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone


@pytest.mark.django_db
class TestAppVersionModel:
    """Tests for AppVersion model."""

    def test_create_app_version(self):
        """AppVersion can be created with required fields."""
        from diveops.operations.models import AppVersion

        version = AppVersion.objects.create(
            platform="android",
            version_code=1,
            version_name="1.0.0",
        )
        assert version.pk is not None
        assert version.platform == "android"
        assert version.version_code == 1
        assert version.version_name == "1.0.0"

    def test_unique_platform_version(self):
        """Cannot create duplicate platform+version_code."""
        from diveops.operations.models import AppVersion

        AppVersion.objects.create(
            platform="android",
            version_code=1,
            version_name="1.0.0",
        )

        with pytest.raises(IntegrityError):
            AppVersion.objects.create(
                platform="android",
                version_code=1,
                version_name="1.0.1",  # Same version_code
            )

    def test_different_platforms_same_version(self):
        """Different platforms can have same version_code."""
        from diveops.operations.models import AppVersion

        android = AppVersion.objects.create(
            platform="android",
            version_code=1,
            version_name="1.0.0",
        )
        ios = AppVersion.objects.create(
            platform="ios",
            version_code=1,
            version_name="1.0.0",
        )
        assert android.pk != ios.pk

    def test_ordering_by_version_code(self):
        """AppVersions are ordered by version_code descending."""
        from diveops.operations.models import AppVersion

        v1 = AppVersion.objects.create(platform="android", version_code=1, version_name="1.0.0")
        v3 = AppVersion.objects.create(platform="android", version_code=3, version_name="1.2.0")
        v2 = AppVersion.objects.create(platform="android", version_code=2, version_name="1.1.0")

        versions = list(AppVersion.objects.filter(platform="android"))
        assert versions[0].version_code == 3
        assert versions[1].version_code == 2
        assert versions[2].version_code == 1

    def test_force_update_default_false(self):
        """is_force_update defaults to False."""
        from diveops.operations.models import AppVersion

        version = AppVersion.objects.create(
            platform="android",
            version_code=1,
            version_name="1.0.0",
        )
        assert version.is_force_update is False

    def test_min_supported_version_default(self):
        """min_supported_version defaults to 1."""
        from diveops.operations.models import AppVersion

        version = AppVersion.objects.create(
            platform="android",
            version_code=5,
            version_name="1.4.0",
        )
        assert version.min_supported_version == 1


@pytest.mark.django_db
class TestLocationUpdateModel:
    """Tests for LocationUpdate model."""

    @pytest.fixture
    def person(self):
        """Create a test person."""
        from django_parties.models import Person

        return Person.objects.create(
            first_name="John",
            last_name="Doe",
        )

    def test_create_location_update(self, person):
        """LocationUpdate can be created with required fields."""
        from diveops.operations.models import LocationUpdate

        loc = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("20.123456"),
            longitude=Decimal("-87.456789"),
            recorded_at=timezone.now(),
        )
        assert loc.pk is not None
        assert loc.latitude == Decimal("20.123456")
        assert loc.longitude == Decimal("-87.456789")

    def test_location_with_optional_fields(self, person):
        """LocationUpdate can include optional accuracy/altitude."""
        from diveops.operations.models import LocationUpdate

        loc = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("20.123456"),
            longitude=Decimal("-87.456789"),
            accuracy_meters=Decimal("10.50"),
            altitude_meters=Decimal("5.25"),
            source="gps",
            recorded_at=timezone.now(),
        )
        assert loc.accuracy_meters == Decimal("10.50")
        assert loc.altitude_meters == Decimal("5.25")
        assert loc.source == "gps"

    def test_latitude_constraint_valid(self, person):
        """Latitude within -90 to 90 is valid."""
        from diveops.operations.models import LocationUpdate

        # North pole
        loc_north = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("90.000000"),
            longitude=Decimal("0.000000"),
            recorded_at=timezone.now(),
        )
        assert loc_north.latitude == Decimal("90.000000")

        # South pole
        loc_south = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("-90.000000"),
            longitude=Decimal("0.000000"),
            recorded_at=timezone.now(),
        )
        assert loc_south.latitude == Decimal("-90.000000")

    def test_latitude_constraint_invalid(self, person):
        """Latitude outside -90 to 90 is rejected."""
        from diveops.operations.models import LocationUpdate

        with pytest.raises(IntegrityError):
            LocationUpdate.objects.create(
                person=person,
                latitude=Decimal("91.000000"),
                longitude=Decimal("0.000000"),
                recorded_at=timezone.now(),
            )

    def test_longitude_constraint_valid(self, person):
        """Longitude within -180 to 180 is valid."""
        from diveops.operations.models import LocationUpdate

        loc = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("0.000000"),
            longitude=Decimal("-180.000000"),
            recorded_at=timezone.now(),
        )
        assert loc.longitude == Decimal("-180.000000")

    def test_longitude_constraint_invalid(self, person):
        """Longitude outside -180 to 180 is rejected."""
        from diveops.operations.models import LocationUpdate

        with pytest.raises(IntegrityError):
            LocationUpdate.objects.create(
                person=person,
                latitude=Decimal("0.000000"),
                longitude=Decimal("181.000000"),
                recorded_at=timezone.now(),
            )

    def test_as_geopoint(self, person):
        """as_geopoint() returns a GeoPoint value object."""
        from diveops.operations.models import LocationUpdate

        loc = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("20.500000"),
            longitude=Decimal("-87.300000"),
            recorded_at=timezone.now(),
        )
        point = loc.as_geopoint()
        assert point.latitude == Decimal("20.500000")
        assert point.longitude == Decimal("-87.300000")

    def test_ordering_by_recorded_at(self, person):
        """LocationUpdates are ordered by recorded_at descending."""
        from diveops.operations.models import LocationUpdate

        now = timezone.now()
        old = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("20.0"),
            longitude=Decimal("-87.0"),
            recorded_at=now - timezone.timedelta(hours=1),
        )
        new = LocationUpdate.objects.create(
            person=person,
            latitude=Decimal("21.0"),
            longitude=Decimal("-88.0"),
            recorded_at=now,
        )

        updates = list(LocationUpdate.objects.filter(person=person))
        assert updates[0].pk == new.pk
        assert updates[1].pk == old.pk


@pytest.mark.django_db
class TestLocationSharingPreferenceModel:
    """Tests for LocationSharingPreference model."""

    @pytest.fixture
    def person(self):
        """Create a test person."""
        from django_parties.models import Person

        return Person.objects.create(
            first_name="Jane",
            last_name="Smith",
        )

    def test_create_preference(self, person):
        """LocationSharingPreference can be created."""
        from diveops.operations.models import LocationSharingPreference

        pref = LocationSharingPreference.objects.create(
            person=person,
        )
        assert pref.pk is not None
        assert pref.visibility == "private"  # Default
        assert pref.is_tracking_enabled is False  # Default

    def test_visibility_choices(self, person):
        """visibility field accepts valid choices."""
        from diveops.operations.models import LocationSharingPreference

        pref = LocationSharingPreference.objects.create(person=person)

        for visibility in ["private", "staff", "trip", "buddies", "public"]:
            pref.visibility = visibility
            pref.save()
            pref.refresh_from_db()
            assert pref.visibility == visibility

    def test_one_preference_per_person(self, person):
        """Only one preference per person (OneToOne)."""
        from diveops.operations.models import LocationSharingPreference

        LocationSharingPreference.objects.create(person=person)

        with pytest.raises(IntegrityError):
            LocationSharingPreference.objects.create(person=person)

    def test_tracking_interval_default(self, person):
        """tracking_interval_seconds defaults to 60."""
        from diveops.operations.models import LocationSharingPreference

        pref = LocationSharingPreference.objects.create(person=person)
        assert pref.tracking_interval_seconds == 60

    def test_always_share_with(self, person):
        """always_share_with M2M relationship works."""
        from django_parties.models import Person
        from diveops.operations.models import LocationSharingPreference

        buddy = Person.objects.create(first_name="Bob", last_name="Buddy")

        pref = LocationSharingPreference.objects.create(person=person)
        pref.always_share_with.add(buddy)

        assert buddy in pref.always_share_with.all()

    def test_never_share_with(self, person):
        """never_share_with M2M relationship works."""
        from django_parties.models import Person
        from diveops.operations.models import LocationSharingPreference

        blocked = Person.objects.create(first_name="Blocked", last_name="User")

        pref = LocationSharingPreference.objects.create(person=person)
        pref.never_share_with.add(blocked)

        assert blocked in pref.never_share_with.all()
