"""
Django settings for HabitHamster.

Supports three run modes:

1. Local quick-start (default): SQLite, no .environment file required.
2. Docker / production-like: reads .environment file with DB_* variables and
   uses PostgreSQL.
3. Vercel (serverless): SQLite copied to /tmp at runtime; auto-detected via
   the ``VERCEL`` environment variable that Vercel injects.

The flag `USE_SQLITE` (env or default `True` when no DB_NAME env var) selects
the engine.
"""

import os
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel injects VERCEL=1 in build & runtime sandboxes.
IS_VERCEL = bool(os.environ.get('VERCEL'))

env = environ.Env(
    DEBUG=(bool, True),
    SECRET_KEY=(str, 'django-insecure-ijbynh6l)0^&6*+d$%=bmyr4s)y9uipf$ybnw)adp^bxrfc5k%'),
    ALLOWED_HOSTS=(list, ['*']),
    USE_SQLITE=(bool, False),
    DB_NAME=(str, ''),
    DB_USER=(str, ''),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, ''),
    DB_PORT=(str, ''),
)

# Read .environment if present; otherwise rely on env defaults above.
env_file = BASE_DIR / '.environment'
if env_file.exists():
    environ.Env.read_env(str(env_file))


SECRET_KEY = env('SECRET_KEY')
DEBUG = False if IS_VERCEL else env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
if IS_VERCEL:
    # Vercel deployments are served from <project>.vercel.app and any custom
    # domains. Allow them all; the platform terminates TLS in front of us.
    ALLOWED_HOSTS = ['.vercel.app', '.now.sh', 'localhost', '127.0.0.1']
    CSRF_TRUSTED_ORIGINS = ['https://*.vercel.app']
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'habits.apps.HabitsConfig',
]

MIDDLEWARE = [
    # MUST be the OUTERMOST middleware: process_response runs in reverse order,
    # so being first here means we push to Blob LAST — i.e. after
    # SessionMiddleware has flushed the new session row to /tmp/db.sqlite3.
    # Putting it any later (e.g. at the bottom of the list) means we'd upload
    # the DB before the session is committed, and users would silently get
    # logged out on the next cold start.
    'core.middleware.BlobDBSyncMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Serve collected /static/ files via WSGI. In DEBUG mode WhiteNoise no-ops
    # (Django's runserver serves them); in production (Docker behind nginx,
    # Vercel function) it serves STATIC_ROOT directly so /static/admin/* works.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'habits.context_processors.profile_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database — SQLite by default for easy local dev, Postgres when DB_NAME is set.
# On Vercel the bundled db.sqlite3 (built at deploy time by build.py) is copied
# to /tmp at startup so Django can write sessions/admin data to it.
if IS_VERCEL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('SQLITE_PATH', '/tmp/db.sqlite3'),
        }
    }
elif env('USE_SQLITE') or not env('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True


# Static & media files.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# When deployed on Vercel (with a Blob read/write token) user-uploaded media
# goes to Vercel Blob so files survive function cold starts. Local/Docker dev
# keeps the existing FileSystemStorage behaviour.
_DEFAULT_STORAGE_BACKEND = (
    'core.blob_storage.BlobMediaStorage'
    if os.environ.get('BLOB_READ_WRITE_TOKEN')
    else 'django.core.files.storage.FileSystemStorage'
)

STORAGES = {
    'default': {
        'BACKEND': _DEFAULT_STORAGE_BACKEND,
    },
    # Compressed (gzip/brotli) but non-manifested storage so the same
    # collectstatic output works whether build-time DEBUG/IS_VERCEL flags differ
    # from runtime ones.
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Auth.
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'


# DRF.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
