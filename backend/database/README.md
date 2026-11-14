# TENeT Database Setup Guide

## Overview

TENeT uses SQLite with SQLAlchemy for storing Community Access Tier (CAT) regions, transport access points, healthcare facilities, FCC broadband coverage, Ookla speed test tiles, and Census income estimates without requiring PostgreSQL or PostGIS during local development or demo deployments.

## Database Schema

[`models.py`](./models.py) defines **8 tables**:

| Table | Purpose |
| --- | --- |
| `cat_regions` | Community records, CAT tier (`1`–`4`), centroid coordinates, GeoJSON geometry, and seasonal/access properties |
| `cat_data_points` | Individual transport/access data points linked to regions and uploads |
| `cat_uploads` | Upload job tracking and processing status for CSV and GeoJSON imports |
| `cat_gating_rules` | Access control rules for CAT Tiers `1`–`4` |
| `healthcare_sites` | Active clinics, hospitals, pharmacies, and health centers with telehealth capability flags |
| `broadband_coverage` | Place-level FCC broadband availability metrics, primary access technology, confidence, and data-gap flags |
| `ookla_performance` | Zoom-16 Ookla fixed performance tiles (`avg_d_kbps`, `avg_u_kbps`, `avg_lat_ms`, `tests`, `devices`) |
| `census_income` | ZCTA-level ACS 5-year median household income records used in affordability burden calculations |

## File Locations

- **Default database:** `backend/data/tenet.db` (configurable via `DB_PATH`)
- **Uploads directory:** `backend/data/uploads/`
- **Processed datasets:** `backend/data/processed_data/`
- **Sample datasets:** `backend/data/samples/`
- **Preprocessing & ingestion scripts:** `backend/data/scripts/`

## Installation and Setup

### 1. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Initialize and seed the database

Run the deterministic initialization workflow from `backend/`:

```bash
python database/init_db.py
```

This creates all 8 tables, inserts the 4 default gating rules (`Tier 1 Basic Access` through `Tier 4 Extreme Access`), and seeds:

1. `seed_cat_data.py` — 421 CAT regions and transport profiles from `backend/data/processed_data/clean_transport_profiles_fixed.csv`
2. `seed_healthcare_data.py` — 325 healthcare facilities from `backend/data/processed_data/healthcare_facilities.csv`
3. `seed_broadband_data.py` — 354 broadband coverage/data-gap records from `backend/data/processed_data/broadband_data_gaps.csv`
4. `seed_census_data.py` — 13 sample Alaska ZCTA income records
5. `seed_ookla_data.py` — 60 curated sample Ookla Open Data tiles from `backend/data/samples/ookla_performance_sample.csv`

For broader Alaska Ookla coverage beyond the offline sample tiles, run `backend/data/scripts/ingest_ookla.py` (uses `pyarrow` to stream public Ookla Open Data parquet tiles from S3). Use `backend/data/scripts/ingest_census.py` for Census income ingestion updates.

## API Reference

Default local backend URL is `http://localhost:5001`. Core database-backed endpoints include:

- **Health & readiness:** `GET /api/health`, `GET /api/ready`
- **Regions & profiles:** `GET /api/cat/regions`, `GET /api/cat/regions/summary`, `GET /api/cat/regions/search`, `GET /api/cat/regions/<region_code>`, `GET /api/cat/regions/<region_code>/research-profile`, `GET /api/cat/regions/research-profiles`
- **Data points & uploads:** `GET /api/cat/data-points`, `POST /api/cat/upload`
- **Gating rules & stats:** `GET /api/cat/gating/rules`, `POST /api/cat/gating/rules`, `POST /api/cat/gating/check`, `GET /api/cat/statistics`, `GET /api/cat/data-gaps`
- **Telehealth, healthcare & scenarios:** `GET /api/cat/telehealth-status/all`, `GET /api/cat/healthcare`, `GET /api/cat/healthcare/summary`, `POST /api/cat/scenarios/preview`
- **Performance & affordability:** `GET /api/cat/performance`, `GET /api/cat/performance/summary`, `GET /api/cat/performance/gaps`, `GET /api/cat/performance/affordability`

### Gating rule validation example

```bash
curl -X POST http://localhost:5001/api/cat/gating/check \
  -H "Content-Type: application/json" \
  -d '{"point_id": 1, "tier_level": 2}'
```

## CSV & GeoJSON Upload Formats

`POST /api/cat/upload` delegates to [`CATDataImporter`](../services/data_importer.py):

- **CSV imports (`CATDataImporter.import_csv`):**
  - Required columns: `region_code`, `latitude`, `longitude`
  - Optional columns: `location_name`, `access_type`, `access_quality`, `distance_km`, `travel_time_minutes` (additional columns are stored in `data_metadata`)
- **GeoJSON imports (`CATDataImporter.import_geojson`):**
  - Required properties: `region_name`, `region_code`, `tier_level` (`1`–`4`)
  - Optional properties: `population`, `area_sqkm`, `access_score`

## Programmatic Usage

### Data Import and Export

```python
from database.config import SessionLocal
from services.data_importer import CATDataImporter

db = SessionLocal()
count, message = CATDataImporter.import_csv(db, "path/to/points.csv")
csv_path = CATDataImporter.export_to_csv(db, region_code="AK-ANCHORAGE")
geojson_path = CATDataImporter.export_to_geojson(db, tier_level=1)
db.close()
```

### Data Querying

```python
from database.config import SessionLocal
from database.handlers import CATDataHandler

db = SessionLocal()
tier1_regions = CATDataHandler.get_regions_by_tier(db, tier_level=1)
points = CATDataHandler.get_data_points_by_region(db, "AK-ANCHORAGE")
nearby = CATDataHandler.get_data_points_in_radius(db, lat=61.2181, lon=-149.9003, radius_km=10)
stats = CATDataHandler.get_statistics(db)
db.close()
```

## Operational Notes

- Coordinates use WGS84 decimal degrees (`latitude`, `longitude`).
- Set `DB_PATH` (default `backend/data/tenet.db`) to point the backend at an alternate SQLite file.
- For production multi-writer workloads requiring spatial database concurrency, PostgreSQL with PostGIS is the planned migration target (`psycopg2-binary` and `geoalchemy2` are noted in `backend/requirements.txt`).
