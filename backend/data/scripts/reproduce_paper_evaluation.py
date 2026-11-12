#!/usr/bin/env python3
"""Reproduce TENeT quantitative evaluation, sensitivity ablations, and API benchmarks.

Runs deterministic analyses over a TENeT SQLite database and optionally benchmarks
Flask API response latencies, emitting JSON and LaTeX-ready table summaries for:
  - Dataset inventory, transport tiers, clinic/hospital proximity, and HDS (tab:tenet_metrics)
  - Readiness stratification, data-quality confidence, and missingness bottlenecks
  - FCC-reported broadband availability vs. Ookla empirical concordance
  - Policy scenario sensitivity and fixed Starlink ($120/mo) substitution (tab:scenario_sensitivity)
  - Spatial join radius ablation for Ookla tiles and ACS ZCTA centroids (tab:radius_ablation)
  - Cold/warm Flask test-client API latency benchmarks (tab:latency_bench)

IMPORTANT: `--db` must be processed before importing `database.*` because
`database.config` binds `DB_PATH` at import time.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_RADII_KM = [10.0, 25.0, 55.0, 75.0, 100.0, 150.0]
SEASONS = ("summer", "year_round", "winter")
DEFAULT_PROFILE_CODE = "AK-ANCHORAGE"
DEFAULT_COMPARE_CODES = ["AK-ANCHORAGE", "AK-UTQIAGVIK", "AK-BETHEL"]

BASELINE_THRESHOLDS: Dict[str, Any] = {
    "min_download_mbps": 25,
    "min_upload_mbps": 3,
    "max_latency_ms": 150,
    "clinic_proximity_km": None,
    "affordability_burden_pct": 2.0,
}

POLICY_SCENARIOS: List[Tuple[str, str, Dict[str, Any]]] = [
    (
        "fcc_standard",
        "FCC Standard (25/3 Mbps, 150 ms, 2.0%, 10/50 km)",
        dict(BASELINE_THRESHOLDS),
    ),
    (
        "broadband_equity",
        "Broadband Equity Goal (100/20 Mbps, 100 ms, 2.0%)",
        {
            "min_download_mbps": 100,
            "min_upload_mbps": 20,
            "max_latency_ms": 100,
            "clinic_proximity_km": None,
            "affordability_burden_pct": 2.0,
        },
    ),
    (
        "universal_clinic",
        "Universal Clinic Access (15 km uniform clinic)",
        {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": 15,
            "affordability_burden_pct": 2.0,
        },
    ),
    (
        "expanded_clinic",
        "Expanded Clinic Fallback (50 km uniform clinic)",
        {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": 50,
            "affordability_burden_pct": 2.0,
        },
    ),
    (
        "relaxed_affordability",
        "Relaxed Affordability Burden (4.0% threshold)",
        {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": None,
            "affordability_burden_pct": 4.0,
        },
    ),
    (
        "strict_affordability",
        "Strict Affordability Burden (1.0% threshold)",
        {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": None,
            "affordability_burden_pct": 1.0,
        },
    ),
]


def interpolated_percentile(ordered: Sequence[float], prob: float) -> float:
    """Compute linear-interpolated percentile from a pre-sorted non-empty sequence."""
    idx = (len(ordered) - 1) * prob
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[int(idx)]
    return ordered[lo] * (hi - idx) + ordered[hi] * (idx - lo)


def quantiles(values: Sequence[float]) -> Optional[Dict[str, Any]]:
    """Compute summary statistics and linear-interpolated quartiles."""
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    count = len(ordered)

    return {
        "n": count,
        "mean": round(statistics.mean(ordered), 2),
        "sd": round(statistics.stdev(ordered), 2) if count > 1 else 0.0,
        "median": round(interpolated_percentile(ordered, 0.5), 2),
        "q1": round(interpolated_percentile(ordered, 0.25), 2),
        "q3": round(interpolated_percentile(ordered, 0.75), 2),
        "min": round(ordered[0], 2),
        "max": round(ordered[-1], 2),
    }


def pct(count: int, total: int) -> float:
    """Return rounded percentage with zero-denominator guard."""
    if total <= 0:
        return 0.0
    return round((count / total) * 100.0, 2)


def _fmt_num(val: Optional[float], digits: int = 2) -> str:
    """Format numeric value deterministically or return '--'."""
    if val is None:
        return "--"
    if digits == 0:
        return f"{int(round(val)):,}"
    return f"{val:,.{digits}f}"


def _nearest_site_distances(
    regions: Sequence[Any],
    sites: Sequence[Any],
    haversine_fn: Callable[[float, float, float, float], float],
) -> List[float]:
    """Compute nearest straight-line haversine distance (km) from each region to sites."""
    if not regions or not sites:
        return []
    distances: List[float] = []
    for region in regions:
        if region.centroid_lat is None or region.centroid_lon is None:
            continue
        best = min(
            haversine_fn(region.centroid_lat, region.centroid_lon, site.latitude, site.longitude)
            for site in sites
        )
        distances.append(best)
    return distances


def compute_hds_by_season(db: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Load fresh season-specific ScenarioInputCache records."""
    from services.scenario_input_cache import ScenarioInputCache

    ScenarioInputCache.clear()
    return {season: ScenarioInputCache.get(db, season) for season in SEASONS}


