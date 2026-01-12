"""Base settings for DiveOps project."""

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = BASE_DIR / "src"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# Debug mode - override in dev.py
DEBUG = False

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

# Django Primitives (from submodule)
PRIMITIVES_APPS = [
    # Foundation
    "django_basemodels",
    "django_singleton",
    "django_sequence",
    "django_money",
    # Infrastructure
    "django_decisioning",
    "django_audit_log",
    "django_communication",
    # Identity
    "django_parties",
    "django_modules",
    "django_rbac",
    # Domain
    "django_catalog",
    "django_encounters",
    "django_worklog",
    "django_ledger",
    # Content
    "django_documents",
    "django_agreements",
    "django_questionnaires",
    "django_notes",
    "django_cms_core",
    # Geo
    "django_geo",
]

# Third-party UI
THIRD_PARTY_APPS = [
    "django_portal_ui",
]

# Local apps
LOCAL_APPS = [
    "diveops.core",
    "diveops.profile",
    "diveops.pricing",
    "diveops.invoicing",
    "diveops.store",
    "diveops.operations",
]

INSTALLED_APPS = DJANGO_APPS + PRIMITIVES_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "diveops.core.middleware.DomainLanguageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "diveops.core.middleware.ImpersonationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "diveops.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "diveops.operations.context_processors.diveops_context",
                "diveops.core.context_processors.impersonation_context",
                "diveops.store.context_processors.cart_context",
                "django_portal_ui.context_processors.portal_ui",
            ],
        },
    },
]

WSGI_APPLICATION = "diveops.wsgi.application"
ASGI_APPLICATION = "diveops.asgi.application"

# Database - PostgreSQL only
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "diveops"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}

# Custom user model
AUTH_USER_MODEL = "core.User"

# Django Modules configuration
MODULES_ORG_MODEL = "django_parties.Organization"
CATALOG_ENCOUNTER_MODEL = "django_encounters.Encounter"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Login redirects
LOGIN_REDIRECT_URL = "/portal/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

