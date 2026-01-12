"""Development settings for DiveOps."""

import os

from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "happydiving.mx", "buceofeliz.com"]

# Development database (use local PostgreSQL or Docker)
DATABASES["default"]["HOST"] = os.environ.get("POSTGRES_HOST", "localhost")  # noqa: F405

# Use local memory cache in development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "diveops-dev-cache",
    }
}

# Static files storage
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Django Debug Toolbar (optional)
if os.environ.get("ENABLE_DEBUG_TOOLBAR", "false").lower() == "true":
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]

# Email - console backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CSRF settings for local development
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Logging - more verbose in development
LOGGING["loggers"]["diveops"]["level"] = "DEBUG"  # noqa: F405
