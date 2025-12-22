"""
Django settings for config project.
"""

from pathlib import Path
from decouple import config
import os
from .version import __version__ as APP_VERSION

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# SECURITY / CORE SETTINGS
# =========================
SECRET_KEY = "django-insecure-g_$d+8ut_a07f&&k2k$kzn(kmotc680@n#avq^gn_x9k-lnqxd"
DEBUG = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*')
if ALLOWED_HOSTS == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ALLOWED_HOSTS.split(',')

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "users.backends.LockedoutBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# =========================
# INSTALLED APPS
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "about",
    "organizations",
    "rewards",
    "issues",
    "applications",
    "audit.apps.AuditConfig",
    "notifications.apps.NotificationsConfig",
    "catalogue.apps.CatalogueConfig",
    "hijack",
    "hijack.contrib.admin",
    "reports",
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "users.middleware.EnforcePasswordRotationMiddleware",
    "audit.middleware.NewLocationBannerMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "users.middleware.SessionTimeoutMiddleware",
    "hijack.middleware.HijackUserMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # NEW: global header points
                'rewards.context_processors.header_points',
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =========================
# SESSION SETTINGS
# =========================
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 4 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
EXTENDED_SESSION_LENGTH = 30 * 24 * 60 * 60
SESSION_WARNING_TIME = 600

# =========================
# DATABASE CONFIG
# =========================
# DB_NAME = config("DB_NAME", default="Team19_DB")
# DB_USER = config("DB_USER", default="Team19")
# DB_PASSWORD = config("DB_PASSWORD", default="")
# DB_HOST = config("DB_HOST", default="cpsc4910-f25.cobd8enwsupz.us-east-1.rds.amazonaws.com")
# DB_PORT = config("DB_PORT", default="3306")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =========================
# PASSWORD VALIDATION
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# =========================
# INTERNATIONALIZATION
# =========================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

# =========================
# STATIC FILES
# =========================
STATIC_URL = '/static/'

STATICFILES_DIRS = [BASE_DIR / "static"]

# Static root for collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise storage
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

if DEBUG:
    WHITENOISE_USE_FINDERS = True

# =========================
# PASSWORD ROTATION / SECURITY
# =========================
PASSWORD_MAX_AGE_DAYS = 30
PASSWORD_GRACE_ALLOWLIST = [
    "/admin/logout/",
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/password_change/",
    "/accounts/password_change/done/",
    "/static/"
]

# =========================
# EMAIL (Mailtrap Sandbox)
# =========================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_PORT = 2525
EMAIL_HOST_USER = "d4c6024865867c"
EMAIL_HOST_PASSWORD = "04ef43185ceac3"   # paste full password here
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = "no-reply@gooddrivers.local"