"""
Abstract base for all card discovery scrapers.

Each scraper targets one source (NerdWallet, CardRatings, an issuer site, etc.)
and returns a list of DiscoveredCard objects. The run_discovery entry point
normalizes and upserts them into card_registry.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from config import REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT

log = logging.getLogger(__name__)


@dataclass
class DiscoveredCard:
    issuer: str
    name: str
    network: str | None = None
    card_type: str = "personal"           # "personal" | "business"
    annual_fee_usd: int | None = None
    product_url: str | None = None
    benefits_pdf_url: str | None = None
    terms_pdf_url: str | None = None
    source_id: str | None = None          # aggregator's internal card ID
    raw_data: dict = field(default_factory=dict)


class BaseDiscoveryScraper(ABC):
    """
    All scrapers must implement `discover()` and set `source_name`.
    The base class provides a shared httpx client with polite defaults.
    """

    source_name: str  # must be overridden in each subclass

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Fetch a URL with a polite delay and basic error logging."""
        await asyncio.sleep(REQUEST_DELAY)
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            log.warning(
                "%s — HTTP %s for %s",
                self.source_name,
                exc.response.status_code,
                url,
            )
            raise
        except httpx.RequestError as exc:
            log.warning("%s — request failed for %s: %s", self.source_name, url, exc)
            raise

    async def close(self) -> None:
        await self._client.aclose()

    @abstractmethod
    async def discover(self) -> list[DiscoveredCard]:
        """
        Fetch and return all cards discoverable from this source.
        Must be idempotent — safe to call multiple times.
        """
        ...
