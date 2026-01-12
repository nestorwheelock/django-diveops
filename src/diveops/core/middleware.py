"""Core middleware for DiveOps."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import translation

IMPERSONATE_SESSION_KEY = "_impersonate_user_id"
IMPERSONATE_ORIGINAL_USER_KEY = "_impersonate_original_user_id"


class DomainLanguageMiddleware:
    """Set language based on the request domain.

    Maps domains to languages:
    - happydiving.mx -> English (en)
    - buceofeliz.com -> Spanish (es)

    This middleware runs AFTER LocaleMiddleware to override browser/cookie
    language preferences with domain-based language selection.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.domain_languages = getattr(settings, "DOMAIN_LANGUAGES", {})

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        lang = None

        for domain, domain_lang in self.domain_languages.items():
            if domain in host:
                lang = domain_lang
                break

        if lang:
            translation.activate(lang)
            request.LANGUAGE_CODE = lang

        response = self.get_response(request)

        if lang:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )

        return response


class ImpersonationMiddleware:
    """Middleware to handle staff impersonation of customers.

    Sets request.is_impersonating and request.original_user for templates.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        User = get_user_model()

        # Check if impersonation is active
        impersonated_user_id = request.session.get(IMPERSONATE_SESSION_KEY)
        original_user_id = request.session.get(IMPERSONATE_ORIGINAL_USER_KEY)

        if impersonated_user_id and request.user.is_authenticated:
            try:
                impersonated_user = User.objects.get(pk=impersonated_user_id)
                original_user = User.objects.get(pk=original_user_id) if original_user_id else request.user

                # Store original user for reference
                request.original_user = original_user
                request.real_user = original_user  # Alias for compatibility
                request.is_impersonating = True

                # Swap the user
                request.user = impersonated_user
            except User.DoesNotExist:
                # Clear invalid impersonation
                if IMPERSONATE_SESSION_KEY in request.session:
                    del request.session[IMPERSONATE_SESSION_KEY]
                if IMPERSONATE_ORIGINAL_USER_KEY in request.session:
                    del request.session[IMPERSONATE_ORIGINAL_USER_KEY]
                request.is_impersonating = False
                request.original_user = None
                request.real_user = request.user
        else:
            request.is_impersonating = False
            request.original_user = None
            request.real_user = request.user

        response = self.get_response(request)
        return response


def start_impersonation(request, user_id):
    """Start impersonating a user."""
    if not request.user.is_staff:
        raise PermissionError("Only staff can impersonate users")

    request.session[IMPERSONATE_SESSION_KEY] = str(user_id)
    request.session[IMPERSONATE_ORIGINAL_USER_KEY] = str(request.user.pk)


def stop_impersonation(request):
    """Stop impersonating a user."""
    if IMPERSONATE_SESSION_KEY in request.session:
        del request.session[IMPERSONATE_SESSION_KEY]
    if IMPERSONATE_ORIGINAL_USER_KEY in request.session:
        del request.session[IMPERSONATE_ORIGINAL_USER_KEY]
