import importlib.util
import json
from pathlib import Path

import pytest

from database.models import (
    BroadbandCoverage,
    CATDataPoint,
    CATRegion,
    CATUpload,
    CensusIncome,
    HealthcareSite,
    OoklaPerformance,
)
from services.scenario_input_cache import ScenarioInputCache

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "scripts"
    / "reproduce_paper_evaluation.py"
)


def _load_repro_module():
    spec = importlib.util.spec_from_file_location("reproduce_paper_evaluation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def repro():
    return _load_repro_module()


@pytest.fixture()
def populated_db(db_session):
    ScenarioInputCache.clear()

    upload = CATUpload(filename="eval_test.csv", file_type="csv", status="completed", records_processed=3)
    db_session.add(upload)
    db_session.flush()

    r1 = CATRegion(
        region_code="AK-TEST-ROAD",
        region_name="Road Hub",
        tier_level=1,
        centroid_lat=61.20,
        centroid_lon=-149.90,
        properties={"primary_access_modes": "road", "has_road_access": True},
    )
    r2 = CATRegion(
        region_code="AK-TEST-AIR",
        region_name="Air Village",
        tier_level=3,
        centroid_lat=64.50,
        centroid_lon=-165.40,
        properties={"primary_access_modes": "air", "has_airport": True},
    )
    r3 = CATRegion(
        region_code="AK-TEST-ISOLATED",
        region_name="Isolated Settlement",
        tier_level=4,
        centroid_lat=59.10,
        centroid_lon=-158.50,
        properties={"primary_access_modes": "no_direct_access"},
    )
    db_session.add_all([r1, r2, r3])
    db_session.flush()

    for reg in (r1, r2, r3):
        db_session.add(
            CATDataPoint(
                upload_id=upload.id,
                region_id=reg.id,
                region_code=reg.region_code,
                latitude=reg.centroid_lat,
                longitude=reg.centroid_lon,
                travel_time_minutes=None,
            )
        )

    db_session.add_all(
        [
            BroadbandCoverage(
                place_id="p1",
                place_name="Road Hub",
                any_tech_25mbps_pct=95.0,
                fiber_25mbps_pct=40.0,
                primary_access="WIRED",
                confidence="HIGH",
                region_code="AK-TEST-ROAD",
                data_source="FCC",
            ),
            BroadbandCoverage(
                place_id="p2",
                place_name="Air Village",
                any_tech_25mbps_pct=85.0,
                fiber_25mbps_pct=0.0,
                primary_access="SATELLITE",
                confidence="MEDIUM",
                region_code="AK-TEST-AIR",
                data_source="FCC",
            ),
            BroadbandCoverage(
                place_id="p3",
                place_name="Isolated Settlement",
                any_tech_25mbps_pct=100.0,
                fiber_25mbps_pct=0.0,
                primary_access="SATELLITE",
                confidence="MEDIUM",
                region_code="AK-TEST-ISOLATED",
                data_source="FCC",
            ),
        ]
    )

    db_session.add_all(
        [
            OoklaPerformance(
                quadkey="q1",
                avg_d_kbps=120000,
                avg_u_kbps=25000,
                avg_lat_ms=20.0,
                tests=50,
                devices=15,
                year=2026,
                quarter=1,
                centroid_lat=61.20,
                centroid_lon=-149.90,
            ),
            OoklaPerformance(
                quadkey="q2",
                avg_d_kbps=12000,
                avg_u_kbps=2000,
                avg_lat_ms=65.0,
                tests=10,
                devices=4,
                year=2026,
                quarter=1,
                centroid_lat=64.50,
                centroid_lon=-165.40,
            ),
            OoklaPerformance(
                quadkey="q3",
                avg_d_kbps=85000,
                avg_u_kbps=18000,
                avg_lat_ms=70.0,
                tests=20,
                devices=8,
                year=2026,
                quarter=1,
                centroid_lat=59.10,
                centroid_lon=-158.50,
            ),
        ]
    )

    # Income near r1 (affordable at baseline) and r3 (~22 km away: fails at $450/mo, passes at $120/mo); none near r2
    db_session.add_all(
        [
            CensusIncome(
                zcta="99501",
                median_income=180000.0,
                acs_year=2022,
                centroid_lat=61.20,
                centroid_lon=-149.90,
            ),
            CensusIncome(
                zcta="99601",
                median_income=84000.0,
                acs_year=2022,
                centroid_lat=59.30,
                centroid_lon=-158.50,
            ),
        ]
    )

    db_session.add_all(
        [
            HealthcareSite(
                name="Hub Clinic",
                site_type="clinic",
                has_emergency=False,
                has_specialists=False,
                latitude=61.20,
                longitude=-149.90,
                region_code="AK-TEST-ROAD",
                is_active=True,
            ),
            HealthcareSite(
                name="Regional Hospital",
                site_type="hospital",
                has_emergency=True,
                has_specialists=True,
                latitude=61.22,
                longitude=-149.90,
                region_code="AK-TEST-ROAD",
                is_active=True,
            ),
            HealthcareSite(
                name="Town Pharmacy",
                site_type="pharmacy",
                has_emergency=False,
                has_specialists=False,
                latitude=64.50,
                longitude=-165.40,
                region_code="AK-TEST-AIR",
                is_active=True,
            ),
        ]
    )
    db_session.commit()
    yield db_session
    ScenarioInputCache.clear()


def test_evaluate_all_empty_database_is_safe(db_session, repro):
    ScenarioInputCache.clear()
    results = repro.evaluate_all(db_session, radii_km=[10.0, 55.0], run_benchmarks=False)

    assert results["dataset_metrics"]["inventory"]["cat_regions"] == 0
    assert results["dataset_metrics"]["proximity_km"]["nearest_clinic_only"] is None
    assert results["classification_and_missingness"]["total_regions"] == 0
    tex = repro.render_latex_tables(results)
    assert r"\label{tab:tenet_metrics}" in tex
    assert r"\label{tab:scenario_sensitivity}" in tex
    assert r"\label{tab:radius_ablation}" in tex
    assert r"\label{tab:latency_bench}" in tex
    assert "Benchmarks skipped" in tex


def test_evaluate_all_reproduces_metrics_concordance_starlink_and_radii(populated_db, repro):
    res1 = repro.evaluate_all(populated_db, radii_km=[10.0, 55.0, 75.0], run_benchmarks=False)
    res2 = repro.evaluate_all(populated_db, radii_km=[10.0, 55.0, 75.0], run_benchmarks=False)
    assert res1 == res2

    dm = res1["dataset_metrics"]
    assert dm["inventory"]["cat_regions"] == 3
    assert dm["transport"]["cat_tiers"] == {1: 1, 2: 0, 3: 1, 4: 1}
    assert dm["transport"]["air_only_count"] == 1
    assert dm["transport"]["no_direct_access_count"] == 1
    assert dm["broadband"]["communities_linked_to_fcc"] == 3
    assert dm["broadband"]["satellite_primary_places"] == 2
    assert dm["healthcare_facilities"]["by_type"] == {"clinic": 1, "hospital": 1, "pharmacy": 1, "other": 0}
    assert dm["healthcare_facilities"]["emergency_count"] == 1
    assert dm["healthcare_facilities"]["specialists_count"] == 1
    assert dm["healthcare_facilities"]["communities_without_linked_facility"] == 1
    assert dm["missing_travel_time_data_points"] == 3

    # Concordance: r1 & r3 pass, r2 fails FCC-pass vs Ookla (dl<25 + ul<3)
    conc = res1["fcc_ookla_concordance"]
    assert conc["linkage_partition"]["both"] == 3
    assert conc["concordance_matrix"]["both_pass"] == 2
    assert conc["concordance_matrix"]["fcc_pass_ookla_fail"] == 1
    assert conc["fcc_pass_ookla_fail_subcauses"] == {"dl<25+ul<3": 1}

    # Missingness: AK-TEST-AIR lacks ACS income despite having broadband + clinic distance
    cls = res1["classification_and_missingness"]
    assert cls["overall_status"]["DATA_UNAVAILABLE"] == 1
    assert cls["overall_status"]["TELEHEALTH_READY"] == 1
    assert cls["overall_status"]["CRITICAL_GAP"] == 1
    assert cls["data_unavailable_reasons"] == {"bb=1,income=0,clinic=1": 1}

    # Starlink $120/mo substitution resolves AK-TEST-ISOLATED's $450/mo affordability barrier
    star = res1["starlink_substitution"]
    assert star["income_linked_count"] == 2
    assert star["isp_baseline_status"].get("TELEHEALTH_READY") == 1
    assert star["starlink_status"].get("TELEHEALTH_READY") == 2

    # Radius ablation shows r3's ACS zone (~22.24 km away) missed at 10 km and matched at 55 km
    rad = {row["radius_km"]: row for row in res1["spatial_radius_ablation"]}
    assert rad[10.0]["acs"]["matched"] == 1
    assert rad[55.0]["acs"]["matched"] == 2
    assert rad[75.0]["ookla"]["matched"] == 3


def test_evaluate_all_with_benchmarks_and_cli_outputs(populated_db, repro, tmp_path):
    results = repro.evaluate_all(
        populated_db,
        radii_km=[10.0, 55.0],
        run_benchmarks=True,
        profile_code="AK-TEST-ROAD",
        compare_codes=["AK-TEST-ROAD", "AK-TEST-AIR", "AK-TEST-ISOLATED"],
        cold_runs=1,
        warm_runs=2,
        standard_runs=1,
        data_gaps_runs=1,
    )
    bench = results["latency_benchmarks"]
    assert bench is not None
    endpoints = [ep["endpoint"] for ep in bench["endpoints"]]
    assert "/scenarios/preview (cold)" in endpoints
    assert "/scenarios/preview (warm)" in endpoints
    assert "/regions/AK-TEST-ROAD/research-profile" in endpoints
    assert "/regions/research-profiles (3 pins)" in endpoints

    tex = repro.render_latex_tables(results)
    assert "Benchmarks skipped" not in tex
    assert r"\label{tab:latency_bench}" in tex

    summary_text = repro.render_human_summary(results)
    assert "TENeT Paper Evaluation Reproduction Summary" in summary_text

    json_out = tmp_path / "eval.json"
    tex_out = tmp_path / "tables.tex"
    rc = repro.main(
        [
            "--skip-benchmarks",
            "--radii",
            "10",
            "55",
            "--json-out",
            str(json_out),
            "--tex-out",
            str(tex_out),
            "--format",
            "summary",
        ]
    )
    assert rc == 0
    parsed = json.loads(json_out.read_text(encoding="utf-8"))
    assert parsed["latency_benchmarks"] is None
    assert parsed["dataset_metrics"]["inventory"]["cat_regions"] == 3
    assert r"\label{tab:tenet_metrics}" in tex_out.read_text(encoding="utf-8")

