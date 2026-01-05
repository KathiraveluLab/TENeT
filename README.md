# TENeT: Telehealth Effectiveness and Necessity Tracker


## Architecture

**Frontend:** React 18 + TypeScript + Leaflet  
**Backend:** Flask 3.0 (Python)  
**Build Tool:** Vite  
**Map Platform:** OpenStreetMap

```
TENeT/
├── frontend/                   # React application with interactive Alaska map
│   ├── src/
│   │   ├── api/
│   │   │   └── catApi.ts       # API client for CAT, broadband, healthcare endpoints
│   │   ├── components/
│   │   │   ├── RegionMarker.tsx     # Map marker with data availability popup
│   │   │   ├── DataCoveragePanel.tsx  # Data coverage summary panel
│   │   │   ├── SeasonSelector.tsx   # Season toggle (Summer/Winter/Year-Round)
│   │   │   └── Legend.tsx           # CAT tier legend
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Main map component with season state
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── backend/                    # Flask API Gateway (Port 5001)
    ├── data/
    │   ├── raw/                # Original data files
    │   │   ├── Airways.csv              # Alaska airways data
    │   │   ├── Roadways.csv             # Alaska roadways data
    │   │   ├── Waterways.csv            # Alaska waterways data
    │   │   ├── fcc-broadband-alaska.csv # FCC broadband data
    │   │   └── alaska_healthsites.geojson  # OSM healthcare facilities
    │   ├── processed_data/     # Combined/cleaned datasets
    │   │   ├── clean_transport_profiles_1.csv  # 421 communities
    │   │   ├── broadband_cleaned.csv           # 354 places with coverage
    │   │   ├── broadband_data_gaps.csv         # Data quality flags
    │   │   ├── healthcare_facilities.csv       # 325 facilities
    │   │   └── healthcare_summary.csv          # Facility statistics
    │   ├── scripts/            # Data preprocessing scripts
    │   │   ├── preprocess_transport.py   # Transport data cleaning
    │   │   ├── preprocess_broadband.py   # FCC data cleaning & gap detection
    │   │   └── preprocess_healthcare.py  # GeoJSON to CSV conversion
    │   ├── samples/            # Sample data files
    │   └── uploads/            # User uploaded files
    │
    ├── database/
    │   ├── config.py           # Database configuration
    │   ├── models.py           # SQLAlchemy models (CATRegion, BroadbandCoverage, HealthcareSite)
    │   ├── handlers.py         # CRUD operations & CAT logic
    │   ├── init_db.py          # Database initialization
    │   ├── seed_cat_data.py    # CSV loader for 421 regions
    │   ├── seed_broadband_data.py   # Broadband coverage seeder
    │   ├── seed_healthcare_data.py  # Healthcare facilities seeder
    │   └── README.md           # Database documentation
    │
    ├── routes/
    │   └── cat_routes.py       # CAT, broadband, healthcare API endpoints
    │
    ├── services/
    │   ├── data_importer.py    # CSV/GeoJSON import service
    │   ├── healthcare_desert_calculator.py  # Season-adjusted necessity scoring
    │   └── season_constants.py # Seasonal transport modifiers
    │
    ├── app.py                  # Flask application entry point
    └── requirements.txt
```


## Getting Started

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Start the Flask server:
```bash
python3 app.py
```

The backend will start at `http://localhost:5001`

**Available endpoints:**
- `GET /api/health` - Health check
- `GET /api/cat/regions?season=winter` - List all 421 communities (season-adjusted tiers)
- `GET /api/cat/statistics` - Database statistics
- `GET /api/cat/healthcare-sites` - Healthcare facilities
- `GET /api/cat/feasibility/<region_code>` - Telehealth feasibility
- `GET /api/cat/healthcare-necessity/<region_code>?season=summer` - Healthcare desert score
- `GET /api/cat/telehealth-priority/<region_code>?season=winter` - Priority classification
- `GET /api/cat/broadband` - Broadband coverage data with filters
- `GET /api/cat/data-gaps` - Data gaps summary
- `GET /api/cat/healthcare` - Healthcare facilities list
- `GET /api/cat/healthcare/by-region/<code>` - Nearest facilities to region
- `GET /api/cat/healthcare/summary` - Healthcare statistics

**Season parameter**: `summer`, `winter`, or `year_round` (default)

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install npm dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will start at `http://localhost:5173`

---

## Data Pipeline

### 1. Broadband Data Pipeline

**Source:** [FCC National Broadband Map](https://broadbandmap.fcc.gov/data-download/nationwide-data)

```bash
# Step 1: Download FCC data (manual)
# Place fcc-broadband-alaska.csv in backend/data/raw/

# Step 2: Preprocess
python backend/data/scripts/preprocess_broadband.py

# Step 3: Seed database
python backend/database/seed_broadband_data.py
```

**Output:**
- 354 Alaska communities with broadband data
- Coverage percentages, primary access types, confidence scores
- Data gap flags: `SATELLITE_DEPENDENT`, `LOW_TERRESTRIAL`, `LOW_CONFIDENCE`

### 2. Healthcare Facility Pipeline

**Source:** OpenStreetMap via Overpass Turbo (ODbL license)

```bash
# Step 1: Export from Overpass (manual)
# Query: amenity=hospital|clinic|pharmacy in Alaska
# Save as backend/data/raw/alaska_healthsites.geojson

# Step 2: Preprocess
python backend/data/scripts/preprocess_healthcare.py

# Step 3: Seed database
python backend/database/seed_healthcare_data.py
```

**Output:**
- 325 healthcare facilities (62 hospitals, 211 clinics, 52 pharmacies)
- 23 facilities with emergency services
- Distance calculations to nearest facility per region

### 3. Transportation Data Pipeline

**Source:** Alaska DOT&PF

```bash
# Preprocess raw transport CSVs
python backend/data/scripts/preprocess_transport.py

# Seed CAT regions
python backend/database/seed_cat_data.py
```

**Output:**
- 421 Alaska communities with CAT tier classification
- Season-adjusted access scoring

---

## Data Architecture

```
Raw Data → Preprocessing → Processed CSV → Database Seeder → SQLite → API → Frontend
```

| Data Type | Raw Format | Processed Output | Database Table |
|-----------|-----------|------------------|----------------|
| Transport | 3 CSVs | clean_transport_profiles_1.csv | cat_regions |
| Broadband | FCC CSV | broadband_cleaned.csv | broadband_coverage |
| Healthcare | GeoJSON | healthcare_facilities.csv | healthcare_sites |

