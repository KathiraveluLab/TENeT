from database.models import OoklaPerformance


def test_performance_summary_empty_database(db_session):
    from app import app

    response = app.test_client().get("/api/cat/performance/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["has_data"] is False


def test_performance_summary_aggregates_speeds_and_excludes_null_or_zero(db_session):
    db_session.add(
        OoklaPerformance(
            quadkey="older-q3",
            avg_d_kbps=999000,
            avg_u_kbps=100000,
            avg_lat_ms=10,
            tests=99,
            devices=50,
            year=2025,
            quarter=3,
            centroid_lat=61.2,
            centroid_lon=-149.9,
        )
    )

    latest_rows = [
        # Missing/zero speeds must count toward tiles/tests/devices but not speed stats
        ("null-speed", None, 5, 2),
        ("zero-speed", 0, 3, 1),
        ("critical-1", 3000, 10, 4),
        ("poor-1", 8000, 12, 5),
        ("moderate-1", 15000, 14, 6),
        ("good-1", 30000, 16, 7),
        ("excellent-1", 60000, 18, 8),
        ("excellent-2", 90000, 20, 9),
    ]
    for quadkey, avg_d_kbps, tests, devices in latest_rows:
        db_session.add(
            OoklaPerformance(
                quadkey=quadkey,
                avg_d_kbps=avg_d_kbps,
                avg_u_kbps=5000,
                avg_lat_ms=40,
                tests=tests,
                devices=devices,
                year=2025,
                quarter=4,
                centroid_lat=61.2,
                centroid_lon=-149.9,
            )
        )
    db_session.commit()

    from app import app

    response = app.test_client().get("/api/cat/performance/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["has_data"] is True
    assert payload["period"] == {"year": 2025, "quarter": 4, "label": "Q4 2025"}
    assert payload["coverage"] == {
        "total_tiles": 8,
        "tiles_with_speed_data": 6,
        "total_tests": 98,
        "total_devices": 42,
    }
    assert payload["speeds"] == {
        "avg_download_mbps": 34.33,
        "max_download_mbps": 90.0,
        "min_download_mbps": 3.0,
        "median_download_mbps": 30.0,
    }
    assert payload["distribution"] == {
        "excellent": 2,
        "good": 1,
        "moderate": 1,
        "poor": 1,
        "critical": 1,
    }
    assert payload["telehealth_viable_pct"] == 50.0


def test_performance_summary_handles_tiles_with_no_valid_speeds(db_session):
    for quadkey, avg_d_kbps in (("only-null", None), ("only-zero", 0)):
        db_session.add(
            OoklaPerformance(
                quadkey=quadkey,
                avg_d_kbps=avg_d_kbps,
                tests=4,
                devices=2,
                year=2025,
                quarter=4,
                centroid_lat=61.2,
                centroid_lon=-149.9,
            )
        )
    db_session.commit()

    from app import app

    response = app.test_client().get("/api/cat/performance/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["has_data"] is True
    assert payload["coverage"] == {
        "total_tiles": 2,
        "tiles_with_speed_data": 0,
        "total_tests": 8,
        "total_devices": 4,
    }
    assert payload["speeds"] == {
        "avg_download_mbps": None,
        "max_download_mbps": None,
        "min_download_mbps": None,
        "median_download_mbps": None,
    }
    assert payload["distribution"] == {
        "excellent": 0,
        "good": 0,
        "moderate": 0,
        "poor": 0,
        "critical": 0,
    }
    assert payload["telehealth_viable_pct"] == 0

