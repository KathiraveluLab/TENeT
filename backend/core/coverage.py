"""
Data Transparency / Coverage Module

Computes data coverage statistics so researchers can gauge
the completeness of the underlying datasets.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import case, func
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
    # ── Single aggregation query instead of loading every row ──
    row = (
        db.query(
            func.count(Community.id).label("total"),
            func.sum(case((Community.access_tier.isnot(None), 1), else_=0)).label("has_income"),
            func.sum(
                case(
                    (func.json_extract(Community.connectivity_data, "$.download_mbps").isnot(None), 1),
                    else_=0,
                )
            ).label("has_broadband"),
            func.sum(
                case(
                    (func.json_extract(Community.digital_equity_data, "$.nearest_facility_km").isnot(None), 1),
                    else_=0,
                )
            ).label("has_clinic_proximity"),
        )
        .one()
    )

    total = row.total or 0
    if total == 0:
        return _empty_coverage()

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
        "pct_with_income_data": _pct(row.has_income or 0, total),
        "pct_with_broadband_data": _pct(row.has_broadband or 0, total),
        "pct_with_clinic_proximity": _pct(row.has_clinic_proximity or 0, total),
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
