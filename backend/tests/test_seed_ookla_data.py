from database.models import OoklaPerformance
from database.seed_ookla_data import load_sample_rows, upsert_sample_rows


def test_checked_in_sample_contains_real_populated_period():
    rows = load_sample_rows()

    assert len(rows) == 60
    assert {(row["year"], row["quarter"]) for row in rows} == {(2024, 4)}
    assert all(row["tests"] >= 1 and row["devices"] >= 1 for row in rows)


def test_sample_upsert_is_idempotent_and_preserves_other_tiles(db_session):
    unrelated = OoklaPerformance(
        quadkey="unrelated-full-ingest-tile",
        avg_d_kbps=12345,
        avg_u_kbps=2345,
        avg_lat_ms=45,
        tests=2,
        devices=1,
        year=2023,
        quarter=1,
        centroid_lat=65.0,
        centroid_lon=-150.0,
    )
    db_session.add(unrelated)
    db_session.commit()

    rows = load_sample_rows()
    assert upsert_sample_rows(db_session, rows) == 60
    assert upsert_sample_rows(db_session, rows) == 60

    assert db_session.query(OoklaPerformance).count() == 61
    assert db_session.query(OoklaPerformance).filter_by(
        quadkey="unrelated-full-ingest-tile"
    ).one().avg_d_kbps == 12345