def compute_dataset_metrics(
    db: Any,
    regions: Sequence[Any],
    contexts: Dict[str, Any],
    hds_by_season: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Compute core inventory, CAT tiering, proximity, and HDS metrics (Table 3)."""
    from database.models import (
        BroadbandCoverage,
        CATDataPoint,
        CensusIncome,
        HealthcareSite,
        OoklaPerformance,
    )
    from services.healthcare_desert_calculator import haversine_km

    n_regions = len(regions)
    broadband_rows = db.query(BroadbandCoverage).all()
    site_rows = db.query(HealthcareSite).all()
    ookla_rows = db.query(OoklaPerformance).all()
    data_points = db.query(CATDataPoint).all()
    census_count = db.query(CensusIncome).count()

    tier_counts = {tier: 0 for tier in (1, 2, 3, 4)}
    for region in regions:
        tier_counts[region.tier_level] = tier_counts.get(region.tier_level, 0) + 1

    air_only = sum(
        1 for r in regions if (r.properties or {}).get("primary_access_modes") == "air"
    )
    no_direct_access = sum(
        1 for r in regions if (r.properties or {}).get("primary_access_modes") == "no_direct_access"
    )

    linked_fcc = sum(1 for c in contexts.values() if c.broadband is not None)
    missing_fcc = n_regions - linked_fcc
    n_bb = len(broadband_rows)
    sat_primary = sum(1 for b in broadband_rows if (b.primary_access or "").upper() == "SATELLITE")
    fiber_mean = round(statistics.mean([b.fiber_25mbps_pct or 0.0 for b in broadband_rows]), 2) if n_bb else None

    site_type_counts = Counter((s.site_type or "unknown").lower() for s in site_rows)
    linked_facility_regions = {s.region_code for s in site_rows if s.region_code}
    communities_with_linked_fac = sum(1 for r in regions if r.region_code in linked_facility_regions)
    communities_without_linked_fac = n_regions - communities_with_linked_fac
    emergency_count = sum(1 for s in site_rows if bool(s.has_emergency))
    specialists_count = sum(1 for s in site_rows if bool(s.has_specialists))

    clinics_only = [s for s in site_rows if (s.site_type or "").lower() == "clinic"]
    hospitals_only = [s for s in site_rows if (s.site_type or "").lower() == "hospital"]
    clinic_distances = _nearest_site_distances(regions, clinics_only, haversine_km)
    hospital_distances = _nearest_site_distances(regions, hospitals_only, haversine_km)
    classifier_backup_distances = [
        c.inputs.nearest_clinic_distance_km
        for c in contexts.values()
        if c.inputs.nearest_clinic_distance_km is not None
    ]

    ookla_viable = sum(
        1
        for tile in ookla_rows
        if (tile.avg_d_kbps or 0.0) >= 25000.0
        and (tile.avg_u_kbps or 0.0) >= 3000.0
        and (tile.avg_lat_ms if tile.avg_lat_ms is not None else 9999.0) <= 150.0
    )
    ookla_mean_dl_mbps = (
        round(statistics.mean([(tile.avg_d_kbps or 0.0) / 1000.0 for tile in ookla_rows]), 2)
        if ookla_rows
        else None
    )

    hds_summary: Dict[str, Any] = {}
    for season in SEASONS:
        scores = [
            item["healthcare_need_score"]
            for item in hds_by_season[season]
            if item.get("healthcare_need_score") is not None
        ]
        stats_dict = quantiles(scores)
        hds_summary[season] = {
            "quantiles": stats_dict,
            "gt_70_count": sum(1 for val in scores if val > 70.0),
            "ge_71_count": sum(1 for val in scores if val >= 71.0),
        }

    missing_travel_time = sum(1 for dp in data_points if dp.travel_time_minutes is None)

    return {
        "inventory": {
            "cat_regions": n_regions,
            "broadband_places": n_bb,
            "census_income_zones": census_count,
            "ookla_tiles": len(ookla_rows),
            "ookla_telehealth_viable_tiles": ookla_viable,
            "ookla_telehealth_viable_pct": pct(ookla_viable, len(ookla_rows)),
            "ookla_mean_download_mbps": ookla_mean_dl_mbps,
            "healthcare_sites": len(site_rows),
            "cat_data_points": len(data_points),
        },
        "transport": {
            "cat_tiers": tier_counts,
            "air_only_count": air_only,
            "air_only_pct": pct(air_only, n_regions),
            "no_direct_access_count": no_direct_access,
            "no_direct_access_pct": pct(no_direct_access, n_regions),
        },
        "broadband": {
            "communities_linked_to_fcc": linked_fcc,
            "communities_linked_to_fcc_pct": pct(linked_fcc, n_regions),
            "communities_missing_fcc": missing_fcc,
            "communities_missing_fcc_pct": pct(missing_fcc, n_regions),
            "fcc_places_total": n_bb,
            "satellite_primary_places": sat_primary,
            "satellite_primary_pct": pct(sat_primary, n_bb),
            "mean_fiber_25mbps_pct": fiber_mean,
        },
        "healthcare_facilities": {
            "total": len(site_rows),
            "by_type": {
                "clinic": site_type_counts.get("clinic", 0),
                "hospital": site_type_counts.get("hospital", 0),
                "pharmacy": site_type_counts.get("pharmacy", 0),
                "other": sum(
                    cnt for kind, cnt in site_type_counts.items() if kind not in {"clinic", "hospital", "pharmacy"}
                ),
            },
            "emergency_count": emergency_count,
            "specialists_count": specialists_count,
            "communities_with_linked_facility": communities_with_linked_fac,
            "communities_without_linked_facility": communities_without_linked_fac,
            "communities_without_linked_facility_pct": pct(communities_without_linked_fac, n_regions),
        },
        "proximity_km": {
            "nearest_clinic_only": quantiles(clinic_distances),
            "communities_gt_50km_clinic": sum(1 for d in clinic_distances if d > 50.0),
            "communities_gt_50km_clinic_pct": pct(sum(1 for d in clinic_distances if d > 50.0), n_regions),
            "nearest_hospital_only": quantiles(hospital_distances),
            "communities_gt_100km_hospital": sum(1 for d in hospital_distances if d > 100.0),
            "communities_gt_100km_hospital_pct": pct(sum(1 for d in hospital_distances if d > 100.0), n_regions),
            "classifier_clinic_backup": quantiles(classifier_backup_distances),
            "classifier_backup_gt_50km": sum(1 for d in classifier_backup_distances if d > 50.0),
        },
        "hds_by_season": hds_summary,
        "missing_travel_time_data_points": missing_travel_time,
        "missing_travel_time_pct": pct(missing_travel_time, len(data_points) or n_regions),
    }


def compute_classification_and_missingness(
    contexts: Dict[str, Any],
    year_round_hds_map: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    """Compute baseline status stratification, confidence profile, and missingness decomposition."""
    from services.data_quality_service import DataQualityService

    n_regions = len(contexts)
    overall_status: Counter[str] = Counter()
    by_tier_status: Dict[int, Counter[str]] = defaultdict(Counter)
    unavailable_reasons: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    has_gap_count = 0
    conn_clinic_matrix: Counter[str] = Counter()

    for code, ctx in contexts.items():
        status = ctx.classification.status
        overall_status[status] += 1
        by_tier_status[ctx.region.tier_level][status] += 1

        if status == "DATA_UNAVAILABLE":
            has_bb = (ctx.inputs.ookla_download_mbps is not None) or (ctx.inputs.fcc_coverage_pct is not None)
            has_inc = ctx.inputs.median_income is not None
            has_clin = bool(ctx.inputs.clinic_data_available)
            key = f"bb={int(has_bb)},income={int(has_inc)},clinic={int(has_clin)}"
            unavailable_reasons[key] += 1

        dq = DataQualityService.evaluate_region_profile(
            region=ctx.region,
            broadband=ctx.broadband,
            ookla=ctx.ookla,
            income=ctx.income,
            nearest_facility=ctx.nearest_clinic,
            desert_score=year_round_hds_map.get(code),
        )
        confidence_counts[dq["data_confidence"]] += 1
        if dq["has_data_gap"]:
            has_gap_count += 1

        cc_key = (
            f"video={int(bool(ctx.classification.video_feasible))},"
            f"audio={int(bool(ctx.classification.audio_feasible))},"
            f"clinic={int(bool(ctx.classification.clinic_supported))}"
        )
        conn_clinic_matrix[cc_key] += 1

    return {
        "total_regions": n_regions,
        "overall_status": dict(sorted(overall_status.items())),
        "overall_status_pct": {k: pct(v, n_regions) for k, v in sorted(overall_status.items())},
        "by_cat_tier": {
            str(tier): dict(sorted(counts.items()))
            for tier, counts in sorted(by_tier_status.items())
        },
        "data_unavailable_reasons": dict(sorted(unavailable_reasons.items())),
        "profile_data_confidence": dict(sorted(confidence_counts.items())),
        "has_data_gap_count": has_gap_count,
        "has_data_gap_pct": pct(has_gap_count, n_regions),
        "connectivity_clinic_matrix": dict(sorted(conn_clinic_matrix.items())),
    }


def compute_hds_stratification(
    regions: Sequence[Any],
    hds_by_season: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """Stratify HDS distributions across CAT tiers and planning seasons."""
    tier_by_code = {r.region_code: r.tier_level for r in regions}
    result: Dict[str, Dict[str, Any]] = {}
    for tier in sorted({r.tier_level for r in regions}):
        tier_entry: Dict[str, Any] = {}
        for season in SEASONS:
            scores = [
                item["healthcare_need_score"]
                for item in hds_by_season[season]
                if tier_by_code.get(item["region_code"]) == tier
                and item.get("healthcare_need_score") is not None
            ]
            tier_entry[season] = {
                "quantiles": quantiles(scores),
                "gt_70_count": sum(1 for val in scores if val > 70.0),
                "ge_71_count": sum(1 for val in scores if val >= 71.0),
            }
        result[str(tier)] = tier_entry
    return result


def compute_fcc_ookla_concordance(contexts: Dict[str, Any]) -> Dict[str, Any]:
    """Compare reported FCC 25/3 availability (>=70%) vs. Ookla empirical video readiness."""
    both = []
    ookla_only = 0
    fcc_only = 0
    neither = 0

    for ctx in contexts.values():
        has_ookla = ctx.inputs.ookla_download_mbps is not None
        has_fcc = ctx.inputs.fcc_coverage_pct is not None
        if has_ookla and has_fcc:
            both.append(ctx)
        elif has_ookla:
            ookla_only += 1
        elif has_fcc:
            fcc_only += 1
        else:
            neither += 1

    matrix: Counter[Tuple[bool, bool]] = Counter()
    subcauses: Counter[str] = Counter()
    tech_metrics: Dict[str, Dict[str, List[float]]] = {
        "SATELLITE": {"dl": [], "ul": [], "lat": []},
        "WIRED": {"dl": [], "ul": [], "lat": []},
    }

    for ctx in both:
        fcc_ok = (ctx.inputs.fcc_coverage_pct or 0.0) >= 70.0
        dl = ctx.inputs.ookla_download_mbps or 0.0
        ul = ctx.inputs.ookla_upload_mbps or 0.0
        lat = ctx.inputs.ookla_latency_ms if ctx.inputs.ookla_latency_ms is not None else 0.0
        ookla_ok = dl >= 25.0 and ul >= 3.0 and lat <= 150.0
        matrix[(fcc_ok, ookla_ok)] += 1

        if fcc_ok and not ookla_ok:
            reasons = []
            if dl < 25.0:
                reasons.append("dl<25")
            if ul < 3.0:
                reasons.append("ul<3")
            if lat > 150.0:
                reasons.append("lat>150")
            subcauses["+".join(reasons)] += 1

        primary_access = ((ctx.broadband.primary_access if ctx.broadband else "") or "").upper()
        if primary_access in tech_metrics:
            if ctx.inputs.ookla_download_mbps is not None:
                tech_metrics[primary_access]["dl"].append(ctx.inputs.ookla_download_mbps)
            if ctx.inputs.ookla_upload_mbps is not None:
                tech_metrics[primary_access]["ul"].append(ctx.inputs.ookla_upload_mbps)
            if ctx.inputs.ookla_latency_ms is not None:
                tech_metrics[primary_access]["lat"].append(ctx.inputs.ookla_latency_ms)

    return {
        "linkage_partition": {
            "both": len(both),
            "ookla_only": ookla_only,
            "fcc_only": fcc_only,
            "neither": neither,
        },
        "concordance_matrix": {
            "both_pass": matrix[(True, True)],
            "fcc_pass_ookla_fail": matrix[(True, False)],
            "fcc_fail_ookla_pass": matrix[(False, True)],
            "both_fail": matrix[(False, False)],
        },
        "fcc_pass_ookla_fail_subcauses": dict(sorted(subcauses.items())),
        "measured_by_primary_access": {
            tech: {metric: quantiles(vals) for metric, vals in bucket.items()}
            for tech, bucket in tech_metrics.items()
        },
    }


def compute_scenario_sensitivity(db: Any) -> List[Dict[str, Any]]:
    """Run all policy preset sensitivity scenarios under year-round conditions."""
    from services.scenario_engine import ScenarioEngine
    from services.scenario_input_cache import ScenarioInputCache

    ScenarioInputCache.clear()
    rows: List[Dict[str, Any]] = []
    for scenario_id, label, thresholds in POLICY_SCENARIOS:
        preview = ScenarioEngine.preview(db, thresholds, season="year_round")
        rows.append(
            {
                "id": scenario_id,
                "label": label,
                "thresholds": thresholds,
                "summary": preview["summary"],
            }
        )
    return rows


def compute_starlink_substitution(
    contexts: Dict[str, Any],
    monthly_cost: float = 120.0,
) -> Dict[str, Any]:
    """Compare configured regional ISP pricing vs. uniform Starlink ($120/mo) on income-linked regions."""
    from services.telehealth_classification import TelehealthInputs, classify_telehealth

    income_contexts = [ctx for ctx in contexts.values() if ctx.inputs.median_income is not None]
    isp_status: Counter[str] = Counter()
    leo_status: Counter[str] = Counter()
    isp_affordability: Counter[str] = Counter()
    leo_affordability: Counter[str] = Counter()
    configured_costs: Counter[str] = Counter()

    for ctx in income_contexts:
        if ctx.inputs.monthly_internet_cost is not None:
            configured_costs[f"{ctx.inputs.monthly_internet_cost:.2f}"] += 1
        isp_status[ctx.classification.status] += 1
        isp_affordability[ctx.classification.affordability_status] += 1

        leo_burden = (monthly_cost / (ctx.inputs.median_income / 12.0)) * 100.0
        leo_inputs = TelehealthInputs(
            latitude=ctx.inputs.latitude,
            longitude=ctx.inputs.longitude,
            access_modes=ctx.inputs.access_modes,
            ookla_download_mbps=ctx.inputs.ookla_download_mbps,
            ookla_upload_mbps=ctx.inputs.ookla_upload_mbps,
            ookla_latency_ms=ctx.inputs.ookla_latency_ms,
            fcc_coverage_pct=ctx.inputs.fcc_coverage_pct,
            median_income=ctx.inputs.median_income,
            monthly_internet_cost=monthly_cost,
            burden_pct=leo_burden,
            nearest_clinic_distance_km=ctx.inputs.nearest_clinic_distance_km,
            clinic_data_available=ctx.inputs.clinic_data_available,
        )
        leo_res = classify_telehealth(leo_inputs)
        leo_status[leo_res.status] += 1
        leo_affordability[leo_res.affordability_status] += 1

    return {
        "income_linked_count": len(income_contexts),
        "substituted_monthly_cost_usd": monthly_cost,
        "configured_monthly_isp_costs_usd": dict(sorted(configured_costs.items())),
        "isp_baseline_status": dict(sorted(isp_status.items())),
        "starlink_status": dict(sorted(leo_status.items())),
        "isp_affordability": dict(sorted(isp_affordability.items())),
        "starlink_affordability": dict(sorted(leo_affordability.items())),
    }


def _nearest_within_radius(
    regions: Sequence[Any],
    buckets: Dict[Tuple[int, int], List[Any]],
    max_radius_km: float,
    candidate_fn: Callable[[float, float, float], Any],
    haversine_fn: Callable[[float, float, float, float], float],
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Compute matched region count and distance quantiles for a candidate radius."""
    distances: List[float] = []
    matched = 0
    for region in regions:
        if region.centroid_lat is None or region.centroid_lon is None:
            continue
        best = float("inf")
        for key in candidate_fn(float(region.centroid_lat), float(region.centroid_lon), max_radius_km):
            for rec in buckets.get(key, []):
                dist = haversine_fn(
                    float(region.centroid_lat),
                    float(region.centroid_lon),
                    rec.centroid_lat,
                    rec.centroid_lon,
                )
                if dist < best:
                    best = dist
        if best <= max_radius_km:
            matched += 1
            distances.append(best)
    return matched, quantiles(distances)


def compute_spatial_radius_ablation(
    db: Any,
    regions: Sequence[Any],
    radii_km: Sequence[float],
) -> List[Dict[str, Any]]:
    """Sweep spatial join cutoffs for Ookla tiles and ACS ZCTA centroids (Table 5)."""
    from services.healthcare_desert_calculator import haversine_km
    from services.telehealth_classification import (
        TelehealthClassificationService,
        _candidate_buckets,
    )

    n_regions = len(regions)
    ookla_buckets = TelehealthClassificationService._latest_ookla_buckets(db)
    income_buckets = TelehealthClassificationService._income_buckets(db)

    rows: List[Dict[str, Any]] = []
    for radius_km in radii_km:
        ookla_matched, ookla_q = _nearest_within_radius(
            regions, ookla_buckets, radius_km, _candidate_buckets, haversine_km
        )
        acs_matched, acs_q = _nearest_within_radius(
            regions, income_buckets, radius_km, _candidate_buckets, haversine_km
        )
        rows.append(
            {
                "radius_km": float(radius_km),
                "ookla": {
                    "matched": ookla_matched,
                    "total": n_regions,
                    "pct": pct(ookla_matched, n_regions),
                    "distance_km": ookla_q,
                },
                "acs": {
                    "matched": acs_matched,
                    "total": n_regions,
                    "pct": pct(acs_matched, n_regions),
                    "distance_km": acs_q,
                },
            }
        )
    return rows


def _measure_endpoint(
    name: str,
    request_fn: Callable[[], Any],
    runs: int,
    clear_cache_each_run: bool = False,
) -> Dict[str, Any]:
    """Measure Flask test client response latency statistics (milliseconds)."""
    from services.scenario_input_cache import ScenarioInputCache

    timings: List[float] = []
    for _ in range(max(1, runs)):
        if clear_cache_each_run:
            ScenarioInputCache.clear()
        start = time.perf_counter()
        response = request_fn()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark endpoint {name} failed with HTTP {response.status_code}")
        timings.append(elapsed_ms)

    ordered = sorted(timings)
    return {
        "endpoint": name,
        "runs": len(ordered),
        "mean_ms": round(statistics.mean(ordered), 2),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(interpolated_percentile(ordered, 0.95), 2),
        "min_ms": round(ordered[0], 2),
        "max_ms": round(ordered[-1], 2),
    }


def _resolve_region_targets(
    regions: Sequence[Any],
    preferred_profile_code: str,
    preferred_compare_codes: Sequence[str],
) -> Tuple[Optional[str], List[str]]:
    """Resolve benchmark region codes cleanly on both Alaska and synthetic databases."""
    available = [r.region_code for r in regions]
    if not available:
        return None, []
    available_set = set(available)
    profile_code = preferred_profile_code if preferred_profile_code in available_set else available[0]
    compare_codes = [code for code in preferred_compare_codes if code in available_set]
    if len(compare_codes) < min(3, len(available)):
        compare_codes = available[: min(3, len(available))]
    return profile_code, compare_codes


def run_latency_benchmarks(
    regions: Sequence[Any],
    profile_code: str = DEFAULT_PROFILE_CODE,
    compare_codes: Sequence[str] = DEFAULT_COMPARE_CODES,
    cold_runs: int = 5,
    warm_runs: int = 50,
    standard_runs: int = 10,
    data_gaps_runs: int = 15,
) -> Dict[str, Any]:
    """Run Flask test-client API latency benchmarks across key endpoints (Table 6)."""
    from app import app

    client = app.test_client()
    health_resp = client.get("/api/health")
    if health_resp.status_code != 200:
        raise RuntimeError(f"/api/health failed with HTTP {health_resp.status_code}")

    resolved_profile, resolved_compare = _resolve_region_targets(regions, profile_code, compare_codes)
    scenario_payload = {
        "min_download_mbps": 100,
        "min_upload_mbps": 20,
        "max_latency_ms": 100,
        "affordability_burden_pct": 2.0,
        "season": "year_round",
    }

    endpoints: List[Dict[str, Any]] = []
    # Prime once before warm measurement, or measure cold first then warm immediately after.
    endpoints.append(
        _measure_endpoint(
            "/scenarios/preview (cold)",
            lambda: client.post("/api/cat/scenarios/preview", json=scenario_payload),
            runs=cold_runs,
            clear_cache_each_run=True,
        )
    )
    client.post("/api/cat/scenarios/preview", json=scenario_payload)
    endpoints.append(
        _measure_endpoint(
            "/scenarios/preview (warm)",
            lambda: client.post("/api/cat/scenarios/preview", json=scenario_payload),
            runs=warm_runs,
            clear_cache_each_run=False,
        )
    )
    endpoints.append(
        _measure_endpoint(
            "/performance/summary",
            lambda: client.get("/api/cat/performance/summary"),
            runs=standard_runs,
        )
    )
    if resolved_profile:
        endpoints.append(
            _measure_endpoint(
                f"/regions/{resolved_profile}/research-profile",
                lambda: client.get(f"/api/cat/regions/{resolved_profile}/research-profile?season=year_round"),
                runs=standard_runs,
            )
        )
    endpoints.append(
        _measure_endpoint(
            "/data-gaps",
            lambda: client.get("/api/cat/data-gaps"),
            runs=data_gaps_runs,
        )
    )
    endpoints.append(
        _measure_endpoint(
            "/regions/summary",
            lambda: client.get("/api/cat/regions/summary?season=year_round"),
            runs=standard_runs,
        )
    )
    if resolved_compare:
        joined = ",".join(resolved_compare)
        endpoints.append(
            _measure_endpoint(
                f"/regions/research-profiles ({len(resolved_compare)} pins)",
                lambda: client.get(f"/api/cat/regions/research-profiles?codes={joined}&season=year_round"),
                runs=standard_runs,
            )
        )

    return {
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        },
        "endpoints": endpoints,
    }


