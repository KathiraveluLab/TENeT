"""
Data Transparency / Coverage Module

Computes data coverage statistics so researchers can gauge
the completeness of the underlying datasets.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.database import Community, HealthcareFacility, BroadbandCoverage


def compute_coverage(db: Session) -> Dict[str, Any]:
    """
    Return data-coverage statistics across all communities.

    Metrics:
      - pct_with_income_data
      - pct_with_broadband_data
      - pct_with_clinic_proximity
      - total_communities
      - total_facilities
      - total_broadband_records
      - data_timestamps
    """
    communities = db.query(Community).all()
    total = len(communities)

    if total == 0:
        return _empty_coverage()

    has_income = 0
    has_broadband = 0
    has_clinic_proximity = 0

    for c in communities:
        # Income availability: if access_tier is set we derive income
        if c.access_tier is not None:
            has_income += 1

        # Broadband data: stored in connectivity_data JSON
        conn = c.connectivity_data or {}
        if conn.get("download_mbps") is not None:
            has_broadband += 1

        # Clinic proximity: digital_equity_data has nearest_facility_km
        eq = c.digital_equity_data or {}
        if eq.get("nearest_facility_km") is not None:
            has_clinic_proximity += 1

    facility_count = db.query(HealthcareFacility).count()
    broadband_count = db.query(BroadbandCoverage).count()

    # Gather timestamps
    latest_community = (
        db.query(Community.updated_at)
        .order_by(Community.updated_at.desc())
        .first()
    )

    return {
        "total_communities": total,
        "pct_with_income_data": _pct(has_income, total),
        "pct_with_broadband_data": _pct(has_broadband, total),
        "pct_with_clinic_proximity": _pct(has_clinic_proximity, total),
        "total_facilities": facility_count,
        "total_broadband_records": broadband_count,
        "data_timestamps": {
            "communities_last_updated": (
                latest_community[0].isoformat() if latest_community and latest_community[0] else None
            ),
            "coverage_computed_at": datetime.now(timezone.utc).isoformat(),
        },
        "dataset_version": "0.3.0",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _pct(count: int, total: int) -> float:
    return round((count / total) * 100, 1) if total else 0.0


def _empty_coverage() -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "total_communities": 0,
        "pct_with_income_data": 0.0,
        "pct_with_broadband_data": 0.0,
        "pct_with_clinic_proximity": 0.0,
        "total_facilities": 0,
        "total_broadband_records": 0,
        "data_timestamps": {
            "communities_last_updated": None,
            "coverage_computed_at": now,
        },
        "dataset_version": "0.3.0",
        "generation_timestamp": now,
    }
