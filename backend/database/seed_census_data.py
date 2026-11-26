"""
Seed Alaska ZCTA income data for local development, reproducibility, and tests.

Loads the curated statewide U.S. Census ACS 5-Year ZCTA snapshot
(backend/data/processed_data/alaska_acs_zcta_income.csv) when present so a fresh
clone runs offline with full statewide coverage, and falls back to the compact
13-ZCTA SAMPLE_CENSUS_INCOME list when the CSV snapshot is unavailable.
"""
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.scripts.ingest_census import DEFAULT_CSV_PATH, load_records_from_csv
from database.config import Base, SessionLocal, engine
from database.models import CensusIncome


SAMPLE_CENSUS_INCOME = [
    {"zcta": "99501", "income": 76000, "lat": 61.2181, "lon": -149.9003, "population": 16500},
    {"zcta": "99559", "income": 47000, "lat": 60.7922, "lon": -161.7558, "population": 6400},
    {"zcta": "99577", "income": 94000, "lat": 61.2308, "lon": -149.4489, "population": 31000},
    {"zcta": "99615", "income": 79000, "lat": 57.7900, "lon": -152.4072, "population": 12500},
    {"zcta": "99654", "income": 89000, "lat": 61.5811, "lon": -149.4389, "population": 57000},
    {"zcta": "99686", "income": 83000, "lat": 61.1308, "lon": -146.3483, "population": 3900},
    {"zcta": "99701", "income": 68000, "lat": 64.8378, "lon": -147.7164, "population": 19000},
    {"zcta": "99723", "income": 71000, "lat": 71.2906, "lon": -156.7886, "population": 4400},
    {"zcta": "99741", "income": 38000, "lat": 64.7414, "lon": -156.8734, "population": 230},
    {"zcta": "99762", "income": 61000, "lat": 64.5011, "lon": -165.4064, "population": 3800},
    {"zcta": "99801", "income": 93000, "lat": 58.3019, "lon": -134.4197, "population": 32000},
    {"zcta": "99835", "income": 82000, "lat": 57.0531, "lon": -135.3350, "population": 8500},
    {"zcta": "99901", "income": 78000, "lat": 55.3422, "lon": -131.6461, "population": 13800},
]


def _normalize_fallback_records() -> List[Dict]:
    """Convert SAMPLE_CENSUS_INCOME fallback rows into the canonical CensusIncome dict shape."""
    return [
        {
            "zcta": row["zcta"],
            "median_income": float(row["income"]),
            "population": int(row["population"]),
            "centroid_lat": float(row["lat"]),
            "centroid_lon": float(row["lon"]),
            "acs_year": 2022,
            "data_source": "Local sample based on ACS workflow",
        }
        for row in SAMPLE_CENSUS_INCOME
    ]


def seed_census_data(csv_path: Optional[str] = DEFAULT_CSV_PATH) -> int:
    """Seed CensusIncome records from the statewide CSV snapshot (or fallback sample)."""
    Base.metadata.create_all(bind=engine)
    if csv_path and os.path.exists(csv_path):
        records = load_records_from_csv(csv_path)
    else:
        records = _normalize_fallback_records()

    db = SessionLocal()
    try:
        deleted = db.query(CensusIncome).delete()
        print(f"Cleared {deleted} existing Census income records")

        for row in records:
            db.add(CensusIncome(
                zcta=row["zcta"],
                state_fips="02",
                median_income=float(row["median_income"]),
                total_households=None,
                population=int(row["population"]) if row.get("population") is not None else None,
                centroid_lat=float(row["centroid_lat"]),
                centroid_lon=float(row["centroid_lon"]),
                acs_year=int(row["acs_year"]),
                data_source=row["data_source"],
            ))

        db.commit()
        print(f"Seeded {len(records)} Census income records")
        return len(records)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_census_data()
