from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from data.database import Base


class PdfStore(Base):
    """
    Tracks every PDF downloaded and stored in GCS for a card.
    One row per (card, pdf_type, quarter/date version).

    pdf_type:
      "terms"    — CFPB cardholder agreement (legal T&C)
      "benefits" — Benefit guide PDF (rewards, perks, protections)

    is_current = true marks the most recent version for a given
    (card_id, pdf_type) pair. Older rows are kept for audit/diff purposes.
    """

    __tablename__ = "pdf_store"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pdf_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # terms | benefits

    gcs_path: Mapped[str] = mapped_column(Text, nullable=False)   # gs://creditwise-pdfs/...
    checksum: Mapped[str] = mapped_column(String, nullable=False)  # SHA-256 hex
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)   # where it was fetched from
    quarter: Mapped[str | None] = mapped_column(String, nullable=True)    # e.g. "2025_Q3" for CFPB PDFs

    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    downloaded_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
