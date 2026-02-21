"""
Digital Equity Analysis Module

Implements the Digital Equity Layer to evaluate real-world telehealth access
based on affordability, continuity of care, and pricing equity.

Key Concepts:
- Affordability Gate: Hard threshold based on UN Broadband Commission (2% of income)
- Continuity of Care: Spatial evaluation of community healthcare anchors
- Value Index: Cost per Mbps to expose pricing inequities

This shifts TENeT's focus from infrastructure availability to meaningful access.
"""

import math
from typing import Optional, Tuple, List
from enum import Enum
from pydantic import BaseModel, Field


class AffordabilityStatus(str, Enum):
    """Affordability classification based on 2% income threshold"""
    AFFORDABLE = "affordable"
    UNAFFORDABLE = "unaffordable"
    INSUFFICIENT_DATA = "insufficient_data"


class EquityClassification(str, Enum):
    """
    Overall digital equity classification combining affordability and community support.
    
    - READY: Affordable home internet, meaningful access available
    - SUPPORTED: Unaffordable home internet, but healthcare facility nearby (community anchor)
    - EXCLUDED: Unaffordable home internet, no nearby healthcare facility (critical gap)
    - INSUFFICIENT_DATA: Cannot determine due to missing data
    """
    READY = "ready"  # Green - Affordable
    SUPPORTED = "supported"  # Yellow - Community safety net exists
    EXCLUDED = "excluded"  # Red - Critical exclusion
    INSUFFICIENT_DATA = "insufficient_data"  # Gray


class DigitalEquityMetrics(BaseModel):
    """Complete digital equity analysis for a community"""
    
    # Affordability metrics
    affordability_status: AffordabilityStatus
    affordability_ratio: Optional[float] = Field(
        None, 
        description="Monthly cost as percentage of monthly income (e.g., 2.5 for 2.5%)"
    )
    monthly_income: Optional[float] = Field(None, description="Median monthly household income (USD)")
    estimated_monthly_cost: Optional[float] = Field(None, description="Estimated monthly broadband cost (USD)")
    
    # Continuity of care metrics
    nearest_facility_km: Optional[float] = Field(None, description="Distance to nearest healthcare facility (km)")
    has_community_anchor: bool = Field(False, description="Healthcare facility within 5km radius")
    facility_count_5km: int = Field(0, description="Number of healthcare facilities within 5km")
    
    # Value/pricing equity metrics
    value_index: Optional[float] = Field(None, description="Cost per Mbps (lower is better)")
    download_mbps: Optional[float] = Field(None, description="Download speed in Mbps")
    
    # Overall classification
    equity_classification: EquityClassification
    classification_reason: str = Field(..., description="Explanation of classification")


def calculate_affordability_ratio(
    estimated_monthly_cost: float,
    median_household_income: float
) -> float:
    """
    Calculate affordability ratio: (Monthly Cost / Monthly Income) × 100
    
    Args:
        estimated_monthly_cost: Estimated monthly broadband cost in USD
        median_household_income: Annual median household income in USD
        
    Returns:
        Affordability ratio as a percentage (e.g., 2.5 for 2.5%)
    """
    if median_household_income <= 0:
        raise ValueError("Median household income must be positive")
    
    monthly_income = median_household_income / 12.0
    ratio = (estimated_monthly_cost / monthly_income) * 100
    return ratio


def check_affordability(
    estimated_monthly_cost: Optional[float],
    median_household_income: Optional[float],
    threshold_percent: float = 2.0
) -> Tuple[AffordabilityStatus, Optional[float]]:
    """
    Apply the affordability gate based on UN Broadband Commission standard.
    
    Args:
        estimated_monthly_cost: Estimated monthly broadband cost in USD
        median_household_income: Annual median household income in USD
        threshold_percent: Affordability threshold (default 2.0 = 2% of income)
        
    Returns:
        Tuple of (AffordabilityStatus, affordability_ratio)
    """
    if estimated_monthly_cost is None or median_household_income is None:
        return AffordabilityStatus.INSUFFICIENT_DATA, None
    
    if median_household_income <= 0:
        return AffordabilityStatus.INSUFFICIENT_DATA, None
    
    ratio = calculate_affordability_ratio(estimated_monthly_cost, median_household_income)
    
    if ratio > threshold_percent:
        return AffordabilityStatus.UNAFFORDABLE, ratio
    else:
        return AffordabilityStatus.AFFORDABLE, ratio


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def check_community_anchor(
    community_lat: float,
    community_lon: float,
    facilities: List[Tuple[float, float]],
    radius_km: float = 5.0
) -> Tuple[bool, int, Optional[float]]:
    """
    Check if community has healthcare facilities within specified radius (community anchor).
    
    Args:
        community_lat: Community latitude
        community_lon: Community longitude
        facilities: List of (lat, lon) tuples for healthcare facilities
        radius_km: Search radius in kilometers (default 5.0 km)
        
    Returns:
        Tuple of (has_anchor, facility_count, nearest_distance_km)
    """
    if not facilities:
        return False, 0, None
    
    distances = []
    for fac_lat, fac_lon in facilities:
        dist = calculate_distance_km(community_lat, community_lon, fac_lat, fac_lon)
        distances.append(dist)
    
    nearest_distance = min(distances)
    facilities_within_radius = sum(1 for d in distances if d <= radius_km)
    has_anchor = facilities_within_radius > 0
    
    return has_anchor, facilities_within_radius, nearest_distance


