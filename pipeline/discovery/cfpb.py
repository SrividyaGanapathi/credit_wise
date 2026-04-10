"""
CFPB Credit Card Agreement Database (CCDB) scraper.

Under the CARD Act, every credit card issuer must submit their cardholder
agreements to the CFPB quarterly. The CFPB publishes quarterly ZIP archives
at files.consumerfinance.gov/a/assets/bulk_agreements/YYYY_QN.zip

The ZIP is ~1.6 GB of PDFs, but we only need the *directory listing* to
discover card names and issuers. We use remotezip to fetch just the ZIP's
central directory via HTTP Range requests (~few hundred KB instead of 1.6 GB).

ZIP structure:
    Q32025/
        AMERICAN EXPRESS NATIONAL BANK/
            American Express Gold Card Cardmember Agreement.pdf-255468.pdf
            Blue Cash Everyday Card Cardmember Agreement.pdf-255458.pdf
        CHASE BANK USA, N.A./
            Sapphire Preferred Cardmember Agreement.pdf-XXXXXX.pdf
            ...

From this we extract:
    issuer  = directory name  (e.g. "AMERICAN EXPRESS NATIONAL BANK")
    name    = cleaned filename (e.g. "American Express Gold Card")
    source_id = CFPB agreement ID embedded in filename suffix (e.g. "255468")

terms_pdf_url is left NULL here — Layer 1 will download the ZIP and extract
individual PDFs. The ZIP URL + in-zip path are stored in raw_data.
"""

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from remotezip import RemoteZip
from tenacity import retry, stop_after_attempt, wait_exponential

from discovery.base import BaseDiscoveryScraper, DiscoveredCard
from discovery.registry import register

log = logging.getLogger(__name__)

_ARCHIVE_PAGE = "https://www.consumerfinance.gov/credit-cards/agreements/archive/"

# Filename suffixes that indicate this is NOT a card agreement (skip these)
_SKIP_PATTERNS = re.compile(
    r"application.*solicitation|solicitation.*disclosure|pricing\s+information|"
    r"rates?\s+and\s+fees?|summary\s+of\s+changes?|addendum",
    re.IGNORECASE,
)

# Trailing noise to strip from filenames to get a clean card name
_AGREEMENT_SUFFIXES = re.compile(
    r"\s*[-–]?\s*("
    r"cardmember\s+agreement|cardholder\s+agreement|credit\s+card\s+agreement|"
    r"card\s+agreement|member\s+agreement|customer\s+agreement|"
    r"account\s+agreement|rewards?\s+program\s+agreement|"
    r"terms\s+and\s+conditions?|user\s+agreement"
    r").*$",
    re.IGNORECASE,
)

# Dates and version strings at end of name (e.g. "- 2024", "2024-01", "v2")
_DATE_SUFFIX = re.compile(r"\s*[-–]?\s*(20\d{2}[-_]\d{0,2}|20\d{2})\s*$")


@register
class CFPBScraper(BaseDiscoveryScraper):
    source_name = "cfpb"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=20))
    async def discover(self) -> list[DiscoveredCard]:
        zip_url = await self._latest_zip_url()
        log.info("CFPB — reading directory listing from %s", zip_url)

        entries = self._list_zip(zip_url)
        log.info("CFPB — found %d entries in ZIP central directory", len(entries))

        cards = self._parse_entries(entries, zip_url)
        log.info("CFPB — extracted %d distinct card agreements", len(cards))
        return cards

    # ------------------------------------------------------------------
    # Step 1: find the most recent quarterly ZIP URL
    # ------------------------------------------------------------------

    async def _latest_zip_url(self) -> str:
        log.debug("CFPB — fetching archive page %s", _ARCHIVE_PAGE)
        response = await self.get(_ARCHIVE_PAGE)
        soup = BeautifulSoup(response.text, "html.parser")

        # Archive page links directly to ZIP files
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "bulk_agreements" in href and href.endswith(".zip"):
                return href if href.startswith("http") else urljoin(_ARCHIVE_PAGE, href)

        raise RuntimeError("Could not find a quarterly ZIP URL on the CFPB archive page")

    # ------------------------------------------------------------------
    # Step 2: read the ZIP central directory via Range requests
    # ------------------------------------------------------------------

    @staticmethod
    def _list_zip(zip_url: str) -> list[str]:
        """
        Use remotezip to fetch only the ZIP's central directory (~few hundred KB)
        rather than the full 1.6 GB archive. Returns all file paths in the ZIP.
        """
        with RemoteZip(zip_url) as zf:
            return zf.namelist()

    # ------------------------------------------------------------------
    # Step 3: parse entries into DiscoveredCard objects
    # ------------------------------------------------------------------

    def _parse_entries(self, entries: list[str], zip_url: str) -> list[DiscoveredCard]:
        seen: set[tuple[str, str]] = set()
        cards: list[DiscoveredCard] = []

        for path in entries:
            parts = path.rstrip("/").split("/")
            # Expect: QYYYYY / ISSUER / filename.pdf
            if len(parts) != 3 or not parts[2].lower().endswith(".pdf"):
                continue

            _quarter, issuer_raw, filename = parts

            if _SKIP_PATTERNS.search(filename):
                continue

            card_name = self._extract_card_name(filename)
            if not card_name:
                continue

            # Deduplicate: same issuer + card name can appear with multiple IDs
            key = (issuer_raw.upper(), card_name.upper())
            if key in seen:
                continue
            seen.add(key)

            agreement_id = self._extract_agreement_id(filename)

            cards.append(
                DiscoveredCard(
                    issuer=issuer_raw.title(),   # normalizer will canonicalize later
                    name=card_name,
                    card_type=self._infer_card_type(card_name),
                    source_id=agreement_id,
                    raw_data={
                        "zip_url": zip_url,
                        "zip_path": path,
                        "agreement_id": agreement_id,
                        "issuer_raw": issuer_raw,
                    },
                )
            )

        return cards

    @staticmethod
    def _extract_card_name(filename: str) -> str | None:
        """
        Strip the CFPB numeric ID suffix and agreement boilerplate from
        a PDF filename to recover the card's marketing name.

        Example:
            "American Express Gold Card Cardmember Agreement.pdf-255468.pdf"
            → "American Express Gold Card"
        """
        # Remove trailing CFPB agreement ID:  "…Agreement.pdf-255468.pdf" → "…Agreement.pdf"
        name = re.sub(r"\.pdf-\d+\.pdf$", ".pdf", filename, flags=re.IGNORECASE)
        # Remove .pdf extension
        name = re.sub(r"\.pdf$", "", name, flags=re.IGNORECASE)
        # Strip agreement boilerplate from the end
        name = _AGREEMENT_SUFFIXES.sub("", name).strip()
        # Strip trailing date/version strings
        name = _DATE_SUFFIX.sub("", name).strip()
        # Strip leading/trailing punctuation
        name = name.strip(" -–_")

        return name if len(name) > 2 else None

    @staticmethod
    def _extract_agreement_id(filename: str) -> str | None:
        """Extract the CFPB agreement ID from the filename suffix."""
        m = re.search(r"-(\d+)\.pdf$", filename, re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def _infer_card_type(card_name: str) -> str:
        business_keywords = (
            "business", "corporate", "commercial", "ink", "spark",
            "blue for business", "platinum business",
        )
        lower = card_name.lower()
        return "business" if any(k in lower for k in business_keywords) else "personal"
