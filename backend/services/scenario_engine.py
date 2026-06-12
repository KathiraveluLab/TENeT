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

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database.models import (
    BroadbandCoverage,
    CATDataPoint,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.data_quality_service import normalize_confidence, split_gap_flags
from services.healthcare_desert_calculator import HealthcareDesertCalculator
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

def _load_isp_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "isp_pricing.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "isp_pricing": {"fastwyre": {"cost": 350}},
            "zcta_mappings": {"gci_urban": [], "extreme_rural": []},
            "thresholds": {"affordability_burden_pct": 2.0},
        }


_ISP_CONFIG = _load_isp_config()


def _get_regional_internet_cost(zcta: str) -> Tuple[float, str]:
    """Exact replica of the cat_routes pricing lookup."""
    try:
        gmap = _ISP_CONFIG.get("zcta_mappings", {})
        gci_urban = set(gmap.get("gci_urban", []))
        extreme_rural = set(gmap.get("extreme_rural", []))
        starlink_satellite = set(gmap.get("starlink_satellite", []))
    except Exception:
        gci_urban = set()
        extreme_rural = set()
        starlink_satellite = set()

    pricing = _ISP_CONFIG.get("isp_pricing", {})

    if zcta in extreme_rural:
        p = pricing.get("extreme_rural", {"cost": 450.0, "name": "Extreme Rural"})
        return float(p.get("cost", 450.0)), str(p.get("name", "Extreme Rural"))
    elif zcta in gci_urban:
        p = pricing.get("gci", {"cost": 125.0, "name": "GCI"})
        return float(p.get("cost", 125.0)), str(p.get("name", "GCI"))
    elif zcta in starlink_satellite:
        p = pricing.get("starlink", {"cost": 120.0, "name": "Starlink"})
        return float(p.get("cost", 120.0)), str(p.get("name", "Starlink"))
    else:
        p = pricing.get("fastwyre", {"cost": 350.0, "name": "FastWyre"})
        return float(p.get("cost", 350.0)), str(p.get("name", "FastWyre"))


BASELINE_THRESHOLDS = {
    "min_download_mbps": 25,
    "min_upload_mbps": 3,
    "max_latency_ms": 150,
    "clinic_proximity_km": None,  # use existing access-mode logic
    "affordability_burden_pct": float(
        _ISP_CONFIG.get("thresholds", {}).get("affordability_burden_pct", 2.0)
    ),
}

