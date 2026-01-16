# TENeT: Telehealth Effectiveness & Necessity Tracker

> **Production-ready data integration pipeline for exploring healthcare access and connectivity in Alaska communities**

[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](http://localhost:8000/api/docs)
[![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB?style=flat&logo=react&logoColor=black)](http://localhost:5173)
[![Database](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite)](./backend/tenet.db)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## 🎯 Project Overview

TENeT is an enhanced research platform for visualizing and analyzing telehealth necessity across Alaska communities. It provides transparent insights into healthcare facilities, internet connectivity, and season-adjusted transportation access—with explicit tracking of data quality and completeness.

**New in v0.2 (Production Pipeline):**
- 📈 **20+ Communities** (up from 8) with real coordinates
- ❄️ **Season-Aware Analysis** (Summer/Winter/Year-Round)
- 🏥 **Healthcare Necessity Scoring** (0-100 scale)
- 💾 **SQLite Database** with SQLAlchemy ORM
- 🔍 **Search & Filter API** endpoints
- 📊 **Access Tier Classification** (1-3 tiers)

**This is a research tool with production-grade features.** It prioritizes transparency, scalability, and data quality awareness while supporting real-world deployment scenarios.

---

## ✨ Key Features

### 🗺️ Interactive Map with Season Awareness
- Alaska-wide visualization of 20+ communities
- Color-coded markers by access tier (1-3)
- Season toggle (Summer/Winter/Year-Round)
- Real-time access difficulty adjustments
- Click to explore detailed healthcare analysis

### 🏥 Healthcare Necessity Analysis
- **Necessity Score (0-100):** Data-driven telehealth need assessment
- Distance to nearest healthcare facility
- Local facility availability
- Season-adjusted travel difficulty
- Priority classification (CRITICAL/HIGH/MODERATE/LOW)

### ❄️ Season-Aware Access Scoring
- **Summer:** Water routes open, ice roads closed
- **Winter:** Ice roads accessible, increased isolation
- **Year-Round:** Conservative baseline (worst-case)
- Dynamic access multipliers by season
- Transport mode availability tracking

### 💾 Scalable Data Architecture
- SQLite database with SQLAlchemy ORM
- 20 communities loaded (easily scales to 100+)
- Healthcare facilities database-ready
- Broadband coverage tracking
- PostgreSQL migration path available

### 📊 Data Transparency
- Explicit confidence tracking (high/medium/low/missing)
- Source attribution for all data points
- Data completeness scores per community
- Raw values (no hidden algorithms)
- Missing data clearly labeled

### 🔍 Enhanced API
- `/api/communities/search` - Search and filter communities
- `/api/communities/stats` - Database statistics
- `/api/communities/{id}/necessity?season=winter` - Healthcare necessity
- Auto-generated API docs at `/api/docs`
- FastAPI performance and type safety

### 🔧 Developer Friendly
- Clean architecture with separation of concerns
- Comprehensive documentation (7 docs files)
- Hot reload on both frontend and backend
- SQLAlchemy ORM for easy database operations
- Production-ready deployment patterns

---

## 🚀 Quick Start

### One-Command Setup (macOS)

```bash
chmod +x start-dev.sh && ./start-dev.sh
```

This opens both servers in separate Terminal tabs.

### Manual Setup

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- API Docs: http://localhost:8000/api/docs

📖 **Detailed setup:** See [SETUP.md](SETUP.md)

---

## 📸 What You'll See

### Interactive Map with Season Selector
An Alaska map with 20+ community markers, featuring:
- 🟢 **Tier 1 (Green):** Well-connected communities (roads + airports)
- 🟡 **Tier 2 (Yellow):** Moderate access (airport + harbor)
- 🔴 **Tier 3 (Red):** Remote (air-only access)
- ❄️ **Season Toggle:** Switch between Summer/Winter/Year-Round views
- 📊 **Dynamic Updates:** Access scores adjust based on selected season

### Community Info Panel
Enhanced slide-in panel showing:
- **Data Completeness:** Progress bar with percentage
- **Healthcare Necessity:** 0-100 score with priority level
- **Access Tier:** Classification (1-3) with explanation
- **Nearest Facility:** Distance and facility type
- **Season Impact:** How winter/summer affects accessibility
- **Healthcare:** Facility count with confidence badge
- **Connectivity:** Speeds and latency with source
- **Access/Transport:** Available modes (air/water/road/ice)
- **Raw JSON:** Collapsible view for debugging

### API Documentation
Auto-generated interactive docs at `/api/docs`:
- Try out all endpoints directly in browser
- See request/response schemas
- Filter by season parameter
- Search and stats endpoints

---

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │  http://localhost:5173
└──────┬──────┘
       │
       │ API Calls
       ▼
┌─────────────┐
│   FastAPI   │  http://localhost:8000/api
│   Backend   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   SQLite    │  20 Alaska Communities
│  Database   │  (tenet.db - persistent)
└─────────────┘
```

📐 **Full documentation:** See [DATA_SOURCES.md](DATA_SOURCES.md)

---

## 📊 Sample Data

The system includes 8 representative Alaska communities:

| Community | Population | Type | Data Quality |
|-----------|------------|------|--------------|
| Anchorage | 291,247 | Major City | ⭐⭐⭐⭐⭐ |
| Juneau | 32,255 | State Capital | ⭐⭐⭐⭐⭐ |
| Bethel | 6,325 | Regional Hub | ⭐⭐⭐⭐ |
| Utqiaġvik (Barrow) | 4,927 | Remote Hub | ⭐⭐⭐⭐ |
| Nome | 3,699 | Coastal Hub | ⭐⭐⭐⭐ |
| Kotzebue | 3,102 | Northwest Hub | ⭐⭐⭐⭐ |
| Haines | 2,508 | Southeast Town | ⭐⭐⭐⭐⭐ |
| Napakiak | 378 | Small Village | ⭐⭐⭐ |

Data includes:
- Healthcare facilities (count, types, source)
- Internet speeds (download, upload, latency)
- Transportation methods
- Access seasonality
- Confidence levels for all metrics

---

## 🔍 API Endpoints

```bash
# List all communities (lightweight view)
GET /api/communities

# Search communities by name or filter by tier
GET /api/communities/search?q={query}&tier={1-3}

# Get community statistics
GET /api/communities/stats

# Get community details
GET /api/communities/{id}

# Get healthcare necessity score (season-aware)
GET /api/communities/{id}/necessity?season={summer|winter|year_round}

# Healthcare data only
GET /api/communities/{id}/healthcare

# Connectivity data only
GET /api/communities/{id}/connectivity

# Health check
GET /api/health
```

**Examples:**
```bash
# Get all communities
curl http://localhost:8000/api/communities | jq

# Search for Anchorage
curl http://localhost:8000/api/communities/search?q=anc | jq

# Get winter necessity score for Bethel
curl "http://localhost:8000/api/communities/bethel/necessity?season=winter" | jq

# Get statistics
curl http://localhost:8000/api/communities/stats | jq
```

📚 **Interactive docs:** http://localhost:8000/api/docs

---

## 🎨 Technology Stack

### Backend
- **FastAPI 0.115.6** - Modern Python web framework
- **SQLAlchemy 2.0.23** - ORM for database management
- **SQLite** - Lightweight database (tenet.db)
- **Pandas 2.1.4** - Data processing
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Python 3.8+**

### Frontend
- **React 18** - UI framework
- **Vite 5.4.21** - Build tool & dev server
- **Leaflet** - Interactive maps
- **react-leaflet** - React bindings
- **Custom CSS** - Green-themed UI

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DATA_SOURCES.md](DATA_SOURCES.md) | Complete data methodology and sources |
| [PR.md](PR.md) | Full pull request documentation |
| [backend/README.md](backend/README.md) | Backend setup guide |
| [frontend/README.md](frontend/README.md) | Frontend setup guide |

---

## 🧪 Testing

### Quick Test

```bash
# Backend health
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","communities_loaded":20}

# Test search
curl "http://localhost:8000/api/communities/search?q=anc" | jq

# Test stats
curl http://localhost:8000/api/communities/stats | jq

# Frontend
open http://localhost:5173
# 1. Click search → Should show all 20 communities
# 2. Type "anc" → Should filter to Anchorage
# 3. Click marker → Panel shows community details
# 4. Change season → Necessity score updates
# 5. Check stats panel → Shows tier distribution
```

### Full Testing
See [PR.md](PR.md) for comprehensive testing checklist.

---

## 🎯 Design Philosophy

### ✅ What This Project IS

- **Exploratory** - For research and discovery
- **Transparent** - Data quality explicitly tracked
- **Analytical** - Healthcare necessity scoring based on multiple factors
- **Extensible** - Easy to add features and communities
- **Honest** - Missing data clearly marked
- **Educational** - Demonstrates integration patterns
- **Season-aware** - Accounts for Alaska's unique seasonal challenges

### ❌ What This Project IS NOT

- ~~A prescriptive tool~~ - Scores inform, don't dictate policy
- ~~A decision engine~~ - Analysis only, no automated recommendations
- ~~Production-hardened~~ - Research/prototype quality
- ~~Comprehensive~~ - Intentionally a foundation for expansion
- ~~Real-time~~ - Static database, not live API integration

---

## 🚧 Current Limitations

- **No authentication** - Open API (appropriate for public data)
- **Limited dataset** - 20 communities (expandable to 100+)
- **No caching** - Fresh database queries each time
- **Basic spatial queries** - Bounding box filtering (could add PostGIS)
- **Manual testing** - No automated test suite yet
- **Single database file** - SQLite (sufficient for current scale)

These are intentional for prototype/research phase.

---

## 🔮 Future Enhancements

### Completed ✅
- [x] Database layer (SQLite with SQLAlchemy)
- [x] Expanded to 20 Alaska communities
- [x] Search and filter functionality
- [x] Season-aware analysis
- [x] Healthcare necessity scoring
- [x] Statistics dashboard

### Near-term
- [ ] Add more Alaska communities (target: 50+)
- [ ] Integrate real-time OSM API for healthcare data
- [ ] Connect to FCC broadband database API
- [ ] Upgrade to PostgreSQL + PostGIS for better spatial queries

### Medium-term
- [ ] Community comparison views (side-by-side)
- [ ] Export to CSV/PDF reports
- [ ] Historical data tracking
- [ ] User authentication for admin features
- [ ] Automated testing suite (unit + integration)
- [ ] Mobile-responsive optimizations

### Long-term
- [ ] Mobile app
- [ ] Real-time data updates
- [ ] Machine learning for data quality prediction
- [ ] Integration with telehealth platforms

---

## 🤝 Contributing

This is a research project. Contributions should maintain the core philosophy:

1. **Transparency first** - Always show data confidence
2. **No inference** - Raw values only
3. **Extensible design** - Keep it modular
4. **Document everything** - Code + docs together

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

### Data Sources
- **OpenStreetMap** - Healthcare facility data
- **FCC** - Broadband availability data
- **Public domain** - Alaska geographic data

### Technologies
- FastAPI, React, Leaflet, and all open source dependencies

---

## 📞 Support

### Getting Help

1. Check [SETUP.md](SETUP.md) troubleshooting section
2. Review [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
3. Look at browser console for errors
4. Check terminal output for backend logs
5. Try the [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### Common Issues

**Backend won't start:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend can't connect:**
- Ensure backend is running on port 8000
- Check `.env` file has correct API URL
- Verify no CORS errors in console

**No markers on map:**
- Check browser console for errors
- Verify `/api/communities` endpoint works:
  ```bash
  curl http://localhost:8000/api/communities
  ```

---

## 🎓 Educational Value

This project demonstrates:

- **Full-stack integration** (FastAPI + React)
- **RESTful API design**
- **Data quality tracking**
- **Geographic visualization**
- **React component architecture**
- **State management**
- **Error handling patterns**
- **Documentation practices**

Perfect for:
- Learning full-stack development
- Understanding data transparency
- GSoC applications
- Research projects
- Portfolio pieces

---

## 📊 Project Status

**Version:** 0.1.0  
**Status:** Prototype / Research Phase  
**Last Updated:** January 7, 2026  

**What Works:**
- ✅ Backend API serving 8 communities
- ✅ Frontend map with interactive markers
- ✅ Community info panel
- ✅ Confidence tracking
- ✅ Data completeness indicators

**Known Issues:**
- ⚠️ Data resets on backend restart (no persistence)
- ⚠️ Limited to 8 communities
- ⚠️ No authentication
- ⚠️ No automated tests

---

## 🌟 Why TENeT?

Alaska presents unique challenges for healthcare access:
- **Geographic isolation** - Many communities accessible only by air
- **Connectivity gaps** - Limited broadband in rural areas
- **Seasonal access** - Some locations only reachable part of the year
- **Healthcare scarcity** - Few facilities in remote regions

TENeT helps visualize these challenges with real data, explicit uncertainty, and a foundation for future analysis.

---

**Made with** ❤️ **for rural healthcare research**

---

## 🔗 Quick Links

- 🌐 [Frontend](http://localhost:5173)
- 🔌 [Backend API](http://localhost:8000/api)
- 📖 [API Docs](http://localhost:8000/api/docs)
- 📋 [Setup Guide](SETUP.md)
- 🎯 [Quick Reference](QUICK_REFERENCE.md)

---

*This project is part of research into telehealth viability assessment. It is not a medical tool and makes no claims about healthcare outcomes or recommendations.*
