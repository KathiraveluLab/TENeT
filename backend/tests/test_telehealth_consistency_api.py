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
    db_session.add(CATRegion(
        region_code="AK-CONSISTENT",
        region_name="Consistent Village",
        tier_level=2,
        centroid_lat=61.2,
        centroid_lon=-149.9,
        properties={"primary_access_modes": "road"},
    ))
    db_session.add(BroadbandCoverage(
        place_id="consistent",
        place_name="Consistent Village",
        confidence="HIGH",
        any_tech_25mbps_pct=95.0,
        region_code="AK-CONSISTENT",
        data_source="FCC",
    ))
    db_session.add(CensusIncome(
        zcta="99501",
        median_income=200000.0,
        acs_year=2022,
        centroid_lat=61.2,
        centroid_lon=-149.9,
    ))
    db_session.add(HealthcareSite(
        name="Consistent Clinic",
        site_type="clinic",
        latitude=61.2,
        longitude=-149.9,
        region_code="AK-CONSISTENT",
        is_active=True,
    ))
    db_session.add(OoklaPerformance(
        quadkey="consistent",
        avg_d_kbps=52000,
        avg_u_kbps=12000,
        avg_lat_ms=45,
        tests=20,
        devices=8,
        year=2025,
        quarter=4,
        centroid_lat=61.2,
        centroid_lon=-149.9,
    ))
    db_session.commit()

    from app import app

    yield app.test_client()
    ScenarioInputCache.clear()


def test_all_public_telehealth_paths_agree_for_same_community(client):
    summary_response = client.get("/api/cat/regions/summary")
    profile_response = client.get(
        "/api/cat/regions/AK-CONSISTENT/research-profile"
    )
    batch_profile_response = client.get(
        "/api/cat/regions/research-profiles?codes=AK-CONSISTENT"
    )
    status_response = client.get(
        "/api/cat/regions/AK-CONSISTENT/telehealth-status"
    )
    status_map_response = client.get("/api/cat/telehealth-status/all")
    scenario_response = client.post(
        "/api/cat/scenarios/preview",
        json={"thresholds": {}, "region_codes": ["AK-CONSISTENT"]},
    )

    for response in (
        summary_response,
        profile_response,
        batch_profile_response,
        status_response,
        status_map_response,
        scenario_response,
    ):
        assert response.status_code == 200

    summary_status = summary_response.get_json()["regions"][0]["telehealth_status"]
    profile_status = profile_response.get_json()["telehealth"]["status"]
    batch_profile_status = (
        batch_profile_response.get_json()["profiles"][0]["telehealth"]["status"]
    )
    single_status = status_response.get_json()["status"]
    map_status = status_map_response.get_json()["regions"][0]["status"]
    scenario_region = scenario_response.get_json()["regions"][0]

    assert {
        summary_status,
        profile_status,
        batch_profile_status,
        single_status,
        map_status,
        scenario_region["baseline_status"],
        scenario_region["scenario_status"],
    } == {"TELEHEALTH_READY"}
    assert scenario_region["reason_codes"] != ["BASELINE_EQUIVALENT"]
