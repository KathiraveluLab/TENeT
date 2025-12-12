# TENeT: Telehealth Effectiveness and Necessity Tracker

This service provides the data ingestion and preprocessing layer for the Telehealth Effectiveness and Necessity Tracker for Alaska. It retrieves,
normalizes, and scores healthcare provider data, specialist availability,
and transportation accessibility to support downstream dashboards and
geospatial analysis.

## Features Implemented

#### 1. NPPES Ingestion Layer
- Fetches healthcare providers using the NPPES Registry API.
- Alaska-specific fallback querying using ZIP-code prefixes.

#### 2. Specialist Access 
- Retrieves specialists filtered by taxonomy or region.
- Supports full taxonomy classification to distinguish provider categories 
  such as cardiology, pharmacy, primary care, and more.
- Identifies NPI Type 1 (individual providers) and NPI Type 2 
  (organizations/clinics), enabling clearer separation between solo practitioners 
  and healthcare facilities.

- Normalized taxonomy metadata includes:
  - taxonomy code
  - description
  - primary/specialty flag

#### 3. Healthsites Access
- Extracts precise practice locations (address, city, state, ZIP), which supports future geocoding and distance-based scoring.

## Tech Stack
- **Backend:** Python, FastAPI
- **Data Sources:** NPPES Registry API, OSRM
- **Output:** JSON for downstream dashboard processing
## Project Structure
```
backend/
├── main.py
├── routers/
│ ├── healthsites.py
│ ├── specialists.py
│ ├── transport.py
│ └── metrics.py
└── services/
├── healthsites_service.py
├── specialists_service.py
├── transport_service.py
└── metrics_service.py
```


## How to Run
```
pip install -r requirements.txt

uvicorn app.main:app --reload
```
Open API docs at:  
```
http://localhost:8000/docs
```
## Next Steps
- Geocoding provider addresses to lat/lon (Mapbox or Nominatim).
- Final definition of the compound healthcare desert score.
- Integration of Internet performance datasets (e.g., broadband mapping).
- Map visualization layer centered on Alaska using OpenStreetMap.


