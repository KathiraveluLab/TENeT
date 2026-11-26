"""Canonical telehealth classification and source-data resolution.

Every backend surface that publishes a telehealth status must use this
module.  Ookla measurements are preferred when a download measurement is
available; FCC 25/3 coverage is the fallback.  Income and clinic availability
remain explicit so missing data cannot be interpreted as a successful result.
"""

from __future__ import annotations

import math
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from sqlalchemy import and_, func, or_
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

TELEHEALTH_CLINIC_SITE_TYPES = frozenset({"clinic", "hospital", "health_center"})
CLINICAL_FACILITY_SITE_TYPES = frozenset(
    {"clinic", "hospital", "health_center", "community_health_center"}
)
DESERT_CLINIC_SITE_TYPES = frozenset({"clinic", "health_center", "community_health_center"})


def normalize_fcc_pct(value: Optional[float]) -> Optional[float]:
    """Normalize FCC coverage values so fractional [0, 1] inputs become 0-100 percentages."""
    if value is None:
        return None
    numeric = float(value)
    if 0.0 < numeric <= 1.0:
        return round(numeric * 100.0, 2)
    return numeric


STATUS_PRESENTATION = {
    "TELEHEALTH_READY": ("Telehealth Ready", "#22c55e"),
    "COMMUNITY_ANCHOR": ("Community Anchor", "#f59e0b"),
    "LIMITED_TELEHEALTH": ("Limited Telehealth", "#eab308"),
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
            and inputs.monthly_internet_cost <= ABSOLUTE_COST_LIMIT
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


@dataclass(frozen=True, slots=True)
class _OoklaPoint:
    id: int
    quadkey: str
    avg_d_kbps: Optional[int]
    avg_u_kbps: Optional[int]
    avg_lat_ms: Optional[float]
    centroid_lat: float
    centroid_lon: float
    year: int
    quarter: int


@dataclass(frozen=True, slots=True)
class _IncomePoint:
    id: int
    zcta: str
    median_income: float
    population: Optional[int]
    centroid_lat: float
    centroid_lon: float
    acs_year: int
    data_source: Optional[str]


@dataclass(frozen=True, slots=True)
class _ClinicPoint:
    id: int
    name: str
    site_type: str
    latitude: float
    longitude: float
    has_emergency: Optional[bool]
    has_specialists: Optional[bool]
    region_code: Optional[str]
    is_active: Optional[bool]


_BUCKET_STEPS_PER_DEGREE = 4
_EARTH_DEG_TO_KM_MIN = 111.1


def _bucket_key(lat: float, lon: float) -> Tuple[int, int]:
    return (
        math.floor(lat * _BUCKET_STEPS_PER_DEGREE),
        math.floor(lon * _BUCKET_STEPS_PER_DEGREE),
    )


def _lat_lon_windows(lat: float, max_km: float) -> Tuple[float, float]:
    lat_window = max_km / 110.5
    furthest_lat = min(89.9, max(abs(lat - lat_window), abs(lat + lat_window)))
    lon_window = max_km / (110.5 * max(math.cos(math.radians(furthest_lat)), 0.1))
    return lat_window, lon_window


def _candidate_buckets(lat: float, lon: float, max_km: float) -> Iterable[Tuple[int, int]]:
    lat_window, lon_window = _lat_lon_windows(lat, max_km)
    min_lat_key = math.floor((lat - lat_window) * _BUCKET_STEPS_PER_DEGREE)
    max_lat_key = math.floor((lat + lat_window) * _BUCKET_STEPS_PER_DEGREE)
    min_lon_key = math.floor((lon - lon_window) * _BUCKET_STEPS_PER_DEGREE)
    max_lon_key = math.floor((lon + lon_window) * _BUCKET_STEPS_PER_DEGREE)
    center_lat_key, center_lon_key = _bucket_key(lat, lon)

    coords = [
        (lat_key, lon_key)
        for lat_key in range(min_lat_key, max_lat_key + 1)
        for lon_key in range(min_lon_key, max_lon_key + 1)
    ]
    coords.sort(
        key=lambda item: (
            max(abs(item[0] - center_lat_key), abs(item[1] - center_lon_key)),
            abs(item[0] - center_lat_key) + abs(item[1] - center_lon_key),
        )
    )
    return coords


def _cell_min_lat_km(lat: float, lat_key: int) -> float:
    cell_min = lat_key / _BUCKET_STEPS_PER_DEGREE
    cell_max = (lat_key + 1) / _BUCKET_STEPS_PER_DEGREE
    if lat < cell_min:
        return (cell_min - lat) * _EARTH_DEG_TO_KM_MIN
    if lat > cell_max:
        return (lat - cell_max) * _EARTH_DEG_TO_KM_MIN
    return 0.0


def _nearest_record(buckets, lat: float, lon: float, max_km: float):
    if not buckets:
        return None
    nearest = None
    nearest_distance = float("inf")
    for lat_key, lon_key in _candidate_buckets(lat, lon, max_km):
        cell_lat_km = _cell_min_lat_km(lat, lat_key)
        if cell_lat_km > max_km or (nearest is not None and cell_lat_km >= nearest_distance):
            continue
        records = buckets.get((lat_key, lon_key))
        if not records:
            continue
        for record in records:
            dlat_km = abs(lat - record.centroid_lat) * _EARTH_DEG_TO_KM_MIN
            if dlat_km > max_km or (nearest is not None and dlat_km >= nearest_distance):
                continue
            distance = haversine_km(lat, lon, record.centroid_lat, record.centroid_lon)
            if distance < nearest_distance and distance <= max_km:
                nearest = record
                nearest_distance = distance
    return nearest


class TelehealthClassificationService:
    """Resolve canonical source inputs and classify one or more regions."""

    _cache_lock = threading.RLock()
    _ookla_bucket_cache: Dict[Tuple[int, str], Tuple[Tuple[Any, ...], Dict[Tuple[int, int], list[_OoklaPoint]]]] = {}
    _income_bucket_cache: Dict[Tuple[int, str], Tuple[Tuple[Any, ...], Dict[Tuple[int, int], list[_IncomePoint]]]] = {}
    _clinic_cache: Dict[Tuple[int, str], Tuple[Tuple[Any, ...], list[_ClinicPoint]]] = {}
    _spatial_match_cache: Dict[
        Tuple[int, str],
        Tuple[
            Tuple[Any, ...],
            Dict[
                Tuple[float, float],
                Tuple[Optional[_IncomePoint], Optional[_OoklaPoint], Optional[_ClinicPoint], Optional[float]],
            ],
        ],
    ] = {}

    @classmethod
    def clear_caches(cls) -> None:
        with cls._cache_lock:
            cls._ookla_bucket_cache.clear()
            cls._income_bucket_cache.clear()
            cls._clinic_cache.clear()
            cls._spatial_match_cache.clear()

    @staticmethod
    def _cache_key(db: Session) -> Tuple[int, str]:
        bind = db.get_bind()
        return id(bind), bind.url.render_as_string(hide_password=True)

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
        if not regions:
            return {}

        region_codes = [region.region_code for region in regions]
        broadband = cls._broadband_lookup(db, region_codes)
        valid_regions = [
            region for region in regions
            if region.centroid_lat is not None and region.centroid_lon is not None
        ]

        use_full_match_cache = False
        spatial_cache_key = None
        spatial_sig = None
        spatial_matches = {}

        if valid_regions:
            income_sig, income_buckets = cls._income_signature_and_buckets(db)
            clinic_sig, clinics = cls._clinic_signature_and_list(db)
            if len(valid_regions) <= 8 and not cls._has_warm_ookla_cache(db):
                ookla_buckets = cls._query_ookla_buckets_for_regions(db, valid_regions)
            else:
                ookla_sig, ookla_buckets = cls._ookla_signature_and_buckets(db)
                use_full_match_cache = True
                spatial_cache_key = cls._cache_key(db)
                spatial_sig = (income_sig, ookla_sig, clinic_sig)
        else:
            income_buckets = {}
            ookla_buckets = {}
            clinics = []

        new_spatial_matches = {}
        if use_full_match_cache:
            with cls._cache_lock:
                cached_matches = cls._spatial_match_cache.get(spatial_cache_key)
                if cached_matches is not None and cached_matches[0] == spatial_sig:
                    spatial_matches = dict(cached_matches[1])
                else:
                    spatial_matches = {}
                    cls._spatial_match_cache[spatial_cache_key] = (spatial_sig, {})

        contexts: Dict[str, TelehealthRegionContext] = {}
        for region in regions:
            lat = float(region.centroid_lat) if region.centroid_lat is not None else None
            lon = float(region.centroid_lon) if region.centroid_lon is not None else None
            if lat is not None and lon is not None:
                coord_key = (lat, lon)
                cached_hit = spatial_matches.get(coord_key) if use_full_match_cache else None
                if cached_hit is not None:
                    income, ookla, nearest_clinic, nearest_clinic_distance = cached_hit
                else:
                    income = _nearest_record(income_buckets, lat, lon, MAX_INCOME_MATCH_KM)
                    ookla = _nearest_record(ookla_buckets, lat, lon, MAX_OOKLA_MATCH_KM)
                    nearest_clinic = None
                    nearest_clinic_distance = None
                    if clinics:
                        nearest_distance = float("inf")
                        for clinic in clinics:
                            if abs(lat - clinic.latitude) * _EARTH_DEG_TO_KM_MIN >= nearest_distance:
                                continue
                            distance = haversine_km(lat, lon, clinic.latitude, clinic.longitude)
                            if distance < nearest_distance:
                                nearest_clinic = clinic
                                nearest_distance = distance
                        nearest_clinic_distance = round(nearest_distance, 2)
                    if use_full_match_cache:
                        match_tuple = (
                            income,
                            ookla,
                            nearest_clinic,
                            nearest_clinic_distance,
                        )
                        spatial_matches[coord_key] = match_tuple
                        new_spatial_matches[coord_key] = match_tuple
            else:
                income = None
                ookla = None
                nearest_clinic = None
                nearest_clinic_distance = None

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
                    normalize_fcc_pct(coverage.any_tech_25mbps_pct)
                    if coverage is not None else None
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

        if use_full_match_cache and new_spatial_matches and spatial_cache_key is not None and spatial_sig is not None:
            with cls._cache_lock:
                entry = cls._spatial_match_cache.get(spatial_cache_key)
                if entry is not None and entry[0] == spatial_sig:
                    entry[1].update(new_spatial_matches)
                else:
                    cls._spatial_match_cache[spatial_cache_key] = (spatial_sig, new_spatial_matches)

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

    @classmethod
    def _clinic_signature_and_list(cls, db: Session) -> Tuple[Tuple[Any, ...], list[_ClinicPoint]]:
        key = cls._cache_key(db)
        sig = db.query(
            func.count(HealthcareSite.id),
            func.coalesce(func.min(HealthcareSite.id), 0),
            func.coalesce(func.max(HealthcareSite.id), 0),
            func.coalesce(func.sum(HealthcareSite.latitude), 0.0),
        ).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None),
        ).one()
        signature = tuple(sig)

        with cls._cache_lock:
            cached = cls._clinic_cache.get(key)
            if cached is not None and cached[0] == signature:
                return cached[0], cached[1]

        rows = db.query(
            HealthcareSite.id,
            HealthcareSite.name,
            HealthcareSite.site_type,
            HealthcareSite.latitude,
            HealthcareSite.longitude,
            HealthcareSite.has_emergency,
            HealthcareSite.has_specialists,
            HealthcareSite.region_code,
            HealthcareSite.is_active,
        ).filter(
            HealthcareSite.is_active == True,
            HealthcareSite.latitude.isnot(None),
            HealthcareSite.longitude.isnot(None),
        ).all()
        clinics = [
            _ClinicPoint(
                id=row.id,
                name=row.name,
                site_type=row.site_type,
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                has_emergency=row.has_emergency,
                has_specialists=row.has_specialists,
                region_code=row.region_code,
                is_active=row.is_active,
            )
            for row in rows
            if (row.site_type or "").lower() in TELEHEALTH_CLINIC_SITE_TYPES
        ]
        with cls._cache_lock:
            cls._clinic_cache[key] = (signature, clinics)
        return signature, clinics

    @classmethod
    def _active_clinics(cls, db: Session) -> list[_ClinicPoint]:
        return cls._clinic_signature_and_list(db)[1]

    @classmethod
    def _income_signature_and_buckets(cls, db: Session):
        key = cls._cache_key(db)
        sig = db.query(
            func.count(CensusIncome.id),
            func.coalesce(func.min(CensusIncome.id), 0),
            func.coalesce(func.max(CensusIncome.id), 0),
            func.coalesce(func.sum(CensusIncome.median_income), 0.0),
            func.coalesce(func.sum(CensusIncome.centroid_lat), 0.0),
        ).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
        ).one()
        signature = tuple(sig)

        with cls._cache_lock:
            cached = cls._income_bucket_cache.get(key)
            if cached is not None and cached[0] == signature:
                return cached[0], cached[1]

        buckets = defaultdict(list)
        rows = db.query(
            CensusIncome.id,
            CensusIncome.zcta,
            CensusIncome.median_income,
            CensusIncome.population,
            CensusIncome.centroid_lat,
            CensusIncome.centroid_lon,
            CensusIncome.acs_year,
            CensusIncome.data_source,
        ).filter(
            CensusIncome.median_income.isnot(None),
            CensusIncome.median_income > 0,
            CensusIncome.centroid_lat.isnot(None),
            CensusIncome.centroid_lon.isnot(None),
        ).all()
        for row in rows:
            point = _IncomePoint(
                id=row.id,
                zcta=row.zcta,
                median_income=float(row.median_income),
                population=row.population,
                centroid_lat=float(row.centroid_lat),
                centroid_lon=float(row.centroid_lon),
                acs_year=row.acs_year,
                data_source=row.data_source,
            )
            buckets[_bucket_key(point.centroid_lat, point.centroid_lon)].append(point)
        result = dict(buckets)
        with cls._cache_lock:
            cls._income_bucket_cache[key] = (signature, result)
        return signature, result

    @classmethod
    def _income_buckets(cls, db: Session):
        return cls._income_signature_and_buckets(db)[1]

    @classmethod
    def _has_warm_ookla_cache(cls, db: Session) -> bool:
        key = cls._cache_key(db)
        with cls._cache_lock:
            return key in cls._ookla_bucket_cache

    @staticmethod
    def _latest_ookla_period(db: Session):
        return db.query(
            OoklaPerformance.year,
            OoklaPerformance.quarter,
        ).order_by(
            OoklaPerformance.year.desc(),
            OoklaPerformance.quarter.desc(),
        ).first()

    @classmethod
    def _query_ookla_buckets_for_regions(
        cls,
        db: Session,
        regions: Iterable[CATRegion],
    ):
        latest = cls._latest_ookla_period(db)
        if latest is None:
            return {}

        spatial_filters = []
        lat_delta = MAX_OOKLA_MATCH_KM / 110.5
        for region in regions:
            lat = float(region.centroid_lat)
            lon = float(region.centroid_lon)
            min_lat = lat - lat_delta
            max_lat = lat + lat_delta
            furthest_lat = min(89.9, max(abs(min_lat), abs(max_lat)))
            lon_delta = MAX_OOKLA_MATCH_KM / (110.5 * max(math.cos(math.radians(furthest_lat)), 0.1))
            min_lon = lon - lon_delta
            max_lon = lon + lon_delta

            if min_lon < -180.0:
                lon_clause = or_(
                    OoklaPerformance.centroid_lon.between(-180.0, max_lon),
                    OoklaPerformance.centroid_lon >= (min_lon + 360.0),
                )
            elif max_lon > 180.0:
                lon_clause = or_(
                    OoklaPerformance.centroid_lon.between(min_lon, 180.0),
                    OoklaPerformance.centroid_lon <= (max_lon - 360.0),
                )
            else:
                lon_clause = OoklaPerformance.centroid_lon.between(min_lon, max_lon)

            spatial_filters.append(
                and_(
                    OoklaPerformance.centroid_lat.between(min_lat, max_lat),
                    lon_clause,
                )
            )

        if not spatial_filters:
            return {}

        rows = db.query(
            OoklaPerformance.id,
            OoklaPerformance.quadkey,
            OoklaPerformance.avg_d_kbps,
            OoklaPerformance.avg_u_kbps,
            OoklaPerformance.avg_lat_ms,
            OoklaPerformance.centroid_lat,
            OoklaPerformance.centroid_lon,
            OoklaPerformance.year,
            OoklaPerformance.quarter,
        ).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
            or_(*spatial_filters),
        ).all()

        buckets = defaultdict(list)
        for row in rows:
            point = _OoklaPoint(
                id=row.id,
                quadkey=row.quadkey,
                avg_d_kbps=row.avg_d_kbps,
                avg_u_kbps=row.avg_u_kbps,
                avg_lat_ms=row.avg_lat_ms,
                centroid_lat=float(row.centroid_lat),
                centroid_lon=float(row.centroid_lon),
                year=row.year,
                quarter=row.quarter,
            )
            buckets[_bucket_key(point.centroid_lat, point.centroid_lon)].append(point)
        return dict(buckets)

    @classmethod
    def _ookla_signature_and_buckets(cls, db: Session):
        latest = cls._latest_ookla_period(db)
        if latest is None:
            return (None, None), {}

        key = cls._cache_key(db)
        agg = db.query(
            func.count(OoklaPerformance.id),
            func.coalesce(func.min(OoklaPerformance.id), 0),
            func.coalesce(func.max(OoklaPerformance.id), 0),
            func.coalesce(func.sum(OoklaPerformance.avg_d_kbps), 0),
            func.coalesce(func.sum(OoklaPerformance.tests), 0),
        ).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
        ).one()
        signature = (latest.year, latest.quarter, *agg)

        with cls._cache_lock:
            cached = cls._ookla_bucket_cache.get(key)
            if cached is not None and cached[0] == signature:
                return cached[0], cached[1]

        buckets = defaultdict(list)
        rows = db.query(
            OoklaPerformance.id,
            OoklaPerformance.quadkey,
            OoklaPerformance.avg_d_kbps,
            OoklaPerformance.avg_u_kbps,
            OoklaPerformance.avg_lat_ms,
            OoklaPerformance.centroid_lat,
            OoklaPerformance.centroid_lon,
            OoklaPerformance.year,
            OoklaPerformance.quarter,
        ).filter(
            OoklaPerformance.year == latest.year,
            OoklaPerformance.quarter == latest.quarter,
            OoklaPerformance.centroid_lat.isnot(None),
            OoklaPerformance.centroid_lon.isnot(None),
        ).all()
        for row in rows:
            point = _OoklaPoint(
                id=row.id,
                quadkey=row.quadkey,
                avg_d_kbps=row.avg_d_kbps,
                avg_u_kbps=row.avg_u_kbps,
                avg_lat_ms=row.avg_lat_ms,
                centroid_lat=float(row.centroid_lat),
                centroid_lon=float(row.centroid_lon),
                year=row.year,
                quarter=row.quarter,
            )
            buckets[_bucket_key(point.centroid_lat, point.centroid_lon)].append(point)
        result = dict(buckets)
        with cls._cache_lock:
            cls._ookla_bucket_cache[key] = (signature, result)
        return signature, result

    @classmethod
    def _latest_ookla_buckets(cls, db: Session):
        return cls._ookla_signature_and_buckets(db)[1]
