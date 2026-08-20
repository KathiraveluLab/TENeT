"""
Research profile assembly for Phase 3.

This service owns the shared backend contract used by sidebar reports,
comparison, and future research exports.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.data_quality_service import DataQualityService
from services.healthcare_desert_calculator import HealthcareDesertCalculator, haversine_km as _haversine_km
from services.isp_config import get_internet_cost, get_affordability_threshold
from services.season_constants import SEASON_YEAR_ROUND, VALID_SEASONS, get_season_display_name
from services.telehealth_classification import (
    ABSOLUTE_COST_LIMIT,
    TelehealthClassification,
    TelehealthClassificationService,
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
        season = ResearchProfileService.normalize_season(season)
        region = db.query(CATRegion).filter(CATRegion.region_code == region_code).first()
        if region is None:
            return None

        telehealth_context = TelehealthClassificationService.classify_region(db, region)
        broadband = telehealth_context.broadband
        ookla = telehealth_context.ookla
        income = telehealth_context.income
        nearest_facility = ResearchProfileService._nearest_facility(db, region)
        facility_count = db.query(HealthcareSite).filter(
            HealthcareSite.region_code == region.region_code,
            HealthcareSite.is_active == True,
        ).count()

        desert = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
            db, region.region_code, season
        )
        desert_score = desert.get("necessity_score") if desert else None
        quality = DataQualityService.evaluate_region_profile(
            region=region,
            broadband=broadband,
            ookla=ookla,
            income=income,
            nearest_facility=nearest_facility,
            desert_score=desert_score,
        )

        affordability = ResearchProfileService._affordability_payload(income)
        healthcare = ResearchProfileService._healthcare_payload(
            nearest_facility,
            facility_count,
            desert_score,
        )
        connectivity = ResearchProfileService._connectivity_payload(
            broadband,
            ookla,
            affordability.pop("isp_name", None),
        )
        access_modes = (region.properties or {}).get("primary_access_modes", "")
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
        if nearest_facility:
            sources.append("Healthcare sites")

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
                "cat_tier": region.tier_level if region.tier_level is not None else None,
                "data_confidence": quality["data_confidence"],
                "has_data_gap": quality["has_data_gap"],
                "missing_fields": quality["missing_fields"],
            },
            "connectivity": connectivity,
            "affordability": affordability,
            "healthcare": healthcare,
            "telehealth": telehealth,
            "methodology": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources": sorted(set(sources)),
                "confidence_notes": ResearchProfileService._confidence_notes(quality),
            },
        }

    @staticmethod
    def get_profiles(db: Session, region_codes: list[str], season: str | None = None) -> tuple[list[dict], list[str]]:
        profiles = []
        missing_codes = []
        for code in region_codes:
            profile = ResearchProfileService.get_profile(db, code, season)
            if profile:
                profiles.append(profile)
            else:
                missing_codes.append(code)
        return profiles, missing_codes

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
        nearest = None
        nearest_distance = float("inf")
        for site in sites:
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
            "fcc_coverage_25mbps_pct": _round(broadband.any_tech_25mbps_pct, 2) if broadband else None,
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
                if burden_pct < threshold and float(cost) < ABSOLUTE_COST_LIMIT
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
    def _healthcare_payload(nearest_facility, facility_count: int, desert_score) -> dict:
        return {
            "nearest_facility_name": nearest_facility.name if nearest_facility else None,
            "nearest_facility_distance_km": _round(
                getattr(nearest_facility, "_research_distance_km", None),
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
