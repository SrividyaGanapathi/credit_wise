import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from config import DATABASE_URL, STALE_DAYS

log = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def check_db() -> bool:
    """
    Verify the database is reachable and card_registry table exists.
    Returns True on success, False on any failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 1 FROM card_registry LIMIT 1"))
        log.info("DB health check: OK")
        return True
    except OperationalError as exc:
        log.error("DB health check failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

def upsert_card(card: dict) -> None:
    """
    Insert or update a single card in card_registry using slug as the
    conflict key. Existing non-null values are never overwritten with nulls
    (COALESCE pattern), so multiple sources enrich the same row safely.
    """
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO card_registry (
                    slug, issuer, name, network, card_type, annual_fee_usd,
                    product_url, benefits_pdf_url, terms_pdf_url,
                    source, source_id, is_active,
                    first_seen_at, last_seen_at,
                    raw_data, created_at, updated_at
                ) VALUES (
                    :slug, :issuer, :name, :network, :card_type, :annual_fee_usd,
                    :product_url, :benefits_pdf_url, :terms_pdf_url,
                    :source, :source_id, true,
                    NOW(), NOW(),
                    CAST(:raw_data AS jsonb), NOW(), NOW()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    last_seen_at     = NOW(),
                    updated_at       = NOW(),
                    is_active        = true,
                    network          = COALESCE(EXCLUDED.network,          card_registry.network),
                    annual_fee_usd   = COALESCE(EXCLUDED.annual_fee_usd,   card_registry.annual_fee_usd),
                    product_url      = COALESCE(EXCLUDED.product_url,      card_registry.product_url),
                    benefits_pdf_url = COALESCE(EXCLUDED.benefits_pdf_url, card_registry.benefits_pdf_url),
                    terms_pdf_url    = COALESCE(EXCLUDED.terms_pdf_url,    card_registry.terms_pdf_url),
                    raw_data         = EXCLUDED.raw_data
            """),
            {**card, "raw_data": __import__("json").dumps(card.get("raw_data") or {})},
        )


# ---------------------------------------------------------------------------
# Stale-card sweep
# ---------------------------------------------------------------------------

def mark_stale_cards() -> int:
    """
    Set is_active = false for cards not seen in the last STALE_DAYS days.
    Returns the number of rows updated.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE card_registry
                SET    is_active  = false,
                       updated_at = NOW()
                WHERE  last_seen_at < :cutoff
                  AND  is_active = true
            """),
            {"cutoff": cutoff},
        )
        return result.rowcount


# ---------------------------------------------------------------------------
# Enrichment helpers (used by enricher.py)
# ---------------------------------------------------------------------------

def get_unenriched_cards(limit: int) -> list[dict]:
    """
    Return cards missing a benefit guide PDF URL, prioritized so that
    major issuers (high card volume, widely-held) come first.
    Credit unions and niche issuers come last — they matter less and
    Claude is less likely to know their PDF URLs anyway.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, issuer, name, network,
                       CASE
                         WHEN issuer ILIKE '%chase%'              THEN 1
                         WHEN issuer ILIKE '%american express%'   THEN 1
                         WHEN issuer ILIKE '%citibank%'
                           OR issuer ILIKE '%citi bank%'          THEN 1
                         WHEN issuer ILIKE '%capital one%'        THEN 1
                         WHEN issuer ILIKE '%discover%'           THEN 1
                         WHEN issuer ILIKE '%bank of america%'    THEN 1
                         WHEN issuer ILIKE '%wells fargo%'        THEN 1
                         WHEN issuer ILIKE '%barclays%'           THEN 1
                         WHEN issuer ILIKE '%u.s. bank%'
                           OR issuer ILIKE '%us bank%'            THEN 1
                         WHEN issuer ILIKE '%synchrony%'          THEN 1
                         WHEN issuer ILIKE '%goldman sachs%'      THEN 2
                         WHEN issuer ILIKE '%usaa%'               THEN 2
                         WHEN issuer ILIKE '%navy federal%'       THEN 2
                         WHEN issuer ILIKE '%td bank%'            THEN 2
                         WHEN issuer ILIKE '%pnc%'                THEN 2
                         WHEN issuer ILIKE '%hsbc%'               THEN 2
                         WHEN issuer ILIKE '%comenity%'
                           OR issuer ILIKE '%bread financial%'    THEN 2
                         -- credit unions and small banks last
                         WHEN issuer ILIKE '%credit union%'       THEN 9
                         ELSE 5
                       END AS priority
                FROM   card_registry
                WHERE  benefits_pdf_url IS NULL
                  AND  is_active = true
                ORDER  BY priority ASC, name ASC
                LIMIT  :limit
            """),
            {"limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]


def update_enriched_urls(card_id: int, product_url: str | None, benefits_pdf_url: str | None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE card_registry SET
                    product_url      = COALESCE(:product_url,      product_url),
                    benefits_pdf_url = COALESCE(:benefits_pdf_url, benefits_pdf_url),
                    updated_at       = NOW()
                WHERE id = :id
            """),
            {"id": card_id, "product_url": product_url, "benefits_pdf_url": benefits_pdf_url},
        )


# ---------------------------------------------------------------------------
# Validation helpers (used by validator.py)
# ---------------------------------------------------------------------------

_VALID_URL_COLS = {"benefits_pdf_url", "terms_pdf_url"}


def get_cards_with_pdf_urls() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, issuer, name, benefits_pdf_url, terms_pdf_url
                FROM   card_registry
                WHERE  (benefits_pdf_url IS NOT NULL OR terms_pdf_url IS NOT NULL)
                  AND  is_active = true
            """)
        ).mappings().all()
    return [dict(r) for r in rows]


