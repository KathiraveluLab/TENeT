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
│  In-Memory  │  8 Alaska Communities
│    Store    │  (Resets on restart)
└─────────────┘
```

📐 **Full architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📊 Sample Data

The system includes 8 representative Alaska communities:

| Community | Population | Type | Data Quality |
|-----------|------------|------|--------------|
| Anchorage | 291,247 | Major City | ⭐⭐⭐⭐⭐ |
| Juneau | 32,255 | State Capital | ⭐⭐⭐⭐⭐ |
| Bethel | 6,325 | Regional Hub | ⭐⭐⭐⭐ |
| Barrow | 4,927 | Remote Hub | ⭐⭐⭐⭐ |
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

**Example:**
```bash
curl http://localhost:8000/api/communities/AK-02185-0001 | jq
```

📚 **Interactive docs:** http://localhost:8000/api/docs

---

## 🎨 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Python 3.8+**

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Leaflet** - Interactive maps
- **react-leaflet** - React bindings

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SETUP.md](SETUP.md) | Complete setup guide with troubleshooting |
| [PR_SUMMARY.md](PR_SUMMARY.md) | Overview of this integration PR |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and data flows |
| [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) | Comprehensive testing guide |
| [FILE_MANIFEST.md](FILE_MANIFEST.md) | All files created/modified |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Quick reference card |

---

## 🧪 Testing

### Quick Test

```bash
# Backend health
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","communities_loaded":8}

# Frontend
open http://localhost:5173
# Click any marker → Panel should show data
```

### Full Testing
See [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) for comprehensive test suite.

---

## 🎯 Design Philosophy

### ✅ What This Project IS

- **Exploratory** - For research and discovery
- **Transparent** - Data quality explicitly tracked
- **Extensible** - Easy to add features
- **Honest** - Missing data clearly marked
- **Educational** - Demonstrates integration patterns

### ❌ What This Project IS NOT

- ~~A scoring system~~ - No feasibility calculations
- ~~A decision tool~~ - No policy recommendations  
- ~~Production-ready~~ - Prototype only
- ~~Complete~~ - Intentionally a foundation
- ~~Optimized~~ - Clarity over performance

---

## 🚧 Current Limitations

- **In-memory storage** - Data resets on server restart
- **No authentication** - Open API
- **Limited data** - Only 8 communities
- **No caching** - Fresh queries each time
- **Basic error handling** - Could be more robust
- **No tests** - Manual testing only

These are intentional for prototype phase.

---

## 🔮 Future Enhancements

### Near-term
- [ ] Add more Alaska communities (target: 50+)
- [ ] Integrate real OSM API for healthcare data
- [ ] Connect to FCC broadband database
- [ ] Add database layer (PostgreSQL + PostGIS)

### Medium-term
- [ ] Search and filter functionality
- [ ] Community comparison views
- [ ] Export to CSV/JSON
- [ ] Historical data tracking
- [ ] User authentication

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
