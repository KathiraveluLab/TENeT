from dataclasses import replace

import pytest

from services.telehealth_classification import (
    TelehealthInputs,
    classify_telehealth,
)


@pytest.fixture()
def complete_inputs():
    return TelehealthInputs(
        latitude=61.2,
        longitude=-149.9,
        access_modes="road",
        ookla_download_mbps=50.0,
        ookla_upload_mbps=10.0,
        ookla_latency_ms=40.0,
        fcc_coverage_pct=95.0,
        median_income=100000.0,
        monthly_internet_cost=100.0,
        burden_pct=1.2,
        nearest_clinic_distance_km=20.0,
        clinic_data_available=True,
    )


def test_measured_broadband_is_preferred_when_available(complete_inputs):
    inputs = replace(
        complete_inputs,
        ookla_download_mbps=1.0,
        ookla_upload_mbps=1.0,
        fcc_coverage_pct=100.0,
    )

    result = classify_telehealth(inputs)

    assert result.broadband_source == "OOKLA"
    assert result.video_feasible is False
    assert result.status == "CRITICAL_GAP"


def test_measured_broadband_can_establish_ready_status(complete_inputs):
    result = classify_telehealth(complete_inputs)

    assert result.broadband_source == "OOKLA"
    assert result.video_feasible is True
    assert result.status == "TELEHEALTH_READY"


def test_fcc_is_used_only_as_broadband_fallback(complete_inputs):
    inputs = replace(
        complete_inputs,
        ookla_download_mbps=None,
        ookla_upload_mbps=None,
        ookla_latency_ms=None,
        fcc_coverage_pct=75.0,
    )

    result = classify_telehealth(inputs)

    assert result.broadband_source == "FCC"
    assert result.video_feasible is True
    assert result.status == "TELEHEALTH_READY"


def test_missing_broadband_is_explicitly_unavailable(complete_inputs):
    inputs = replace(
        complete_inputs,
        ookla_download_mbps=None,
        ookla_upload_mbps=None,
        ookla_latency_ms=None,
        fcc_coverage_pct=None,
        nearest_clinic_distance_km=1.0,
    )

    result = classify_telehealth(inputs)

    assert result.status == "DATA_UNAVAILABLE"
    assert "NO_BROADBAND_DATA" in result.reason_codes


@pytest.mark.parametrize(
    "burden_pct, monthly_cost, expected_status",
    [
        (1.999, 399.99, "TELEHEALTH_READY"),
        (2.0, 399.99, "COMMUNITY_ANCHOR"),
        (1.0, 400.0, "COMMUNITY_ANCHOR"),
    ],
)
def test_affordability_boundaries_are_exclusive(
    complete_inputs,
    burden_pct,
    monthly_cost,
    expected_status,
):
    inputs = replace(
        complete_inputs,
        burden_pct=burden_pct,
        monthly_internet_cost=monthly_cost,
        nearest_clinic_distance_km=5.0,
    )

    assert classify_telehealth(inputs).status == expected_status


def test_missing_income_is_not_treated_as_affordable(complete_inputs):
    inputs = replace(
        complete_inputs,
        median_income=None,
        monthly_internet_cost=None,
        burden_pct=None,
        nearest_clinic_distance_km=1.0,
    )

    result = classify_telehealth(inputs)

    assert result.affordability_status == "unknown"
    assert result.status == "DATA_UNAVAILABLE"
    assert "NO_INCOME_DATA" in result.reason_codes


def test_unaffordable_home_access_is_not_labeled_limited(complete_inputs):
    inputs = replace(
        complete_inputs,
        burden_pct=3.0,
        nearest_clinic_distance_km=20.0,
    )

    result = classify_telehealth(inputs)

    assert result.audio_feasible is True
    assert result.status == "CRITICAL_GAP"


@pytest.mark.parametrize(
    "distance_km, expected_status",
    [
        (9.99, "COMMUNITY_ANCHOR"),
        (10.01, "CRITICAL_GAP"),
    ],
)
def test_nearby_and_distant_clinics(complete_inputs, distance_km, expected_status):
    inputs = replace(
        complete_inputs,
        ookla_download_mbps=1.0,
        ookla_upload_mbps=1.0,
        burden_pct=3.0,
        nearest_clinic_distance_km=distance_km,
    )

    assert classify_telehealth(inputs).status == expected_status


@pytest.mark.parametrize(
    "access_modes, expected_threshold, expected_status",
    [
        ("air,road", 10.0, "CRITICAL_GAP"),
        ("air", 50.0, "COMMUNITY_ANCHOR"),
        ("no_direct_access", 50.0, "COMMUNITY_ANCHOR"),
    ],
)
def test_access_mode_selects_road_or_non_road_clinic_threshold(
    complete_inputs,
    access_modes,
    expected_threshold,
    expected_status,
):
    inputs = replace(
        complete_inputs,
        access_modes=access_modes,
        ookla_download_mbps=1.0,
        ookla_upload_mbps=1.0,
        burden_pct=3.0,
        nearest_clinic_distance_km=20.0,
    )

    result = classify_telehealth(inputs)

    assert result.clinic_threshold_km == expected_threshold
    assert result.status == expected_status


@pytest.mark.parametrize(
    "changes, reason_code",
    [
        ({"latitude": None}, "MISSING_COORDINATES"),
        ({"longitude": None}, "MISSING_COORDINATES"),
        ({"clinic_data_available": False}, "NO_CLINIC_DATA"),
    ],
)
def test_missing_coordinates_and_clinic_data_are_explicit(
    complete_inputs,
    changes,
    reason_code,
):
    inputs = replace(
        complete_inputs,
        ookla_download_mbps=1.0,
        ookla_upload_mbps=1.0,
        burden_pct=3.0,
        **changes,
    )

    result = classify_telehealth(inputs)

    assert result.status == "DATA_UNAVAILABLE"
    assert reason_code in result.reason_codes


def test_missing_measured_upload_does_not_create_video_success(complete_inputs):
    result = classify_telehealth(replace(complete_inputs, ookla_upload_mbps=None))

    assert result.video_feasible is None
    assert result.status == "LIMITED_TELEHEALTH"
    assert "MISSING_UPLOAD" in result.reason_codes
