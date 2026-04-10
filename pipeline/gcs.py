"""
Google Cloud Storage helpers for PDF upload and retrieval.

GCS path convention:
  gs://creditwise-pdfs/
    cfpb/{quarter}/{slug}.pdf          ← CFPB terms/agreement PDFs
    benefits/{YYYY-MM-DD}/{slug}.pdf   ← Benefit guide PDFs

All uploads are idempotent — if the checksum matches what's already in GCS
the upload is skipped. The DB (pdf_store table) is the authoritative record
of what's stored and when.
"""

import hashlib
import io
import logging
import os

from google.cloud import storage
from google.api_core.exceptions import NotFound

log = logging.getLogger(__name__)

_BUCKET_NAME = os.getenv("GCS_BUCKET", "creditwise-pdfs")

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def gcs_path_for_terms(slug: str, quarter: str) -> str:
    """e.g. cfpb/2025_Q3/chase-sapphire-preferred.pdf"""
    return f"cfpb/{quarter}/{slug}.pdf"


def gcs_path_for_benefits(slug: str, date_str: str) -> str:
    """e.g. benefits/2026-04-09/chase-sapphire-preferred.pdf"""
    return f"benefits/{date_str}/{slug}.pdf"


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_exists_with_checksum(gcs_path: str, expected_checksum: str) -> bool:
    """
    Return True if a blob at gcs_path already exists and its SHA-256
    metadata matches expected_checksum. Avoids redundant re-uploads.
    """
    try:
        client = _get_client()
        bucket = client.bucket(_BUCKET_NAME)
        blob = bucket.get_blob(gcs_path)
        if blob is None:
            return False
        stored = (blob.metadata or {}).get("sha256")
        return stored == expected_checksum
    except Exception as exc:
        log.debug("GCS existence check failed for %s: %s", gcs_path, exc)
        return False


def upload_pdf(data: bytes, gcs_path: str, source_url: str | None = None) -> str:
    """
    Upload PDF bytes to GCS at gcs_path.
    Stores the SHA-256 checksum in blob metadata.
    Returns the full gs:// URI.
    """
    client = _get_client()
    bucket = client.bucket(_BUCKET_NAME)
    blob = bucket.blob(gcs_path)

    sha = checksum(data)
    blob.metadata = {"sha256": sha, "source_url": source_url or ""}

    blob.upload_from_file(
        io.BytesIO(data),
        content_type="application/pdf",
    )

    uri = f"gs://{_BUCKET_NAME}/{gcs_path}"
    log.debug("Uploaded %d bytes → %s", len(data), uri)
    return uri
