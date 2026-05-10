"""
Vercel Blob storage helpers.

This module provides two integration points for the deployed Django app:

1. ``download_db`` / ``upload_db`` — pull-on-cold-start / push-on-write helpers
   for the SQLite database.  Combined with ``BlobDBSyncMiddleware`` they make
   admin & user writes survive cold starts of the Vercel function (where
   ``/tmp`` is wiped between invocations).
2. ``BlobMediaStorage`` — a drop-in Django storage backend so user uploads
   (avatars, images, etc.) are persisted to Vercel Blob instead of the
   function's read-only filesystem.

All operations are no-ops when ``BLOB_READ_WRITE_TOKEN`` is not set in the
environment — local dev (Docker) keeps the existing FileSystemStorage
behaviour unchanged.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional
from urllib.parse import urlparse

import requests
import vercel_blob

from django.core.files.base import ContentFile
from django.core.files.storage import Storage


logger = logging.getLogger(__name__)


# Pathnames inside the blob store. Using prefixes keeps DB and media uploads
# easy to identify and lets us add future namespaces (caches, exports, etc.)
# without clashing.
DB_BLOB_PATH = 'db/db.sqlite3'
MEDIA_BLOB_PREFIX = 'media/'


# Module-level lock so concurrent push attempts within one warm instance don't
# read+upload the SQLite file mid-write.
_db_upload_lock = threading.Lock()

# Cached store base URL (e.g. ``https://abc123.public.blob.vercel-storage.com``).
# Resolved lazily from the first ``vercel_blob.list`` call so we can construct
# media URLs without an extra round-trip per render.
_blob_base_url: Optional[str] = None


def is_enabled() -> bool:
    """Return True if the Blob token is present (i.e. we're on Vercel)."""
    return bool(os.environ.get('BLOB_READ_WRITE_TOKEN'))


def _list(prefix: str = '', limit: int = 1000) -> dict:
    return vercel_blob.list({'prefix': prefix, 'limit': str(limit)})


def _find_blob(pathname: str) -> Optional[dict]:
    """Return the blob metadata dict for the exact ``pathname`` if it exists."""
    if not is_enabled():
        return None
    resp = _list(prefix=pathname, limit=5)
    for blob in resp.get('blobs', []):
        if blob.get('pathname') == pathname:
            return blob
    return None


def _resolve_base_url() -> Optional[str]:
    """Cache and return the public base URL of the Blob store.

    Falls back to ``None`` if the store is empty (no blobs to read the host
    from); callers must handle that case.
    """
    global _blob_base_url
    if _blob_base_url:
        return _blob_base_url
    if not is_enabled():
        return None
    try:
        resp = _list(limit=1)
    except Exception:
        logger.exception('Failed to list Vercel Blob store')
        return None
    blobs = resp.get('blobs', [])
    if not blobs:
        return None
    parsed = urlparse(blobs[0]['url'])
    _blob_base_url = f'{parsed.scheme}://{parsed.netloc}'
    return _blob_base_url


def download_db(local_path: str) -> bool:
    """Pull the canonical SQLite file from Blob into ``local_path``.

    Returns True if a file was downloaded, False if the blob does not yet
    exist (first-ever cold start) or the token is missing.
    """
    if not is_enabled():
        return False
    blob = _find_blob(DB_BLOB_PATH)
    if blob is None:
        return False
    try:
        r = requests.get(blob['downloadUrl'], timeout=30)
        r.raise_for_status()
    except Exception:
        logger.exception('Failed to download SQLite from Blob')
        return False
    os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(r.content)
    return True


def upload_db(local_path: str) -> None:
    """Push the local SQLite file to Blob, overwriting any existing copy.

    Best-effort: any failure is logged and swallowed so a Blob outage doesn't
    take the request down.
    """
    if not is_enabled() or not os.path.exists(local_path):
        return
    try:
        with _db_upload_lock, open(local_path, 'rb') as f:
            data = f.read()
        vercel_blob.put(
            DB_BLOB_PATH,
            data,
            {'addRandomSuffix': 'false', 'allowOverwrite': 'true'},
        )
    except Exception:
        logger.exception('Failed to push SQLite to Blob')


class BlobMediaStorage(Storage):
    """Django Storage backend that persists ``MEDIA_ROOT`` files in Vercel Blob.

    Designed to be used as ``STORAGES['default']`` only when ``BLOB_READ_WRITE_TOKEN``
    is set; on local dev Django falls back to ``FileSystemStorage``. URLs
    returned by ``url()`` are full Blob HTTPS URLs, so templates rendering
    ``{{ obj.image.url }}`` work without any extra config.
    """

    blob_prefix = MEDIA_BLOB_PREFIX

    def _path(self, name: str) -> str:
        return f"{self.blob_prefix}{name.lstrip('/')}"

    def _save(self, name: str, content) -> str:
        if hasattr(content, 'seek'):
            try:
                content.seek(0)
            except Exception:
                pass
        data = content.read()
        vercel_blob.put(
            self._path(name),
            data,
            {'addRandomSuffix': 'false', 'allowOverwrite': 'true'},
        )
        return name

    def _open(self, name: str, mode: str = 'rb'):
        blob = _find_blob(self._path(name))
        if blob is None:
            raise FileNotFoundError(name)
        r = requests.get(blob['downloadUrl'], timeout=30)
        r.raise_for_status()
        return ContentFile(r.content, name=name)

    def url(self, name: str) -> str:
        base = _resolve_base_url()
        if base is None:
            return ''
        return f"{base}/{self._path(name)}"

    def exists(self, name: str) -> bool:
        return _find_blob(self._path(name)) is not None

    def delete(self, name: str) -> None:
        blob = _find_blob(self._path(name))
        if blob is not None:
            try:
                vercel_blob.delete([blob['url']])
            except Exception:
                logger.exception('Failed to delete blob %s', name)

    def size(self, name: str) -> int:
        blob = _find_blob(self._path(name))
        return int(blob['size']) if blob else 0

    def get_available_name(self, name: str, max_length: Optional[int] = None) -> str:
        # We rely on ``allowOverwrite=true`` rather than appending a random
        # suffix so URLs stay stable across re-uploads of the same logical
        # filename.
        return name