def evaluate_all(
    db: Any,
    radii_km: Sequence[float] = DEFAULT_RADII_KM,
    run_benchmarks: bool = False,
    profile_code: str = DEFAULT_PROFILE_CODE,
    compare_codes: Sequence[str] = DEFAULT_COMPARE_CODES,
    cold_runs: int = 5,
    warm_runs: int = 50,
    standard_runs: int = 10,
    data_gaps_runs: int = 15,
) -> Dict[str, Any]:
    """Execute the full evaluation pipeline over an open SQLAlchemy session."""
    from database.models import CATRegion
    from services.telehealth_classification import TelehealthClassificationService

    regions = db.query(CATRegion).order_by(CATRegion.region_code).all()
    contexts = TelehealthClassificationService.classify_regions(db, regions)
    hds_by_season = compute_hds_by_season(db)
    year_round_hds_map = {
        item["region_code"]: item.get("healthcare_need_score") for item in hds_by_season["year_round"]
    }

    dataset_metrics = compute_dataset_metrics(db, regions, contexts, hds_by_season)
    classification = compute_classification_and_missingness(contexts, year_round_hds_map)
    hds_strat = compute_hds_stratification(regions, hds_by_season)
    concordance = compute_fcc_ookla_concordance(contexts)
    scenarios = compute_scenario_sensitivity(db)
    starlink = compute_starlink_substitution(contexts)
    radius_ablation = compute_spatial_radius_ablation(db, regions, radii_km)

    benchmarks: Optional[Dict[str, Any]] = None
    if run_benchmarks:
        benchmarks = run_latency_benchmarks(
            regions=regions,
            profile_code=profile_code,
            compare_codes=compare_codes,
            cold_runs=cold_runs,
            warm_runs=warm_runs,
            standard_runs=standard_runs,
            data_gaps_runs=data_gaps_runs,
        )

    return {
        "dataset_metrics": dataset_metrics,
        "classification_and_missingness": classification,
        "hds_stratification": hds_strat,
        "fcc_ookla_concordance": concordance,
        "scenario_sensitivity": scenarios,
        "starlink_substitution": starlink,
        "spatial_radius_ablation": radius_ablation,
        "latency_benchmarks": benchmarks,
    }


