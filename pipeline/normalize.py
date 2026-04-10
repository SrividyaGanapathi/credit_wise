"""
Canonicalize issuer names, card networks, and generate URL-safe slugs.
Add entries to the maps as new issuers/networks are encountered.
"""

import re
import unicodedata

# Raw string (lowercased) → canonical display name
ISSUER_ALIASES: dict[str, str] = {
    "jpmorgan chase": "Chase",
    "jpmorgan": "Chase",
    "chase bank": "Chase",
    "chase bank usa": "Chase",
    "american express": "Amex",
    "amex": "Amex",
    "bank of america": "Bank of America",
    "bank of america, n.a.": "Bank of America",
    "bofa": "Bank of America",
    "capital one": "Capital One",
    "capital one bank": "Capital One",
    "citibank": "Citi",
    "citi bank": "Citi",
    "citigroup": "Citi",
    "citi": "Citi",
    "wells fargo": "Wells Fargo",
    "wells fargo bank": "Wells Fargo",
    "u.s. bank": "US Bank",
    "us bank": "US Bank",
    "u.s. bank national association": "US Bank",
    "barclays": "Barclays",
    "barclays bank delaware": "Barclays",
    "barclays bank": "Barclays",
    "synchrony": "Synchrony",
    "synchrony bank": "Synchrony",
    "synchrony financial": "Synchrony",
    "discover": "Discover",
    "discover bank": "Discover",
    "usaa": "USAA",
    "usaa federal savings bank": "USAA",
    "navy federal": "Navy Federal",
    "navy federal credit union": "Navy Federal",
    "pnc": "PNC",
    "pnc bank": "PNC",
    "td bank": "TD Bank",
    "td": "TD Bank",
    "hsbc": "HSBC",
    "hsbc bank usa": "HSBC",
    "goldman sachs": "Goldman Sachs",
    "marcus by goldman sachs": "Goldman Sachs",
    "apple card": "Goldman Sachs",
    "bmo": "BMO",
    "bmo harris bank": "BMO",
    "keybank": "KeyBank",
    "key bank": "KeyBank",
    "regions bank": "Regions",
    "fifth third bank": "Fifth Third",
    "truist": "Truist",
    "suntrust bank": "Truist",
    "bb&t": "Truist",
    "first national bank of omaha": "FNBO",
    "fnbo": "FNBO",
    "bread financial": "Bread Financial",
    "comenity bank": "Bread Financial",
    "comenity": "Bread Financial",
}

NETWORK_ALIASES: dict[str, str] = {
    "visa": "Visa",
    "visa signature": "Visa",
    "visa infinite": "Visa",
    "mastercard": "Mastercard",
    "master card": "Mastercard",
    "mastercard world": "Mastercard",
    "mastercard world elite": "Mastercard",
    "american express": "Amex",
    "amex": "Amex",
    "discover": "Discover",
    "unionpay": "UnionPay",
    "union pay": "UnionPay",
}


def normalize_issuer(raw: str) -> str:
    key = raw.strip().lower()
    return ISSUER_ALIASES.get(key, raw.strip().title())


def normalize_network(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    return NETWORK_ALIASES.get(key, raw.strip().title())


def slugify(text: str) -> str:
    """Convert arbitrary text to a lowercase, hyphen-separated ASCII slug."""
    # Decompose unicode (é → e + combining accent) then drop non-ASCII
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    # Drop anything that's not alphanumeric, whitespace, or hyphen
    text = re.sub(r"[^\w\s-]", "", text)
    # Collapse whitespace and underscores to hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Collapse repeated hyphens
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def make_slug(issuer: str, name: str) -> str:
    """Canonical slug for a card: '<issuer>-<name>' in slug form."""
    return slugify(f"{issuer} {name}")
