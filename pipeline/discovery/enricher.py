"""
LLM-based URL enricher — batched, prioritized.

Sends 10 cards per Claude call instead of 1, cutting API cost and latency
by ~10x. Cards are fetched in priority order (major issuers first, credit
unions last) so the highest-value cards get enriched in the first few runs.

Cost estimate:
  - 10 cards/call × ~800 tokens/call ≈ $0.003 per call
  - Default batch of 100 cards = 10 Claude calls = ~$0.03/week
  - All major-issuer cards (~200) enriched in 2 weekly runs

Reads:
  ANTHROPIC_API_KEY   required
  ENRICHMENT_BATCH    total cards to process per run (default 100)
  ENRICHMENT_CHUNK    cards per Claude call (default 10)
"""

import json
import logging
import os
import re

import anthropic

from db import get_unenriched_cards, update_enriched_urls

log = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

_BATCH_PROMPT = """\
You are building a credit card benefits database. For each card below, \
return the issuer's official product page URL and a direct URL to the \
card's benefit guide PDF (the document covering rewards, perks, travel \
protections, purchase protections, etc.).

Cards:
{cards_block}

Respond with ONLY a JSON array — one object per card, same order, \
no explanation, no markdown fences:
[
  {{"id": <id>, "product_url": "<URL or null>", "benefits_pdf_url": "<URL or null>"}},
  ...
]

Rules:
- product_url must be on the issuer's official domain
- benefits_pdf_url must be a direct .pdf link or known PDF-serving endpoint
- Return null for any URL you are not highly confident about
- Never fabricate a URL — null is always better than a wrong URL
"""


async def enrich_missing_urls(batch_size: int | None = None) -> None:
    """
    Process up to batch_size cards in chunks of ENRICHMENT_CHUNK,
    sending each chunk to Claude in a single batched API call.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("Enricher skipped — ANTHROPIC_API_KEY not set")
        return

    total = batch_size or int(os.getenv("ENRICHMENT_BATCH", "100"))
    chunk_size = int(os.getenv("ENRICHMENT_CHUNK", "10"))

    cards = get_unenriched_cards(limit=total)
    if not cards:
        log.info("Enricher — all cards already have benefit PDF URLs")
        return

    log.info(
        "Enricher — %d cards to process, %d per Claude call",
        len(cards), chunk_size,
    )
    client = anthropic.Anthropic(api_key=api_key)

    enriched = total_calls = 0
    for i in range(0, len(cards), chunk_size):
        chunk = cards[i : i + chunk_size]
        total_calls += 1
        results = _ask_claude_batch(client, chunk)

        for card, (product_url, benefits_pdf_url) in zip(chunk, results):
            if product_url or benefits_pdf_url:
                update_enriched_urls(card["id"], product_url, benefits_pdf_url)
                enriched += 1
                log.info(
                    "Enriched  %s – %s → pdf=%s  product=%s",
                    card["issuer"], card["name"],
                    benefits_pdf_url or "—",
                    product_url or "—",
                )

    log.info(
        "Enricher done — %d/%d cards enriched in %d Claude call(s)",
        enriched, len(cards), total_calls,
    )


def _ask_claude_batch(
    client: anthropic.Anthropic,
    cards: list[dict],
) -> list[tuple[str | None, str | None]]:
    """
    Send a chunk of cards to Claude in one call.
    Returns a list of (product_url, benefits_pdf_url) tuples,
    one per card, in the same order. Falls back to (None, None)
    for any card whose result is missing or unparseable.
    """
    cards_block = "\n".join(
        f'{i+1}. id={c["id"]}  "{c["name"]}"  issuer="{c["issuer"]}"'
        f'  network="{c.get("network") or "unknown"}"'
        for i, c in enumerate(cards)
    )
    prompt = _BATCH_PROMPT.format(cards_block=cards_block)

    # Index by id for fast lookup
    id_to_card = {c["id"]: c for c in cards}
    fallback = [(None, None)] * len(cards)

    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=512 + len(cards) * 80,   # scale with chunk size
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        items = json.loads(raw)
        if not isinstance(items, list):
            log.warning("Enricher — expected JSON array, got %s", type(items))
            return fallback

        # Build result list aligned to input order
        results: list[tuple[str | None, str | None]] = []
        returned_ids = {item.get("id") for item in items if isinstance(item, dict)}

        for card in cards:
            match = next(
                (item for item in items
                 if isinstance(item, dict) and item.get("id") == card["id"]),
                None,
            )
            if match:
                results.append((
                    _clean_url(match.get("product_url")),
                    _clean_url(match.get("benefits_pdf_url")),
                ))
            else:
                log.debug("Enricher — no result returned for id=%s", card["id"])
                results.append((None, None))

        return results

    except json.JSONDecodeError:
        log.warning("Enricher — non-JSON response from Claude (chunk of %d)", len(cards))
        return fallback
    except anthropic.APIError as exc:
        log.error("Enricher — API error: %s", exc)
        return fallback


def _clean_url(value: object) -> str | None:
    """Reject nulls, non-strings, and anything that doesn't look like https."""
    if not value or not isinstance(value, str):
        return None
    url = value.strip()
    return url if url.startswith("https://") else None