def _format_median_iqr(stats_dict: Optional[Dict[str, Any]], unit: str = "") -> str:
    """Format 'median [q1, q3]' helper for LaTeX tables."""
    if not stats_dict:
        return "--"
    suffix = f" {unit}" if unit else ""
    return f"{stats_dict['median']:.2f} [{stats_dict['q1']:.2f}, {stats_dict['q3']:.2f}]{suffix}"


def render_latex_tables(results: Dict[str, Any]) -> str:
    """Render deterministic LaTeX tables matching the paper evaluation suite."""
    dm = results["dataset_metrics"]
    inv = dm["inventory"]
    n_reg = inv["cat_regions"]
    tr = dm["transport"]
    tiers = tr["cat_tiers"]
    bb = dm["broadband"]
    hc = dm["healthcare_facilities"]
    by_type = hc["by_type"]
    prox = dm["proximity_km"]
    hds = dm["hds_by_season"]

    # Table: Dataset coverage, transport access, proximity, and HDS
    t3_lines = [
        r"\begin{table*}[t]",
        (
            r"\caption{Dataset coverage, transport access, healthcare proximity, and modeled "
            f"healthcare desert scores in TENeT ({n_reg} communities).}}"
        ),
        r"\label{tab:tenet_metrics}",
        r"\centering",
        r"\footnotesize",
        (
            r"\begin{tabular}{@{} >{\raggedright\arraybackslash}p{\dimexpr 0.38\textwidth - 5pt\relax} "
            r"@{\hspace{8pt}} >{\raggedright\arraybackslash}p{\dimexpr 0.37\textwidth - 6pt\relax} "
            r"@{\hspace{8pt}} >{\raggedright\arraybackslash}p{\dimexpr 0.25\textwidth - 5pt\relax} @{}}"
        ),
        r"\hline",
        r"\textbf{Metric} & \textbf{Result} & \textbf{Interpretation}\\\hline",
        f"Communities represented & {n_reg} & Community inventory \\\\",
        (
            f"CAT tier 1 / 2 / 3 / 4 & {tiers.get(1, 0)} / {tiers.get(2, 0)} / "
            f"{tiers.get(3, 0)} / {tiers.get(4, 0)} & Transport classification \\\\"
        ),
        (
            f"Air-only communities & {tr['air_only_count']}/{n_reg} "
            f"({tr['air_only_pct']:.2f}\\%) & Transport classification \\\\"
        ),
        (
            f"No direct access & {tr['no_direct_access_count']}/{n_reg} "
            f"({tr['no_direct_access_pct']:.2f}\\%) & Transport classification \\\\"
        ),
        (
            f"Communities linked to FCC places & {bb['communities_linked_to_fcc']}/{n_reg} "
            f"({bb['communities_linked_to_fcc_pct']:.2f}\\%) & Join completeness \\\\"
        ),
        (
            f"Satellite-primary FCC places & {bb['satellite_primary_places']}/{bb['fcc_places_total']} "
            f"({bb['satellite_primary_pct']:.2f}\\%) & Reported availability \\\\"
        ),
        (
            f"Mean fiber 25/3 coverage & {_fmt_num(bb['mean_fiber_25mbps_pct'])}\\% "
            f"({bb['fcc_places_total']} places) & Unweighted place average \\\\"
        ),
        (
            f"Healthcare facilities & {hc['total']}: {by_type['clinic']} clinics, "
            f"{by_type['hospital']} hospitals, {by_type['pharmacy']} pharmacies & Recorded OSM inventory \\\\"
        ),
        (
            f"Communities without linked facility & {hc['communities_without_linked_facility']}/{n_reg} "
            f"({hc['communities_without_linked_facility_pct']:.2f}\\%) & Nearest-region assignment \\\\"
        ),
        (
            f"Emergency / specialist flags & {hc['emergency_count']} / {hc['specialists_count']} "
            f"of {hc['total']} facilities & Recorded tags \\\\"
        ),
        (
            f"Nearest clinic distance: median [Q1,Q3] & "
            f"{_format_median_iqr(prox['nearest_clinic_only'], 'km')} & Straight-line; centroids \\\\"
        ),
        (
            f"Nearest hospital distance: median [Q1,Q3] & "
            f"{_format_median_iqr(prox['nearest_hospital_only'], 'km')} & Straight-line; centroids \\\\"
        ),
        (
            f"Communities $>$50 km from clinic & {prox['communities_gt_50km_clinic']}/{n_reg} "
            f"({prox['communities_gt_50km_clinic_pct']:.2f}\\%) & Straight-line; centroids \\\\"
        ),
        (
            f"Communities $>$100 km from hospital & {prox['communities_gt_100km_hospital']}/{n_reg} "
            f"({prox['communities_gt_100km_hospital_pct']:.2f}\\%) & Straight-line; centroids \\\\"
        ),
        (
            f"HDS mean: summer / year-round / winter & "
            f"{_fmt_num(hds['summer']['quantiles']['mean'] if hds['summer']['quantiles'] else None)} / "
            f"{_fmt_num(hds['year_round']['quantiles']['mean'] if hds['year_round']['quantiles'] else None)} / "
            f"{_fmt_num(hds['winter']['quantiles']['mean'] if hds['winter']['quantiles'] else None)} "
            r"& Model outputs; 0--100 \\"
        ),
        (
            f"HDS $>$70: summer / year-round / winter & "
            f"{hds['summer']['gt_70_count']} / {hds['year_round']['gt_70_count']} / "
            f"{hds['winter']['gt_70_count']} of {n_reg} & Continuous score bins \\\\"
        ),
        (
            f"CAT travel-time fields missing & {dm['missing_travel_time_data_points']}/"
            f"{inv['cat_data_points'] or n_reg} ({dm['missing_travel_time_pct']:.2f}\\%) "
            r"& Seasonality uses defaults \\"
        ),
        (
            f"FCC coverage missing after join & {bb['communities_missing_fcc']}/{n_reg} "
            f"({bb['communities_missing_fcc_pct']:.2f}\\%) & Data completeness \\\\"
        ),
        r"\hline",
        r"\end{tabular}",
        r"\end{table*}",
    ]

    # Table: Scenario sensitivity
    starlink = results["starlink_substitution"]
    leo_st = starlink["starlink_status"]
    unavail_total = (
        results["classification_and_missingness"]["overall_status"].get("DATA_UNAVAILABLE", 0)
    )
    t4_lines = [
        r"\begin{table*}[t]",
        (
            f"\\caption{{What-if policy scenario sensitivity across {n_reg} communities "
            f"(year-round season; {unavail_total} regions remain DATA\\_UNAVAILABLE).}}"
        ),
        r"\label{tab:scenario_sensitivity}",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\begin{tabulary}{\textwidth}{@{}Lrrrrrr@{}}",
        r"\hline",
        (
            r"\textbf{Scenario / Policy Configuration} & \textbf{Ready} & \textbf{Anchor} & "
            r"\textbf{Limited} & \textbf{Critical} & \textbf{Unavail.} & "
            r"\shortstack[r]{\textbf{Changed}\\\textbf{(+ / --)}}\\"
        ),
        r"\hline",
    ]
    for row in results["scenario_sensitivity"]:
        s = row["summary"]
        label_tex = row["label"].replace("%", r"\%")
        t4_lines.append(
            f"{label_tex} & {s['telehealth_ready']} & {s['community_anchor']} & "
            f"{s['limited_telehealth']} & {s['critical_gap']} & {s['data_unavailable']} & "
            f"{s['status_changed_regions']} ({s['improved_count']} / {s['worsened_count']}) \\\\"
        )
    leo_unavail = (n_reg - starlink["income_linked_count"]) + leo_st.get("DATA_UNAVAILABLE", 0)
    t4_lines.extend(
        [
            (
                r"Starlink LEO Cost Substitution (\$120/mo fixed)\textsuperscript{\dag} & "
                f"{leo_st.get('TELEHEALTH_READY', 0)} & {leo_st.get('COMMUNITY_ANCHOR', 0)} & "
                f"{leo_st.get('LIMITED_TELEHEALTH', 0)} & {leo_st.get('CRITICAL_GAP', 0)} & "
                f"{leo_unavail} & --- \\\\"
            ),
            r"\hline",
            r"\end{tabulary}",
            r"\end{table*}",
        ]
    )

    # Table: Spatial join radius ablation
    t5_lines = [
        r"\begin{table}[t]",
        (
            f"\\caption{{Spatial join radius sensitivity for Ookla speed tiles and ACS ZCTA records "
            f"($N={n_reg}$ communities).}}"
        ),
        r"\label{tab:radius_ablation}",
        r"\centering",
        r"\scriptsize",
        (
            r"\begin{tabular}{@{} >{\raggedleft\arraybackslash}p{\dimexpr 0.14\columnwidth\relax} "
            r"@{\hspace{6pt}} >{\raggedleft\arraybackslash}p{\dimexpr 0.43\columnwidth - 6pt\relax} "
            r"@{\hspace{6pt}} >{\raggedleft\arraybackslash}p{\dimexpr 0.43\columnwidth - 6pt\relax} @{}}"
        ),
        r"\hline",
        (
            r"\textbf{Radius} & \shortstack[r]{\textbf{Ookla Match (\%)}\\\textbf{Med.\ [Q1, Q3]~km}} & "
            r"\shortstack[r]{\textbf{ACS Match (\%)}\\\textbf{Med.\ [Q1, Q3]~km}}\\"
        ),
        r"\hline",
    ]
    rows_rad = results["spatial_radius_ablation"]
    for idx_r, row in enumerate(rows_rad):
        o = row["ookla"]
        a = row["acs"]
        o_top = f"{o['matched']} ({o['pct']:.2f}\\%)"
        o_bot = _format_median_iqr(o["distance_km"])
        a_top = f"{a['matched']} ({a['pct']:.2f}\\%)"
        a_bot = _format_median_iqr(a["distance_km"])
        if abs(row["radius_km"] - 75.0) < 1e-6:
            o_cell = f"\\shortstack[r]{{\\textbf{{{o_top}}}\\\\\\textbf{{{o_bot}}}}}"
        else:
            o_cell = f"\\shortstack[r]{{{o_top}\\\\{o_bot}}}"
        if abs(row["radius_km"] - 55.0) < 1e-6:
            a_cell = f"\\shortstack[r]{{\\textbf{{{a_top}}}\\\\\\textbf{{{a_bot}}}}}"
        else:
            a_cell = f"\\shortstack[r]{{{a_top}\\\\{a_bot}}}"
        sep = r" \\[5pt]" if idx_r < len(rows_rad) - 1 else r" \\"
        t5_lines.append(f"{row['radius_km']:g}~km & {o_cell} & {a_cell}{sep}")
    t5_lines.extend([r"\hline", r"\end{tabular}", r"\end{table}"])

    # Table: Latency benchmark
    t6_lines = [
        r"\begin{table}[t]",
        r"\caption{Flask API response latency benchmark (single-worker Flask test client).}",
        r"\label{tab:latency_bench}",
        r"\centering",
        r"\scriptsize",
        (
            r"\begin{tabular}{@{} >{\raggedright\arraybackslash}p{\dimexpr \columnwidth - 95pt\relax} "
            r"@{\hspace{4pt}} r @{\hspace{4pt}} r @{\hspace{4pt}} r @{}}"
        ),
        r"\hline",
        (
            r"\textbf{Endpoint ($n$ runs)} & \shortstack[r]{\textbf{Mean}\\\textbf{(ms)}} & "
            r"\shortstack[r]{\textbf{Med.}\\\textbf{(ms)}} & \shortstack[r]{\textbf{p95}\\\textbf{(ms)}}\\"
        ),
        r"\hline",
    ]
    bench = results.get("latency_benchmarks")
    if bench and bench.get("endpoints"):
        eps = bench["endpoints"]
        for idx_e, ep in enumerate(eps):
            raw_ep = ep["endpoint"].replace("_", r"\_")
            if " (" in raw_ep:
                path_part, tag_part = raw_ep.split(" (", 1)
                tag_clean = tag_part.rstrip(")")
                ep_label = f"\\texttt{{{path_part}}}\\newline({tag_clean}, $n={ep['runs']}$)"
            else:
                ep_label = f"\\texttt{{{raw_ep}}} ($n={ep['runs']}$)"
            ep_label = ep_label.replace("/research-profile}", r"}\newline\texttt{/research-profile}")
            ep_label = ep_label.replace("research-profiles", r"research-}\newline\texttt{profiles")
            sep = r" \\[3pt]" if idx_e < len(eps) - 1 else r" \\"
            t6_lines.append(
                f"{ep_label} & {ep['mean_ms']:,.2f} & {ep['median_ms']:,.2f} & {ep['p95_ms']:,.2f}{sep}"
            )
    else:
        t6_lines.append(r"\multicolumn{4}{c}{Benchmarks skipped (--skip-benchmarks)} \\")
    t6_lines.extend([r"\hline", r"\end{tabular}", r"\end{table}"])

    return "\n\n".join(["\n".join(t3_lines), "\n".join(t4_lines), "\n".join(t5_lines), "\n".join(t6_lines)]) + "\n"


