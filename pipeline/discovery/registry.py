"""
Scraper registry — zero hardcoding.

Each scraper file decorates its class with @register. The runner then calls
get_enabled_scrapers() which returns only the scrapers whose source_name
appears in the ENABLED_SCRAPERS env var (or all of them if the var is unset).

Adding a new scraper:
  1. Create a file in pipeline/discovery/ (or pipeline/discovery/issuers/)
  2. Decorate the class with @register
  3. Add its source_name to ENABLED_SCRAPERS in your .env / Cloud Run config
     (or leave ENABLED_SCRAPERS unset to run everything)
"""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discovery.base import BaseDiscoveryScraper

log = logging.getLogger(__name__)

_registry: dict[str, type[BaseDiscoveryScraper]] = {}


def register(cls: type) -> type:
    """Class decorator — call once per scraper class."""
    name = getattr(cls, "source_name", None)
    if not name:
        raise ValueError(f"{cls.__name__} must define source_name")
    if name in _registry:
        log.debug("Registry — overwriting existing scraper for '%s'", name)
    _registry[name] = cls
    return cls


def autodiscover() -> None:
    """
    Import every Python module under pipeline/discovery/ (and sub-packages)
    so that @register decorators fire.  Call this once at startup.
    """
    discovery_root = Path(__file__).parent

    for finder, module_name, _ in pkgutil.walk_packages(
        path=[str(discovery_root)],
        prefix="discovery.",
        onerror=lambda name: log.warning("Could not import %s", name),
    ):
        if module_name == "discovery.registry":
            continue
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            log.warning("Failed to import %s: %s", module_name, exc)


def get_enabled_scrapers() -> list[BaseDiscoveryScraper]:
    """
    Return instantiated scrapers according to the ENABLED_SCRAPERS env var.

    ENABLED_SCRAPERS=cfpb,issuer_chase,issuer_amex   → run those three
    ENABLED_SCRAPERS=                                 → run all registered
    (unset)                                           → run all registered
    """
    raw = os.getenv("ENABLED_SCRAPERS", "").strip()
    if raw:
        names = [n.strip() for n in raw.split(",") if n.strip()]
        missing = [n for n in names if n not in _registry]
        if missing:
            log.warning("Requested scrapers not registered: %s", missing)
        return [_registry[n]() for n in names if n in _registry]

    # No filter — run everything registered
    return [cls() for cls in _registry.values()]


def list_registered() -> list[str]:
    return sorted(_registry.keys())
