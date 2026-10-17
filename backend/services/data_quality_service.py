"""
Shared data quality decisions for research-facing outputs.

The API keeps unavailable values as None and exposes quality metadata beside the
metrics, so every UI surface can render gaps consistently.
"""

from __future__ import annotations

from typing import Iterable


CONFIDENCE_RANK = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "MISSING": 0,
}


def split_gap_flags(value: str | None) -> list[str]:
    if not value:
        return []
    return [flag.strip() for flag in value.split(";") if flag.strip()]


def normalize_confidence(value: str | None) -> str:
    normalized = (value or "MISSING").strip().upper()
    return normalized if normalized in CONFIDENCE_RANK else normalized


def combine_confidence(values: Iterable[str | None]) -> str:
    normalized = [normalize_confidence(value) for value in values]
    ranked = [value for value in normalized if value in CONFIDENCE_RANK]
    if not ranked:
        return "MISSING"
    return min(ranked, key=lambda item: CONFIDENCE_RANK[item])


class DataQualityService:
    """Centralized missing-field and confidence evaluation."""

    @staticmethod
    def evaluate_region_profile(
        *,
        region,
        broadband,
        ookla,
        income,
        nearest_facility,
        desert_score,
    ) -> dict:
        missing_fields: list[str] = []

        if region.centroid_lat is None:
            missing_fields.append("region.lat")
        if region.centroid_lon is None:
            missing_fields.append("region.lon")
        if broadband is None:
            missing_fields.extend([
                "connectivity.fcc_coverage_25mbps_pct",
                "connectivity.isp_name",
            ])
        else:
            if broadband.any_tech_25mbps_pct is None:
                missing_fields.append("connectivity.fcc_coverage_25mbps_pct")
            if not broadband.primary_access:
                missing_fields.append("connectivity.isp_name")

        if ookla is None:
            missing_fields.extend([
                "connectivity.ookla_download_mbps",
                "connectivity.ookla_upload_mbps",
                "connectivity.latency_ms",
            ])
        else:
            if ookla.avg_d_kbps is None:
                missing_fields.append("connectivity.ookla_download_mbps")
            if ookla.avg_u_kbps is None:
                missing_fields.append("connectivity.ookla_upload_mbps")
            if ookla.avg_lat_ms is None:
                missing_fields.append("connectivity.latency_ms")

        if income is None or income.median_income is None:
            missing_fields.append("affordability.median_income")
        if nearest_facility is None:
            missing_fields.extend([
                "healthcare.nearest_facility_name",
                "healthcare.nearest_facility_distance_km",
            ])
        if desert_score is None:
            missing_fields.append("healthcare.desert_score")

        source_confidence = normalize_confidence(
            getattr(broadband, "confidence", None) if broadband else None
        )
        if source_confidence == "HIGH" and missing_fields:
            data_confidence = "MEDIUM" if len(missing_fields) <= 3 else "LOW"
        elif source_confidence == "MEDIUM" and len(missing_fields) > 4:
            data_confidence = "LOW"
        elif source_confidence == "MISSING" and len(missing_fields) < 4:
            data_confidence = "LOW"
        else:
            data_confidence = source_confidence

        broadband_gaps = split_gap_flags(getattr(broadband, "data_gaps", None) if broadband else None)

        return {
            "has_data_gap": bool(missing_fields or broadband_gaps),
            "missing_fields": sorted(set(missing_fields + broadband_gaps)),
            "data_confidence": data_confidence,
        }