def render_human_summary(results: Dict[str, Any]) -> str:
    """Build concise console summary of reproduced findings."""
    dm = results["dataset_metrics"]
    inv = dm["inventory"]
    cls = results["classification_and_missingness"]
    conc = results["fcc_ookla_concordance"]
    star = results["starlink_substitution"]

    lines = [
        "=== TENeT Paper Evaluation Reproduction Summary ===",
        (
            f"Inventory: regions={inv['cat_regions']}, broadband={inv['broadband_places']}, "
            f"income_zones={inv['census_income_zones']}, ookla={inv['ookla_tiles']}, sites={inv['healthcare_sites']}"
        ),
        f"Baseline Status: {cls['overall_status']}",
        f"Data Confidence: {cls['profile_data_confidence']} (has_data_gap={cls['has_data_gap_count']})",
        f"FCC-vs-Ookla Matrix: {conc['concordance_matrix']} | Fail subcauses: {conc['fcc_pass_ookla_fail_subcauses']}",
        f"Starlink $120/mo Status (n={star['income_linked_count']}): {star['starlink_status']}",
        "Spatial Radius Ablation:",
    ]
    for row in results["spatial_radius_ablation"]:
        o = row["ookla"]
        a = row["acs"]
        lines.append(
            f"  {row['radius_km']:5.1f} km -> Ookla={o['matched']}/{o['total']} ({o['pct']:.2f}%) | "
            f"ACS={a['matched']}/{a['total']} ({a['pct']:.2f}%)"
        )
    bench = results.get("latency_benchmarks")
    if bench and bench.get("endpoints"):
        lines.append("Latency Benchmarks:")
        for ep in bench["endpoints"]:
            lines.append(
                f"  {ep['endpoint']} (n={ep['runs']}): mean={ep['mean_ms']:.2f} ms, "
                f"median={ep['median_ms']:.2f} ms, p95={ep['p95_ms']:.2f} ms"
            )
    else:
        lines.append("Latency Benchmarks: skipped")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Reproduce TENeT quantitative evaluation tables, ablations, and Flask benchmarks."
    )
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database (defaults to backend DB_PATH).")
    parser.add_argument("--json-out", type=str, default=None, help="Optional path to write full deterministic JSON.")
    parser.add_argument("--tex-out", type=str, default=None, help="Optional path to write LaTeX tables.")
    parser.add_argument(
        "--format",
        choices=("summary", "json", "tex"),
        default="summary",
        help="Stdout output format (default: summary).",
    )
    parser.add_argument(
        "--radii",
        type=float,
        nargs="+",
        default=DEFAULT_RADII_KM,
        help="Spatial join radii in km for ablation (default: 10 25 55 75 100 150).",
    )
    parser.add_argument("--profile-code", type=str, default=DEFAULT_PROFILE_CODE, help="Region code for profile bench.")
    parser.add_argument(
        "--compare-codes",
        type=str,
        nargs="+",
        default=DEFAULT_COMPARE_CODES,
        help="Region codes for multi-pin comparison benchmark.",
    )
    parser.add_argument("--cold-runs", type=int, default=5, help="Cold-cache runs for scenario benchmark.")
    parser.add_argument("--warm-runs", type=int, default=50, help="Warm-cache runs for scenario benchmark.")
    parser.add_argument("--runs", type=int, default=10, help="Standard runs for summary/profile/compare endpoints.")
    parser.add_argument("--data-gaps-runs", type=int, default=15, help="Runs for /api/cat/data-gaps benchmark.")
    parser.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip timed Flask endpoint benchmarks for deterministic fast execution.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    args = build_arg_parser().parse_args(argv)
    if args.db:
        os.environ["DB_TYPE"] = "sqlite"
        os.environ["DB_PATH"] = os.path.abspath(args.db)

    from database.config import SessionLocal

    db = SessionLocal()
    try:
        results = evaluate_all(
            db,
            radii_km=args.radii,
            run_benchmarks=not args.skip_benchmarks,
            profile_code=args.profile_code,
            compare_codes=args.compare_codes,
            cold_runs=args.cold_runs,
            warm_runs=args.warm_runs,
            standard_runs=args.runs,
            data_gaps_runs=args.data_gaps_runs,
        )
    finally:
        db.close()

    json_payload = json.dumps(results, indent=2, sort_keys=True) + "\n"
    tex_payload = render_latex_tables(results)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_payload, encoding="utf-8")

    if args.tex_out:
        tex_path = Path(args.tex_out)
        tex_path.parent.mkdir(parents=True, exist_ok=True)
        tex_path.write_text(tex_payload, encoding="utf-8")

    if args.format == "json":
        sys.stdout.write(json_payload)
    elif args.format == "tex":
        sys.stdout.write(tex_payload)
    else:
        print(render_human_summary(results))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
