import pytest

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
)


@pytest.fixture()
def client(db_session):
    ready_region = CATRegion(
        region_code="AK-ANCHORAGE",
        region_name="Anchorage",
        tier_level=1,
        geometry='{"type":"Point","coordinates":[-149.9,61.2]}',
        centroid_lat=61.2181,
        centroid_lon=-149.9003,
        access_score=95,
        properties={
            "primary_access_modes": "road",
            "region": "Southcentral",
        },
    )
    critical_region = CATRegion(
        region_code="AK-EARECKSON",
        region_name="Eareckson",
        tier_level=4,
        geometry='{"type":"Point","coordinates":[174.1,52.7]}',
        centroid_lat=52.7123,
        centroid_lon=174.114,
        access_score=20,
        properties={
            "primary_access_modes": "air",
            "region": "Aleutians",
        },
    )
    missing_region = CATRegion(
        region_code="AK-MISSING",
        region_name="Missing Data",
        tier_level=3,
        geometry='{"type":"Point","coordinates":[0,0]}',
        centroid_lat=None,
        centroid_lon=None,
        access_score=None,
        properties={},
    )
    db_session.add_all([ready_region, critical_region, missing_region])
    db_session.flush()

    db_session.add(CensusIncome(
        zcta="99501",
        median_income=200000,
        acs_year=2022,
        centroid_lat=61.2181,
        centroid_lon=-149.9003,
    ))
    db_session.add(HealthcareSite(
        name="Anchorage Clinic",
        site_type="clinic",
        has_specialists=True,
        latitude=61.2181,
        longitude=-149.9003,
        region_code="AK-ANCHORAGE",
        is_active=True,
    ))
    db_session.add(BroadbandCoverage(
        place_id="001",
        place_name="Anchorage",
        confidence="HIGH",
        data_gaps=None,
        telehealth_viable="YES",
        primary_access="WIRED",
        region_code="AK-ANCHORAGE",
    ))
    db_session.add(BroadbandCoverage(
        place_id="002",
        place_name="Eareckson",
        confidence="LOW",
        data_gaps="MISSING_WIRED_DATA;LOW_CONFIDENCE",
        telehealth_viable="UNCERTAIN",
        primary_access="SATELLITE",
        region_code="AK-EARECKSON",
    ))
    db_session.commit()

    from app import app

    return app.test_client()


def region_names(payload):
    return {region["name"] for region in payload["regions"]}


def test_regions_summary_returns_communities(client):
    response = client.get("/api/cat/regions/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 3
    assert region_names(payload) == {"Anchorage", "Eareckson", "Missing Data"}


def test_regions_summary_excludes_geometry(client):
    response = client.get("/api/cat/regions/summary")

    assert response.status_code == 200
    for region in response.get_json()["regions"]:
        assert "geometry" not in region
        assert "geojson" not in region
        assert set(region.keys()) == {
            "id",
            "region_code",
            "name",
            "lat",
            "lon",
            "cat_tier",
            "telehealth_status",
            "desert_score",
            "affordability_status",
            "data_confidence",
            "has_data_gap",
            "region",
        }


def test_regions_search_by_name(client):
    response = client.get("/api/cat/regions/search?name=anchor")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["regions"][0]["region_code"] == "AK-ANCHORAGE"


def test_regions_search_filters_by_cat_tier(client):
    response = client.get("/api/cat/regions/search?tier=4")

    assert response.status_code == 200
    assert region_names(response.get_json()) == {"Eareckson"}


def test_regions_search_filters_by_telehealth_status(client):
    response = client.get("/api/cat/regions/search?status=critical")

    assert response.status_code == 200
    assert region_names(response.get_json()) == {"Eareckson"}


def test_regions_search_filters_by_desert_score_threshold(client):
    response = client.get("/api/cat/regions/search?q=desert:>70")

    assert response.status_code == 200
    assert region_names(response.get_json()) == {"Eareckson"}


def test_regions_search_filters_by_data_gap(client):
    response = client.get("/api/cat/regions/search?q=data:missing")

    assert response.status_code == 200
    assert region_names(response.get_json()) == {"Eareckson", "Missing Data"}


def test_regions_search_filters_by_region_syntax(client):
    response = client.get("/api/cat/regions/search?q=region:aleutians")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["regions"][0]["region_code"] == "AK-EARECKSON"


def test_regions_search_invalid_filters_do_not_crash(client):
    response = client.get(
        "/api/cat/regions/search?q=tier:nope desert:>>bad&status=not-real&data_gap=maybe"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 3
    assert region_names(payload) == {"Anchorage", "Eareckson", "Missing Data"}


def test_regions_summary_preserves_missing_data_labels(client):
    response = client.get("/api/cat/regions/summary")

    assert response.status_code == 200
    payload = response.get_json()
    missing = next(region for region in payload["regions"] if region["region_code"] == "AK-MISSING")

    assert missing["lat"] is None
    assert missing["lon"] is None
    assert missing["desert_score"] is None
    assert missing["telehealth_status"] == "DATA_UNAVAILABLE"
    assert missing["affordability_status"] == "unknown"
    assert missing["data_confidence"] == "missing"
    assert missing["has_data_gap"] is True
