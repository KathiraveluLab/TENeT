"""
Core Digital Equity Analysis Module

Re-exports and extends the existing digital equity engine with
parameterized thresholds for simulation support.
"""

from typing import Optional, List, Tuple
from app.digital_equity import (
    AffordabilityStatus,
    EquityClassification,
    DigitalEquityMetrics,
    check_affordability,
    check_community_anchor,
    calculate_value_index,
    classify_digital_equity,
    analyze_digital_equity,
    calculate_distance_km,
)

__all__ = [
    "AffordabilityStatus",
    "EquityClassification",
    "DigitalEquityMetrics",
    "check_affordability",
    "check_community_anchor",
    "calculate_value_index",
    "classify_digital_equity",
    "analyze_digital_equity",
    "calculate_distance_km",
    "run_equity_analysis",
]


def run_equity_analysis(
    estimated_monthly_cost: Optional[float],
    median_household_income: Optional[float],
    download_mbps: Optional[float],
    community_lat: float,
    community_lon: float,
    healthcare_facilities: List[Tuple[float, float]],
    affordability_threshold: float = 2.0,
    anchor_radius_km: float = 5.0,
) -> DigitalEquityMetrics:
    """
    Convenience wrapper around analyze_digital_equity with explicit
    threshold parameters for simulation engine use.
    """
    return analyze_digital_equity(
        estimated_monthly_cost=estimated_monthly_cost,
        median_household_income=median_household_income,
        download_mbps=download_mbps,
        community_lat=community_lat,
        community_lon=community_lon,
        healthcare_facilities=healthcare_facilities,
        affordability_threshold=affordability_threshold,
        anchor_radius_km=anchor_radius_km,
    )
