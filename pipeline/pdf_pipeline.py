"""
PDF Download & GCS Storage
============================
For each card in card_registry, downloads its PDFs and stores them in GCS.

Two PDF sources:
  1. CFPB terms PDF  — extracted from the quarterly ZIP via HTTP Range request
                       (remotezip, no full 1.6 GB download)
  2. Benefits PDF    — fetched from benefits_pdf_url when available

Change detection:
  - Compute SHA-256 of downloaded bytes
  - Compare against pdf_store.checksum for the current record
  - Skip GCS upload if unchanged; still update downloaded_at

Environment variables:
  PDF_BATCH       Max cards to process per run (default 200)
  GCS_BUCKET      GCS bucket name (default creditwise-pdfs)
"""

import asyncio
import io
import logging
import os
import re
from datetime import date

import httpx
from remotezip import RemoteZip

from config import REQUEST_TIMEOUT, USER_AGENT
from db import (
    get_cards_for_pdf_download,
    get_current_checksum,
    record_pdf,
)
from gcs import (
    blob_exists_with_checksum,
    checksum,
    gcs_path_for_benefits,
    gcs_path_for_terms,
    upload_pdf,
)

log = logging.getLogger(__name__)

_TODAY = date.today().isoformat()


async def run_pdf_download() -> None:
    limit = int(os.getenv("PDF_BATCH", "200"))
    cards = get_cards_for_pdf_download(limit=limit)

    if not cards:
        log.info("PDF pipeline —no cards need PDF downloads")
        return

    log.info("PDF pipeline —downloading PDFs for %d cards", len(cards))

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as http:
        tasks = [_process_card(http, card) for card in cards]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    downloaded = sum(1 for r in results if r is True)
    skipped = sum(1 for r in results if r is False)
    errors = sum(1 for r in results if isinstance(r, Exception))
    log.info(
        "Layer 1 done — %d downloaded, %d unchanged, %d errors",
        downloaded, skipped, errors,
    )


async def _process_card(http: httpx.AsyncClient, card: dict) -> bool:
    """
    Download and store PDFs for one card.
    Returns True if anything was newly uploaded, False if all unchanged.
    """
    did_upload = False

    # ── Terms PDF (CFPB ZIP) ────────────────────────────────────────────────
    if not card.get("has_terms"):
        ok = await _fetch_terms_pdf(card)
        if ok:
            did_upload = True

    # ── Benefits PDF ────────────────────────────────────────────────────────
    if card.get("benefits_pdf_url") and not card.get("has_benefits"):
        ok = await _fetch_benefits_pdf(http, card)
        if ok:
            did_upload = True

    return did_upload


async def _fetch_terms_pdf(card: dict) -> bool:
    """
    Extract the card's terms PDF from the CFPB quarterly ZIP using remotezip.
    Runs in a thread pool since remotezip is synchronous.
    """
    zip_url = card.get("zip_url")
    zip_path = card.get("zip_path")
    if not zip_url or not zip_path:
        return False

    quarter = _quarter_from_zip_url(zip_url)
    gcs_path = gcs_path_for_terms(card["slug"], quarter)

    try:
        data = await asyncio.get_event_loop().run_in_executor(
            None, _extract_from_zip, zip_url, zip_path
        )
    except Exception as exc:
        log.warning("PDF pipeline —failed to extract terms PDF for %s: %s", card["name"], exc)
        return False

    return _store_pdf(
        card=card,
        data=data,
        pdf_type="terms",
        gcs_path=gcs_path,
        source_url=zip_url,
        quarter=quarter,
    )


def _extract_from_zip(zip_url: str, zip_path: str) -> bytes:
    """Synchronous: uses remotezip Range requests to extract one file."""
    with RemoteZip(zip_url) as zf:
        with zf.open(zip_path) as f:
            return f.read()


async def _fetch_benefits_pdf(http: httpx.AsyncClient, card: dict) -> bool:
    """Download the benefits guide PDF from its direct URL."""
    url = card["benefits_pdf_url"]
    gcs_path = gcs_path_for_benefits(card["slug"], _TODAY)

    try:
        response = await http.get(url)
        response.raise_for_status()
        data = response.content
    except Exception as exc:
        log.warning(
            "PDF pipeline —failed to fetch benefits PDF for %s: %s", card["name"], exc
        )
        return False

    return _store_pdf(
        card=card,
        data=data,
        pdf_type="benefits",
        gcs_path=gcs_path,
        source_url=url,
        quarter=None,
    )


def _store_pdf(
    card: dict,
    data: bytes,
    pdf_type: str,
    gcs_path: str,
    source_url: str | None,
    quarter: str | None,
) -> bool:
    """
    Compute checksum, skip if unchanged, otherwise upload to GCS and
    record in pdf_store. Returns True if newly uploaded.
    """
    sha = checksum(data)

    # Skip if content unchanged since last download
    existing = get_current_checksum(card["id"], pdf_type)
    if existing == sha:
        log.debug(
            "PDF pipeline —%s %s PDF unchanged (checksum match), skipping",
            card["name"], pdf_type,
        )
        return False

    # Skip GCS upload if blob already exists with same checksum
    if not blob_exists_with_checksum(gcs_path, sha):
        try:
            upload_pdf(data, gcs_path, source_url)
        except Exception as exc:
            log.error(
                "PDF pipeline —GCS upload failed for %s %s: %s",
                card["name"], pdf_type, exc,
            )
            return False

    record_pdf(
        card_id=card["id"],
        pdf_type=pdf_type,
        gcs_path=f"gs://creditwise-pdfs/{gcs_path}",
        checksum=sha,
        file_size_bytes=len(data),
        source_url=source_url,
        quarter=quarter,
    )
    log.info(
        "PDF pipeline —stored %s %s PDF → gs://creditwise-pdfs/%s (%d KB)",
        card["name"], pdf_type, gcs_path, len(data) // 1024,
    )
    return True


def _quarter_from_zip_url(zip_url: str) -> str:
    """Extract quarter string from ZIP URL, e.g. '2025_Q3' from '.../2025_Q3.zip'."""
    m = re.search(r"(\d{4}_Q\d)", zip_url)
    return m.group(1) if m else "unknown"
