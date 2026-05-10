"""
Custom middleware for HabitHamster.
"""
from __future__ import annotations

import logging
import os

from .blob_storage import is_enabled as blob_enabled, upload_db


logger = logging.getLogger(__name__)


class BlobDBSyncMiddleware:
    """Push the local SQLite file to Vercel Blob after every successful write.

    Without this, the bundled DB lives in ``/tmp`` for the lifetime of a warm
    function instance and is wiped on cold start — admin edits would silently
    disappear. The upload runs synchronously after the response is generated
    so we don't lose it to function suspension; failures are logged but never
    block the user-facing response.

    No-op outside Vercel (where ``BLOB_READ_WRITE_TOKEN`` is unset), so local
    dev and Docker behaviour is unchanged.
    """

    WRITE_METHODS = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})

    def __init__(self, get_response):
        self.get_response = get_response
        self.sqlite_path = os.environ.get('SQLITE_PATH', '/tmp/db.sqlite3')

    def __call__(self, request):
        response = self.get_response(request)
        if (
            blob_enabled()
            and request.method in self.WRITE_METHODS
            and response.status_code < 400
        ):
            upload_db(self.sqlite_path)
        return response