def calculate_value_index(
    estimated_monthly_cost: Optional[float],
    download_mbps: Optional[float]
) -> Optional[float]:
    """
    Calculate Value Index: Cost per Mbps.
    
    Lower values indicate better value/pricing equity.
    High values expose pricing inequities (e.g., rural price gouging).
    
    Args:
        estimated_monthly_cost: Estimated monthly broadband cost in USD
        download_mbps: Download speed in Mbps
        
    Returns:
        Cost per Mbps, or None if data is insufficient
    """
    if estimated_monthly_cost is None or download_mbps is None:
        return None
    
    if download_mbps <= 0:
        return None
    
    return estimated_monthly_cost / download_mbps


def classify_digital_equity(
    affordability_status: AffordabilityStatus,
    has_community_anchor: bool,
    affordability_ratio: Optional[float] = None
) -> Tuple[EquityClassification, str]:
    """
    Determine overall digital equity classification.
    
    Decision tree:
    1. If insufficient data → INSUFFICIENT_DATA
    2. If affordable → READY (green)
    3. If unaffordable + community anchor → SUPPORTED (yellow)
    4. If unaffordable + no anchor → EXCLUDED (red)
    
    Args:
        affordability_status: Result from affordability check
        has_community_anchor: Whether healthcare facility exists within 5km
        affordability_ratio: Optional affordability ratio for detailed reasoning
        
    Returns:
        Tuple of (EquityClassification, explanation)
    """
    if affordability_status == AffordabilityStatus.INSUFFICIENT_DATA:
        return (
            EquityClassification.INSUFFICIENT_DATA,
            "Insufficient data to determine affordability"
        )
    
    if affordability_status == AffordabilityStatus.AFFORDABLE:
        ratio_str = f"{affordability_ratio:.1f}%" if affordability_ratio else ""
        return (
            EquityClassification.READY,
            f"Affordable home internet access (cost {ratio_str} of income, below 2% threshold)"
        )
    
    # Unaffordable case - check for community safety net
    if has_community_anchor:
        return (
            EquityClassification.SUPPORTED,
            "Home internet unaffordable, but healthcare facility within 5km provides community anchor for telehealth access"
        )
    else:
        return (
            EquityClassification.EXCLUDED,
            "Critical exclusion: home internet unaffordable and no nearby healthcare facility (continuity of care gap)"
        )


def analyze_digital_equity(
    estimated_monthly_cost: Optional[float],
    median_household_income: Optional[float],
    download_mbps: Optional[float],
    community_lat: float,
    community_lon: float,
    healthcare_facilities: List[Tuple[float, float]],
    affordability_threshold: float = 2.0,
    anchor_radius_km: float = 5.0
) -> DigitalEquityMetrics:
    """
    Perform complete digital equity analysis for a community.
    
    This is the main entry point for the Digital Equity Layer.
    
    Args:
        estimated_monthly_cost: Estimated monthly broadband cost in USD
        median_household_income: Annual median household income in USD
        download_mbps: Download speed in Mbps
        community_lat: Community latitude
        community_lon: Community longitude
        healthcare_facilities: List of (lat, lon) tuples for nearby facilities
        affordability_threshold: Affordability threshold as percentage (default 2.0)
        anchor_radius_km: Community anchor search radius (default 5.0 km)
        
    Returns:
        Complete DigitalEquityMetrics analysis
    """
    # Step 1: Check affordability
    affordability_status, affordability_ratio = check_affordability(
        estimated_monthly_cost,
        median_household_income,
        affordability_threshold
    )
    
    # Step 2: Check for community anchor (continuity of care)
    has_anchor, facility_count, nearest_distance = check_community_anchor(
        community_lat,
        community_lon,
        healthcare_facilities,
        anchor_radius_km
    )
    
    # Step 3: Calculate value index (pricing equity)
    value_index = calculate_value_index(estimated_monthly_cost, download_mbps)
    
    # Step 4: Classify overall equity status
    equity_classification, reason = classify_digital_equity(
        affordability_status,
        has_anchor,
        affordability_ratio
    )
    
    # Step 5: Assemble complete metrics
    monthly_income = median_household_income / 12.0 if median_household_income else None
    
    return DigitalEquityMetrics(
        affordability_status=affordability_status,
        affordability_ratio=affordability_ratio,
        monthly_income=monthly_income,
        estimated_monthly_cost=estimated_monthly_cost,
        nearest_facility_km=nearest_distance,
        has_community_anchor=has_anchor,
        facility_count_5km=facility_count,
        value_index=value_index,
        download_mbps=download_mbps,
        equity_classification=equity_classification,
        classification_reason=reason
    )
