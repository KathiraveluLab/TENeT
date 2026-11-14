"""Unit and regression tests for Census ACS ZCTA ingestion and seeding."""

import io
import json
import urllib.error
from unittest.mock import MagicMock

from data.scripts.ingest_census import (
    DEFAULT_CSV_PATH,
    ZCTA_CENTROIDS,
    fetch_zcta_batch,
    parse_acs_dat_stream,
    parse_acs_nonnegative_int,
    parse_acs_positive_float,
    parse_place_gazetteer,
    parse_zcta_gazetteer,
    parse_zcta_place_rel_stream,
    resolve_zcta_centroid,
)
from database.models import CensusIncome
from database.seed_census_data import SAMPLE_CENSUS_INCOME, seed_census_data


def test_parse_acs_numeric_sentinels():
    assert parse_acs_positive_float("75668") == 75668.0
    assert parse_acs_positive_float("-666666666") is None
    assert parse_acs_positive_float(None) is None
    assert parse_acs_positive_float(".") is None
    assert parse_acs_positive_float("0") is None

    assert parse_acs_nonnegative_int("16175") == 16175
    assert parse_acs_nonnegative_int("0") == 0
    assert parse_acs_nonnegative_int("-666666666") is None
    assert parse_acs_nonnegative_int(None) is None


def test_fetch_zcta_batch_tolerates_null_and_suppressed_rows(monkeypatch):
    payload = [
        ["NAME", "B19013_001E", "B01003_001E", "zip code tabulation area"],
        ["ZCTA5 99501", "70891", "16175", "99501"],
        ["ZCTA5 99545", None, "42", "99545"],
        ["ZCTA5 99720", "-666666666", "178", "99720"],
        ["ZCTA5 98101", "95000", "20000", "98101"],
    ]
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = False
    monkeypatch.setattr("data.scripts.ingest_census.urllib.request.urlopen", lambda *a, **kw: mock_cm)

    records = fetch_zcta_batch(["99501", "99545", "99720", "98101"], api_key="test-key", year=2024)
    assert len(records) == 1
    assert records[0]["zcta"] == "99501"
    assert records[0]["median_income"] == 70891.0
    assert records[0]["population"] == 16175

    def _raise_http_error(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://api.census.gov/data", 404, "Not Found", {}, None)

    monkeypatch.setattr("data.scripts.ingest_census.urllib.request.urlopen", _raise_http_error)
    assert fetch_zcta_batch(["99501"], api_key="test-key", year=2024) == []


def test_parse_gazetteer_dat_and_place_weighted_centroid():
    zcta_tsv = io.StringIO(
        "GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG\n"
        "99574\t8526240000\t0\t3292.0\t0.0\t61.1174\t-147.6070\n"
        "99588\t9085700000\t0\t3508.0\t0.0\t62.7078\t-146.7194\n"
        "99599\t44029797\t0\t17.0\t0.0\t61.1600\t-149.9900\n"
        "98101\t1000\t0\t1.0\t0.0\t47.61\t-122.33\n"
    )
    gaz_zctas = parse_zcta_gazetteer(zcta_tsv)
    assert set(gaz_zctas.keys()) == {"99574", "99588", "99599"}

    place_tsv = io.StringIO(
        "USPS\tGEOID\tANSICODE\tNAME\tLSAD\tFUNCSTAT\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG\n"
        "AK\t0217410\t0\tCordova city\t25\tA\t0\t0\t60.0\t0\t60.5300\t-145.6419\n"
        "AK\t0212970\t0\tChenega CDP\t57\tS\t0\t0\t29.0\t0\t60.0920\t-147.9947\n"
        "AK\t0203000\t0\tAnchorage municipality\t53\tA\t0\t0\t1707.0\t0\t61.1743\t-149.2843\n"
        "WA\t5363000\t0\tSeattle city\t25\tA\t0\t0\t83.0\t0\t47.62\t-122.35\n"
    )
    ak_places = parse_place_gazetteer(place_tsv)
    assert "0217410" in ak_places and "5363000" not in ak_places

    dat_stream = io.StringIO(
        "GEO_ID|B01003_E001\n"
        "860Z200US99574|2551\n"
        "1600000US0217410|2400\n"
        "1600000US0212970|60\n"
        "1600000US0203000|288976\n"
    )
    z_pops, p_pops = parse_acs_dat_stream(dat_stream, "B01003_E001")
    assert z_pops["99574"] == "2551"
    assert p_pops["0217410"] == "2400"

    rel_stream = io.StringIO(
        "GEOID_ZCTA5_20|GEOID_PLACE_20|AREALAND_ZCTA5_20|AREALAND_PART\n"
        "99574|0217410|8526240000|411549110\n"
        "99574|0212970|8526240000|196321098\n"
        "99599|0203000|44029797|44029797\n"
    )
    links = parse_zcta_place_rel_stream(rel_stream, ak_places)
    place_pop_ints = {k: parse_acs_nonnegative_int(v) for k, v in p_pops.items()}

    lat, lon, method = resolve_zcta_centroid(
        "99574", gaz_zctas, ak_places=ak_places, place_pops=place_pop_ints, zcta_place_links=links
    )
    assert method == "place_pop_weighted"
    assert 60.45 < lat < 60.54
    assert -145.75 < lon < -145.60

    # Small urban ZCTA enclosed by a consolidated municipality keeps its Gazetteer internal point
    lat_sub, lon_sub, sub_method = resolve_zcta_centroid(
        "99599", gaz_zctas, ak_places=ak_places, place_pops=place_pop_ints, zcta_place_links=links
    )
    assert sub_method == "census_gazetteer"
    assert (lat_sub, lon_sub) == (61.1600, -149.9900)

    # Curated hub takes priority for multi-polygon/split hub ZCTAs
    lat_hub, lon_hub, hub_method = resolve_zcta_centroid("99503", gaz_zctas)
    assert hub_method == "curated_hub"
    assert (lat_hub, lon_hub) == ZCTA_CENTROIDS["99503"]

    # Gazetteer fallback when no contained Places match
    lat_gaz, lon_gaz, gaz_method = resolve_zcta_centroid("99588", gaz_zctas)
    assert gaz_method == "census_gazetteer"
    assert (lat_gaz, lon_gaz) == (62.7078, -146.7194)


def test_seed_census_data_loads_statewide_csv_and_fallback(db_session, tmp_path):
    count = seed_census_data(DEFAULT_CSV_PATH)
    assert count >= 190
    rows = db_session.query(CensusIncome).all()
    assert len(rows) == count
    assert all(r.median_income > 0 for r in rows)
    assert all(50.0 < r.centroid_lat < 73.0 and -180.0 < r.centroid_lon < -129.0 for r in rows)

    fallback_count = seed_census_data(str(tmp_path / "missing_census.csv"))
    assert fallback_count == len(SAMPLE_CENSUS_INCOME)
    assert db_session.query(CensusIncome).count() == len(SAMPLE_CENSUS_INCOME)
