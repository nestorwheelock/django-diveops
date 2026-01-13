"""Test settings for DiveOps."""

import os

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-for-testing-only"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Test database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_TEST_DB", "test_diveops"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Fast password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Local memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "diveops-test-cache",
    }
}

# Email - in-memory backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Static files
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
