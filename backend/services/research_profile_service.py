"""
Research profile assembly for Phase 3.

This service owns the shared backend contract used by sidebar reports,
comparison, and future research exports.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from database.models import (
    BroadbandCoverage,
    CATDataPoint,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.data_quality_service import DataQualityService
from services.healthcare_desert_calculator import HealthcareDesertCalculator, haversine_km as _haversine_km
from services.isp_config import get_internet_cost, get_affordability_threshold
from services.season_constants import (
    ROAD_QUALITY_LOCAL,
    SEASON_YEAR_ROUND,
    VALID_SEASONS,
    calculate_seasonal_tier,
    get_season_display_name,
)
from services.telehealth_classification import (
    ABSOLUTE_COST_LIMIT,
    CLINICAL_FACILITY_SITE_TYPES,
    DESERT_CLINIC_SITE_TYPES,
    TelehealthClassification,
    TelehealthClassificationService,
    normalize_fcc_pct,
)


MAX_INCOME_MATCH_KM = 55.0
MAX_OOKLA_MATCH_KM = 75.0


def _round(value, digits=2):
    return round(float(value), digits) if value is not None else None


def _region_group(region: CATRegion) -> str | None:
    properties = region.properties or {}
    return (
        properties.get("region")
        or properties.get("economic_region")
        or properties.get("area")
    )


class ResearchProfileService:
    @staticmethod
    def normalize_season(season: str | None) -> str:
        return season if season in VALID_SEASONS else SEASON_YEAR_ROUND

    @staticmethod
    def get_profile(db: Session, region_code: str, season: str | None = None) -> dict | None:
        profiles, _ = ResearchProfileService.get_profiles(db, [region_code], season)
        return profiles[0] if profiles else None

    @staticmethod
    def get_profiles(db: Session, region_codes: list[str], season: str | None = None) -> tuple[list[dict], list[str]]:
        season = ResearchProfileService.normalize_season(season)
        if not region_codes:
            return [], []

        found_regions = db.query(CATRegion).filter(CATRegion.region_code.in_(region_codes)).all()
        regions_by_code = {region.region_code: region for region in found_regions}

        ordered_regions = []
        missing_codes = []
        for code in region_codes:
            region = regions_by_code.get(code)
            if region is not None:
                ordered_regions.append(region)
            else:
                missing_codes.append(code)

        if not ordered_regions:
            return [], missing_codes

        ordered_codes = [region.region_code for region in ordered_regions]
        telehealth_contexts = TelehealthClassificationService.classify_regions(db, ordered_regions)

        active_sites = db.query(HealthcareSite).filter(HealthcareSite.is_active == True).all()
        coord_sites = [
            site for site in active_sites
            if site.latitude is not None and site.longitude is not None
        ]
        clinical_sites = [
            site for site in coord_sites
            if (site.site_type or "").lower() in CLINICAL_FACILITY_SITE_TYPES
        ] or coord_sites

        facility_counts: dict[str, int] = defaultdict(int)
        specialist_regions: set[str] = set()
        for site in active_sites:
            if not site.region_code:
                continue
            facility_counts[site.region_code] += 1
            if site.has_specialists:
                specialist_regions.add(site.region_code)

        data_points = db.query(CATDataPoint).filter(
            CATDataPoint.region_code.in_(ordered_codes)
        ).all()
        points_by_region: dict[str, list[CATDataPoint]] = defaultdict(list)
        for point in data_points:
            if point.region_code:
                points_by_region[point.region_code].append(point)

        generated_at = datetime.now(timezone.utc).isoformat()
        profiles = []
        for region in ordered_regions:
            telehealth_context = telehealth_contexts[region.region_code]
            nearest_facility = ResearchProfileService._nearest_facility_from_sites(
                region, clinical_sites
            )
            region_points = points_by_region.get(region.region_code, [])
            desert_score = ResearchProfileService._desert_score_from_loaded(
                region=region,
                region_points=region_points,
                coord_sites=coord_sites,
                num_sites=facility_counts.get(region.region_code, 0),
                has_specialists=region.region_code in specialist_regions,
                season=season,
            )
            profiles.append(
                ResearchProfileService._assemble_profile(
                    region=region,
                    telehealth_context=telehealth_context,
                    nearest_facility=nearest_facility,
                    facility_count=facility_counts.get(region.region_code, 0),
                    desert_score=desert_score,
                    season=season,
                    generated_at=generated_at,
                )
            )
        return profiles, missing_codes

    @staticmethod
    def _nearest_facility_from_sites(region: CATRegion, clinical_sites: list[HealthcareSite]):
        if region.centroid_lat is None or region.centroid_lon is None or not clinical_sites:
            return None

        nearest = None
        nearest_distance = float("inf")
        for site in clinical_sites:
            distance = _haversine_km(
                region.centroid_lat,
                region.centroid_lon,
                site.latitude,
                site.longitude,
            )
            if distance < nearest_distance:
                nearest = site
                nearest_distance = distance
        return (nearest, nearest_distance) if nearest is not None else None

    @staticmethod
    def _desert_score_from_loaded(
        *,
        region: CATRegion,
        region_points: list[CATDataPoint],
        coord_sites: list[HealthcareSite],
        num_sites: int,
        has_specialists: bool,
        season: str,
    ) -> float:
        if region_points:
            center = (
                sum(p.latitude for p in region_points) / len(region_points),
                sum(p.longitude for p in region_points) / len(region_points),
            )
        elif region.centroid_lat is not None and region.centroid_lon is not None:
            center = (region.centroid_lat, region.centroid_lon)
        else:
            center = None

        if center is None:
            clinic_dist = 500.0
            hospital_dist = 500.0
        elif not coord_sites:
            clinic_dist = 999.0
            hospital_dist = 999.0
        else:
            avg_lat, avg_lon = center
            clinic_dist = float("inf")
            hospital_dist = float("inf")
            for site in coord_sites:
                distance = HealthcareDesertCalculator.calculate_distance(
                    avg_lat, avg_lon, site.latitude, site.longitude
                )
                site_type = (site.site_type or "").lower()
                if site_type in DESERT_CLINIC_SITE_TYPES:
                    clinic_dist = min(clinic_dist, distance)
                if site_type == "hospital":
                    hospital_dist = min(hospital_dist, distance)
            clinic_dist = 999.0 if clinic_dist == float("inf") else clinic_dist
            hospital_dist = 999.0 if hospital_dist == float("inf") else hospital_dist

        clinic_score = HealthcareDesertCalculator.score_distance_component(clinic_dist)
        hospital_score = min(100.0, (hospital_dist / 500.0) * 100.0)
        distance_score = (0.6 * hospital_score) + (0.4 * clinic_score)
        density_score = HealthcareDesertCalculator.score_density_component(num_sites)
        specialist_score = HealthcareDesertCalculator.score_specialist_component(has_specialists)

        first_point = region_points[0] if region_points else None
        transport_mode = HealthcareDesertCalculator.resolve_transport_mode(region, first_point)
        transport_score = HealthcareDesertCalculator.score_transport_component(
            first_point.travel_time_minutes if first_point else None,
            season,
            ROAD_QUALITY_LOCAL,
            transport_mode,
        )
        necessity_score = float(
            0.50 * distance_score
            + 0.15 * density_score
            + 0.15 * specialist_score
            + 0.20 * transport_score
        )
        return round(necessity_score, 2)

    @staticmethod
    def _assemble_profile(
        *,
        region: CATRegion,
        telehealth_context,
        nearest_facility,
        facility_count: int,
        desert_score: float,
        season: str,
        generated_at: str,
    ) -> dict:
        broadband = telehealth_context.broadband
        ookla = telehealth_context.ookla
        income = telehealth_context.income

        facility_obj = nearest_facility[0] if nearest_facility is not None else None
        facility_distance = nearest_facility[1] if nearest_facility is not None else None

        quality = DataQualityService.evaluate_region_profile(
            region=region,
            broadband=broadband,
            ookla=ookla,
            income=income,
            nearest_facility=facility_obj,
            desert_score=desert_score,
        )

        affordability = ResearchProfileService._affordability_payload(income)
        healthcare = ResearchProfileService._healthcare_payload(
            facility_obj,
            facility_count,
            desert_score,
            nearest_distance_km=facility_distance,
        )
        connectivity = ResearchProfileService._connectivity_payload(
            broadband,
            ookla,
            affordability.pop("isp_name", None),
        )
        telehealth = ResearchProfileService._telehealth_payload(
            telehealth_context.classification,
            season,
        )

        sources = ["CAT region boundaries"]
        if broadband:
            sources.append(broadband.data_source or "FCC Broadband Availability Data")
        if ookla:
            sources.append("Ookla Open Data")
        if income:
            sources.append(income.data_source or "ACS 5-Year Estimates")
        if facility_obj:
            sources.append("Healthcare sites")

        adjusted_tier = None
        if region.tier_level is not None:
            adjusted_tier, _, _ = calculate_seasonal_tier(
                region.tier_level,
                region.access_score if region.access_score is not None else 50,
                region.properties,
                season,
            )

        return {
            "region": {
                "region_code": region.region_code,
                "name": region.region_name,
                "lat": _round(region.centroid_lat, 6),
                "lon": _round(region.centroid_lon, 6),
                "region": _region_group(region),
                "population": (
                    region.population
                    if region.population is not None
                    else getattr(income, "population", None)
                ),
                "cat_tier": adjusted_tier,
                "data_confidence": quality["data_confidence"],
                "has_data_gap": quality["has_data_gap"],
                "missing_fields": quality["missing_fields"],
            },
            "connectivity": connectivity,
            "affordability": affordability,
            "healthcare": healthcare,
            "telehealth": telehealth,
            "methodology": {
                "generated_at": generated_at,
                "sources": sorted(set(sources)),
                "confidence_notes": ResearchProfileService._confidence_notes(quality),
            },
        }

    @staticmethod
    def _broadband_for_region(db: Session, region_code: str):
        return db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code == region_code
        ).order_by(BroadbandCoverage.confidence.desc()).first()

    @staticmethod
    def _nearest_income_record(db: Session, region: CATRegion):
        if region.centroid_lat is None or region.centroid_lon is None:
            return None

        region_lat = float(region.centroid_lat)
        region_lon = float(region.centroid_lon)
        lat_window = MAX_INCOME_MATCH_KM / 111.0
        lon_window = MAX_INCOME_MATCH_KM / (
            111.0 * max(math.cos(math.radians(region_lat)), 0.1)
        )

        records = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
            CensusIncome.centroid_lat.between(region_lat - lat_window, region_lat + lat_window),
            CensusIncome.centroid_lon.between(region_lon - lon_window, region_lon + lon_window),
        ).all()
        nearest = None
        nearest_distance = float("inf")
        for record in records:
            distance = _haversine_km(
                region_lat,
                region_lon,
                record.centroid_lat,
                record.centroid_lon,
            )
            if distance < nearest_distance and distance <= MAX_INCOME_MATCH_KM:
                nearest = record
                nearest_distance = distance
        return nearest

    @staticmethod
    def _nearest_ookla_tile(db: Session, region: CATRegion):
        if region.centroid_lat is None or region.centroid_lon is None:
            return None

        latest = db.query(OoklaPerformance.year, OoklaPerformance.quarter).distinct().order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc(),
        ).first()
        if latest is None:
            return None

        lat_window = MAX_OOKLA_MATCH_KM / 111.0
        lon_window = MAX_OOKLA_MATCH_KM / (
            111.0 * max(math.cos(math.radians(float(region.centroid_lat))), 0.1)
        )
        candidates = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.between(region.centroid_lat - lat_window, region.centroid_lat + lat_window),
            OoklaPerformance.centroid_lon.between(region.centroid_lon - lon_window, region.centroid_lon + lon_window),
        ).all()

        nearest = None
        nearest_distance = float("inf")
        for tile in candidates:
            distance = _haversine_km(
                region.centroid_lat,
                region.centroid_lon,
                tile.centroid_lat,
                tile.centroid_lon,
            )
            if distance < nearest_distance and distance <= MAX_OOKLA_MATCH_KM:
                nearest = tile
                nearest_distance = distance
        return nearest

    @staticmethod
    def _nearest_facility(db: Session, region: CATRegion):
        if region.centroid_lat is None or region.centroid_lon is None:
            return None

        sites = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None),
        ).all()
        clinical_sites = [
            site for site in sites
            if (site.site_type or "").lower() in CLINICAL_FACILITY_SITE_TYPES
        ] or sites
        nearest = None
        nearest_distance = float("inf")
        for site in clinical_sites:
            distance = _haversine_km(
                region.centroid_lat,
                region.centroid_lon,
                site.latitude,
                site.longitude,
            )
            if distance < nearest_distance:
                nearest = site
                nearest_distance = distance

        if nearest is not None:
            nearest._research_distance_km = nearest_distance
        return nearest

    @staticmethod
    def _connectivity_payload(broadband, ookla, isp_name=None) -> dict:
        download_mbps = _round(ookla.avg_d_kbps / 1000, 2) if ookla and ookla.avg_d_kbps is not None else None
        upload_mbps = _round(ookla.avg_u_kbps / 1000, 2) if ookla and ookla.avg_u_kbps is not None else None
        latency_ms = _round(ookla.avg_lat_ms, 1) if ookla and ookla.avg_lat_ms is not None else None

        if download_mbps is None:
            reliability = None
        elif download_mbps >= 25 and (latency_ms is None or latency_ms <= 150):
            reliability = "Video-capable"
        elif download_mbps >= 5:
            reliability = "Audio/store-and-forward"
        else:
            reliability = "Constrained"

        return {
            "fcc_coverage_25mbps_pct": (
                _round(normalize_fcc_pct(broadband.any_tech_25mbps_pct), 2) if broadband else None
            ),
            "ookla_download_mbps": download_mbps,
            "ookla_upload_mbps": upload_mbps,
            "latency_ms": latency_ms,
            "reliability_label": reliability,
            "isp_name": isp_name,
            "data_source": broadband.data_source if broadband else None,
        }

    @staticmethod
    def _affordability_payload(income) -> dict:
        zcta = getattr(income, "zcta", None)
        cost, isp_name = get_internet_cost(str(zcta)) if zcta else (None, None)
        threshold = get_affordability_threshold()
        median_income = income.median_income if income else None
        if cost is None or not median_income:
            burden_pct = None
            status = "unknown"
        else:
            burden_pct = (float(cost) / (float(median_income) / 12.0)) * 100.0
            status = (
                "affordable"
                if burden_pct < threshold and float(cost) <= ABSOLUTE_COST_LIMIT
                else "unaffordable"
            )

        return {
            "monthly_cost": _round(cost, 2),
            "median_income": _round(median_income, 2),
            "burden_pct": _round(burden_pct, 2),
            "threshold_pct": threshold,
            "status": status,
            "isp_name": isp_name,
        }

    @staticmethod
    def _healthcare_payload(
        nearest_facility,
        facility_count: int,
        desert_score,
        nearest_distance_km: float | None = None,
    ) -> dict:
        distance_km = (
            nearest_distance_km
            if nearest_distance_km is not None
            else getattr(nearest_facility, "_research_distance_km", None)
        )
        return {
            "nearest_facility_name": nearest_facility.name if nearest_facility else None,
            "nearest_facility_distance_km": _round(
                distance_km,
                2,
            ) if nearest_facility else None,
            "nearest_facility_type": nearest_facility.site_type if nearest_facility else None,
            "emergency_services": nearest_facility.has_emergency if nearest_facility else None,
            "specialist_available": nearest_facility.has_specialists if nearest_facility else None,
            "facility_count": facility_count,
            "desert_score": _round(desert_score, 2),
        }

    @staticmethod
    def _telehealth_payload(classification: TelehealthClassification, season: str) -> dict:
        return {
            "status": classification.status,
            "label": classification.label,
            "video_feasible": classification.video_feasible,
            "audio_feasible": classification.audio_feasible,
            "clinic_supported": classification.clinic_supported,
            "season": season,
            "season_note": f"{get_season_display_name(season)} scenario applied.",
        }

    @staticmethod
    def _confidence_notes(quality: dict) -> list[str]:
        notes = [f"Overall data confidence: {quality['data_confidence']}."]
        if quality["has_data_gap"]:
            notes.append("Some profile fields are unavailable or flagged by source data quality checks.")
        else:
            notes.append("No source data gaps are flagged for this profile.")
        return notes
