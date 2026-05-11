"""Test-only Django settings.

Inherits everything from the real ``core.settings`` then overrides a few
knobs so tests run hermetically without needing Postgres or the prod
``SECRET_KEY``. Used by ``pytest`` (configured in ``pyproject.toml``).
"""
from __future__ import annotations

import os


# These have to be set BEFORE the real settings module is imported because
# ``django-environ`` evaluates them at import time.
os.environ.setdefault('SECRET_KEY', 'pytest-not-secret')
os.environ.setdefault('DEBUG', 'False')
os.environ.setdefault('USE_SQLITE', '1')
os.environ.setdefault('ALLOWED_HOSTS', '*')

from core.settings import *  # noqa: E402,F401,F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up tests: cheap password hasher and an in-memory cache backend.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Disable rate limiting / debug toolbar if they get added later.
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m]  # noqa: F405

# Static handling: noop storage so collectstatic isn't needed in tests.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
