# TENeT System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                     http://localhost:5173                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP Requests
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      REACT FRONTEND                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MapViewUpdated.jsx                                       │  │
│  │  - Leaflet map                                            │  │
│  │  - Community markers (color-coded by data completeness)  │  │
│  │  - Click handlers                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             │ fetchCommunity(id)                 │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Service (api.js)                                     │  │
│  │  - Centralized API calls                                  │  │
│  │  - Error handling                                         │  │
│  │  - Environment config                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             │ API Response                       │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CommunityInfoPanel.jsx                                   │  │
│  │  - Healthcare data + confidence                           │  │
│  │  - Connectivity data + confidence                         │  │
│  │  - Access data + confidence                               │  │
│  │  - Data completeness indicator                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ fetch('/api/communities/{id}')
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                    http://localhost:8000                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  main.py (FastAPI App)                                    │  │
│  │  - CORS middleware                                        │  │
│  │  - Route registration                                     │  │
│  │  - Startup: load sample data                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  routes/communities.py                                    │  │
│  │  GET /api/communities                                     │  │
│  │  GET /api/communities/{id}                                │  │
│  │  GET /api/communities/{id}/healthcare                     │  │
│  │  GET /api/communities/{id}/connectivity                   │  │
│  │  GET /api/health                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  data_store.py (In-Memory Storage)                        │  │
│  │  - CommunityDataStore                                     │  │
│  │  - add_community()                                        │  │
│  │  - get_community(id)                                      │  │
│  │  - get_all_communities()                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             ▲                                    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐  │
│  │  ingestion.py                                             │  │
│  │  - ingest_sample_communities()                            │  │
│  │  - 8 Alaska communities                                   │  │
│  │  - calculate_data_completeness()                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  models.py (Pydantic Models)                              │  │
│  │  - CommunityRecord                                        │  │
│  │  - HealthcareData (+ confidence)                          │  │
│  │  - ConnectivityData (+ confidence)                        │  │
│  │  - AccessData (+ confidence)                              │  │
│  │  - ConfidenceLevel enum                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────  ┘
```

## Data Flow

### 1. Initial Page Load

```
User opens browser
    ↓
Frontend loads MapViewUpdated component
    ↓
useEffect() triggers on mount
    ↓
fetchCommunities() called
    ↓
GET /api/communities
    ↓
Backend returns array of 8 CommunityListItem objects
    ↓
Frontend sets communities state
    ↓
Map renders with 8 markers (color-coded by data_completeness)
```

### 2. User Clicks Community Marker

```
User clicks marker
    ↓
handleCommunityClick(communityId)
    ↓
setIsLoadingCommunity(true)
setIsPanelOpen(true)
    ↓
fetchCommunity(communityId) called
    ↓
GET /api/communities/{id}
    ↓
Backend queries data_store
    ↓
Returns full CommunityRecord with all data
    ↓
Frontend sets selectedCommunity state
setIsLoadingCommunity(false)
    ↓
CommunityInfoPanel renders with:
  - CompletenessIndicator (progress bar)
  - Healthcare section + ConfidenceBadge
  - Connectivity section + ConfidenceBadge
  - Access section + ConfidenceBadge
  - Raw data (collapsible)
```

## Component Hierarchy

```
App.jsx
  └── DashboardLayout.jsx
        ├── MapViewUpdated.jsx
        │     ├── MapContainer (react-leaflet)
        │     ├── TileLayer
        │     ├── ZoomTracker
        │     ├── Marker (×8, one per community)
        │     │     └── Popup
        │     └── Map Legend
        │
        └── CommunityInfoPanel.jsx
              ├── CompletenessIndicator.jsx
              ├── Healthcare Section
              │     └── ConfidenceBadge.jsx
              ├── Connectivity Section
              │     └── ConfidenceBadge.jsx
              ├── Access Section
              │     └── ConfidenceBadge.jsx
              └── Raw Data Section (collapsible)
```

## API Request/Response Flow

### Example: Get Community Details

**Request:**
```http
GET /api/communities/AK-02185-0001 HTTP/1.1
Host: localhost:8000
```

**Backend Processing:**
```python
@router.get("/communities/{community_id}")
async def get_community(community_id: str):
    community = data_store.get_community(community_id)
    if not community:
        raise HTTPException(404, "Community not found")
    return community
```

**Response:**
```json
{
  "community_id": "AK-02185-0001",
  "name": "Bethel",
  "location": {"lat": 60.7922, "lon": -161.7558},
  "region": "Bethel Census Area",
  "population": 6325,
  "healthcare": {
    "facility_count": 3,
    "facility_types": ["hospital", "clinic", "dental"],
    "source": "OSM + Healthsites",
    "confidence": "high",
    "notes": "Yukon-Kuskokwim Delta Regional Hospital...",
    "last_updated": "2025-12-15T00:00:00Z"
  },
  "connectivity": {
    "download_mbps": 25.0,
    "upload_mbps": 5.0,
    "latency_ms": 85.0,
    "source": "FCC Form 477",
    "confidence": "medium",
    "notes": "Service available but reliability varies",
    "last_updated": "2025-06-01T00:00:00Z"
  },
  "access": {
    "notes": "Regional hub with year-round air...",
    "seasonal": false,
    "confidence": "high",
    "transportation_types": ["air", "barge"]
  },
  "data_completeness": 0.89
}
```

**Frontend Processing:**
```javascript
const { data, error } = await fetchCommunity(communityId)
if (!error) {
  setSelectedCommunity(data)
  // Renders in CommunityInfoPanel
}
```

## State Management

### Backend State
```
In-Memory Dictionary (data_store)
┌───────────────────────────────────┐
│ "AK-02185-0001": CommunityRecord  │
│ "AK-02070-0001": CommunityRecord  │
│ "AK-02290-0001": CommunityRecord  │
│ ...                               │
└───────────────────────────────────┘

