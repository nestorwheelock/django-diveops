"""App version management models.

This module contains:
- AppVersion: Track mobile app versions and force-update requirements
"""

from django.db import models

from django_basemodels import BaseModel


class AppVersion(BaseModel):
    """Track mobile app versions and force-update requirements.

    Used by the mobile app to check for updates on startup.
    Supports force-update for critical security patches.

    Inherits from BaseModel: id (UUID), created_at, updated_at, deleted_at,
    objects (excludes deleted), all_objects (includes deleted).
    """

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        help_text="Mobile platform (android or ios)",
    )

    version_code = models.PositiveIntegerField(
        help_text="Numeric version code (e.g., 1, 2, 3). Matches Android versionCode.",
    )

    version_name = models.CharField(
        max_length=20,
        help_text="Display version string (e.g., '1.0.0')",
    )

    download_url = models.URLField(
        blank=True,
        help_text="Direct APK/IPA download URL",
    )

    is_force_update = models.BooleanField(
        default=False,
        help_text="If True, users on older versions must update before using the app",
    )

    min_supported_version = models.PositiveIntegerField(
        default=1,
        help_text="Minimum version_code still allowed to run. Versions below this are blocked.",
    )

    release_notes = models.TextField(
        blank=True,
        help_text="What's new in this version (shown in update dialog)",
    )

    released_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this version was released",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "version_code"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_platform_version_active",
            ),
        ]
        ordering = ["-version_code"]
        indexes = [
            models.Index(fields=["platform", "version_code"]),
        ]

    def __str__(self):
        return f"{self.platform} v{self.version_name} ({self.version_code})"
