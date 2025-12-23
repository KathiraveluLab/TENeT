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
│   │   │   └── catApi.ts       # API client for CAT endpoints
│   │   ├── components/
│   │   │   ├── RegionMarker.tsx  # Map marker component
│   │   │   └── Legend.tsx        # CAT tier legend
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Main map component
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── backend/                    # Flask API Gateway (Port 5001)
    ├── data/
    │   ├── raw/                # Original transportation CSV files
    │   │   ├── Airways.csv
    │   │   ├── Roadways.csv
    │   │   └── Waterways.csv
    │   ├── processed_data/     # Combined/cleaned datasets
    │   │   └── clean_transport_profiles_1.csv  # 422 communities
    │   ├── scripts/            # Data preprocessing scripts
    │   ├── samples/            # Sample data files
    │   └── uploads/            # User uploaded files
    │
    ├── database/
    │   ├── config.py           # Database configuration
    │   ├── models.py           # SQLAlchemy models (CATRegion, HealthcareSite)
    │   ├── handlers.py         # CRUD operations & CAT logic
    │   ├── init_db.py          # Database initialization
    │   ├── seed_cat_data.py    # CSV loader for 421 regions
    │   ├── seed_healthcare_sites.py  # Healthcare facilities seeder
    │   └── README.md           # Database documentation
    │
    ├── routes/
    │   └── cat_routes.py       # CAT API endpoints
    │
    ├── services/
    │   ├── data_importer.py    # CSV/GeoJSON import service
    │   └── healthcare_desert_calculator.py  # Necessity scoring
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
- `GET /api/cat/regions` - List all 421 communities
- `GET /api/cat/statistics` - Database statistics
- `GET /api/cat/healthcare-sites` - Healthcare facilities
- `GET /api/cat/feasibility/<region_code>` - Telehealth feasibility

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




