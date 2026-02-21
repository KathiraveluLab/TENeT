"""
Digital Equity Integration Module

Integrates digital equity analysis with TENeT's database and data models.
Handles data retrieval, analysis computation, and storage.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import Community, HealthcareFacility
from app.digital_equity import (
    analyze_digital_equity,
    DigitalEquityMetrics,
    EquityClassification
)
from app.models import DigitalEquityData, ConfidenceLevel


# Pricing estimates (placeholder - in production, pull from FCC or provider APIs)
# These are rough estimates for Alaska based on provider data
ESTIMATED_BROADBAND_COST = {
    "urban": 80.0,  # Urban areas (Anchorage, Fairbanks, Juneau)
    "suburban": 120.0,  # Suburban/semi-rural
    "rural": 200.0,  # Rural communities
    "remote": 450.0  # Remote/isolated communities (satellite only)
}


def estimate_monthly_cost(
    community: Community,
    download_mbps: Optional[float] = None
) -> Optional[float]:
    """
    Estimate monthly broadband cost for a community.
    
    In production, this would:
    - Query FCC provider data
    - Use actual plan pricing from ISPs
    - Factor in subsidy programs (ACP, etc.)
    
    For now, uses tier-based estimates.
    
    Args:
        community: Community database record
        download_mbps: Advertised/measured download speed
        
    Returns:
        Estimated monthly cost in USD, or None if cannot estimate
    """
    if not community.access_tier:
        return None
    
    tier_to_category = {
        1: "urban",
        2: "suburban",
        3: "rural"
    }
    
    # Check if truly remote (very low population, high isolation)
    if community.population and community.population < 100:
        category = "remote"
    else:
        category = tier_to_category.get(community.access_tier, "suburban")
    
    return ESTIMATED_BROADBAND_COST[category]


def get_census_income(
    community: Community,
    db: Session
) -> Optional[float]:
    """
    Retrieve median household income from census data.
    
    In production, this would:
    - Query ACS 5-Year estimates by ZCTA
    - Handle ZCTA to community mapping
    - Cache results for performance
    
    For prototype, uses rough Alaska estimates by region/tier.
    
    Args:
        community: Community database record
        db: Database session
        
    Returns:
        Annual median household income in USD, or None if not available
    """
    # Alaska statewide median (2024): ~$84,000
    # Urban areas higher, rural lower
    
    tier_income_estimates = {
        1: 90000,  # Urban (Anchorage area ~$95k)
        2: 75000,  # Suburban/semi-rural
        3: 55000   # Rural/remote (lower cost of living, but also lower incomes)
    }
    
    if community.access_tier:
        return tier_income_estimates.get(community.access_tier, 70000)
    
    return 70000  # Alaska average fallback


def get_nearby_facilities(
    community: Community,
    db: Session,
    radius_km: float = 50.0
) -> List[Tuple[float, float]]:
    """
    Retrieve healthcare facilities near a community.
    
    Args:
        community: Community database record
        db: Database session
        radius_km: Search radius in km (default 50km for broad search)
        
    Returns:
        List of (latitude, longitude) tuples for facilities
    """
    # Query all facilities
    # In production, would use spatial query with PostGIS
    facilities = db.query(HealthcareFacility).all()
    
    # Return as coordinate tuples
    return [(f.latitude, f.longitude) for f in facilities]


def compute_digital_equity_for_community(
    community: Community,
    db: Session,
    affordability_threshold: float = 2.0,
    anchor_radius_km: float = 5.0
) -> Optional[DigitalEquityMetrics]:
    """
    Compute complete digital equity analysis for a community.
    
    Args:
        community: Community database record
        db: Database session
        affordability_threshold: Affordability threshold % (default 2.0)
        anchor_radius_km: Community anchor search radius (default 5.0 km)
        
    Returns:
        DigitalEquityMetrics, or None if insufficient data
    """
    # Extract connectivity data
    connectivity_data = community.connectivity_data or {}
    download_mbps = connectivity_data.get("download_mbps")
    
    # Estimate monthly cost
    estimated_monthly_cost = estimate_monthly_cost(community, download_mbps)
    
    # Get census income
    median_household_income = get_census_income(community, db)
    
    # Get nearby facilities
    healthcare_facilities = get_nearby_facilities(community, db)
    
    # Perform analysis
    try:
        metrics = analyze_digital_equity(
            estimated_monthly_cost=estimated_monthly_cost,
            median_household_income=median_household_income,
            download_mbps=download_mbps,
            community_lat=community.latitude,
            community_lon=community.longitude,
            healthcare_facilities=healthcare_facilities,
            affordability_threshold=affordability_threshold,
            anchor_radius_km=anchor_radius_km
        )
        return metrics
    except Exception as e:
        print(f"Error computing digital equity for {community.name}: {e}")
        return None


def convert_to_pydantic(metrics: DigitalEquityMetrics) -> DigitalEquityData:
    """
    Convert DigitalEquityMetrics to Pydantic model for API response.
    
    Args:
        metrics: Computed equity metrics
        
    Returns:
        DigitalEquityData for API serialization
    """
    # Determine confidence based on data availability
    if metrics.affordability_ratio is not None and metrics.nearest_facility_km is not None:
        confidence = ConfidenceLevel.HIGH
    elif metrics.affordability_ratio is not None or metrics.nearest_facility_km is not None:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW
    
    return DigitalEquityData(
        affordability_status=metrics.affordability_status.value,
        affordability_ratio=metrics.affordability_ratio,
        monthly_income=metrics.monthly_income,
        estimated_monthly_cost=metrics.estimated_monthly_cost,
        nearest_facility_km=metrics.nearest_facility_km,
        has_community_anchor=metrics.has_community_anchor,
        facility_count_5km=metrics.facility_count_5km,
        value_index=metrics.value_index,
        equity_classification=metrics.equity_classification.value,
        classification_reason=metrics.classification_reason,
        last_updated=datetime.utcnow().isoformat(),
        confidence=confidence
    )


def update_community_equity_data(
    community: Community,
    db: Session,
    commit: bool = True
) -> bool:
    """
    Compute and store digital equity data for a community.
    
    Args:
        community: Community database record
        db: Database session
        commit: Whether to commit the transaction (default True)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        metrics = compute_digital_equity_for_community(community, db)
        if metrics:
            equity_data = convert_to_pydantic(metrics)
            community.digital_equity_data = equity_data.dict()
            
            if commit:
                db.commit()
            
            return True
        return False
    except Exception as e:
        print(f"Failed to update equity data for {community.name}: {e}")
        db.rollback()
        return False


def batch_update_equity_data(db: Session, limit: Optional[int] = None) -> int:
    """
    Compute and store digital equity data for all communities.
    
    Args:
        db: Database session
        limit: Optional limit on number of communities to process
        
    Returns:
        Number of communities successfully updated
    """
    query = db.query(Community)
    if limit:
        query = query.limit(limit)
    
    communities = query.all()
    updated_count = 0
    
    for community in communities:
        if update_community_equity_data(community, db, commit=False):
            updated_count += 1
    
    db.commit()
    print(f"Updated digital equity data for {updated_count}/{len(communities)} communities")
    
    return updated_count
