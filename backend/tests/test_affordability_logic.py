from database.models import CATRegion, CensusIncome
from routes.cat_routes import _get_regional_internet_cost


def test_isp_pricing_lookup_for_known_provider_buckets():
    assert _get_regional_internet_cost("99501") == (125.0, "GCI")
    assert _get_regional_internet_cost("99723") == (450.0, "Extreme Rural")
    assert _get_regional_internet_cost("99654") == (120.0, "Starlink")
    assert _get_regional_internet_cost("99615") == (450.0, "FastWyre/Rural")


def test_itu_two_percent_threshold_boundary_is_exclusive():
    income = CensusIncome(zcta="99501", median_income=72000, acs_year=2022)

    assert income.is_affordable(119.99, threshold_pct=2.0) is True
    assert income.is_affordable(120.00, threshold_pct=2.0) is False


def test_missing_or_invalid_income_is_not_treated_as_affordable():
    missing = CensusIncome(zcta="99502", median_income=None, acs_year=2022)
    zero = CensusIncome(zcta="99503", median_income=0, acs_year=2022)

    assert missing.is_affordable(1, threshold_pct=2.0) is False
    assert zero.is_affordable(1, threshold_pct=2.0) is False


def test_burden_percentage_distinguishes_affordable_and_unaffordable_cases():
    income = CensusIncome(zcta="99501", median_income=60000, acs_year=2022)
    monthly_income = income.monthly_income()

    gci_cost, _ = _get_regional_internet_cost("99501")
    rural_cost, _ = _get_regional_internet_cost("99723")

    assert round((gci_cost / monthly_income) * 100, 2) == 2.5
    assert round((rural_cost / monthly_income) * 100, 2) == 9.0
    assert income.is_affordable(gci_cost, threshold_pct=3.0) is True
    assert income.is_affordable(rural_cost, threshold_pct=3.0) is False


def test_region_affordability_matches_nearest_zcta_income(db_session):
    region = CATRegion(
        region_code="AK-AFFORD",
        region_name="Affordability Test Region",
        tier_level=2,
        centroid_lat=61.6,
        centroid_lon=-149.1,
        access_score=55,
    )
    db_session.add(region)
    db_session.add(CensusIncome(
        zcta="99654",
        median_income=72000,
        acs_year=2022,
        centroid_lat=61.6,
        centroid_lon=-149.1,
    ))
    db_session.commit()

    from app import app

    response = app.test_client().get("/api/cat/regions/AK-AFFORD/affordability")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["zcta"] == "99654"
    assert payload["internet_cost"] == 120
    assert payload["isp"] == "Starlink"
    assert payload["burden_pct"] == 2.0
    assert payload["is_affordable"] is False
