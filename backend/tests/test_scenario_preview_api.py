import pytest

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.scenario_input_cache import ScenarioInputCache


@pytest.fixture()
def client(db_session):
    ScenarioInputCache.clear()
    ready = CATRegion(
        region_code="AK-READY",
        region_name="Ready Village",
        tier_level=2,
        centroid_lat=61.2,
        centroid_lon=-149.9,
        properties={"primary_access_modes": "road"},
    )
    anchor = CATRegion(
        region_code="AK-ANCHOR",
        region_name="Anchor Village",
        tier_level=3,
        centroid_lat=61.25,
        centroid_lon=-149.95,
        properties={"primary_access_modes": "road"},
    )
    db_session.add_all([ready, anchor])
    db_session.flush()

    db_session.add_all([
        CensusIncome(
            zcta="99501",
            median_income=200000,
            acs_year=2022,
            centroid_lat=61.2,
            centroid_lon=-149.9,
        ),
        CensusIncome(
            zcta="99502",
            median_income=20000,
            acs_year=2022,
            centroid_lat=61.25,
            centroid_lon=-149.95,
        ),
        HealthcareSite(
            name="Ready Clinic",
            site_type="clinic",
            latitude=61.2,
            longitude=-149.9,
            region_code="AK-READY",
            is_active=True,
        ),
        BroadbandCoverage(
            place_id="ready",
            place_name="Ready Village",
            confidence="HIGH",
            data_gaps=None,
            any_tech_25mbps_pct=95,
            primary_access="WIRED",
            telehealth_viable="YES",
            region_code="AK-READY",
        ),
        BroadbandCoverage(
            place_id="anchor",
            place_name="Anchor Village",
            confidence="HIGH",
            data_gaps=None,
            any_tech_25mbps_pct=95,
            primary_access="WIRED",
            telehealth_viable="YES",
            region_code="AK-ANCHOR",
        ),
        OoklaPerformance(
            quadkey="ready",
            avg_d_kbps=52000,
            avg_u_kbps=12000,
            avg_lat_ms=45,
            tests=20,
            devices=8,
            year=2025,
            quarter=4,
            centroid_lat=61.2,
            centroid_lon=-149.9,
        ),
        OoklaPerformance(
            quadkey="anchor",
            avg_d_kbps=52000,
            avg_u_kbps=12000,
            avg_lat_ms=45,
            tests=20,
            devices=8,
            year=2025,
            quarter=4,
            centroid_lat=61.25,
            centroid_lon=-149.95,
        ),
    ])
    db_session.commit()

    from app import app

    yield app.test_client()
    ScenarioInputCache.clear()


def post_preview(client, payload):
    return client.post("/api/cat/scenarios/preview", json=payload)


def test_baseline_equivalent_preview_preserves_statuses(client):
    response = post_preview(client, {
        "mode": "preview",
        "season": "year_round",
        "thresholds": {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": None,
            "affordability_burden_pct": 2,
        },
        "region_codes": ["AK-READY", "AK-ANCHOR"],
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["scenario"]["is_baseline_equivalent"] is True
    assert payload["summary"]["status_changed_regions"] == 0
    for region in payload["regions"]:
        assert region["scenario_status"] == region["baseline_status"]
        assert region["status_delta"] == "unchanged"


def test_partial_threshold_request_uses_baseline_defaults(client):
    response = post_preview(client, {
        "thresholds": {"min_download_mbps": 25},
        "region_codes": ["AK-READY"],
    })

    assert response.status_code == 200
    thresholds = response.get_json()["scenario"]["thresholds"]
    assert thresholds["min_download_mbps"] == 25.0
    assert thresholds["min_upload_mbps"] == 3
    assert thresholds["max_latency_ms"] == 150
    assert thresholds["clinic_proximity_km"] is None
    assert thresholds["affordability_burden_pct"] == 2.0


def test_non_nullable_threshold_null_returns_400(client):
    response = post_preview(client, {
        "thresholds": {"min_download_mbps": None},
    })

    assert response.status_code == 400
    assert "cannot be null" in response.get_json()["error"]


def test_latency_threshold_can_be_disabled_with_null(client):
    response = post_preview(client, {
        "thresholds": {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": None,
            "affordability_burden_pct": 2,
        },
        "region_codes": ["AK-READY"],
    })

    assert response.status_code == 200
    assert response.get_json()["scenario"]["thresholds"]["max_latency_ms"] is None


def test_invalid_region_codes_shape_returns_400(client):
    response = post_preview(client, {
        "thresholds": {},
        "region_codes": "AK-READY",
    })

    assert response.status_code == 400
    assert "region_codes" in response.get_json()["error"]


def test_scenario_preview_reuses_cached_inputs(client, db_session):
    ScenarioInputCache.clear()

    first = post_preview(client, {
        "thresholds": {},
        "season": "year_round",
        "region_codes": ["AK-READY", "AK-ANCHOR"],
    })
    second = post_preview(client, {
        "thresholds": {"min_download_mbps": 100},
        "season": "year_round",
        "region_codes": ["AK-READY", "AK-ANCHOR"],
    })

    assert first.status_code == 200
    assert second.status_code == 200
    assert ScenarioInputCache.build_count(db_session, "year_round") == 1


def test_scenario_cache_rebuilds_per_season(client, db_session):
    ScenarioInputCache.clear()

    year_round = post_preview(client, {
        "thresholds": {},
        "season": "year_round",
        "region_codes": ["AK-READY"],
    })
    winter = post_preview(client, {
        "thresholds": {},
        "season": "winter",
        "region_codes": ["AK-READY"],
    })

    assert year_round.status_code == 200
    assert winter.status_code == 200
    assert ScenarioInputCache.build_count(db_session, "year_round") == 1
    assert ScenarioInputCache.build_count(db_session, "winter") == 1


def test_scenario_preview_excludes_geometry(client):
    response = post_preview(client, {
        "thresholds": {},
        "region_codes": ["AK-READY"],
    })

    assert response.status_code == 200
    region = response.get_json()["regions"][0]
    assert "geometry" not in region
