import pytest

from database.models import (
    BroadbandCoverage,
    CATRegion,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
import services.research_profile_service as research_profile_module
from services.research_profile_service import ResearchProfileService


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
        population=16000,
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
    assert payload["region"]["population"] == 16000
    assert payload["region"]["data_confidence"] == "HIGH"
    assert payload["region"]["has_data_gap"] is False
    assert payload["connectivity"]["ookla_download_mbps"] == 52.0
    assert payload["connectivity"]["latency_ms"] == 45.0
    assert payload["connectivity"]["isp_name"] not in {None, "WIRED"}
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


def test_income_lookup_filters_distant_records_before_distance_loop(db_session, monkeypatch):
    region = CATRegion(
        region_code="AK-INCOME",
        region_name="Income Village",
        tier_level=3,
        centroid_lat=61.2,
        centroid_lon=-149.9,
    )
    nearby_income = CensusIncome(
        zcta="99501",
        median_income=90000,
        acs_year=2022,
        centroid_lat=61.21,
        centroid_lon=-149.91,
    )
    distant_income = CensusIncome(
        zcta="99999",
        median_income=95000,
        acs_year=2022,
        centroid_lat=40.0,
        centroid_lon=-75.0,
    )
    db_session.add_all([region, nearby_income, distant_income])
    db_session.commit()

    distance_calls = []

    def fake_haversine(*args):
        distance_calls.append(args)
        return 1.0

    monkeypatch.setattr(research_profile_module, "_haversine_km", fake_haversine)

    nearest = ResearchProfileService._nearest_income_record(db_session, region)

    assert nearest.zcta == "99501"
    assert len(distance_calls) == 1


def test_research_profile_applies_seasonal_cat_tier_and_excludes_pharmacies(db_session):
    region = CATRegion(
        region_code="AK-SEASONAL",
        region_name="Seasonal Village",
        tier_level=1,
        centroid_lat=62.0,
        centroid_lon=-150.0,
        access_score=90.0,
        properties={"primary_access_modes": "road,water", "region": "Interior Economic Region"},
    )
    db_session.add(region)
    db_session.add(BroadbandCoverage(
        place_id="seasonal",
        place_name="Seasonal Village",
        confidence="HIGH",
        any_tech_25mbps_pct=0.85,
        primary_access="WIRED",
        region_code="AK-SEASONAL",
        data_source="FCC",
    ))
    db_session.add(HealthcareSite(
        name="Nearest Pharmacy",
        site_type="pharmacy",
        latitude=62.0,
        longitude=-150.0,
        region_code="AK-SEASONAL",
        is_active=True,
    ))
    db_session.add(HealthcareSite(
        name="Clinical Center",
        site_type="clinic",
        latitude=62.1,
        longitude=-150.0,
        region_code="AK-SEASONAL",
        is_active=True,
    ))
    db_session.commit()

    from app import app

    response = app.test_client().get("/api/cat/regions/AK-SEASONAL/research-profile?season=winter")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["region"]["cat_tier"] == 3
    assert payload["connectivity"]["fcc_coverage_25mbps_pct"] == 85.0
    assert payload["healthcare"]["nearest_facility_name"] == "Clinical Center"


def test_batch_research_profiles_matches_single_profiles_with_one_classification_pass(client, monkeypatch):
    from services.telehealth_classification import TelehealthClassificationService

    single_ready = client.get("/api/cat/regions/AK-READY/research-profile?season=winter").get_json()
    single_gaps = client.get("/api/cat/regions/AK-GAPS/research-profile?season=winter").get_json()

    classify_calls = []
    original_classify_regions = TelehealthClassificationService.classify_regions

    def spy_classify_regions(db, regions):
        classify_calls.append(len(regions))
        return original_classify_regions(db, regions)

    monkeypatch.setattr(TelehealthClassificationService, "classify_regions", staticmethod(spy_classify_regions))

    batch_response = client.get("/api/cat/regions/research-profiles?codes=AK-READY,AK-GAPS&season=winter")

    assert batch_response.status_code == 200
    payload = batch_response.get_json()
    assert classify_calls == [2]

    for profile in (*payload["profiles"], single_ready, single_gaps):
        assert isinstance(profile["methodology"].pop("generated_at"), str)

    assert payload["profiles"] == [single_ready, single_gaps]


def test_telehealth_cache_refreshes_automatically_after_ookla_and_income_commits(client, db_session):
    from services.telehealth_classification import TelehealthClassificationService

    TelehealthClassificationService.clear_caches()

    # Warm all-regions cache before inserting a new community and nearby Ookla/income rows.
    initial_summary = client.get("/api/cat/regions/summary")
    assert initial_summary.status_code == 200

    db_session.add(
        CATRegion(
            region_code="AK-WARM-UPDATE",
            region_name="Warm Update Village",
            tier_level=2,
            centroid_lat=64.84,
            centroid_lon=-147.72,
            properties={"region": "Interior", "primary_access_modes": "road"},
        )
    )
    db_session.add(
        CensusIncome(
            zcta="99701",
            median_income=85000,
            population=31000,
            acs_year=2022,
            centroid_lat=64.84,
            centroid_lon=-147.72,
        )
    )
    db_session.add(
        OoklaPerformance(
            quadkey="warm-update-tile",
            avg_d_kbps=65000,
            avg_u_kbps=15000,
            avg_lat_ms=32,
            tests=12,
            devices=6,
            year=2025,
            quarter=4,
            centroid_lat=64.841,
            centroid_lon=-147.721,
        )
    )
    db_session.commit()

    refreshed_profile = client.get("/api/cat/regions/AK-WARM-UPDATE/research-profile")
    assert refreshed_profile.status_code == 200
    profile_json = refreshed_profile.get_json()
    assert profile_json["connectivity"]["ookla_download_mbps"] == 65.0
    assert profile_json["affordability"]["median_income"] == 85000

    refreshed_summary = client.get("/api/cat/regions/summary")
    assert refreshed_summary.status_code == 200
    assert any(r["region_code"] == "AK-WARM-UPDATE" for r in refreshed_summary.get_json()["regions"])
