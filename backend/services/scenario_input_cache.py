"""
Cached scenario inputs for interactive what-if analysis.

The scenario preview endpoint needs to respond quickly while users drag
sliders.  This service precomputes the expensive, factual inputs once per
database/season and lets ScenarioEngine do cheap threshold comparisons.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database.models import (
    CATDataPoint,
    CATRegion,
    HealthcareSite,
)
from services.data_quality_service import normalize_confidence, split_gap_flags
from services.healthcare_desert_calculator import HealthcareDesertCalculator, haversine_km as _haversine_km
from services.season_constants import (
    ROAD_QUALITY_LOCAL,
    SEASON_YEAR_ROUND,
    VALID_ROAD_QUALITIES,
    VALID_SEASONS,
)
from services.telehealth_classification import (
    TelehealthClassificationService,
    TelehealthRegionContext,
)


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
        telehealth_contexts = TelehealthClassificationService.classify_regions(db, regions)
        data_points_by_region, first_data_point_by_region = cls._data_points(db, region_codes)
        site_counts, specialist_regions = cls._healthcare_site_stats(facilities)

        return [
            cls._region_input(
                region=region,
                season=season,
                facilities=facilities,
                telehealth_context=telehealth_contexts[region.region_code],
                data_points=data_points_by_region.get(region.region_code, []),
                first_data_point=first_data_point_by_region.get(region.region_code),
                site_count=site_counts.get(region.region_code, 0),
                has_specialists=region.region_code in specialist_regions,
            )
            for region in regions
        ]

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
        telehealth_context: TelehealthRegionContext,
        data_points: List[CATDataPoint],
        first_data_point: Optional[CATDataPoint],
        site_count: int,
        has_specialists: bool,
    ) -> Dict[str, Any]:
        display_lat = region.centroid_lat
        display_lon = region.centroid_lon
        score_lat = display_lat
        score_lon = display_lon
        if data_points:
            score_lat = sum(point.latitude for point in data_points) / len(data_points)
            score_lon = sum(point.longitude for point in data_points) / len(data_points)

        inputs = telehealth_context.inputs
        broadband = telehealth_context.broadband
        facility_distances = cls._facility_distances(facilities, score_lat, score_lon)
        healthcare_need_score = cls._need_score(
            facility_distances=facility_distances,
            site_count=site_count,
            has_specialists=has_specialists,
            first_data_point=first_data_point,
            season=season,
            access_modes=inputs.access_modes,
        )

        missing_fields: List[str] = []
        if inputs.ookla_download_mbps is None and inputs.fcc_coverage_pct is None:
            missing_fields.append("connectivity.fcc_coverage")
        if display_lat is None or display_lon is None or inputs.median_income is None:
            missing_fields.append("affordability.median_income")

        return {
            "region_code": region.region_code,
            "name": region.region_name,
            "lat": float(display_lat) if display_lat is not None else None,
            "lon": float(display_lon) if display_lon is not None else None,
            "access_modes": inputs.access_modes,
            "baseline_status": telehealth_context.classification.status,
            "healthcare_need_score": healthcare_need_score,
            "nearest_clinic_distance_km": inputs.nearest_clinic_distance_km,
            "distance_threshold_km": telehealth_context.classification.clinic_threshold_km,
            "clinic_data_available": inputs.clinic_data_available,
            "median_income": inputs.median_income,
            "monthly_internet_cost": inputs.monthly_internet_cost,
            "burden_pct": inputs.burden_pct,
            "ookla_download_mbps": inputs.ookla_download_mbps,
            "ookla_upload_mbps": inputs.ookla_upload_mbps,
            "ookla_latency_ms": inputs.ookla_latency_ms,
            "fcc_coverage_pct": inputs.fcc_coverage_pct,
            "has_data_gap": bool(missing_fields) or bool(
                split_gap_flags(getattr(broadband, "data_gaps", None) if broadband else None)
            ),
            "missing_fields": missing_fields,
            "data_confidence": normalize_confidence(
                getattr(broadband, "confidence", None) if broadband else None
            ),
        }

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
    def _need_score(
        *,
        facility_distances: Dict[str, float],
        site_count: int,
        has_specialists: bool,
        first_data_point: Optional[CATDataPoint],
        season: str,
        access_modes: str = "",
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
            ScenarioInputCache._transport_mode(access_modes),
        )

        necessity_score = float(
            0.50 * distance_score
            + 0.15 * density_score
            + 0.15 * specialist_score
            + 0.20 * transport_score
        )
        return round(necessity_score, 1)

    @staticmethod
    def _transport_mode(access_modes: str) -> str:
        for mode in str(access_modes or "").lower().replace(";", ",").split(","):
            normalized = mode.strip()
            if normalized in {"air", "road", "water"}:
                return normalized
        return "unknown"
