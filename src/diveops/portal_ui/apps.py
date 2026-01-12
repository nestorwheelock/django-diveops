"""Django app configuration for portal_ui."""

from django.apps import AppConfig


class PortalUiConfig(AppConfig):
    """App configuration for portal UI components."""

    name = "diveops.portal_ui"
    verbose_name = "Portal UI"
    default_auto_field = "django.db.models.BigAutoField"
