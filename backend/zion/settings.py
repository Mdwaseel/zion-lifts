"""Django settings for the Zion Lifts site."""
from datetime import timedelta
from pathlib import Path
import os

from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-not-for-production-4f9a2c81")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "apps.accounts",
    "apps.core",
    "apps.catalog",
    "apps.projects",
    "apps.content",
    "apps.enquiries",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "zion.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "zion.wsgi.application"

import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME" ),
        "USER": os.getenv("DB_USER" ),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

def env_bool(name, default):
    return os.getenv(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 48,
    # The public content endpoints stay AllowAny (DRF's default). This only
    # decides *who* a request is when it carries an auth cookie: the JWT cookie
    # first, then the session, so a signed-in admin browsing the API in a tab
    # is recognised too.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.JWTCookieAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # How many reverse proxies sit in front of Django. This is the setting that
    # decides which address a throttle counts against, so getting it wrong
    # disables rate limiting entirely: left as None, DRF keys the bucket on the
    # whole client-supplied X-Forwarded-For header, and an attacker varying that
    # header lands in a fresh bucket on every request. 0 = no proxy, trust
    # REMOTE_ADDR; 1 = one nginx in front, take the last hop it appended.
    "NUM_PROXIES": int(os.getenv("NUM_PROXIES", "0")),
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "enquiry": "12/hour",
        # Loose enough for a person mistyping a password a few times; tight
        # enough that a script cannot work through a wordlist.
        "login": os.getenv("LOGIN_RATE_LIMIT", "10/minute"),
        "login_account": os.getenv("LOGIN_ACCOUNT_RATE_LIMIT", "12/hour"),
        "captcha": os.getenv("CAPTCHA_RATE_LIMIT", "30/minute"),
    },
}

# --- authentication --------------------------------------------------------
# Email first, so the React login page and the admin's own form accept the same
# identifier. ModelBackend stays behind it for usernames and for permissions.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# The cache backs DRF throttling and the CAPTCHA store, both of which are only
# correct if every worker sees the same entries. LocMemCache is per-process:
# fine for development and the test suite, wrong behind more than one gunicorn
# worker. Set REDIS_URL in production.
_redis_url = os.getenv("REDIS_URL", "").strip()
CACHES = {
    "default": (
        {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": _redis_url}
        if _redis_url
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "zion-default",
        }
    )
}

# JWT. The access token is short-lived because it is presented on every request
# and is never checked against a server-side list — once minted it is valid
# until it expires, so the window is the whole of its blast radius. The refresh
# token is long-lived because its only job is to avoid asking for the password
# again; it is scoped to one URL path, rotated on every use, and revocable,
# because rotation puts the spent one on the blacklist.
JWT_ACCESS_COOKIE = os.getenv("JWT_ACCESS_COOKIE", "access_token")
JWT_REFRESH_COOKIE = os.getenv("JWT_REFRESH_COOKIE", "refresh_token")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_LIFETIME_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    # A separate key by preference: rotating the JWT secret then invalidates
    # every session without also invalidating signed cookies and password-reset
    # links, which is what changing DJANGO_SECRET_KEY would do.
    "SIGNING_KEY": os.getenv("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- auth cookies ----------------------------------------------------------
# Same-site by default: in development Vite proxies /api to Django, and in
# production nginx serves the site and proxies /api and /admin from one origin.
# SameSite=Lax is therefore correct and is a free layer of CSRF defence. Only
# set SameSite=None (which requires Secure) if the API really does move to a
# different site from the front end.
AUTH_COOKIE_SECURE = env_bool("AUTH_COOKIE_SECURE", not DEBUG)
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN", "").strip()
AUTH_COOKIE_PATH = "/"
# The refresh token is only ever read by /api/accounts/refresh/ and /logout/, so
# the browser is told not to send it anywhere else.
AUTH_REFRESH_COOKIE_PATH = "/api/accounts/"

# --- CAPTCHA ---------------------------------------------------------------
CAPTCHA_TTL_SECONDS = int(os.getenv("CAPTCHA_TTL_SECONDS", "300"))
CAPTCHA_MAX_ATTEMPTS = int(os.getenv("CAPTCHA_MAX_ATTEMPTS", "3"))
CAPTCHA_LENGTH = int(os.getenv("CAPTCHA_LENGTH", "5"))

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if o.strip()
]

# The one origin the site is actually served from. Kept separate because the
# login flow needs to name it (redirects, cookie scope) rather than guess from a
# list, and folded into the allow-lists so it cannot be forgotten in either.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")
if FRONTEND_URL and FRONTEND_URL not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)

