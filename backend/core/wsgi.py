"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import shutil
from pathlib import Path

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')


# On Vercel the function filesystem is read-only except for /tmp. The seeded
# SQLite database is bundled at build time into the project; copy it to /tmp on
# the first cold start so Django can write sessions and admin changes against
# it for the lifetime of the warm instance.
if os.environ.get('VERCEL'):
    src = Path(__file__).resolve().parent.parent / 'db.sqlite3'
    dst = Path(os.environ.get('SQLITE_PATH', '/tmp/db.sqlite3'))
    if src.exists() and not dst.exists():
        shutil.copy(src, dst)


application = get_wsgi_application()
