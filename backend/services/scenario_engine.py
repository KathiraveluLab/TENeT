"""
Scenario Engine - What-If Scenario Analysis

Re-evaluates telehealth readiness status for all (or selected) communities
under user-specified thresholds.  The engine never mutates baseline data; it
returns a modeled preview of how readiness status would change. Healthcare
need remains a factual score and is included as context, not recalculated from
policy thresholds.

Reuses the canonical telehealth classifier and cached factual inputs.

Status ranking (worst → best):
    DATA_UNAVAILABLE < CRITICAL_GAP < LIMITED_TELEHEALTH < COMMUNITY_ANCHOR < TELEHEALTH_READY
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from services.scenario_input_cache import ScenarioInputCache
from services.season_constants import SEASON_YEAR_ROUND, VALID_SEASONS
from services.telehealth_classification import (
    TelehealthInputs,
    TelehealthThresholds,
    baseline_thresholds,
    classify_telehealth,
)


# ── Status ranking ──────────────────────────────────────────────────────────

STATUS_RANK: Dict[str, int] = {
    "DATA_UNAVAILABLE": 0,
    "CRITICAL_GAP": 1,
    "LIMITED_TELEHEALTH": 2,
    "COMMUNITY_ANCHOR": 3,
    "TELEHEALTH_READY": 4,
}

# ── Default baseline thresholds ─────────────────────────────────────────────

_CANONICAL_BASELINE = baseline_thresholds()
BASELINE_THRESHOLDS = {
    "min_download_mbps": _CANONICAL_BASELINE.min_download_mbps,
    "min_upload_mbps": _CANONICAL_BASELINE.min_upload_mbps,
    "max_latency_ms": _CANONICAL_BASELINE.max_latency_ms,
    "clinic_proximity_km": None,  # use existing access-mode logic
    "affordability_burden_pct": _CANONICAL_BASELINE.affordability_burden_pct,
}

_NULLABLE_THRESHOLD_KEYS = {"max_latency_ms", "clinic_proximity_km"}


# ── Helpers ─────────────────────────────────────────────────────────────────


def _status_delta(baseline: str, scenario: str) -> str:
    b = STATUS_RANK.get(baseline, -1)
    s = STATUS_RANK.get(scenario, -1)
    if s > b:
        return "improved"
    elif s < b:
        return "worsened"
    return "unchanged"


# ── Scenario Engine ─────────────────────────────────────────────────────────

class ScenarioEngine:
    """Evaluate scenario previews without mutating baseline data."""

    @staticmethod
    def validate_thresholds(thresholds: dict) -> Optional[str]:
        """Return an error message if thresholds are invalid, else None."""
        bd = thresholds.get("min_download_mbps")
        up = thresholds.get("min_upload_mbps")
        lat = thresholds.get("max_latency_ms")
        clinic = thresholds.get("clinic_proximity_km")
        aff = thresholds.get("affordability_burden_pct")

        def invalid_number(value, minimum, maximum):
            return (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < minimum
                or value > maximum
            )

        if bd is not None and invalid_number(bd, 0, 1000):
            return f"min_download_mbps must be 0-1000, got {bd}"
        if up is not None and invalid_number(up, 0, 500):
            return f"min_upload_mbps must be 0-500, got {up}"
        if lat is not None and invalid_number(lat, 0, 5000):
            return f"max_latency_ms must be 0-5000, got {lat}"
        if clinic is not None and invalid_number(clinic, 0, 1000):
            return f"clinic_proximity_km must be 0-1000, got {clinic}"
        if aff is not None and invalid_number(aff, 0, 100):
            return f"affordability_burden_pct must be 0-100, got {aff}"
        return None

    @staticmethod
    def preview(
        db: Session,
        thresholds: dict,
        season: str = SEASON_YEAR_ROUND,
        region_codes: Optional[List[str]] = None,
    ) -> dict:
        """
        Compute a scenario preview comparing modeled status to baseline.

        Parameters
        ----------
        db : Session
        thresholds : dict with keys min_download_mbps, min_upload_mbps,
                     max_latency_ms, clinic_proximity_km, affordability_burden_pct
        season : str – year_round | summer | winter
        region_codes : list or None (None = all communities)
        """
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND

        # ── Merge with baseline defaults ────────────────────────────────
        merged = dict(BASELINE_THRESHOLDS)
        for key, value in thresholds.items():
            if key in merged:
                if value is None and key not in _NULLABLE_THRESHOLD_KEYS:
                    continue
                merged[key] = value

        is_baseline_equivalent = all(
            merged[k] == BASELINE_THRESHOLDS[k] for k in BASELINE_THRESHOLDS
        )

        cached_inputs = ScenarioInputCache.get(db, season)
        if region_codes:
            requested = set(region_codes)
            cached_inputs = [
                item for item in cached_inputs
                if item["region_code"] in requested
            ]

        results: List[dict] = []
        summary_counters = {
            "telehealth_ready": 0,
            "community_anchor": 0,
            "limited_telehealth": 0,
            "critical_gap": 0,
            "data_unavailable": 0,
            "status_changed_regions": 0,
            "improved_count": 0,
            "worsened_count": 0,
            "unchanged_count": 0,
        }

        for scenario_input in cached_inputs:
            entry = ScenarioEngine._evaluate_cached_input(
                scenario_input=scenario_input,
                merged_thresholds=merged,
            )
            results.append(entry)

            # Update summary
            scenario_status_key = entry["scenario_status"].lower()
            if scenario_status_key in summary_counters:
                summary_counters[scenario_status_key] += 1

            delta = entry["status_delta"]
            if delta == "improved":
                summary_counters["improved_count"] += 1
            elif delta == "worsened":
                summary_counters["worsened_count"] += 1
            else:
                summary_counters["unchanged_count"] += 1

            if entry["status_delta"] != "unchanged":
                summary_counters["status_changed_regions"] += 1

        return {
            "scenario": {
                "season": season,
                "thresholds": merged,
                "is_baseline_equivalent": is_baseline_equivalent,
            },
            "summary": {
                "total_regions": len(results),
                **summary_counters,
            },
            "regions": results,
        }

    # ── Per-region evaluation ───────────────────────────────────────────

    @staticmethod
    def _evaluate_cached_input(
        *,
        scenario_input: dict,
        merged_thresholds: dict,
    ) -> dict:
        baseline_status = scenario_input["baseline_status"]
        healthcare_need_score = scenario_input["healthcare_need_score"]
        scenario = ScenarioEngine._scenario_status_from_input(
            scenario_input=scenario_input,
            merged_thresholds=merged_thresholds,
        )

        scenario_status = scenario["status"]
        delta = _status_delta(baseline_status, scenario_status)

        return {
            "region_code": scenario_input["region_code"],
            "name": scenario_input["name"],
            "lat": scenario_input["lat"],
            "lon": scenario_input["lon"],
            "baseline_status": baseline_status,
            "scenario_status": scenario_status,
            "status_delta": delta,
            "healthcare_need_score": healthcare_need_score,
            "changed": delta != "unchanged",
            "has_data_gap": scenario_input["has_data_gap"],
            "missing_fields": scenario_input["missing_fields"],
            "data_confidence": scenario_input["data_confidence"],
            "reason_codes": scenario["reason_codes"],
            "explanation": scenario["explanation"],
        }

    @staticmethod
    def _scenario_status_from_input(
        *,
        scenario_input: dict,
        merged_thresholds: dict,
    ) -> dict:
        thresholds = TelehealthThresholds(
            min_download_mbps=float(merged_thresholds["min_download_mbps"]),
            min_upload_mbps=float(merged_thresholds["min_upload_mbps"]),
            max_latency_ms=(
                float(merged_thresholds["max_latency_ms"])
                if merged_thresholds["max_latency_ms"] is not None else None
            ),
            clinic_proximity_km=(
                float(merged_thresholds["clinic_proximity_km"])
                if merged_thresholds["clinic_proximity_km"] is not None else None
            ),
            affordability_burden_pct=float(
                merged_thresholds["affordability_burden_pct"]
            ),
        )
        classification = classify_telehealth(
            TelehealthInputs(
                latitude=scenario_input.get("lat"),
                longitude=scenario_input.get("lon"),
                access_modes=scenario_input.get("access_modes", ""),
                ookla_download_mbps=scenario_input.get("ookla_download_mbps"),
                ookla_upload_mbps=scenario_input.get("ookla_upload_mbps"),
                ookla_latency_ms=scenario_input.get("ookla_latency_ms"),
                fcc_coverage_pct=scenario_input.get("fcc_coverage_pct"),
                median_income=scenario_input.get("median_income"),
                monthly_internet_cost=scenario_input.get("monthly_internet_cost"),
                burden_pct=scenario_input.get("burden_pct"),
                nearest_clinic_distance_km=scenario_input.get("nearest_clinic_distance_km"),
                clinic_data_available=scenario_input.get("clinic_data_available", False),
            ),
            thresholds,
        )
        return {
            "status": classification.status,
            "reason_codes": list(classification.reason_codes),
            "explanation": classification.explanation,
        }
