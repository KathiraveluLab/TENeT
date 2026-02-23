"""
Sensitivity Analysis / Simulation Engine

Allows parameterized re-computation of digital equity metrics
without persisting results to the database.

Endpoint consumers can override:
  - affordability_threshold  (default 2.0 %)
  - clinic_radius_km         (default 5.0 km)
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import Community, HealthcareFacility
from app.digital_equity_integration import (
    estimate_monthly_cost,
    get_census_income,
    get_nearby_facilities,
)
from core.digital_equity import run_equity_analysis
from core.safety_net import evaluate_safety_net
from app.digital_equity import AffordabilityStatus, check_affordability


def simulate_all(
    db: Session,
    affordability_threshold: float = 2.0,
    clinic_radius_km: float = 5.0,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run simulation across all communities with custom thresholds.

    Returns a summary dict without writing to the database.
    """
    query = db.query(Community)
    if limit:
        query = query.limit(limit)

    communities = query.all()
    facilities = [(f.latitude, f.longitude) for f in db.query(HealthcareFacility).all()]

    results: list = []
    summary = {
        "ready": 0,
        "supported": 0,
        "excluded": 0,
        "insufficient_data": 0,
        "total": 0,
    }

    for community in communities:
        conn = community.connectivity_data or {}
        download_mbps = conn.get("download_mbps")
        monthly_cost = estimate_monthly_cost(community, download_mbps)
        income = get_census_income(community, db)

        metrics = run_equity_analysis(
            estimated_monthly_cost=monthly_cost,
            median_household_income=income,
            download_mbps=download_mbps,
            community_lat=community.latitude,
            community_lon=community.longitude,
            healthcare_facilities=facilities,
            affordability_threshold=affordability_threshold,
            anchor_radius_km=clinic_radius_km,
        )

        # Safety net evaluation
        aff_status, aff_ratio = check_affordability(monthly_cost, income, affordability_threshold)
        safety = evaluate_safety_net(
            aff_status,
            community.latitude,
            community.longitude,
            facilities,
            anchor_radius_km=clinic_radius_km,
        )

        classification = metrics.equity_classification.value
        summary[classification] = summary.get(classification, 0) + 1
        summary["total"] += 1

        results.append({
            "community_id": community.community_id,
            "name": community.name,
            "equity_classification": classification,
            "affordability_ratio": round(metrics.affordability_ratio, 2) if metrics.affordability_ratio else None,
            "affordability_status": metrics.affordability_status.value,
            "value_index": round(metrics.value_index, 2) if metrics.value_index else None,
            "safety_net": safety,
        })

    return {
        "parameters": {
            "affordability_threshold": affordability_threshold,
            "clinic_radius_km": clinic_radius_km,
        },
        "summary": summary,
        "communities": results,
        "dataset_version": "0.3.0",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
