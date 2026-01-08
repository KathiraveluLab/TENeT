# TENeT - End-to-End Data Integration Pipeline

## Architecture Overview

This PR implements a complete data flow from backend ingestion → API exposure → frontend visualization.

```
[ Sample Alaska Data ]
        ↓
[ FastAPI Backend + Data Models ]
        ↓
[ REST API Endpoints ]
        ↓
[ React Frontend with Leaflet Map ]
        ↓
[ Community Info Panel with Confidence Indicators ]
```

## What's Included

### Backend (`/backend`)

1. **Data Models** (`app/models.py`)
   - `CommunityRecord`: Complete community data structure
   - `HealthcareData`: Facility counts, types, with confidence tracking
   - `ConnectivityData`: Speed metrics with source attribution
   - `AccessData`: Transportation info
   - `ConfidenceLevel`: Explicit data quality enum (high/medium/low/missing)

2. **Data Ingestion** (`app/ingestion.py`)
   - Sample Alaska communities (8 representative locations)
   - Realistic healthcare, connectivity, and access data
   - Data completeness calculation
   - Ready to be replaced with real API integrations (OSM, FCC, etc.)

3. **API Endpoints** (`app/routes/communities.py`)
   - `GET /api/communities` - List all communities
   - `GET /api/communities/{id}` - Full community details
   - `GET /api/communities/{id}/healthcare` - Healthcare data only
   - `GET /api/communities/{id}/connectivity` - Connectivity data only
   - `GET /api/health` - API health check

4. **FastAPI Application** (`app/main.py`)
   - CORS enabled for local development
   - Auto-generated API docs at `/api/docs`
   - In-memory data store (prototype level)

### Frontend (`/frontend`)

1. **API Service** (`src/services/api.js`)
   - Centralized API communication
   - Error handling
   - Environment-based configuration

2. **Map Integration** (`src/components/MapViewUpdated.jsx`)
   - Interactive Alaska map using react-leaflet
   - Community markers color-coded by data completeness
   - Click to view details
   - Legend for data quality visualization

3. **Community Info Panel** (`src/components/CommunityInfoPanel.jsx`)
   - **Completely rewritten** to match new data structure
   - Shows raw values (no scores/categories)
   - Confidence badges for each data section
   - Data completeness indicator
   - Handles missing data explicitly
   - Collapsible raw JSON view

4. **Data Confidence Components**
   - `ConfidenceBadge.jsx`: Visual quality indicators
   - `CompletenessIndicator.jsx`: Progress bar for data coverage

## Setup Instructions

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at:
- API: http://localhost:8000/api
- Docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:5173

## Key Design Decisions

### ✅ What This PR Does

- **Raw data exposure**: All metrics are presented as-is
- **Confidence tracking**: Every data point has a quality indicator
- **Transparent missing data**: "No data" is a first-class citizen
- **Data completeness**: Visual progress bars show coverage
- **Source attribution**: Every field tracks its data source
- **Prototype-level ingestion**: Sample data for 8 Alaska communities
- **Clean API design**: RESTful, well-documented, easy to extend

### ❌ What This PR Does NOT Do

- ❌ Calculate feasibility scores
- ❌ Apply CAT tiering logic
- ❌ Use thresholds or categories (e.g., "good/poor connectivity")
- ❌ Include AI/ML components
- ❌ Make policy recommendations
- ❌ Implement authentication
- ❌ Optimize for production scale

## Data Transparency

Every community record includes:

- **Source attribution**: Where data came from (OSM, FCC, etc.)
- **Confidence levels**: 
  - High: Verified from reliable sources
  - Medium: Available but possibly incomplete
  - Low: Limited or outdated
  - Missing: No data available
- **Last updated timestamps**: When data was collected
- **Notes**: Context and caveats

Example response:

```json
{
  "community_id": "AK-02185-0001",
  "name": "Bethel",
  "location": {"lat": 60.7922, "lon": -161.7558},
  "healthcare": {
    "facility_count": 3,
    "facility_types": ["hospital", "clinic", "dental"],
    "source": "OSM + Healthsites",
    "confidence": "high",
    "notes": "Yukon-Kuskokwim Delta Regional Hospital serves hub community"
  },
  "connectivity": {
    "download_mbps": 25.0,
    "upload_mbps": 5.0,
    "latency_ms": 85.0,
    "source": "FCC Form 477",
    "confidence": "medium",
    "notes": "Service available but reliability varies"
  },
  "data_completeness": 0.89
}
```

## Testing

### Backend

```bash
cd backend
# Check API health
curl http://localhost:8000/api/health

# Get all communities
curl http://localhost:8000/api/communities

# Get specific community
curl http://localhost:8000/api/communities/AK-02185-0001
```

### Frontend

1. Open http://localhost:5173
2. Click on any community marker on the map
3. Community info panel should slide in from the right
4. Verify:
   - Data loads correctly
   - Confidence badges display
   - Missing data shows "No data"
   - Data completeness indicator works

## Future Extensions

This foundation supports:

1. **Real data ingestion**: Replace sample data with actual API calls
2. **Database integration**: Add PostgreSQL/PostGIS for persistence
3. **Additional data sources**: USGS, weather, census data
4. **Historical tracking**: Store time-series data
5. **Export functionality**: Download community reports
6. **Filtering/search**: Find communities by criteria
7. **Comparison views**: Side-by-side community analysis

## File Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app & startup
│   ├── models.py            # Pydantic data models
│   ├── data_store.py        # In-memory storage
│   ├── ingestion.py         # Sample data loader
│   └── routes/
│       └── communities.py   # API endpoints
└── requirements.txt

frontend/
├── src/
│   ├── components/
│   │   ├── MapViewUpdated.jsx         # New map with backend integration
│   │   ├── CommunityInfoPanel.jsx     # Rewritten for new data structure
│   │   ├── ConfidenceBadge.jsx        # Data quality indicators
│   │   └── CompletenessIndicator.jsx  # Coverage progress bar
│   ├── services/
│   │   └── api.js           # Backend API client
│   ├── layout/
│   │   └── DashboardLayout.jsx  # Updated to use new components
│   └── styles/
│       ├── confidence-badge.css
│       └── completeness-indicator.css
└── package.json
```

## Success Criteria ✓

- [x] Data flows cleanly from backend → frontend
- [x] Communities can be clicked and inspected
- [x] Missing data is explicitly visible
- [x] System is easy to extend
- [x] No scoring/CAT logic included
- [x] Confidence tracking throughout
- [x] Clean API design
- [x] Interactive map with markers

## Research Value

This PR demonstrates:

- System-level integration skills
- Data transparency best practices
- Research-oriented software design
- Handling incomplete real-world data
- API design for exploration (not production)
- Frontend/backend separation
- GSoC-relevant architectural thinking

## Notes

- Backend uses in-memory storage (resets on restart)
- Sample data represents 8 diverse Alaska communities
- Frontend shows data completeness via marker colors
- All confidence badges are interactive (hover for details)
- Raw JSON view available for debugging
- API auto-documentation at `/api/docs`
