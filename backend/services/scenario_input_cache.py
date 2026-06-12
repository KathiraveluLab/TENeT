"""
Cached scenario inputs for interactive what-if analysis.

The scenario preview endpoint needs to respond quickly while users drag
sliders.  This service precomputes the expensive, factual inputs once per
database/season and lets ScenarioEngine do cheap threshold comparisons.
"""

from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
from services.season_constants import (
    ROAD_QUALITY_LOCAL,
    SEASON_YEAR_ROUND,
    VALID_ROAD_QUALITIES,
    VALID_SEASONS,
)


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
    gmap = _ISP_CONFIG.get("zcta_mappings", {})
    gci_urban = set(gmap.get("gci_urban", []))
    extreme_rural = set(gmap.get("extreme_rural", []))
    starlink_satellite = set(gmap.get("starlink_satellite", []))
    pricing = _ISP_CONFIG.get("isp_pricing", {})

    if zcta in extreme_rural:
        p = pricing.get("extreme_rural", {"cost": 450.0, "name": "Extreme Rural"})
        return float(p.get("cost", 450.0)), str(p.get("name", "Extreme Rural"))
    if zcta in gci_urban:
        p = pricing.get("gci", {"cost": 125.0, "name": "GCI"})
        return float(p.get("cost", 125.0)), str(p.get("name", "GCI"))
    if zcta in starlink_satellite:
        p = pricing.get("starlink", {"cost": 120.0, "name": "Starlink"})
        return float(p.get("cost", 120.0)), str(p.get("name", "Starlink"))

    p = pricing.get("fastwyre", {"cost": 350.0, "name": "FastWyre"})
    return float(p.get("cost", 350.0)), str(p.get("name", "FastWyre"))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return HealthcareDesertCalculator.calculate_distance(lat1, lon1, lat2, lon2)


def _bucket_key(lat: float, lon: float) -> Tuple[int, int]:
    return math.floor(lat), math.floor(lon)


def _candidate_buckets(lat: float, lon: float, max_km: float) -> Iterable[Tuple[int, int]]:
    lat_window = max_km / 111.0
    lon_window = max_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    min_lat = math.floor(lat - lat_window)
    max_lat = math.floor(lat + lat_window)
    min_lon = math.floor(lon - lon_window)
    max_lon = math.floor(lon + lon_window)
    for lat_key in range(min_lat, max_lat + 1):
        for lon_key in range(min_lon, max_lon + 1):
            yield lat_key, lon_key