# Never CORS_ALLOW_ALL_ORIGINS: credentialed requests plus a wildcard origin is
# an open door to every authenticated endpoint on the site.
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + ["x-csrftoken"]
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)

# Session cookie: the admin runs on it, so it gets the same posture as the JWT
# cookies. HttpOnly is on in every environment, not only in production.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "Lax")
# CSRF_COOKIE_HTTPONLY stays False on purpose: the React client has to read this
# one to echo it back in X-CSRFToken. It is a token, not a credential — knowing
# it is useless without also being able to send the session cookie.
CSRF_COOKIE_HTTPONLY = False

# Where the React build writes its public asset tree — the seeder points at it.
FRONTEND_MEDIA_URL = os.getenv("FRONTEND_MEDIA_URL", "/media")

# --- Outbound notification for new enquiries -------------------------------
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "website@zionlifts.com")
ENQUIRY_NOTIFY_TO = [
    e for e in os.getenv("ENQUIRY_NOTIFY_TO", "sales@zionlifts.com").split(",") if e
]

# --- logging ---------------------------------------------------------------
# One named logger for security events. Everything written to it is an outcome
# plus an actor — user id, email on failure, client address — and never a
# credential: no passwords, no tokens, no cookie values, no CAPTCHA answers.
# Point AUTH_LOG_FILE at a path in production to keep the trail off stdout.
_auth_log_file = os.getenv("AUTH_LOG_FILE", "").strip()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "security": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "security",
        },
        **(
            {
                "auth_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": _auth_log_file,
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "security",
                    "encoding": "utf-8",
                }
            }
            if _auth_log_file
            else {}
        ),
    },
    "loggers": {
        "apps.accounts.security": {
            "handlers": ["console"] + (["auth_file"] if _auth_log_file else []),
            "level": os.getenv("AUTH_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"] + (["auth_file"] if _auth_log_file else []),
            "level": "WARNING",
            "propagate": False,
        },
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

# --- Production hardening ---------------------------------------------------
# Applied automatically whenever DJANGO_DEBUG=0, so a deployment cannot forget
# them. Assumes TLS is terminated at a reverse proxy that sets the header below.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "1") == "1"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 365))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

    if SECRET_KEY.startswith("dev-only"):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set to a real value when DEBUG is off."
        )

    # The auth cookies carry the same weight as the session cookie, so they get
    # the same rule rather than an environment variable that can be left at
    # false by accident.
    if not AUTH_COOKIE_SECURE:
        raise ImproperlyConfigured(
            "AUTH_COOKIE_SECURE must be true when DEBUG is off: the JWT cookies "
            "would otherwise be sent over plain HTTP."
        )

    # SameSite=None means the cookie is attached to cross-site requests, which
    # removes a layer of CSRF defence. Browsers only accept it with Secure, and
    # this project should only need it if the API is moved to another domain.
    if AUTH_COOKIE_SAMESITE.lower() == "none" and not AUTH_COOKIE_SECURE:
        raise ImproperlyConfigured("AUTH_COOKIE_SAMESITE=None requires AUTH_COOKIE_SECURE=true.")

    # The development origins are permissive by design and must not survive into
    # production: CORS_ALLOW_CREDENTIALS is on, and CSRF_TRUSTED_ORIGINS mirrors
    # this list, so leaving localhost in it means a process on a visitor's own
    # machine is treated as a trusted origin for credentialed requests.
    _dev_origins = [o for o in CORS_ALLOWED_ORIGINS if "localhost" in o or "127.0.0.1" in o]
    if _dev_origins:
        raise ImproperlyConfigured(
            "CORS_ALLOWED_ORIGINS and FRONTEND_URL must name the real site when "
            f"DEBUG is off; found development origins: {', '.join(_dev_origins)}"
        )

    # The JWT signing key falls back to SECRET_KEY, and SECRET_KEY has a
    # committed development default — anyone with the repository could otherwise
    # mint a token for any user id. The SECRET_KEY check above covers the
    # fallback; this covers an explicitly set but throwaway JWT key.
    if SIMPLE_JWT["SIGNING_KEY"].startswith("dev-only") or len(SIMPLE_JWT["SIGNING_KEY"]) < 32:
        raise ImproperlyConfigured(
            "JWT_SIGNING_KEY (or DJANGO_SECRET_KEY, which it falls back to) must "
            "be a long random value when DEBUG is off."
        )