# Authentication backends - allow email login
AUTHENTICATION_BACKENDS = [
    "diveops.core.backends.EmailBackend",
]

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("es", _("Spanish")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Domain-based language mapping
DOMAIN_LANGUAGES = {
    "happydiving.mx": "en",
    "buceofeliz.com": "es",
}

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Dive Operations configuration
DIVE_SHOP_NAME = os.environ.get("DIVE_SHOP_NAME", "DiveOps")
DIVE_SHOP_TIMEZONE = os.environ.get("DIVE_SHOP_TIMEZONE", "America/New_York")
DIVE_SHOP_LATITUDE = float(os.environ.get("DIVE_SHOP_LATITUDE", "25.7617"))
DIVE_SHOP_LONGITUDE = float(os.environ.get("DIVE_SHOP_LONGITUDE", "-80.1918"))

# Site configuration
SITE_NAME = DIVE_SHOP_NAME
STAFF_PORTAL_TITLE = f"{DIVE_SHOP_NAME} Staff"
CUSTOMER_PORTAL_TITLE = f"{DIVE_SHOP_NAME} Portal"

# Portal UI configuration
PORTAL_UI = {
    "SITE_NAME": DIVE_SHOP_NAME,
    "PORTAL_NAV": [
        {
            "section": "Main",
            "label": "Dashboard",
            "url": "portal:dashboard",
            "icon": "home",
        },
        {
            "section": "Main",
            "label": "My Orders",
            "url": "portal:orders",
            "icon": "receipt",
        },
        {
            "section": "Main",
            "label": "Messages",
            "url": "portal:messages",
            "icon": "chat-bubble-left-right",
        },
        {
            "section": "Learning",
            "label": "My Courseware",
            "url": "portal:content",
            "url_kwargs": {"path": "open-water-courseware"},
            "icon": "book-open",
        },
        {
            "section": "Learning",
            "label": "Dive Site Guides",
            "url": "portal:content",
            "url_kwargs": {"path": "dive-sites"},
            "icon": "map-pin",
        },
        {
            "section": "Shop",
            "label": "Browse Store",
            "url": "store:list",
            "icon": "gift",
        },
        {
            "section": "Shop",
            "label": "My Cart",
            "url": "store:cart",
            "icon": "shopping-cart",
        },
        {
            "section": "Help",
            "label": "Help Center",
            "url": "portal:content",
            "url_kwargs": {"path": "help"},
            "icon": "help-circle",
        },
    ],
    "STAFF_NAV": [
        {
            "section": "Dive Operations",
            "label": "Excursions",
            "url": "diveops:excursion-list",
            "icon": "anchor",
        },
        {
            "section": "Dive Operations",
            "label": "Divers",
            "url": "diveops:diver-list",
            "icon": "users",
        },
        {
            "section": "CRM",
            "label": "Inbox",
            "url": "diveops:crm-inbox",
            "icon": "inbox",
        },
        {
            "section": "CRM",
            "label": "Leads",
            "url": "diveops:lead-list",
            "icon": "user-plus",
        },
        {
            "section": "CMS",
            "label": "Pages",
            "url": "diveops:cms-page-list",
            "icon": "file-text",
        },
        {
            "section": "CMS",
            "label": "Posts",
            "url": "diveops:blog-post-list",
            "icon": "edit-3",
        },
        {
            "section": "CMS",
            "label": "Categories",
            "url": "diveops:blog-category-list",
            "icon": "folder",
        },
        {
            "section": "CMS",
            "label": "Redirects",
            "url": "diveops:cms-redirect-list",
            "icon": "arrow-right",
        },
        {
            "section": "CMS",
            "label": "Settings",
            "url": "diveops:cms-settings",
            "icon": "settings",
        },
        {
            "section": "Dive Operations",
            "label": "Dive Sites",
            "url": "diveops:staff-site-list",
            "icon": "map-pin",
        },
        {
            "section": "Dive Operations",
            "label": "Protected Areas",
            "url": "diveops:protected-area-list",
            "icon": "shield",
        },
        {
            "section": "Dive Operations",
            "label": "Agreements",
            "url": "diveops:signable-agreement-list",
            "icon": "file-text",
        },
        {
            "section": "Dive Operations",
            "label": "Medical Questionnaires",
            "url": "diveops:medical-list",
            "icon": "heart",
        },
        {
            "section": "Planning",
            "label": "Dive Plans",
            "url": "diveops:dive-plan-list",
            "icon": "compass",
        },
        {
            "section": "Planning",
            "label": "Dive Logs",
            "url": "diveops:dive-log-list",
            "icon": "book-open",
        },
        {
            "section": "System",
            "label": "Documents",
            "url": "diveops:document-browser",
            "icon": "folder",
        },
        {
            "section": "System",
            "label": "Media",
            "url": "diveops:media-library",
            "icon": "image",
        },
        {
            "section": "System",
            "label": "Audit Log",
            "url": "diveops:audit-log",
            "icon": "file-text",
        },
        {
            "section": "Configuration",
            "label": "Excursion Types",
            "url": "diveops:excursion-type-list",
            "icon": "package",
        },
        {
            "section": "Configuration",
            "label": "Agreement Types",
            "url": "diveops:agreement-template-list",
            "icon": "clipboard",
        },
        {
            "section": "Configuration",
            "label": "Catalog Items",
            "url": "diveops:catalog-item-list",
            "icon": "tag",
        },
        {
            "section": "Configuration",
            "label": "AI Settings",
            "url": "diveops:ai-settings",
            "icon": "cpu",
        },
        {
            "section": "Configuration",
            "label": "Communication Settings",
            "url": "diveops:communication-settings",
            "icon": "mail",
        },
        {
            "section": "Configuration",
            "label": "Message Templates",
            "url": "diveops:message-template-list",
            "icon": "file-text",
        },
        {
            "section": "Configuration",
            "label": "Canned Responses",
            "url": "diveops:canned-response-list",
            "icon": "document-text",
        },
        {
            "section": "Finance",
            "label": "Chart of Accounts",
            "url": "diveops:account-list",
            "icon": "book",
        },
        {
            "section": "Finance",
            "label": "Payables",
            "url": "diveops:payables-summary",
            "icon": "credit-card",
        },
        {
            "section": "Help",
            "label": "Help Center",
            "url": "diveops:help-center",
            "icon": "help-circle",
        },
    ],
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "diveops": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
