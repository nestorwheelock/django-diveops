"""URL configuration for DiveOps project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from diveops.core.impersonation import ImpersonateStartView, ImpersonateStopView
from diveops.core.views import health_check, index

urlpatterns = [
    # Health check
    path("health/", health_check, name="health_check"),

    # Django admin
    path("admin/", admin.site.urls),

    # User impersonation (staff only)
    path("impersonate/<uuid:user_id>/", ImpersonateStartView.as_view(), name="impersonate-start"),
    path("impersonate/stop/", ImpersonateStopView.as_view(), name="impersonate-stop"),

    # Authentication
    path("accounts/", include("django.contrib.auth.urls")),

    # User profile
    path("profile/", include("diveops.profile.urls", namespace="profile")),

    # Staff portal
    path("staff/", include("diveops.operations.urls.staff", namespace="diveops")),

    # Customer portal
    path("portal/", include("diveops.operations.urls.customer", namespace="portal")),

    # Public pages (agreement signing, medical questionnaire)
    path("sign/", include("diveops.operations.urls.public")),

    # Store
    path("shop/", include("diveops.store.urls", namespace="store")),

    # Invoicing
    path("invoices/", include("diveops.invoicing.urls", namespace="invoicing")),

    # Pricing
    path("pricing/", include("diveops.pricing.urls")),

    # Homepage
    path("", index, name="index"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Django Debug Toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
