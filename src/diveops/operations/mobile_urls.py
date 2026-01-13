"""Mobile API URL patterns for the staff chat Android app."""

from django.urls import path

from . import mobile_api_views

app_name = "mobile"

urlpatterns = [
    # Authentication (Staff)
    path("login/", mobile_api_views.MobileLoginView.as_view(), name="login"),

    # Authentication (Customer - returns is_staff flag)
    path("customer/login/", mobile_api_views.CustomerLoginView.as_view(), name="customer-login"),

    # FCM Device Registration
    path("fcm/register/", mobile_api_views.FCMRegisterView.as_view(), name="fcm-register"),
    path("fcm/unregister/", mobile_api_views.FCMUnregisterView.as_view(), name="fcm-unregister"),

    # Conversations (Staff)
    path("conversations/", mobile_api_views.MobileConversationsView.as_view(), name="conversations"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        mobile_api_views.MobileMessagesView.as_view(),
        name="messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/send/",
        mobile_api_views.MobileSendMessageView.as_view(),
        name="send-message",
    ),

    # App Version Check (In-App Updates - No Auth)
    path("version/check/", mobile_api_views.VersionCheckView.as_view(), name="version-check"),

    # Customer Bookings
    path("customer/bookings/", mobile_api_views.CustomerBookingsView.as_view(), name="customer-bookings"),

    # Location Tracking
    path("location/", mobile_api_views.LocationUpdateView.as_view(), name="location-update"),
    path("location/batch/", mobile_api_views.LocationBatchUpdateView.as_view(), name="location-batch"),
    path("location/settings/", mobile_api_views.LocationSettingsView.as_view(), name="location-settings"),
]
