"""Location tracking models for mobile app.

This module contains:
- LocationUpdate: GPS location recording from mobile devices
- LocationSharingPreference: Privacy controls for location sharing
"""

from django.db import models
from django.db.models import Q

from django_basemodels import BaseModel


class LocationUpdate(BaseModel):
    """GPS location update from a mobile device.

    Records real-time location for tracking divers on trips,
    staff during operations, or customers sharing location.

    Inherits from BaseModel: id (UUID), created_at, updated_at, deleted_at,
    objects (excludes deleted), all_objects (includes deleted).
    """

    class Source(models.TextChoices):
        GPS = "gps", "GPS"
        NETWORK = "network", "Network"
        FUSED = "fused", "Fused (GPS+Network)"
        MANUAL = "manual", "Manual Entry"

    # Who
    person = models.ForeignKey(
        "django_parties.Person",
        on_delete=models.CASCADE,
        related_name="location_updates",
        help_text="Person whose location was recorded",
    )

    # Where (using Decimal for geographic precision)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude coordinate (-90 to 90)",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude coordinate (-180 to 180)",
    )

    # Accuracy & source
    accuracy_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS accuracy in meters",
    )
    altitude_meters = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altitude above sea level in meters",
    )
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.FUSED,
        help_text="How location was obtained",
    )

    # When (device time vs server time)
    recorded_at = models.DateTimeField(
        help_text="Device timestamp when location was captured",
    )
    # created_at from BaseModel is server receipt time

    # Optional context
    excursion = models.ForeignKey(
        "diveops.Excursion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_updates",
        help_text="Active excursion when location was recorded",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(latitude__gte=-90) & Q(latitude__lte=90),
                name="location_update_valid_latitude",
            ),
            models.CheckConstraint(
                condition=Q(longitude__gte=-180) & Q(longitude__lte=180),
                name="location_update_valid_longitude",
            ),
        ]
        indexes = [
            models.Index(fields=["person", "-recorded_at"]),
            models.Index(fields=["recorded_at"]),
            models.Index(fields=["excursion", "recorded_at"]),
        ]
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.person} @ ({self.latitude}, {self.longitude})"

    def as_geopoint(self):
        """Return coordinates as a GeoPoint value object."""
        from django_geo.geo import GeoPoint

        return GeoPoint(latitude=self.latitude, longitude=self.longitude)


class LocationSharingPreference(BaseModel):
    """User preferences for location sharing visibility.

    Controls who can see this person's location updates.

    Inherits from BaseModel: id (UUID), created_at, updated_at, deleted_at,
    objects (excludes deleted), all_objects (includes deleted).
    """

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private (No one)"
        STAFF = "staff", "Staff Only"
        TRIP = "trip", "Trip Participants"
        BUDDIES = "buddies", "Dive Buddies"
        PUBLIC = "public", "All Users"

    person = models.OneToOneField(
        "django_parties.Person",
        on_delete=models.CASCADE,
        related_name="location_sharing_preference",
        help_text="Person these preferences belong to",
    )

    # Global visibility setting
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        help_text="Default visibility level for location updates",
    )

    # Override: always share with specific people
    always_share_with = models.ManyToManyField(
        "django_parties.Person",
        blank=True,
        related_name="always_sees_location_of",
        help_text="People who can always see this person's location regardless of visibility setting",
    )

    # Override: never share with specific people
    never_share_with = models.ManyToManyField(
        "django_parties.Person",
        blank=True,
        related_name="never_sees_location_of",
        help_text="People blocked from seeing location even if visibility would allow",
    )

    # Tracking behavior
    is_tracking_enabled = models.BooleanField(
        default=False,
        help_text="Whether to actively upload location updates",
    )
    tracking_interval_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Minimum seconds between location uploads",
    )

    class Meta:
        indexes = [
            models.Index(fields=["visibility"]),
        ]

    def __str__(self):
        return f"{self.person} - {self.visibility}"

    def can_see_location(self, viewer_person):
        """Check if viewer_person can see this person's location.

        Args:
            viewer_person: The Person trying to view the location

        Returns:
            bool: True if viewer can see location, False otherwise
        """
        # Blocklist always wins
        if self.never_share_with.filter(pk=viewer_person.pk).exists():
            return False

        # Explicit allowlist
        if self.always_share_with.filter(pk=viewer_person.pk).exists():
            return True

        # Fall back to visibility setting
        # Note: "staff", "trip", "buddies" require additional context checks
        # that should be implemented in the service layer
        if self.visibility == self.Visibility.PUBLIC:
            return True

        return False
