"""
Configuración Django — Plataforma de Simulación de Inversión (Aura Farmers).
Ingeniería de Software I · UIS · 2026-2
"""
import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-aurafarmers-simulador-cambiar-en-produccion",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Módulos del sistema
    "users",
    "market",
    "portfolios",
    "savings",
    "scenarios",
    "learning",
    "social",
    "support",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # WAL permite lecturas mientras otra petición escribe precios cada segundo
        # IMMEDIATE: cada transacción toma el bloqueo de escritura al iniciar. SQLite ignora
        # select_for_update, así que esto evita que dos peticiones cierren la misma posición.
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── API REST ──────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "COERCE_DECIMAL_TO_STRING": False,
    # Límites contra fuerza bruta y spam (las consultas de precios no se limitan)
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "register": "5/min",
        "password": "5/min",
        "messages": "40/min",
        "tickets": "10/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# El panel /admin también se abre a través del frontend (puerto 5173), en local y en GitHub Codespaces
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
if os.environ.get("CODESPACE_NAME"):
    _domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    CSRF_TRUSTED_ORIGINS += [f"https://{os.environ['CODESPACE_NAME']}-{port}.{_domain}" for port in (5173, 8000)]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ── Producción ────────────────────────────────────────────────────────────
if not DEBUG:
    from django.core.exceptions import ImproperlyConfigured

    if SECRET_KEY.startswith("django-insecure"):
        raise ImproperlyConfigured("Define DJANGO_SECRET_KEY antes de desplegar con DJANGO_DEBUG=0.")
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("DJANGO_CORS_ORIGINS", "").split(",") if o]

# ── Términos y política de datos (Ley 1581 de 2012) ──────────────────────
# Si se cambia el texto legal, subir la versión: a cada usuario se le pedirá aceptarla de nuevo.
LEGAL = {"TERMS_VERSION": "1.0", "TERMS_DATE": "2026-11-11"}

# ── Parámetros de la simulación ───────────────────────────────────────────
SIMULATION = {
    # Saldo ficticio con el que inicia cada usuario (USD)
    "INITIAL_BALANCE": Decimal("100000.00"),
    # Comisión por operación (0,1 %) con mínimo de 1 USD
    "COMMISSION_RATE": Decimal("0.001"),
    "MIN_COMMISSION": Decimal("1.00"),
    # Reloj del mercado: 1 segundo real equivale a 6 segundos de mercado,
    # para que la variación se vea en vivo en el gráfico
    "MARKET_SPEED": 6,
    # Segundos mínimos entre dos actualizaciones de precio
    "TICK_MIN_SECONDS": 1,
    # Hilo que mueve los precios y ejecuta TP/SL en segundo plano (desactivado en pruebas)
    "MARKET_CLOCK": os.environ.get("AF_MARKET_CLOCK", "1") == "1",
    # Días de velas de 1 minuto que se conservan para los gráficos intradía
    "INTRADAY_DAYS": 3,
    # Trading con margen (CFD), según los límites ESMA para clientes minoristas
    # Por clase de activo; cada instrumento puede fijar su propio tope (acciones y ETF siempre 1:5)
    "MAX_LEVERAGE": {"equity": 20, "real_estate": 5, "bond": 5, "commodity": 10, "forex": 30, "crypto": 2},
    "SPREAD": {"equity": 0.0006, "real_estate": 0.0006, "bond": 0.0005, "commodity": 0.0005,
               "forex": 0.0001, "crypto": 0.002},
    "MARGIN_CALL_LEVEL": 100,   # % — aviso
    "STOP_OUT_LEVEL": 50,       # % — cierre forzoso de posiciones
    # Volatilidad anual del factor de mercado común
    "MARKET_VOLATILITY": 0.17,
    # Tasa libre de riesgo para Sharpe
    "RISK_FREE_RATE": 0.04,
    # Años de historia sintética generada por instrumento
    "HISTORY_YEARS": 2,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.server": {"level": "WARNING"}},
}
