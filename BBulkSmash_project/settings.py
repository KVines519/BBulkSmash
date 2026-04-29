import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key — read from environment, required in production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY environment variable is not set. "
        "Set it before starting the application."
    )

DEBUG = False

# Allow any IP for local use — restrict via ALLOWED_HOSTS_ENV if needed
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# CSRF trusted origins — required for POST requests when accessed by IP/hostname
# Set DJANGO_CSRF_TRUSTED_ORIGINS as a comma-separated list, e.g.:
#   http://192.168.1.100,http://localhost
_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

# Application definition
INSTALLED_APPS = [
    'BBulkSmash',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'BBulkSmash_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'BBulkSmash.context_processors.version_context'
            ],
        },
    },
]

# WSGI_APPLICATION = 'BBulkSmash_project.wsgi.application'
ASGI_APPLICATION = 'BBulkSmash_project.asgi.application'

# Localization
LANGUAGE_CODE = 'en-us'

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'collectstatic/'

# Databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_data' / 'db.sqlite3',
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {filename}:{lineno} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(Path(BASE_DIR) / 'logs' / 'debug.log'),
            'formatter': 'verbose',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
        'django.server': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
