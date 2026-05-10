"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import logging
import os
import shutil
from pathlib import Path

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')


logger = logging.getLogger(__name__)


# On Vercel the function filesystem is read-only except for /tmp. We need a
# fresh writable SQLite file at /tmp/db.sqlite3 before the WSGI app is built.
#
# Order of preference:
#   1. Vercel Blob (canonical source of truth in production — populated by
#      ``BlobDBSyncMiddleware`` after every successful write request).
#   2. The build-bundled ``db.sqlite3`` (seeded by ``build.py`` at deploy time).
#      Used only on the very first cold start, before any writes have been
#      pushed to Blob.
if os.environ.get('VERCEL'):
    src = Path(__file__).resolve().parent.parent / 'db.sqlite3'
    dst = Path(os.environ.get('SQLITE_PATH', '/tmp/db.sqlite3'))

    if not dst.exists():
        downloaded = False
        try:
            from .blob_storage import download_db

            downloaded = download_db(str(dst))
        except Exception:
            logger.exception('Failed to fetch SQLite from Vercel Blob; falling back to bundled DB')

        if not downloaded and src.exists():
            shutil.copy(src, dst)


application = get_wsgi_application()
