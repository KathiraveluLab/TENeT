import pytest

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)


@pytest.fixture()
def client(db_session):
    complete = CATRegion(
        region_code="AK-READY",
        region_name="Ready Village",
        tier_level=2,
        centroid_lat=61.2,
        centroid_lon=-149.9,
        properties={"region": "Southcentral", "primary_access_modes": "road"},
    )
    missing = CATRegion(
        region_code="AK-GAPS",
        region_name="Gap Village",
        tier_level=4,
        centroid_lat=None,
        centroid_lon=None,
        properties={},
    )
    db_session.add_all([complete, missing])
    db_session.flush()

    db_session.add(BroadbandCoverage(
        place_id="ready",
        place_name="Ready Village",
        confidence="HIGH",
        data_gaps=None,
        any_tech_25mbps_pct=91.5,
        primary_access="WIRED",
        telehealth_viable="YES",
        region_code="AK-READY",
        data_source="FCC",
    ))
    db_session.add(CensusIncome(
        zcta="99501",
        median_income=120000,
        acs_year=2022,
        centroid_lat=61.2,
        centroid_lon=-149.9,
    ))
    db_session.add(HealthcareSite(
        name="Ready Clinic",
        site_type="clinic",
        has_emergency=True,
        has_specialists=True,
        has_telehealth=True,
        latitude=61.21,
        longitude=-149.91,
        region_code="AK-READY",
        is_active=True,
    ))
    db_session.add(OoklaPerformance(
        quadkey="021230",
        avg_d_kbps=52000,
        avg_u_kbps=12000,
        avg_lat_ms=45,
        tests=20,
        devices=8,
        year=2025,
        quarter=4,
        centroid_lat=61.205,
        centroid_lon=-149.905,
    ))
    db_session.commit()

    from app import app

    return app.test_client()


def test_single_research_profile_schema_with_complete_data(client):
    response = client.get("/api/cat/regions/AK-READY/research-profile?season=winter")

    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload.keys()) == {
        "region",
        "connectivity",
        "affordability",
        "healthcare",
        "telehealth",
        "methodology",
    }
    assert payload["region"]["region_code"] == "AK-READY"
    assert payload["region"]["data_confidence"] == "HIGH"
    assert payload["region"]["has_data_gap"] is False
    assert payload["connectivity"]["ookla_download_mbps"] == 52.0
    assert payload["connectivity"]["latency_ms"] == 45.0
    assert payload["healthcare"]["nearest_facility_name"] == "Ready Clinic"
    assert payload["healthcare"]["emergency_services"] is True
    assert payload["affordability"]["status"] in {"affordable", "unaffordable"}
    assert payload["telehealth"]["season"] == "winter"


def test_research_profile_keeps_missing_metrics_as_null(client):
    response = client.get("/api/cat/regions/AK-GAPS/research-profile")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["region"]["lat"] is None
    assert payload["region"]["lon"] is None
    assert payload["region"]["has_data_gap"] is True
    assert payload["region"]["data_confidence"] in {"LOW", "MISSING"}
    assert payload["connectivity"]["ookla_download_mbps"] is None
    assert payload["affordability"]["median_income"] is None
    assert payload["healthcare"]["nearest_facility_name"] is None
    assert "connectivity.ookla_download_mbps" in payload["region"]["missing_fields"]


def test_research_profile_invalid_region_returns_structured_404(client):
    response = client.get("/api/cat/regions/AK-NOT-REAL/research-profile")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"] == "Community not found"
    assert payload["region_code"] == "AK-NOT-REAL"


def test_research_profile_invalid_season_falls_back_to_year_round(client):
    response = client.get("/api/cat/regions/AK-READY/research-profile?season=monsoon")

    assert response.status_code == 200
    assert response.get_json()["telehealth"]["season"] == "year_round"


def test_batch_research_profiles_preserve_order_and_missing_codes(client):
    response = client.get(
        "/api/cat/regions/research-profiles?codes=AK-GAPS,AK-NOT-REAL,AK-READY&season=summer"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 2
    assert [profile["region"]["region_code"] for profile in payload["profiles"]] == [
        "AK-GAPS",
        "AK-READY",
    ]
    assert payload["missing_codes"] == ["AK-NOT-REAL"]
    assert payload["season"] == "summer"