_NULLABLE_THRESHOLD_KEYS = {"max_latency_ms", "clinic_proximity_km"}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


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

    @staticmethod
    def _evaluate_region(
        *,
        region: CATRegion,
        merged_thresholds: dict,
        is_baseline_equivalent: bool,
        season: str,
        clinics: list,
        broadband_lookup: dict,
        latest_ookla,
        dp_by_region: dict,
        db: Session,
    ) -> dict:
        lat = region.centroid_lat
        lon = region.centroid_lon

        # ── Baseline status (uses existing formula) ─────────────────────
        baseline = ScenarioEngine._baseline_status(
            region=region,
            clinics=clinics,
            broadband_lookup=broadband_lookup,
            db=db,
        )
        baseline_status = baseline["status"]

        # ── Baseline need score ─────────────────────────────────────────
        desert_data = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
            db, region.region_code, season
        )
        baseline_need_score = round(desert_data.get("necessity_score", 0), 1)

        if is_baseline_equivalent:
            scenario = {
                "status": baseline_status,
                "reason_codes": ["BASELINE_EQUIVALENT"],
                "explanation": "Baseline thresholds applied; modeled status matches the current classification.",
            }
        else:
            scenario = ScenarioEngine._scenario_status(
                region=region,
                merged_thresholds=merged_thresholds,
                clinics=clinics,
                broadband_lookup=broadband_lookup,
                latest_ookla=latest_ookla,
                db=db,
            )
        scenario_status = scenario["status"]
        reason_codes = scenario["reason_codes"]
        explanation = scenario["explanation"]

        # ── Scenario need score (same as baseline for v1; broadband
        #    threshold changes don't affect the desert score formula) ────
        scenario_need_score = baseline_need_score

        # ── Data quality ────────────────────────────────────────────────
        broadband = broadband_lookup.get(region.region_code)
        missing_fields: list[str] = []
        if broadband is None:
            missing_fields.append("connectivity.fcc_coverage")
        if lat is None or lon is None or ScenarioEngine._find_nearest_income(db, lat, lon) is None:
            missing_fields.append("affordability.median_income")
        has_data_gap = bool(missing_fields) or bool(
            split_gap_flags(getattr(broadband, "data_gaps", None) if broadband else None)
        )
        data_confidence = normalize_confidence(
            getattr(broadband, "confidence", None) if broadband else None
        )

        delta = _status_delta(baseline_status, scenario_status)
        need_delta = round(scenario_need_score - baseline_need_score, 1)

        return {
            "region_code": region.region_code,
            "name": region.region_name,
            "lat": float(lat) if lat is not None else None,
            "lon": float(lon) if lon is not None else None,
            "baseline_status": baseline_status,
            "scenario_status": scenario_status,
            "status_delta": delta,
            "baseline_need_score": baseline_need_score,
            "scenario_need_score": scenario_need_score,
            "need_score_delta": need_delta,
            "changed": delta != "unchanged",
            "has_data_gap": has_data_gap,
            "missing_fields": missing_fields,
            "data_confidence": data_confidence,
            "reason_codes": reason_codes,
            "explanation": explanation,
        }

    # ── Baseline status (mirrors /telehealth-status/all formula) ────────

    @staticmethod
    def _baseline_status(
        *,
        region: CATRegion,
        clinics: list,
        broadband_lookup: dict,
        db: Session,
    ) -> dict:
        """Reproduce the baseline telehealth status classification."""
        if region.centroid_lat is None or region.centroid_lon is None:
            return {"status": "DATA_UNAVAILABLE"}

        # Find nearest ZCTA
        best_zcta = ScenarioEngine._find_nearest_income(
            db, region.centroid_lat, region.centroid_lon
        )

        has_income_data = best_zcta is not None
        is_affordable = False
        internet_cost: Optional[float] = None

        if has_income_data and best_zcta is not None:
            zcta_str = str(getattr(best_zcta, "zcta", ""))
            internet_cost, _ = _get_regional_internet_cost(zcta_str)
            median_income = float(getattr(best_zcta, "median_income", 0) or 0)
            monthly_income = median_income / 12.0
            burden_pct = float((internet_cost / monthly_income) * 100.0) if monthly_income > 0 else 100.0
            threshold = float(
                _ISP_CONFIG.get("thresholds", {}).get("affordability_burden_pct", 2.0)
            )
            is_affordable = bool(burden_pct < threshold) and bool(internet_cost < 400.0)
        else:
            internet_cost = 450

        # Find nearest clinic
        access_modes = (region.properties or {}).get("primary_access_modes", "")
        distance_threshold_km = 10 if "road" in access_modes.lower() else 50

        nearest_distance = float("inf")
        for clinic in clinics:
            dist = _haversine_km(
                region.centroid_lat, region.centroid_lon,
                clinic.latitude, clinic.longitude,
            )
            nearest_distance = min(nearest_distance, dist)

        has_nearby_clinic = nearest_distance <= distance_threshold_km
        is_extreme_cost = internet_cost is not None and internet_cost >= 400

        if not has_income_data:
            if is_extreme_cost:
                status = "COMMUNITY_ANCHOR" if has_nearby_clinic else "CRITICAL_GAP"
            elif has_nearby_clinic:
                status = "COMMUNITY_ANCHOR"
            else:
                status = "DATA_UNAVAILABLE"
        elif is_affordable:
            status = "TELEHEALTH_READY"
        elif has_nearby_clinic:
            status = "COMMUNITY_ANCHOR"
        else:
            status = "CRITICAL_GAP"

        return {"status": status}

    # ── Scenario status (parameterized thresholds) ──────────────────────

    @staticmethod
    def _scenario_status(
        *,
        region: CATRegion,
        merged_thresholds: dict,
        clinics: list,
        broadband_lookup: dict,
        latest_ookla,
        db: Session,
    ) -> dict:
        """Compute telehealth status under scenario thresholds."""
        reason_codes: List[str] = []
        explanation_parts: List[str] = []

        if region.centroid_lat is None or region.centroid_lon is None:
            return {
                "status": "DATA_UNAVAILABLE",
                "reason_codes": ["MISSING_COORDINATES"],
                "explanation": "Region has no geolocation data.",
            }

        # ── Broadband check ─────────────────────────────────────────────
        min_download = merged_thresholds.get("min_download_mbps", 25)
        min_upload = merged_thresholds.get("min_upload_mbps", 3)
        max_latency = merged_thresholds.get("max_latency_ms", 150)

        broadband = broadband_lookup.get(region.region_code)
        # Try Ookla measured speed
        ookla = ScenarioEngine._find_nearest_ookla(
            db, region.centroid_lat, region.centroid_lon, latest_ookla
        )

        download_mbps = None
        upload_mbps = None
        latency_ms = None

        if ookla:
            if ookla.avg_d_kbps is not None:
                download_mbps = ookla.avg_d_kbps / 1000.0
            if ookla.avg_u_kbps is not None:
                upload_mbps = ookla.avg_u_kbps / 1000.0
            if ookla.avg_lat_ms is not None:
                latency_ms = ookla.avg_lat_ms

        # Use FCC coverage percentage as fallback signal
        fcc_coverage = None
        if broadband and broadband.any_tech_25mbps_pct is not None:
            fcc_coverage = broadband.any_tech_25mbps_pct

        meets_broadband = False
        if download_mbps is not None:
            if download_mbps >= min_download:
                if upload_mbps is None or upload_mbps >= min_upload:
                    if max_latency is None or latency_ms is None or latency_ms <= max_latency:
                        meets_broadband = True
                        reason_codes.append("MEETS_BROADBAND")
                        explanation_parts.append(f"Broadband meets {min_download}/{min_upload} Mbps threshold")
                    else:
                        reason_codes.append("HIGH_LATENCY")
                        explanation_parts.append(f"Latency {latency_ms:.0f}ms exceeds {max_latency}ms")
                else:
                    reason_codes.append("LOW_UPLOAD")
                    explanation_parts.append(f"Upload {upload_mbps:.1f} Mbps below {min_upload} Mbps")
            else:
                reason_codes.append("LOW_DOWNLOAD")
                explanation_parts.append(f"Download {download_mbps:.1f} Mbps below {min_download} Mbps")
        elif fcc_coverage is not None and fcc_coverage >= 70:
            # FCC claims ≥70% coverage at 25/3 → treat as meeting baseline broadband
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

        # ── Affordability check ─────────────────────────────────────────
        aff_threshold = merged_thresholds.get("affordability_burden_pct", 2.0)

        best_zcta = ScenarioEngine._find_nearest_income(
            db, region.centroid_lat, region.centroid_lon
        )

        has_income_data = best_zcta is not None
        is_affordable = False
        internet_cost: Optional[float] = None

        if has_income_data and best_zcta is not None:
            zcta_str = str(getattr(best_zcta, "zcta", ""))
            internet_cost, _ = _get_regional_internet_cost(zcta_str)
            median_income = float(getattr(best_zcta, "median_income", 0) or 0)
            monthly_income = median_income / 12.0
            burden_pct = float((internet_cost / monthly_income) * 100.0) if monthly_income > 0 else 100.0

            is_affordable = bool(burden_pct < aff_threshold) and bool(internet_cost < 400.0)
            if is_affordable:
                reason_codes.append("AFFORDABLE")
                explanation_parts.append(f"Internet burden {burden_pct:.1f}% below {aff_threshold}%")
            else:
                reason_codes.append("UNAFFORDABLE")
                explanation_parts.append(f"Internet burden {burden_pct:.1f}% exceeds {aff_threshold}%")
        else:
            internet_cost = 450
            reason_codes.append("NO_INCOME_DATA")
            explanation_parts.append("No income data to assess affordability")

        # ── Clinic proximity check ──────────────────────────────────────
        clinic_threshold_km = merged_thresholds.get("clinic_proximity_km")
        access_modes = (region.properties or {}).get("primary_access_modes", "")

        if clinic_threshold_km is None:
            # Use existing access-mode-based rules
            distance_threshold_km = 10 if "road" in access_modes.lower() else 50
        else:
            distance_threshold_km = float(clinic_threshold_km)

        nearest_distance = float("inf")
        for clinic in clinics:
            dist = _haversine_km(
                region.centroid_lat, region.centroid_lon,
                clinic.latitude, clinic.longitude,
            )
            nearest_distance = min(nearest_distance, dist)

        has_nearby_clinic = nearest_distance <= distance_threshold_km
        if has_nearby_clinic:
            reason_codes.append("ACCESSIBLE_CARE")
            explanation_parts.append(f"Clinic within {distance_threshold_km:.0f}km")
        else:
            reason_codes.append("NO_NEARBY_CLINIC")
            explanation_parts.append(f"No clinic within {distance_threshold_km:.0f}km")

        # ── Classify (same logic as research_profile_service) ───────────
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
            # Affordable but broadband fails – still ready if broadband data is missing
            if "NO_BROADBAND_DATA" in reason_codes:
                status = "DATA_UNAVAILABLE"
            else:
                # Has data but doesn't meet threshold
                if has_nearby_clinic:
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

    # ── Lookup helpers ──────────────────────────────────────────────────

    @staticmethod
    def _find_nearest_income(
        db: Session, lat: float, lon: float, max_km: float = 55.0
    ):
        lat = float(lat)
        lon = float(lon)
        lat_window = max_km / 111.0
        lon_window = max_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
        census_records = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
            CensusIncome.centroid_lat.between(lat - lat_window, lat + lat_window),
            CensusIncome.centroid_lon.between(lon - lon_window, lon + lon_window),
        ).all()

        best = None
        min_dist = float("inf")
        for record in census_records:
            dist = _haversine_km(lat, lon, record.centroid_lat, record.centroid_lon)
            if dist < min_dist and dist <= max_km:
                min_dist = dist
                best = record
        return best

    @staticmethod
    def _find_nearest_ookla(
        db: Session, lat: float, lon: float, latest_ookla, max_km: float = 75.0
    ):
        if latest_ookla is None:
            return None

        lat = float(lat)
        lon = float(lon)
        lat_window = max_km / 111.0
        lon_window = max_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
        ookla_tiles = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == latest_ookla.year,
            OoklaPerformance.quarter == latest_ookla.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
            OoklaPerformance.centroid_lat.between(lat - lat_window, lat + lat_window),
            OoklaPerformance.centroid_lon.between(lon - lon_window, lon + lon_window),
        ).all()

        best = None
        min_dist = float("inf")
        for tile in ookla_tiles:
            dist = _haversine_km(lat, lon, tile.centroid_lat, tile.centroid_lon)
            if dist < min_dist and dist <= max_km:
                min_dist = dist
                best = tile
        return best
