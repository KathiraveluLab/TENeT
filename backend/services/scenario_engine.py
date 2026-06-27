"""
Scenario Engine - What-If Scenario Analysis

Re-evaluates telehealth readiness status for all (or selected) communities
under user-specified thresholds.  The engine never mutates baseline data; it
returns a modeled preview of how status and need-scores would change.

Reuses:
    - ResearchProfileService (income, broadband, ookla lookups)
    - DataQualityService (confidence evaluation)
    - HealthcareDesertCalculator (distance + density scoring)
    - ISP pricing configuration

Status ranking (worst → best):
    DATA_UNAVAILABLE < CRITICAL_GAP < LIMITED_TELEHEALTH < COMMUNITY_ANCHOR < TELEHEALTH_READY
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from services.data_quality_service import normalize_confidence, split_gap_flags
from services.healthcare_desert_calculator import HealthcareDesertCalculator
from services.isp_config import get_internet_cost, get_affordability_threshold
from services.scenario_input_cache import ScenarioInputCache
from services.season_constants import SEASON_YEAR_ROUND, VALID_SEASONS


# ── Status ranking ──────────────────────────────────────────────────────────

STATUS_RANK: Dict[str, int] = {
    "DATA_UNAVAILABLE": 0,
    "CRITICAL_GAP": 1,
    "LIMITED_TELEHEALTH": 2,
    "COMMUNITY_ANCHOR": 3,
    "TELEHEALTH_READY": 4,
}

STATUS_DISPLAY = {
    "TELEHEALTH_READY": "Telehealth Ready",
    "COMMUNITY_ANCHOR": "Community Anchor",
    "LIMITED_TELEHEALTH": "Limited Telehealth",
    "CRITICAL_GAP": "Critical Gap",
    "DATA_UNAVAILABLE": "Data Unavailable",
}


# ── Default baseline thresholds ─────────────────────────────────────────────

BASELINE_THRESHOLDS = {
    "min_download_mbps": 25,
    "min_upload_mbps": 3,
    "max_latency_ms": 150,
    "clinic_proximity_km": None,  # use existing access-mode logic
    "affordability_burden_pct": get_affordability_threshold(),
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

        if bd is not None and (not isinstance(bd, (int, float)) or bd < 0 or bd > 1000):
            return f"min_download_mbps must be 0-1000, got {bd}"
        if up is not None and (not isinstance(up, (int, float)) or up < 0 or up > 500):
            return f"min_upload_mbps must be 0-500, got {up}"
        if lat is not None and (not isinstance(lat, (int, float)) or lat < 0 or lat > 5000):
            return f"max_latency_ms must be 0-5000, got {lat}"
        if clinic is not None and (not isinstance(clinic, (int, float)) or clinic < 0 or clinic > 1000):
            return f"clinic_proximity_km must be 0-1000, got {clinic}"
        if aff is not None and (not isinstance(aff, (int, float)) or aff < 0 or aff > 100):
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
            "score_changed_regions": 0,
            "improved_count": 0,
            "worsened_count": 0,
            "unchanged_count": 0,
        }

        for scenario_input in cached_inputs:
            entry = ScenarioEngine._evaluate_cached_input(
                scenario_input=scenario_input,
                merged_thresholds=merged,
                is_baseline_equivalent=is_baseline_equivalent,
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
            if entry["need_score_delta"] != 0:
                summary_counters["score_changed_regions"] += 1

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
        is_baseline_equivalent: bool,
    ) -> dict:
        baseline_status = scenario_input["baseline_status"]
        baseline_need_score = scenario_input["baseline_need_score"]

        if is_baseline_equivalent:
            scenario = {
                "status": baseline_status,
                "reason_codes": ["BASELINE_EQUIVALENT"],
                "explanation": "Baseline thresholds applied; modeled status matches the current classification.",
            }
        else:
            scenario = ScenarioEngine._scenario_status_from_input(
                scenario_input=scenario_input,
                merged_thresholds=merged_thresholds,
            )

        scenario_status = scenario["status"]
        scenario_need_score = baseline_need_score
        delta = _status_delta(baseline_status, scenario_status)
        need_delta = round(scenario_need_score - baseline_need_score, 1)

        return {
            "region_code": scenario_input["region_code"],
            "name": scenario_input["name"],
            "lat": scenario_input["lat"],
            "lon": scenario_input["lon"],
            "baseline_status": baseline_status,
            "scenario_status": scenario_status,
            "status_delta": delta,
            "baseline_need_score": baseline_need_score,
            "scenario_need_score": scenario_need_score,
            "need_score_delta": need_delta,
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
        reason_codes: List[str] = []
        explanation_parts: List[str] = []

        if scenario_input["lat"] is None or scenario_input["lon"] is None:
            return {
                "status": "DATA_UNAVAILABLE",
                "reason_codes": ["MISSING_COORDINATES"],
                "explanation": "Region has no geolocation data.",
            }

        min_download = merged_thresholds.get("min_download_mbps", 25)
        min_upload = merged_thresholds.get("min_upload_mbps", 3)
        max_latency = merged_thresholds.get("max_latency_ms", 150)
        download_mbps = scenario_input.get("ookla_download_mbps")
        upload_mbps = scenario_input.get("ookla_upload_mbps")
        latency_ms = scenario_input.get("ookla_latency_ms")
        fcc_coverage = scenario_input.get("fcc_coverage_pct")

        meets_broadband = False
        if download_mbps is not None:
            if download_mbps >= min_download:
                if upload_mbps is None or upload_mbps >= min_upload:
                    if max_latency is None or latency_ms is None or latency_ms <= max_latency:
                        meets_broadband = True
                        reason_codes.append("MEETS_BROADBAND")
                        explanation_parts.append(
                            f"Broadband meets {min_download:g}/{min_upload:g} Mbps threshold"
                        )
                    else:
                        reason_codes.append("HIGH_LATENCY")
                        explanation_parts.append(
                            f"Latency {latency_ms:.0f}ms exceeds {max_latency:g}ms"
                        )
                else:
                    reason_codes.append("LOW_UPLOAD")
                    explanation_parts.append(
                        f"Upload {upload_mbps:.1f} Mbps below {min_upload:g} Mbps"
                    )
            else:
                reason_codes.append("LOW_DOWNLOAD")
                explanation_parts.append(
                    f"Download {download_mbps:.1f} Mbps below {min_download:g} Mbps"
                )
        elif fcc_coverage is not None and fcc_coverage >= 70:
            if min_download <= 25 and min_upload <= 3:
                meets_broadband = True
                reason_codes.append("MEETS_BROADBAND_FCC")
                explanation_parts.append("FCC coverage supports broadband threshold")
            else:
                reason_codes.append("FCC_BELOW_SCENARIO_THRESHOLD")
                explanation_parts.append("FCC data doesn't cover higher scenario thresholds")
        else:
            reason_codes.append("NO_BROADBAND_DATA")
            explanation_parts.append("No measured broadband data available")

        aff_threshold = merged_thresholds.get("affordability_burden_pct", 2.0)
        burden_pct = scenario_input.get("burden_pct")
        internet_cost = scenario_input.get("monthly_internet_cost")
        has_income_data = burden_pct is not None
        is_affordable = False

        if has_income_data:
            is_affordable = bool(
                burden_pct < aff_threshold
                and internet_cost is not None
                and internet_cost < 400.0
            )
            if is_affordable:
                reason_codes.append("AFFORDABLE")
                explanation_parts.append(
                    f"Internet burden {burden_pct:.1f}% below {aff_threshold:g}%"
                )
            else:
                reason_codes.append("UNAFFORDABLE")
                explanation_parts.append(
                    f"Internet burden {burden_pct:.1f}% exceeds {aff_threshold:g}%"
                )
        else:
            internet_cost = 450.0
            reason_codes.append("NO_INCOME_DATA")
            explanation_parts.append("No income data to assess affordability")

        clinic_threshold_km = merged_thresholds.get("clinic_proximity_km")
        distance_threshold_km = (
            scenario_input["distance_threshold_km"]
            if clinic_threshold_km is None
            else float(clinic_threshold_km)
        )
        nearest_distance = scenario_input.get("nearest_clinic_distance_km")
        has_nearby_clinic = (
            nearest_distance is not None
            and nearest_distance <= distance_threshold_km
        )
        if has_nearby_clinic:
            reason_codes.append("ACCESSIBLE_CARE")
            explanation_parts.append(f"Clinic within {distance_threshold_km:.0f}km")
        else:
            reason_codes.append("NO_NEARBY_CLINIC")
            explanation_parts.append(f"No clinic within {distance_threshold_km:.0f}km")

        is_extreme_cost = internet_cost is not None and internet_cost >= 400

        if not has_income_data:
            if is_extreme_cost:
                status = "COMMUNITY_ANCHOR" if has_nearby_clinic else "CRITICAL_GAP"
            elif has_nearby_clinic:
                status = "COMMUNITY_ANCHOR"
            else:
                status = "DATA_UNAVAILABLE"
        elif meets_broadband and is_affordable:
            status = "TELEHEALTH_READY"
        elif is_affordable:
            if "NO_BROADBAND_DATA" in reason_codes:
                status = "DATA_UNAVAILABLE"
            elif has_nearby_clinic:
                status = "LIMITED_TELEHEALTH"
            else:
                status = "CRITICAL_GAP"
        elif has_nearby_clinic:
            status = "COMMUNITY_ANCHOR"
        else:
            status = "CRITICAL_GAP"

        return {
            "status": status,
            "reason_codes": reason_codes,
            "explanation": "; ".join(explanation_parts) if explanation_parts else "No assessment available.",
        }
