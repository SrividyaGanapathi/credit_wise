"""
Card Data Pipeline — entry point for the weekly Cloud Run Job.

Steps (each can be skipped via env vars for local testing):
  1. DB health check     — fail fast if Postgres is unreachable
  2. CFPB discovery      — populate card_registry from government API
  3. Stale-card sweep    — mark cards not seen recently as inactive
  4. LLM enrichment      — ask Claude for missing benefit guide PDF URLs
  5. PDF URL validation  — HTTP HEAD check; null out any bad URLs
  6. PDF download → GCS  — store PDFs in Cloud Storage, track in pdf_store

Environment variables:
  DATABASE_URL        Postgres connection string (required)
  ANTHROPIC_API_KEY   Required for the enrichment step
  GCS_BUCKET          GCS bucket name (default: creditwise-pdfs)
  SKIP_ENRICHMENT     Set to "true" to skip step 4
  SKIP_VALIDATION     Set to "true" to skip step 5
  SKIP_PDF_DOWNLOAD   Set to "true" to skip step 6
  ENRICHMENT_BATCH    Max cards to enrich per run (default: 100)
  ENRICHMENT_CHUNK    Cards per Claude call (default: 10)
  PDF_BATCH           Max cards to download PDFs for per run (default: 200)
"""

import asyncio
import json
import logging
import os
import sys

from config import STALE_DAYS
from db import check_db, mark_stale_cards, upsert_card
from discovery.cfpb import CFPBScraper
from discovery.enricher import enrich_missing_urls
from pdf_pipeline import run_pdf_download
from normalize import make_slug, normalize_issuer, normalize_network
from validator import validate_pdf_urls

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


async def main() -> None:
    log.info("══════════════════════════════════════")
    log.info("  CreditWise — Card Data Pipeline")
    log.info("══════════════════════════════════════")

    # ── Step 1: DB health check ─────────────────────────────────────────────
    log.info("Step 1/5 — DB health check")
    if not check_db():
        log.error("Cannot reach database. Exiting.")
        sys.exit(1)

    # ── Step 2: CFPB discovery ──────────────────────────────────────────────
    log.info("Step 2/5 — CFPB discovery")
    scraper = CFPBScraper()
    try:
        discovered = await scraper.discover()
    except Exception as exc:
        log.error("CFPB scraper failed: %s", exc)
        sys.exit(1)
    finally:
        await scraper.close()

    log.info("Discovered %d cards — upserting into card_registry", len(discovered))
    upserted = 0
    for card in discovered:
        issuer = normalize_issuer(card.issuer)
        network = normalize_network(card.network)
        slug = make_slug(issuer, card.name)
        try:
            upsert_card({
                "slug": slug,
                "issuer": issuer,
                "name": card.name,
                "network": network,
                "card_type": card.card_type,
                "annual_fee_usd": card.annual_fee_usd,
                "product_url": card.product_url,
                "benefits_pdf_url": card.benefits_pdf_url,
                "terms_pdf_url": card.terms_pdf_url,
                "source": scraper.source_name,
                "source_id": card.source_id,
                "raw_data": card.raw_data or {},
            })
            upserted += 1
        except Exception as exc:
            log.error("Failed to upsert %s – %s: %s", issuer, card.name, exc)

    log.info("Upserted %d / %d cards", upserted, len(discovered))

    # ── Step 3: Stale-card sweep ────────────────────────────────────────────
    log.info("Step 3/5 — Stale-card sweep (threshold: %d days)", STALE_DAYS)
    stale = mark_stale_cards()
    if stale:
        log.warning("Marked %d cards as potentially discontinued", stale)
    else:
        log.info("No stale cards found")

    # ── Step 4: LLM enrichment ──────────────────────────────────────────────
    if os.getenv("SKIP_ENRICHMENT", "false").lower() == "true":
        log.info("Step 4/5 — Enrichment skipped (SKIP_ENRICHMENT=true)")
    else:
        log.info("Step 4/5 — LLM enrichment (benefit guide PDF URLs)")
        batch = int(os.getenv("ENRICHMENT_BATCH", "50"))
        await enrich_missing_urls(batch_size=batch)

    # ── Step 5: PDF URL validation ──────────────────────────────────────────
    if os.getenv("SKIP_VALIDATION", "false").lower() == "true":
        log.info("Step 5/6 — Validation skipped (SKIP_VALIDATION=true)")
    else:
        log.info("Step 5/6 — Validating PDF URLs")
        await validate_pdf_urls()

    # ── Step 6: PDF download → GCS ──────────────────────────────────────────
    if os.getenv("SKIP_PDF_DOWNLOAD", "false").lower() == "true":
        log.info("Step 6/6 — PDF download skipped (SKIP_PDF_DOWNLOAD=true)")
    else:
        log.info("Step 6/6 — Downloading PDFs → GCS")
        await run_pdf_download()

    log.info("══════════════════════════════════════")
    log.info("  Pipeline complete")
    log.info("══════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