class ScenarioInputCache:
    """In-memory cache of factual inputs needed by scenario previews."""

    _cache: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    _build_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()
        cls._build_counts.clear()

    @classmethod
    def build_count(cls, db: Session, season: str = SEASON_YEAR_ROUND) -> int:
        return cls._build_counts.get(cls._cache_key(db, season), 0)

    @classmethod
    def get(cls, db: Session, season: str = SEASON_YEAR_ROUND) -> List[Dict[str, Any]]:
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND

        key = cls._cache_key(db, season)
        cached = cls._cache.get(key)
        if cached is not None:
            return cached

        built = cls._build(db, season)
        cls._cache[key] = built
        cls._build_counts[key] += 1
        return built

    @staticmethod
    def _cache_key(db: Session, season: str) -> Tuple[str, str]:
        bind = db.get_bind()
        return bind.url.render_as_string(hide_password=True), season

    @classmethod
    def _build(cls, db: Session, season: str) -> List[Dict[str, Any]]:
        regions = db.query(CATRegion).order_by(CATRegion.region_name).all()
        region_codes = [region.region_code for region in regions]

        facilities = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None),
        ).all()
        status_clinics = [
            site for site in facilities
            if (site.site_type or "").lower() in {"clinic", "hospital", "health_center"}
        ]

        broadband_lookup = cls._broadband_lookup(db, region_codes)
        census_buckets: Dict[Tuple[int, int], List[CensusIncome]] = defaultdict(list)
        for record in cls._census_records(db):
            census_buckets[
                _bucket_key(float(record.centroid_lat), float(record.centroid_lon))
            ].append(record)

        ookla_buckets = cls._latest_ookla_buckets(db)
        data_points_by_region, first_data_point_by_region = cls._data_points(db, region_codes)
        site_counts, specialist_regions = cls._healthcare_site_stats(facilities)

        baseline_threshold = float(
            _ISP_CONFIG.get("thresholds", {}).get("affordability_burden_pct", 2.0)
        )

        return [
            cls._region_input(
                region=region,
                season=season,
                facilities=facilities,
                status_clinics=status_clinics,
                broadband=broadband_lookup.get(region.region_code),
                census_buckets=census_buckets,
                ookla_buckets=ookla_buckets,
                data_points=data_points_by_region.get(region.region_code, []),
                first_data_point=first_data_point_by_region.get(region.region_code),
                site_count=site_counts.get(region.region_code, 0),
                has_specialists=region.region_code in specialist_regions,
                baseline_threshold=baseline_threshold,
            )
            for region in regions
        ]

    @staticmethod
    def _broadband_lookup(db: Session, region_codes: List[str]) -> Dict[str, BroadbandCoverage]:
        records = db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code.in_(region_codes)
        ).all()
        lookup: Dict[str, BroadbandCoverage] = {}
        for record in records:
            if record.region_code and record.region_code not in lookup:
                lookup[record.region_code] = record
        return lookup

    @staticmethod
    def _census_records(db: Session) -> List[CensusIncome]:
        return db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
        ).all()

    @staticmethod
    def _latest_ookla_buckets(db: Session) -> Dict[Tuple[int, int], List[Any]]:
        latest = db.query(
            OoklaPerformance.year, OoklaPerformance.quarter
        ).distinct().order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc(),
        ).first()
        if latest is None:
            return {}

        rows = db.query(
            OoklaPerformance.centroid_lat,
            OoklaPerformance.centroid_lon,
            OoklaPerformance.avg_d_kbps,
            OoklaPerformance.avg_u_kbps,
            OoklaPerformance.avg_lat_ms,
        ).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
        ).all()

        buckets: Dict[Tuple[int, int], List[Any]] = defaultdict(list)
        for row in rows:
            buckets[_bucket_key(float(row.centroid_lat), float(row.centroid_lon))].append(row)
        return buckets

    @staticmethod
    def _data_points(
        db: Session, region_codes: List[str]
    ) -> Tuple[Dict[str, List[CATDataPoint]], Dict[str, CATDataPoint]]:
        records = db.query(CATDataPoint).filter(
            CATDataPoint.region_code.in_(region_codes)
        ).all()
        grouped: Dict[str, List[CATDataPoint]] = defaultdict(list)
        first: Dict[str, CATDataPoint] = {}
        for record in records:
            if not record.region_code:
                continue
            grouped[record.region_code].append(record)
            first.setdefault(record.region_code, record)
        return grouped, first

    @staticmethod
    def _healthcare_site_stats(
        facilities: List[HealthcareSite],
    ) -> Tuple[Dict[str, int], set[str]]:
        counts: Dict[str, int] = defaultdict(int)
        specialists: set[str] = set()
        for site in facilities:
            if not site.region_code:
                continue
            counts[site.region_code] += 1
            if site.has_specialists:
                specialists.add(site.region_code)
        return counts, specialists

    @classmethod
    def _region_input(
        cls,
        *,
        region: CATRegion,
        season: str,
        facilities: List[HealthcareSite],
        status_clinics: List[HealthcareSite],
        broadband: Optional[BroadbandCoverage],
        census_buckets: Dict[Tuple[int, int], List[CensusIncome]],
        ookla_buckets: Dict[Tuple[int, int], List[Any]],
        data_points: List[CATDataPoint],
        first_data_point: Optional[CATDataPoint],
        site_count: int,
        has_specialists: bool,
        baseline_threshold: float,
    ) -> Dict[str, Any]:
        display_lat = region.centroid_lat
        display_lon = region.centroid_lon
        score_lat = display_lat
        score_lon = display_lon
        if data_points:
            score_lat = sum(point.latitude for point in data_points) / len(data_points)
            score_lon = sum(point.longitude for point in data_points) / len(data_points)

        access_modes = (region.properties or {}).get("primary_access_modes", "")
        distance_threshold_km = 10 if "road" in access_modes.lower() else 50

        income = (
            cls._nearest_income(census_buckets, display_lat, display_lon)
            if display_lat is not None and display_lon is not None
            else None
        )
        monthly_internet_cost: Optional[float] = None
        burden_pct: Optional[float] = None
        median_income: Optional[float] = None
        has_income_data = income is not None

        if income is not None:
            median_income = float(income.median_income)
            monthly_internet_cost, _ = _get_regional_internet_cost(str(income.zcta))
            monthly_income = median_income / 12.0
            burden_pct = (
                float((monthly_internet_cost / monthly_income) * 100.0)
                if monthly_income > 0
                else 100.0
            )
        else:
            monthly_internet_cost = 450.0

        nearest_status_clinic = (
            cls._nearest_distance(status_clinics, display_lat, display_lon)
            if display_lat is not None and display_lon is not None
            else None
        )
        facility_distances = cls._facility_distances(facilities, score_lat, score_lon)
        ookla = (
            cls._nearest_ookla(ookla_buckets, display_lat, display_lon)
            if display_lat is not None and display_lon is not None
            else None
        )

        baseline_status = cls._baseline_status(
            has_income_data=has_income_data,
            burden_pct=burden_pct,
            monthly_internet_cost=monthly_internet_cost,
            affordability_threshold=baseline_threshold,
            nearest_clinic_distance_km=nearest_status_clinic,
            distance_threshold_km=distance_threshold_km,
        )
        baseline_need_score = cls._need_score(
            facility_distances=facility_distances,
            site_count=site_count,
            has_specialists=has_specialists,
            first_data_point=first_data_point,
            season=season,
        )

        missing_fields: List[str] = []
        if broadband is None:
            missing_fields.append("connectivity.fcc_coverage")
        if display_lat is None or display_lon is None or income is None:
            missing_fields.append("affordability.median_income")

        return {
            "region_code": region.region_code,
            "name": region.region_name,
            "lat": float(display_lat) if display_lat is not None else None,
            "lon": float(display_lon) if display_lon is not None else None,
            "access_modes": access_modes,
            "baseline_status": baseline_status,
            "baseline_need_score": baseline_need_score,
            "nearest_clinic_distance_km": nearest_status_clinic,
            "distance_threshold_km": distance_threshold_km,
            "median_income": median_income,
            "monthly_internet_cost": monthly_internet_cost,
            "burden_pct": burden_pct,
            "ookla_download_mbps": (
                float(ookla.avg_d_kbps) / 1000.0
                if ookla is not None and ookla.avg_d_kbps is not None
                else None
            ),
            "ookla_upload_mbps": (
                float(ookla.avg_u_kbps) / 1000.0
                if ookla is not None and ookla.avg_u_kbps is not None
                else None
            ),
            "ookla_latency_ms": (
                float(ookla.avg_lat_ms)
                if ookla is not None and ookla.avg_lat_ms is not None
                else None
            ),
            "fcc_coverage_pct": (
                float(broadband.any_tech_25mbps_pct)
                if broadband is not None and broadband.any_tech_25mbps_pct is not None
                else None
            ),
            "has_data_gap": bool(missing_fields) or bool(
                split_gap_flags(getattr(broadband, "data_gaps", None) if broadband else None)
            ),
            "missing_fields": missing_fields,
            "data_confidence": normalize_confidence(
                getattr(broadband, "confidence", None) if broadband else None
            ),
        }

    @staticmethod
    def _nearest_distance(
        sites: List[HealthcareSite],
        lat: Optional[float],
        lon: Optional[float],
    ) -> Optional[float]:
        if lat is None or lon is None or not sites:
            return None
        nearest = min(
            _haversine_km(float(lat), float(lon), site.latitude, site.longitude)
            for site in sites
        )
        return round(float(nearest), 2)

    @staticmethod
    def _facility_distances(
        facilities: List[HealthcareSite],
        lat: Optional[float],
        lon: Optional[float],
    ) -> Dict[str, float]:
        if lat is None or lon is None:
            return {"clinic": 500.0, "hospital": 500.0, "nearest": 500.0}
        if not facilities:
            return {"clinic": 999.0, "hospital": 999.0, "nearest": 999.0}

        clinic_types = {"clinic", "health_center", "community_health_center"}
        distances = {"clinic": float("inf"), "hospital": float("inf"), "nearest": float("inf")}
        for site in facilities:
            distance = _haversine_km(float(lat), float(lon), site.latitude, site.longitude)
            distances["nearest"] = min(distances["nearest"], distance)
            site_type = (site.site_type or "").lower()
            if site_type in clinic_types:
                distances["clinic"] = min(distances["clinic"], distance)
            if site_type == "hospital":
                distances["hospital"] = min(distances["hospital"], distance)

        return {
            key: (999.0 if value == float("inf") else round(float(value), 2))
            for key, value in distances.items()
        }

    @staticmethod
    def _nearest_income(
        census_buckets: Dict[Tuple[int, int], List[CensusIncome]],
        lat: float,
        lon: float,
        max_km: float = 55.0,
    ) -> Optional[CensusIncome]:
        best = None
        min_dist = float("inf")
        for key in _candidate_buckets(float(lat), float(lon), max_km):
            for record in census_buckets.get(key, []):
                dist = _haversine_km(
                    float(lat),
                    float(lon),
                    record.centroid_lat,
                    record.centroid_lon,
                )
                if dist < min_dist and dist <= max_km:
                    min_dist = dist
                    best = record
        return best

    @staticmethod
    def _nearest_ookla(
        buckets: Dict[Tuple[int, int], List[Any]],
        lat: float,
        lon: float,
        max_km: float = 75.0,
    ) -> Optional[Any]:
        best = None
        min_dist = float("inf")
        for key in _candidate_buckets(float(lat), float(lon), max_km):
            for tile in buckets.get(key, []):
                dist = _haversine_km(float(lat), float(lon), tile.centroid_lat, tile.centroid_lon)
                if dist < min_dist and dist <= max_km:
                    min_dist = dist
                    best = tile
        return best

    @staticmethod
    def _baseline_status(
        *,
        has_income_data: bool,
        burden_pct: Optional[float],
        monthly_internet_cost: Optional[float],
        affordability_threshold: float,
        nearest_clinic_distance_km: Optional[float],
        distance_threshold_km: float,
    ) -> str:
        is_affordable = (
            has_income_data
            and burden_pct is not None
            and monthly_internet_cost is not None
            and burden_pct < affordability_threshold
            and monthly_internet_cost < 400.0
        )
        has_nearby_clinic = (
            nearest_clinic_distance_km is not None
            and nearest_clinic_distance_km <= distance_threshold_km
        )
        is_extreme_cost = monthly_internet_cost is not None and monthly_internet_cost >= 400.0

        if not has_income_data:
            if is_extreme_cost:
                return "COMMUNITY_ANCHOR" if has_nearby_clinic else "CRITICAL_GAP"
            if has_nearby_clinic:
                return "COMMUNITY_ANCHOR"
            return "DATA_UNAVAILABLE"
        if is_affordable:
            return "TELEHEALTH_READY"
        if has_nearby_clinic:
            return "COMMUNITY_ANCHOR"
        return "CRITICAL_GAP"

    @staticmethod
    def _need_score(
        *,
        facility_distances: Dict[str, float],
        site_count: int,
        has_specialists: bool,
        first_data_point: Optional[CATDataPoint],
        season: str,
        road_quality: str = ROAD_QUALITY_LOCAL,
    ) -> float:
        if season not in VALID_SEASONS:
            season = SEASON_YEAR_ROUND
        if road_quality not in VALID_ROAD_QUALITIES:
            road_quality = ROAD_QUALITY_LOCAL

        clinic_score = HealthcareDesertCalculator.score_distance_component(
            facility_distances["clinic"]
        )
        hospital_score = min(100.0, (facility_distances["hospital"] / 500.0) * 100.0)
        distance_score = (0.6 * hospital_score) + (0.4 * clinic_score)
        density_score = HealthcareDesertCalculator.score_density_component(site_count)
        specialist_score = HealthcareDesertCalculator.score_specialist_component(has_specialists)
        transport_score = HealthcareDesertCalculator.score_transport_component(
            first_data_point.travel_time_minutes if first_data_point else None,
            season,
            road_quality,
            "road",
        )

        necessity_score = float(
            0.50 * distance_score
            + 0.15 * density_score
            + 0.15 * specialist_score
            + 0.20 * transport_score
        )
        return round(necessity_score, 1)
