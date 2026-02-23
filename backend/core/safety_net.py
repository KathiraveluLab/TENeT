"""
Community Safety Net Logic

Evaluates whether a community has a healthcare safety net when
broadband is unaffordable.

Outcomes:
  - Unaffordable + Clinic Nearby   → Partial Access  ("supported")
  - Unaffordable + No Clinic       → Critical Exclusion ("excluded")
"""

from typing import Optional, List, Tuple
from app.digital_equity import (
    AffordabilityStatus,
    check_community_anchor,
)


def evaluate_safety_net(
    affordability_status: AffordabilityStatus,
    community_lat: float,
    community_lon: float,
    healthcare_facilities: List[Tuple[float, float]],
    anchor_radius_km: float = 5.0,
) -> dict:
    """
    Evaluate community safety net status.

    Returns dict with:
      - safety_net_status: "not_applicable" | "partial_access" | "critical_exclusion" | "insufficient_data"
      - has_nearby_clinic: bool
      - nearest_facility_km: float | None
      - facility_count_in_radius: int
    """
    if affordability_status == AffordabilityStatus.INSUFFICIENT_DATA:
        return {
            "safety_net_status": "insufficient_data",
            "has_nearby_clinic": False,
            "nearest_facility_km": None,
            "facility_count_in_radius": 0,
        }

    if affordability_status == AffordabilityStatus.AFFORDABLE:
        has_anchor, count, nearest = check_community_anchor(
            community_lat, community_lon, healthcare_facilities, anchor_radius_km
        )
        return {
            "safety_net_status": "not_applicable",
            "has_nearby_clinic": has_anchor,
            "nearest_facility_km": round(nearest, 2) if nearest else None,
            "facility_count_in_radius": count,
        }

    # Unaffordable path
    has_anchor, count, nearest = check_community_anchor(
        community_lat, community_lon, healthcare_facilities, anchor_radius_km
    )

    if has_anchor:
        return {
            "safety_net_status": "partial_access",
            "has_nearby_clinic": True,
            "nearest_facility_km": round(nearest, 2) if nearest else None,
            "facility_count_in_radius": count,
        }
    else:
        return {
            "safety_net_status": "critical_exclusion",
            "has_nearby_clinic": False,
            "nearest_facility_km": round(nearest, 2) if nearest else None,
            "facility_count_in_radius": count,
        }
