import os

# Database — same Postgres instance as the backend
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/cardwise",
)

# HTTP behaviour
REQUEST_TIMEOUT: int = 30       # seconds per request
REQUEST_DELAY: float = 2.0      # polite delay between requests to same host
MAX_RETRIES: int = 3

# Enrichment tuning
ENRICHMENT_BATCH: int = int(os.getenv("ENRICHMENT_BATCH", "100"))   # cards per run
ENRICHMENT_CHUNK: int = int(os.getenv("ENRICHMENT_CHUNK", "10"))    # cards per Claude call

# Identifies the pipeline to sites we scrape
USER_AGENT: str = (
    "CreditWiseBot/1.0 (+https://github.com/your-org/credit-wise; "
    "data-pipeline/discovery; contact: yourteam@example.com)"
)

# Cards not seen within this window are flagged as potentially discontinued
STALE_DAYS: int = 14
