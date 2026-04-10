from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from data.database import Base


class CardRegistry(Base):
    """
    Master catalog of all US credit cards discovered by the data pipeline.
    This is the upstream source that feeds into the cards + reward_rules tables
    after PDF collection and LLM extraction (Layers 1-2).
    """

    __tablename__ = "card_registry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Identity ---
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    issuer: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    network: Mapped[str | None] = mapped_column(String, nullable=True)
    card_type: Mapped[str] = mapped_column(String, default="personal")  # personal | business

    # --- Pricing (coarse — exact rules come from PDFs) ---
    annual_fee_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- URLs ---
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Discovery provenance ---
    source: Mapped[str] = mapped_column(String, nullable=False, index=True)  # nerdwallet | cardratings | manual
    source_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Lifecycle ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    first_seen_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # --- Raw scraped payload (for debugging / re-parsing) ---
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