def null_out_url(card_id: int, col: str) -> None:
    """Blank a PDF URL that failed validation. col must be a known safe column name."""
    if col not in _VALID_URL_COLS:
        raise ValueError(f"Unknown column: {col}")
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE card_registry SET {col} = NULL, updated_at = NOW() WHERE id = :id"),
            {"id": card_id},
        )


# ---------------------------------------------------------------------------
# pdf_store helpers (used by pdf_pipeline.py)
# ---------------------------------------------------------------------------

def get_cards_for_pdf_download(limit: int) -> list[dict]:
    """
    Return cards that need at least one PDF downloaded:
      - terms PDF:    always available via CFPB ZIP (raw_data has zip_path)
      - benefits PDF: available when benefits_pdf_url is set

    Prioritizes cards not yet in pdf_store, then major issuers first.
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    cr.id, cr.slug, cr.issuer, cr.name,
                    cr.benefits_pdf_url,
                    cr.raw_data->>'zip_url'  AS zip_url,
                    cr.raw_data->>'zip_path' AS zip_path,
                    cr.raw_data->>'quarter'  AS quarter,
                    -- has either PDF type already been downloaded?
                    EXISTS (
                        SELECT 1 FROM pdf_store ps
                        WHERE ps.card_id = cr.id AND ps.pdf_type = 'terms' AND ps.is_current
                    ) AS has_terms,
                    EXISTS (
                        SELECT 1 FROM pdf_store ps
                        WHERE ps.card_id = cr.id AND ps.pdf_type = 'benefits' AND ps.is_current
                    ) AS has_benefits
                FROM card_registry cr
                WHERE cr.is_active = true
                  AND cr.raw_data->>'zip_path' IS NOT NULL
                  AND (
                    -- needs terms PDF
                    NOT EXISTS (
                        SELECT 1 FROM pdf_store ps
                        WHERE ps.card_id = cr.id AND ps.pdf_type = 'terms' AND ps.is_current
                    )
                    OR
                    -- needs benefits PDF and URL is known
                    (cr.benefits_pdf_url IS NOT NULL AND NOT EXISTS (
                        SELECT 1 FROM pdf_store ps
                        WHERE ps.card_id = cr.id AND ps.pdf_type = 'benefits' AND ps.is_current
                    ))
                  )
                ORDER BY
                    CASE
                        WHEN cr.issuer ILIKE ANY(ARRAY[
                            '%chase%','%american express%','%citibank%',
                            '%capital one%','%discover%','%bank of america%',
                            '%wells fargo%','%barclays%','%u.s. bank%',
                            '%synchrony%'
                        ]) THEN 1
                        WHEN cr.issuer ILIKE '%credit union%' THEN 9
                        ELSE 5
                    END ASC,
                    cr.name ASC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]


def record_pdf(
    card_id: int,
    pdf_type: str,
    gcs_path: str,
    checksum: str,
    file_size_bytes: int,
    source_url: str | None,
    quarter: str | None,
) -> None:
    """
    Mark any previous current record as superseded, then insert the new one.
    """
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE pdf_store
                SET    is_current = false
                WHERE  card_id = :card_id AND pdf_type = :pdf_type AND is_current = true
            """),
            {"card_id": card_id, "pdf_type": pdf_type},
        )
        conn.execute(
            text("""
                INSERT INTO pdf_store
                    (card_id, pdf_type, gcs_path, checksum, file_size_bytes,
                     source_url, quarter, is_current, downloaded_at, created_at)
                VALUES
                    (:card_id, :pdf_type, :gcs_path, :checksum, :file_size_bytes,
                     :source_url, :quarter, true, NOW(), NOW())
            """),
            {
                "card_id": card_id,
                "pdf_type": pdf_type,
                "gcs_path": gcs_path,
                "checksum": checksum,
                "file_size_bytes": file_size_bytes,
                "source_url": source_url,
                "quarter": quarter,
            },
        )


def get_current_checksum(card_id: int, pdf_type: str) -> str | None:
    """Return the SHA-256 of the currently stored PDF, or None if not yet downloaded."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT checksum FROM pdf_store
                WHERE card_id = :card_id AND pdf_type = :pdf_type AND is_current = true
                LIMIT 1
            """),
            {"card_id": card_id, "pdf_type": pdf_type},
        ).fetchone()
    return row[0] if row else None
