"""
PDF URL validator.

After the enricher writes URLs into card_registry, this module verifies each
one with an HTTP HEAD request. A URL that doesn't resolve, returns a non-200
status, or isn't content-typed as a PDF gets nulled out so the enricher will
retry it on the next weekly run.

This is the safety net that prevents Claude hallucinations from landing in
the database as permanent bad data.
"""

import asyncio
import logging

import httpx

from config import REQUEST_TIMEOUT, USER_AGENT
from db import get_cards_with_pdf_urls, null_out_url

log = logging.getLogger(__name__)

# Columns we validate — must match the whitelist in db.null_out_url
_PDF_COLS = ["benefits_pdf_url", "terms_pdf_url"]

# Some PDF servers respond to HEAD with 405; retry as GET with Range to avoid
# downloading the whole file
_RANGE_HEADER = {"Range": "bytes=0-1023"}


async def validate_pdf_urls() -> None:
    """
    Check every non-null PDF URL in card_registry.
    Invalid URLs are nulled out in-place.
    """
    cards = get_cards_with_pdf_urls()
    if not cards:
        log.info("Validator — no PDF URLs to validate")
        return

    log.info("Validator — checking %d cards for valid PDF URLs", len(cards))

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        tasks = [_validate_card(client, card) for card in cards]
        await asyncio.gather(*tasks, return_exceptions=True)


async def _validate_card(client: httpx.AsyncClient, card: dict) -> None:
    for col in _PDF_COLS:
        url = card.get(col)
        if not url:
            continue

        ok = await _url_is_valid_pdf(client, url)
        if not ok:
            log.warning(
                "Validator — nulling bad URL for %s – %s (%s): %s",
                card["issuer"], card["name"], col, url,
            )
            null_out_url(card["id"], col)
        else:
            log.debug(
                "Validator — OK  %s – %s (%s)",
                card["issuer"], card["name"], col,
            )


async def _url_is_valid_pdf(client: httpx.AsyncClient, url: str) -> bool:
    """
    Return True if the URL serves a PDF.
    Strategy: HEAD first, fall back to partial GET if HEAD is not supported.
    """
    try:
        response = await client.head(url)
        if response.status_code == 405:
            # Server doesn't support HEAD — do a partial GET instead
            response = await client.get(url, headers=_RANGE_HEADER)

        if response.status_code not in (200, 206):
            log.debug("Validator — HTTP %s for %s", response.status_code, url)
            return False

        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type:
            # Some servers don't set Content-Type correctly on HEAD —
            # check if the URL path strongly implies PDF before rejecting
            if url.lower().endswith(".pdf"):
                return True
            log.debug("Validator — non-PDF content-type '%s' for %s", content_type, url)
            return False

        return True

    except httpx.TimeoutException:
        log.debug("Validator — timeout for %s", url)
        return False
    except httpx.RequestError as exc:
        log.debug("Validator — request error for %s: %s", url, exc)
        return False
