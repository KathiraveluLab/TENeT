# TENeT Quick Reference Card

## 🚀 One-Liner Start

```bash
chmod +x start-dev.sh && ./start-dev.sh
```

---

## 📍 URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Main UI |
| Backend API | http://localhost:8000/api | Data endpoints |
| API Docs | http://localhost:8000/api/docs | Interactive docs |
| Health Check | http://localhost:8000/api/health | Server status |

---

## 🔧 Backend Commands

```bash
# Setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000

# Test
curl http://localhost:8000/api/health
curl http://localhost:8000/api/communities | jq
```

---

## 🎨 Frontend Commands

```bash
# Setup
cd frontend
npm install
cp .env.example .env

# Run
npm run dev

# Build
npm run build
```

---

## 🗺️ API Endpoints

```bash
# List all communities
GET /api/communities

# Get community details
GET /api/communities/{id}

# Healthcare data only
GET /api/communities/{id}/healthcare

# Connectivity data only  
GET /api/communities/{id}/connectivity

# Health check
GET /api/health
```

---

## 📊 Sample Community IDs

| ID | Name | Type | Data Quality |
|----|------|------|--------------|
| AK-02020-0001 | Anchorage | Major City | High |
| AK-02158-0001 | Juneau | State Capital | High |
| AK-02185-0001 | Bethel | Regional Hub | Good |
| AK-02070-0001 | Barrow | Remote Hub | Good |
| AK-02290-0001 | Nome | Coastal Hub | Good |
| AK-02220-0001 | Kotzebue | Northwest Hub | Good |
| AK-02110-0001 | Haines | Town | High |
| AK-02185-0002 | Napakiak | Village | Limited |

---

## 🎯 Data Model

```python
{
  "community_id": "AK-XXXXX",
  "name": "Community Name",
  "location": {"lat": 64.5, "lon": -147.3},
  "region": "Census Area",
  "population": 1234,
  
  "healthcare": {
    "facility_count": 2,
    "facility_types": ["clinic"],
    "source": "OSM",
    "confidence": "high|medium|low|missing"
  },
  
  "connectivity": {
    "download_mbps": 25.0,
    "upload_mbps": 5.0,
    "latency_ms": 85.0,
    "source": "FCC",
    "confidence": "high|medium|low|missing"
  },
  
  "access": {
    "notes": "Access information",
    "seasonal": true,
    "confidence": "high|medium|low|missing",
    "transportation_types": ["air"]
  },
  
  "data_completeness": 0.85
}
```

---

## 🎨 Confidence Levels

| Level | Badge | Color | Meaning |
|-------|-------|-------|---------|
| high | ✓ | 🟢 Green | Verified, reliable |
| medium | ~ | 🟡 Yellow | Available, incomplete |
| low | ? | 🟠 Orange | Limited, outdated |
| missing | ✗ | ⚫ Gray | No data |

---

## 🗂️ File Structure

```
TENeT/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # Data models
│   │   ├── data_store.py        # Storage
│   │   ├── ingestion.py         # Sample data
│   │   └── routes/
│   │       └── communities.py   # API endpoints
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapViewUpdated.jsx
│   │   │   ├── CommunityInfoPanel.jsx
│   │   │   ├── ConfidenceBadge.jsx
│   │   │   └── CompletenessIndicator.jsx
│   │   ├── services/
│   │   │   └── api.js           # API client
│   │   └── layout/
│   │       └── DashboardLayout.jsx
│   └── package.json
│
└── docs/
    ├── SETUP.md
    ├── PR_SUMMARY.md
    ├── ARCHITECTURE.md
    └── TESTING_CHECKLIST.md
```

---

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't start | Activate venv, reinstall requirements |
| Frontend can't connect | Check backend is running on port 8000 |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |
| Port 5173 in use | `lsof -ti:5173 \| xargs kill -9` |
| No markers on map | Check browser console, verify API call |
| CORS errors | Check backend CORS settings in main.py |

---

## ✅ Quick Test

```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Test
curl http://localhost:8000/api/health
# Should return: {"status":"healthy","communities_loaded":8}

# Terminal 3 - Frontend
cd frontend && npm run dev

# Browser
# Open http://localhost:5173
# Click any marker
# Panel should show community data
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| SETUP.md | Setup instructions |
| PR_SUMMARY.md | PR overview |
| ARCHITECTURE.md | System design |
| TESTING_CHECKLIST.md | Test steps |
| FILE_MANIFEST.md | File changes |

---

## 🎯 Key Features

✅ Interactive Alaska map  
✅ 8 sample communities  
✅ Healthcare + connectivity data  
✅ Confidence tracking  
✅ Data completeness scores  
✅ Missing data handling  
✅ RESTful API  
✅ Auto-generated docs  

❌ No scoring/CAT logic  
❌ No authentication  
❌ No database (in-memory)  

---

## 💡 Tips

- Use API docs for testing: http://localhost:8000/api/docs
- Check browser console for errors
- Backend auto-reloads on file changes
- Frontend hot-reloads on file changes
- Data resets when backend restarts
- Marker colors = data completeness
- Hover badges for confidence info

---

## 📞 Support

1. Check SETUP.md troubleshooting
2. Review TESTING_CHECKLIST.md
3. Check browser console
4. Check terminal output
5. Verify both servers running

---

## 🚦 Status Indicators

| Indicator | Meaning |
|-----------|---------|
| Green marker | High data quality (75%+) |
| Yellow marker | Medium quality (50-75%) |
| Orange marker | Low quality (25-50%) |
| Gray marker | Limited quality (<25%) |
| Pulse animation | Selected community |

---

## ⚡ Performance

| Metric | Value |
|--------|-------|
| Backend startup | <1 second |
| API response | <50ms |
| Frontend load | ~2 seconds |
| Panel open | <300ms |
| Map render | ~500ms |

---

## 🔐 Security Note

**This is a prototype.**  
❌ No authentication  
❌ No rate limiting  
❌ CORS open to localhost  
❌ No input validation  

Do not use in production without security hardening.

---

## 📈 Data Coverage

8 communities with:
- Healthcare facilities: 100% coverage
- Connectivity metrics: 75% coverage  
- Access information: 100% coverage
- Population data: 100% coverage

---

**Last Updated:** January 7, 2026  
**Version:** 0.1.0  
**Status:** Prototype - Research Only
