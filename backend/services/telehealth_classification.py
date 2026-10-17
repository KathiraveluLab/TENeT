"""Canonical telehealth classification and source-data resolution.

Every backend surface that publishes a telehealth status must use this
module.  Ookla measurements are preferred when a download measurement is
available; FCC 25/3 coverage is the fallback.  Income and clinic availability
remain explicit so missing data cannot be interpreted as a successful result.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.healthcare_desert_calculator import haversine_km
from services.isp_config import get_affordability_threshold, get_internet_cost


MAX_INCOME_MATCH_KM = 55.0
MAX_OOKLA_MATCH_KM = 75.0
FCC_VIDEO_COVERAGE_PCT = 70.0
FCC_AUDIO_COVERAGE_PCT = 25.0
AUDIO_DOWNLOAD_MBPS = 5.0
ABSOLUTE_COST_LIMIT = 400.0
ROAD_CLINIC_THRESHOLD_KM = 10.0
NON_ROAD_CLINIC_THRESHOLD_KM = 50.0

STATUS_PRESENTATION = {
    "TELEHEALTH_READY": ("Telehealth Ready", "#22c55e"),
    "COMMUNITY_ANCHOR": ("Community Anchor", "#f59e0b"),
    "LIMITED_TELEHEALTH": ("Limited Telehealth", "#f97316"),
    "CRITICAL_GAP": ("Critical Gap", "#ef4444"),
    "DATA_UNAVAILABLE": ("Data Unavailable", "#6b7280"),
}


@dataclass(frozen=True)
class TelehealthThresholds:
    min_download_mbps: float = 25.0
    min_upload_mbps: float = 3.0
    max_latency_ms: Optional[float] = 150.0
    clinic_proximity_km: Optional[float] = None
    affordability_burden_pct: float = 2.0


def baseline_thresholds() -> TelehealthThresholds:
    return TelehealthThresholds(
        affordability_burden_pct=get_affordability_threshold(),
    )


@dataclass(frozen=True)
class TelehealthInputs:
    latitude: Optional[float]
    longitude: Optional[float]
    access_modes: str = ""
    ookla_download_mbps: Optional[float] = None
    ookla_upload_mbps: Optional[float] = None
    ookla_latency_ms: Optional[float] = None
    fcc_coverage_pct: Optional[float] = None
    median_income: Optional[float] = None
    monthly_internet_cost: Optional[float] = None
    burden_pct: Optional[float] = None
    nearest_clinic_distance_km: Optional[float] = None
    clinic_data_available: bool = False


@dataclass(frozen=True)
class TelehealthClassification:
    status: str
    label: str
    color: str
    video_feasible: Optional[bool]
    audio_feasible: Optional[bool]
    clinic_supported: Optional[bool]
    affordability_status: str
    broadband_source: Optional[str]
    clinic_threshold_km: float
    reason_codes: Tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class TelehealthRegionContext:
    region: CATRegion
    broadband: Optional[BroadbandCoverage]
    income: Optional[CensusIncome]
    ookla: Optional[object]
    nearest_clinic: Optional[HealthcareSite]
    inputs: TelehealthInputs
    classification: TelehealthClassification
    isp_name: Optional[str]


def clinic_threshold_km(access_modes: str, override: Optional[float] = None) -> float:
    if override is not None:
        return float(override)
    modes = {
        token for token in re.split(r"[,;/|\s]+", (access_modes or "").lower())
        if token
    }
    return ROAD_CLINIC_THRESHOLD_KM if "road" in modes else NON_ROAD_CLINIC_THRESHOLD_KM


def classify_telehealth(
    inputs: TelehealthInputs,
    thresholds: Optional[TelehealthThresholds] = None,
) -> TelehealthClassification:
    """Classify one community from factual inputs without mutating them."""
    thresholds = thresholds or baseline_thresholds()
    reasons = []
    details = []
    clinic_threshold = clinic_threshold_km(
        inputs.access_modes,
        thresholds.clinic_proximity_km,
    )

    if inputs.latitude is None or inputs.longitude is None:
        return _classification(
            status="DATA_UNAVAILABLE",
            video_feasible=None,
            audio_feasible=None,
            clinic_supported=None,
            affordability_status="unknown",
            broadband_source=None,
            clinic_threshold=clinic_threshold,
            reasons=("MISSING_COORDINATES",),
            details=("Community coordinates are unavailable",),
        )

    video_feasible: Optional[bool]
    audio_feasible: Optional[bool]
    broadband_source: Optional[str]
    download = inputs.ookla_download_mbps
    if download is not None:
        broadband_source = "OOKLA"
        audio_feasible = download >= AUDIO_DOWNLOAD_MBPS
        if download < thresholds.min_download_mbps:
            video_feasible = False
            reasons.append("LOW_DOWNLOAD")
            details.append(
                f"Measured download {download:.1f} Mbps is below {thresholds.min_download_mbps:g} Mbps"
            )
        elif inputs.ookla_upload_mbps is None:
            video_feasible = None
            reasons.append("MISSING_UPLOAD")
            details.append("Measured upload speed is unavailable")
        elif inputs.ookla_upload_mbps < thresholds.min_upload_mbps:
            video_feasible = False
            reasons.append("LOW_UPLOAD")
            details.append(
                f"Measured upload {inputs.ookla_upload_mbps:.1f} Mbps is below {thresholds.min_upload_mbps:g} Mbps"
            )
        elif (
            thresholds.max_latency_ms is not None
            and inputs.ookla_latency_ms is not None
            and inputs.ookla_latency_ms > thresholds.max_latency_ms
        ):
            video_feasible = False
            reasons.append("HIGH_LATENCY")
            details.append(
                f"Measured latency {inputs.ookla_latency_ms:.0f} ms exceeds {thresholds.max_latency_ms:g} ms"
            )
        else:
            video_feasible = True
            reasons.append("MEETS_BROADBAND_OOKLA")
            details.append("Measured Ookla performance meets the video threshold")
            if thresholds.max_latency_ms is not None and inputs.ookla_latency_ms is None:
                reasons.append("MISSING_LATENCY")
        if audio_feasible:
            reasons.append("MEETS_AUDIO_OOKLA")
    elif inputs.fcc_coverage_pct is not None:
        broadband_source = "FCC"
        supports_requested_speed = (
            thresholds.min_download_mbps <= 25.0
            and thresholds.min_upload_mbps <= 3.0
        )
        video_feasible = bool(
            supports_requested_speed
            and inputs.fcc_coverage_pct >= FCC_VIDEO_COVERAGE_PCT
        )
        audio_feasible = inputs.fcc_coverage_pct >= FCC_AUDIO_COVERAGE_PCT
        if video_feasible:
            reasons.append("MEETS_BROADBAND_FCC")
            details.append("FCC 25/3 coverage meets the video fallback threshold")
        elif not supports_requested_speed:
            reasons.append("FCC_BELOW_SCENARIO_THRESHOLD")
            details.append("FCC 25/3 data cannot establish the requested higher speed")
        else:
            reasons.append("LOW_FCC_COVERAGE")
            details.append("FCC coverage is below the video fallback threshold")
        if audio_feasible:
            reasons.append("MEETS_AUDIO_FCC")
    else:
        broadband_source = None
        video_feasible = None
        audio_feasible = None
        reasons.append("NO_BROADBAND_DATA")
        details.append("Neither measured Ookla nor FCC coverage data is available")

    has_income = (
        inputs.median_income is not None
        and inputs.median_income > 0
        and inputs.monthly_internet_cost is not None
        and inputs.burden_pct is not None
    )
    if has_income:
        affordable = bool(
            inputs.burden_pct < thresholds.affordability_burden_pct
            and inputs.monthly_internet_cost < ABSOLUTE_COST_LIMIT
        )
        affordability_status = "affordable" if affordable else "unaffordable"
        reasons.append("AFFORDABLE" if affordable else "UNAFFORDABLE")
        details.append(
            f"Internet burden is {inputs.burden_pct:.1f}% "
            f"against a {thresholds.affordability_burden_pct:g}% threshold"
        )
    else:
        affordable = None
        affordability_status = "unknown"
        reasons.append("NO_INCOME_DATA")
        details.append("Income or price data is unavailable")

    if not inputs.clinic_data_available:
        clinic_supported = None
        reasons.append("NO_CLINIC_DATA")
        details.append("Clinic proximity data is unavailable")
    else:
        clinic_supported = bool(
            inputs.nearest_clinic_distance_km is not None
            and inputs.nearest_clinic_distance_km <= clinic_threshold
        )
        reasons.append("ACCESSIBLE_CARE" if clinic_supported else "NO_NEARBY_CLINIC")
        if clinic_supported:
            details.append(f"A clinic is within the {clinic_threshold:g} km access threshold")
        else:
            details.append(f"No clinic is within the {clinic_threshold:g} km access threshold")

    # Missing broadband or income prevents a positive status. Missing clinic
    # data prevents an anchor/gap decision when home access is not viable.
    if video_feasible is None and audio_feasible is None:
        status = "DATA_UNAVAILABLE"
    elif affordable is None:
        status = "DATA_UNAVAILABLE"
    elif video_feasible and affordable:
        status = "TELEHEALTH_READY"
    elif clinic_supported is True:
        status = "COMMUNITY_ANCHOR"
    elif audio_feasible and affordable:
        status = "LIMITED_TELEHEALTH"
    elif clinic_supported is None:
        status = "DATA_UNAVAILABLE"
    else:
        status = "CRITICAL_GAP"

    return _classification(
        status=status,
        video_feasible=video_feasible,
        audio_feasible=audio_feasible,
        clinic_supported=clinic_supported,
        affordability_status=affordability_status,
        broadband_source=broadband_source,
        clinic_threshold=clinic_threshold,
        reasons=tuple(reasons),
        details=tuple(details),
    )


def _classification(
    *,
    status: str,
    video_feasible: Optional[bool],
    audio_feasible: Optional[bool],
    clinic_supported: Optional[bool],
    affordability_status: str,
    broadband_source: Optional[str],
    clinic_threshold: float,
    reasons: Tuple[str, ...],
    details: Tuple[str, ...],
) -> TelehealthClassification:
    label, color = STATUS_PRESENTATION[status]
    return TelehealthClassification(
        status=status,
        label=label,
        color=color,
        video_feasible=video_feasible,
        audio_feasible=audio_feasible,
        clinic_supported=clinic_supported,
        affordability_status=affordability_status,
        broadband_source=broadband_source,
        clinic_threshold_km=clinic_threshold,
        reason_codes=reasons,
        explanation="; ".join(details) + ".",
    )


def _bucket_key(lat: float, lon: float) -> Tuple[int, int]:
    return math.floor(lat), math.floor(lon)


def _candidate_buckets(lat: float, lon: float, max_km: float) -> Iterable[Tuple[int, int]]:
    lat_window = max_km / 111.0
    lon_window = max_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    for lat_key in range(math.floor(lat - lat_window), math.floor(lat + lat_window) + 1):
        for lon_key in range(math.floor(lon - lon_window), math.floor(lon + lon_window) + 1):
            yield lat_key, lon_key


def _nearest_record(buckets, lat: float, lon: float, max_km: float):
    nearest = None
    nearest_distance = float("inf")
    for key in _candidate_buckets(lat, lon, max_km):
        for record in buckets.get(key, []):
            distance = haversine_km(lat, lon, record.centroid_lat, record.centroid_lon)
            if distance < nearest_distance and distance <= max_km:
                nearest = record
                nearest_distance = distance
    return nearest


class TelehealthClassificationService:
    """Resolve canonical source inputs and classify one or more regions."""

    @classmethod
    def classify_region(cls, db: Session, region: CATRegion) -> TelehealthRegionContext:
        return cls.classify_regions(db, [region])[region.region_code]

    @classmethod
    def classify_regions(
        cls,
        db: Session,
        regions: Iterable[CATRegion],
    ) -> Dict[str, TelehealthRegionContext]:
        regions = list(regions)
        region_codes = [region.region_code for region in regions]
        broadband = cls._broadband_lookup(db, region_codes)
        income_buckets = cls._income_buckets(db)
        ookla_buckets = cls._latest_ookla_buckets(db)
        clinics = db.query(HealthcareSite).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None),
        ).all()
        clinics = [
            site for site in clinics
            if (site.site_type or "").lower() in {"clinic", "hospital", "health_center"}
        ]

        contexts: Dict[str, TelehealthRegionContext] = {}
        for region in regions:
            lat = float(region.centroid_lat) if region.centroid_lat is not None else None
            lon = float(region.centroid_lon) if region.centroid_lon is not None else None
            income = (
                _nearest_record(income_buckets, lat, lon, MAX_INCOME_MATCH_KM)
                if lat is not None and lon is not None else None
            )
            ookla = (
                _nearest_record(ookla_buckets, lat, lon, MAX_OOKLA_MATCH_KM)
                if lat is not None and lon is not None else None
            )

            nearest_clinic = None
            nearest_clinic_distance = None
            if lat is not None and lon is not None and clinics:
                nearest_distance = float("inf")
                for clinic in clinics:
                    distance = haversine_km(lat, lon, clinic.latitude, clinic.longitude)
                    if distance < nearest_distance:
                        nearest_clinic = clinic
                        nearest_distance = distance
                nearest_clinic_distance = round(nearest_distance, 2)

            monthly_cost = None
            isp_name = None
            median_income = None
            burden_pct = None
            if income is not None:
                median_income = float(income.median_income)
                monthly_cost, isp_name = get_internet_cost(str(income.zcta))
                if median_income > 0:
                    burden_pct = (monthly_cost / (median_income / 12.0)) * 100.0

            coverage = broadband.get(region.region_code)
            inputs = TelehealthInputs(
                latitude=lat,
                longitude=lon,
                access_modes=(region.properties or {}).get("primary_access_modes", ""),
                ookla_download_mbps=(
                    float(ookla.avg_d_kbps) / 1000.0
                    if ookla is not None and ookla.avg_d_kbps is not None else None
                ),
                ookla_upload_mbps=(
                    float(ookla.avg_u_kbps) / 1000.0
                    if ookla is not None and ookla.avg_u_kbps is not None else None
                ),
                ookla_latency_ms=(
                    float(ookla.avg_lat_ms)
                    if ookla is not None and ookla.avg_lat_ms is not None else None
                ),
                fcc_coverage_pct=(
                    float(coverage.any_tech_25mbps_pct)
                    if coverage is not None and coverage.any_tech_25mbps_pct is not None else None
                ),
                median_income=median_income,
                monthly_internet_cost=monthly_cost,
                burden_pct=burden_pct,
                nearest_clinic_distance_km=nearest_clinic_distance,
                clinic_data_available=bool(clinics),
            )
            classification = classify_telehealth(inputs)
            contexts[region.region_code] = TelehealthRegionContext(
                region=region,
                broadband=coverage,
                income=income,
                ookla=ookla,
                nearest_clinic=nearest_clinic,
                inputs=inputs,
                classification=classification,
                isp_name=isp_name,
            )
        return contexts

    @staticmethod
    def _broadband_lookup(db: Session, region_codes) -> Dict[str, BroadbandCoverage]:
        confidence_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        lookup = {}
        for record in db.query(BroadbandCoverage).filter(
            BroadbandCoverage.region_code.in_(region_codes)
        ).all():
            current = lookup.get(record.region_code)
            record_rank = confidence_rank.get((record.confidence or "").upper(), 0)
            current_rank = confidence_rank.get(
                (current.confidence or "").upper(), 0
            ) if current is not None else -1
            if current is None or record_rank > current_rank:
                lookup[record.region_code] = record
        return lookup

    @staticmethod
    def _income_buckets(db: Session):
        buckets = defaultdict(list)
        records = db.query(CensusIncome).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
        ).all()
        for record in records:
            buckets[_bucket_key(float(record.centroid_lat), float(record.centroid_lon))].append(record)
        return buckets

    @staticmethod
    def _latest_ookla_buckets(db: Session):
        latest = db.query(
            OoklaPerformance.year,
            OoklaPerformance.quarter,
        ).distinct().order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc(),
        ).first()
        buckets = defaultdict(list)
        if latest is None:
            return buckets
        records = db.query(OoklaPerformance).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
        ).all()
        for record in records:
            buckets[_bucket_key(float(record.centroid_lat), float(record.centroid_lon))].append(record)
        return buckets
