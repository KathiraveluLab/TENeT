import pytest

from database.models import CATDataPoint, CATRegion, CATUpload, HealthcareSite
from services.healthcare_desert_calculator import HealthcareDesertCalculator
from services.season_constants import SEASON_SUMMER, SEASON_WINTER, SEASON_YEAR_ROUND


def add_region(db, code="AK-TEST", lat=61.0, lon=-149.0, travel_time=120):
    upload = CATUpload(filename="test.csv", file_type="csv", status="completed")
    db.add(upload)
    db.flush()

    region = CATRegion(
        region_code=code,
        region_name="Test Region",
        tier_level=2,
        centroid_lat=lat,
        centroid_lon=lon,
        access_score=60,
        properties={"primary_access_modes": "road,air"},
    )
    db.add(region)
    db.flush()

    db.add(CATDataPoint(
        upload_id=upload.id,
        region_id=region.id,
        region_code=code,
        latitude=lat,
        longitude=lon,
        location_name="Test Region",
        access_type="road",
        access_quality=60,
        travel_time_minutes=travel_time,
    ))
    db.commit()
    return region


def add_site(db, code="AK-TEST", name="Clinic", site_type="clinic", lat=61.0, lon=-149.0, specialists=False):
    site = HealthcareSite(
        name=name,
        site_type=site_type,
        latitude=lat,
        longitude=lon,
        region_code=code,
        has_emergency=site_type == "hospital",
        has_specialists=specialists,
        is_active=True,
    )
    db.add(site)
    db.commit()
    return site


def test_distance_to_nearest_facility_zero_when_facility_matches_region_center(db_session):
    add_region(db_session)
    add_site(db_session, name="Clinic at Center", site_type="clinic")

    distances = HealthcareDesertCalculator.get_nearest_facility_distances(db_session, "AK-TEST")

    assert distances["clinic"] == 0


@pytest.mark.parametrize(
    "distance_km, expected_score",
    [
        (0, 0),
        (150, 50),
        (300, 100),
        (450, 100),
    ],
)
def test_distance_component_formula(distance_km, expected_score):
    assert HealthcareDesertCalculator.score_distance_component(distance_km) == expected_score


@pytest.mark.parametrize(
    "num_sites, expected_score",
    [
        (0, 100),
        (1, 70),
        (2, 40),
        (3, 10),
        (8, 10),
    ],
)
def test_facility_density_component_formula(num_sites, expected_score):
    assert HealthcareDesertCalculator.score_density_component(num_sites) == expected_score


@pytest.mark.parametrize(
    "has_specialists, expected_score",
    [
        (True, 0),
        (False, 100),
    ],
)
def test_specialist_component_formula(has_specialists, expected_score):
    assert HealthcareDesertCalculator.score_specialist_component(has_specialists) == expected_score


@pytest.mark.parametrize(
    "mode, season, road_quality, expected_score",
    [
        ("road", SEASON_SUMMER, "local", 65.0),
        ("road", SEASON_YEAR_ROUND, "local", 72.5),
        ("road", SEASON_WINTER, "local", 100.0),
        ("water", SEASON_SUMMER, "local", 50.0),
        ("water", SEASON_WINTER, "local", 77.0),
        ("air", SEASON_WINTER, "local", 59.0),
    ],
)
def test_transport_component_formula_for_access_modes(mode, season, road_quality, expected_score):
    score = HealthcareDesertCalculator.score_transport_component(
        travel_time_minutes=120,
        season=season,
        road_quality=road_quality,
        transport_mode=mode,
    )

    assert score == pytest.approx(expected_score)


def test_composite_score_matches_hand_calculated_example(db_session):
    add_region(db_session, travel_time=120)
    add_site(db_session, name="Clinic", site_type="clinic")
    add_site(db_session, name="Hospital", site_type="hospital", specialists=True)

    score = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
        db_session,
        "AK-TEST",
        season=SEASON_YEAR_ROUND,
    )

    assert score["distance_to_nearest_clinic_km"] == 0
    assert score["distance_to_nearest_hospital_km"] == 0
    assert score["num_healthcare_sites"] == 2
    assert score["has_specialist_access"] is True
    assert score["breakdown"]["density_component"] == 40
    assert score["breakdown"]["specialist_component"] == 0
    assert score["breakdown"]["transport_component"] == 72.5
    assert score["necessity_score"] == 20.5


def test_winter_transport_adjustment_increases_score_against_summer(db_session):
    add_region(db_session, travel_time=120)
    add_site(db_session, site_type="clinic")
    add_site(db_session, name="Hospital", site_type="hospital", specialists=True)

    summer = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
        db_session,
        "AK-TEST",
        season=SEASON_SUMMER,
    )
    winter = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
        db_session,
        "AK-TEST",
        season=SEASON_WINTER,
    )

    assert summer["breakdown"]["transport_component"] == 65
    assert winter["breakdown"]["transport_component"] == 100
    assert winter["necessity_score"] > summer["necessity_score"]


def test_specialist_availability_lowers_need_score(db_session):
    add_region(db_session, travel_time=60)
    add_site(db_session, site_type="clinic")
    no_specialist = HealthcareDesertCalculator.calculate_healthcare_necessity_score(db_session, "AK-TEST")

    add_site(db_session, name="Specialist Hospital", site_type="hospital", specialists=True)
    with_specialist = HealthcareDesertCalculator.calculate_healthcare_necessity_score(db_session, "AK-TEST")

    assert no_specialist["has_specialist_access"] is False
    assert with_specialist["has_specialist_access"] is True
    assert with_specialist["necessity_score"] < no_specialist["necessity_score"]


def test_missing_region_data_is_handled_safely(db_session):
    score = HealthcareDesertCalculator.calculate_healthcare_necessity_score(
        db_session,
        "AK-MISSING",
        season=SEASON_YEAR_ROUND,
    )

    assert score["distance_to_nearest_clinic_km"] == 500
    assert score["distance_to_nearest_hospital_km"] == 500
    assert score["num_healthcare_sites"] == 0
    assert score["necessity_score"] == 90