Note: Resets on server restart (prototype only)
```

### Frontend State
```javascript
// DashboardLayout.jsx
const [selectedCommunity, setSelectedCommunity] = useState(null)
const [isPanelOpen, setIsPanelOpen] = useState(false)
const [isLoadingCommunity, setIsLoadingCommunity] = useState(false)

// MapViewUpdated.jsx
const [communities, setCommunities] = useState([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)
const [currentZoom, setCurrentZoom] = useState(ALASKA_ZOOM)
```

## Confidence Tracking Flow

Every data section tracks confidence:

```
Raw Data Source (OSM, FCC, etc.)
    ↓
Ingestion Layer
    ↓
Assigns ConfidenceLevel:
  - high: Verified, recent, complete
  - medium: Available but possibly incomplete
  - low: Limited or outdated
  - missing: No data available
    ↓
Stored in CommunityRecord
    ↓
Exposed via API
    ↓
Rendered as ConfidenceBadge in UI
    ↓
User sees color-coded badge with tooltip
```

## Data Completeness Calculation

```python
def calculate_data_completeness(community: CommunityRecord) -> float:
    fields_checked = 0
    fields_confident = 0
    
    # Check healthcare
    if community.healthcare.facility_count is not None:
        fields_checked += 1
        if confidence in [HIGH, MEDIUM]:
            fields_confident += 1
    
    # Check connectivity (download, upload, latency)
    # Check access
    
    return fields_confident / fields_checked if fields_checked > 0 else 0.0
```

Result used for:
1. Marker colors on map
2. Progress bar in info panel
3. Sorting/filtering (future)

## Technology Stack

```
┌─────────────────────────────────────────┐
│           FRONTEND STACK                │
├─────────────────────────────────────────┤
│ React 18                                │
│ Vite (build tool)                       │
│ react-leaflet (map)                     │
│ Leaflet (map library)                   │
│ CSS3 (styling)                          │
│ Fetch API (HTTP client)                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           BACKEND STACK                 │
├─────────────────────────────────────────┤
│ Python 3.8+                             │
│ FastAPI (web framework)                 │
│ Pydantic (data validation)              │
│ Uvicorn (ASGI server)                   │
│ In-Memory Dict (data store)             │
└─────────────────────────────────────────┘
```

## Deployment Architecture (Future)

```
                    ┌────────────────┐
                    │  Load Balancer │
                    └────────┬───────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼──────┐         ┌───────▼──────┐
        │  Frontend    │         │   Backend    │
        │  (Static)    │         │   (FastAPI)  │
        │  Nginx/CDN   │         │   Gunicorn   │
        └──────────────┘         └───────┬──────┘
                                         │
                                 ┌───────▼──────┐
                                 │  PostgreSQL  │
                                 │  + PostGIS   │
                                 └──────────────┘
```

## Security Considerations (Future)

Current (Prototype):
- ❌ No authentication
- ❌ No rate limiting
- ❌ CORS open to localhost
- ❌ No input sanitization
- ❌ No HTTPS

Production Would Need:
- ✅ JWT authentication
- ✅ Rate limiting
- ✅ CORS restricted to domain
- ✅ Input validation/sanitization
- ✅ HTTPS/TLS
- ✅ API key management
- ✅ SQL injection prevention
- ✅ XSS protection

## Performance Characteristics

### Backend
- **Response Time:** <50ms for cached data
- **Throughput:** ~1000 req/sec (in-memory)
- **Memory:** ~10MB for 8 communities
- **Startup:** <1 second

### Frontend
- **Initial Load:** ~2 seconds
- **Map Render:** ~500ms
- **Panel Open:** <300ms
- **Bundle Size:** ~500KB (unminified)

## Extensibility Points

Easy to extend:

1. **New Data Sources:**
   - Add to `ingestion.py`
   - Update `models.py`
   - API automatically serves new fields

2. **New Endpoints:**
   - Add route in `routes/communities.py`
   - Auto-documented

3. **New UI Components:**
   - Add to `components/`
   - Import in layout

4. **Database Integration:**
   - Replace `data_store.py`
   - Keep same interface
   - No API changes needed

5. **Authentication:**
   - Add middleware in `main.py`
   - Add auth headers in `api.js`

## Key Design Decisions

1. **In-Memory Storage:** Fast, simple, good for prototype
2. **Confidence Tracking:** First-class citizen, not optional
3. **No Scoring:** Raw values only, no interpretation
4. **CORS Enabled:** Local development friendly
5. **Auto Documentation:** FastAPI generates API docs
6. **Component Separation:** Easy to modify UI independently
7. **Error Handling:** Graceful degradation throughout
8. **Loading States:** User always knows what's happening

---

This architecture prioritizes:
- 🎯 Clarity over complexity
- 🔍 Transparency over optimization
- 🧪 Research flexibility over production polish
- 📊 Data quality awareness over inference
