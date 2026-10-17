"""
Shared ISP pricing config loader and ZCTA-to-cost lookup.

This is the single source of truth for ISP pricing in the backend.
All modules that need `get_internet_cost` should import from here.

Note: performance_routes.py keeps its own 3-tuple variant because it
additionally returns a description string for its API response.
"""
import os
import json
from typing import Tuple

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "isp_pricing.json")

_FALLBACK_CONFIG = {
    "isp_pricing": {
        "gci": {"name": "GCI", "cost": 125.0},
        "fastwyre": {"name": "FastWyre/Rural", "cost": 350.0},
        "starlink": {"name": "Starlink", "cost": 120.0},
        "extreme_rural": {"name": "Extreme Rural", "cost": 450.0},
    },
    "zcta_mappings": {
        "gci_urban": [],
        "extreme_rural": [],
        "starlink_satellite": [],
    },
    "thresholds": {"affordability_burden_pct": 2.0},
}


def load_isp_config() -> dict:
    """Load ISP pricing config from JSON file, falling back to defaults."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _FALLBACK_CONFIG


# Module-level singleton — loaded once at import time.
ISP_CONFIG: dict = load_isp_config()


def get_internet_cost(zcta: str) -> Tuple[float, str]:
    """
    Return (monthly_cost, isp_name) for a given ZCTA code.

    Lookup order: extreme_rural → gci_urban → starlink_satellite → fastwyre (default).
    Includes the Starlink satellite branch for communities in starlink_satellite ZCTAs.
    """
    try:
        gmap = ISP_CONFIG.get("zcta_mappings", {})
        extreme_rural = set(gmap.get("extreme_rural", []))
        gci_urban = set(gmap.get("gci_urban", []))
        starlink_satellite = set(gmap.get("starlink_satellite", []))
    except Exception:
        extreme_rural = set()
        gci_urban = set()
        starlink_satellite = set()

    pricing = ISP_CONFIG.get("isp_pricing", {})
    if not isinstance(pricing, dict):
        pricing = {}

    if zcta in extreme_rural:
        p = pricing.get("extreme_rural", {"cost": 450.0, "name": "Extreme Rural"})
    elif zcta in gci_urban:
        p = pricing.get("gci", {"cost": 125.0, "name": "GCI"})
    elif zcta in starlink_satellite:
        p = pricing.get("starlink", {"cost": 120.0, "name": "Starlink"})
    else:
        p = pricing.get("fastwyre", {"cost": 350.0, "name": "FastWyre"})

    if not isinstance(p, dict):
        p = {"cost": 350.0, "name": "FastWyre"}

    return float(p.get("cost", 350.0)), str(p.get("name", "FastWyre"))


def get_affordability_threshold() -> float:
    """Return the affordability burden % threshold from config (default 2.0)."""
    value = ISP_CONFIG.get("thresholds", {}).get("affordability_burden_pct", 2.0)
    return float(value) if isinstance(value, (int, float)) else 2.0
