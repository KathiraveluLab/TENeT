# TENeT - Telehealth Effectiveness & Necessity Tracker

> **No Alaskan family should be left in a healthcare desert simply because of where they live.**

TENeT is an interactive map-based tool that shows - community by community - where telehealth can actually work in Alaska and where it can't. It pulls together real data on roads, broadband, healthcare facilities, and affordability, then adjusts everything for Alaska's brutal seasonal swings so decision-makers get the full picture.

Built for **state administrators, healthcare planners, ISPs, and researchers** who need honest answers to two questions:

1. **Where does telehealth actually reach the people who need it most?**
2. **Where should we expand access next?**

---

## Why This Exists

Alaska has over 400 scattered communities. Many are fly-in only. Roads freeze. Rivers close. Broadband coverage that looks great on an FCC map often doesn't match reality on the ground. Hospitals can be hundreds of miles away.

TENeT connects all these dots into a single view so you can see which communities are well-served, which are struggling, and which are in genuine crisis - without digging through a dozen spreadsheets.

---

## What It Does

| Feature | What you see on the map |
|---------|------------------------|
| **Community Access Tiers (CAT)** | Every community is color-coded by its Telehealth Need Score (0-100) - a composite of healthcare access gaps, broadband quality, transport limitations, and seasonal effects |
| **Healthcare Desert Score (0–100)** | How far people are from clinics, how many providers exist nearby, whether specialists are reachable, and how transport disruptions make things worse |
| **Broadband Reality Check** | Side-by-side comparison of FCC-claimed speeds vs. Ookla-measured speeds - exposing the real connectivity gap |
| **Internet Affordability** | Monthly broadband cost as a percentage of local household income - because 25 Mbps means nothing if no one can afford it |
| **Seasonal Adjustment** | Toggle between summer and winter to see how access changes when roads freeze and rivers shut down |

---

## Tech Stack

| Layer | What we use |
|-------|-------------|
| **Frontend** | React 18 · TypeScript · Leaflet · Vite |
| **Backend** | Flask 3.0 · Python |
| **Database** | SQLite · SQLAlchemy ORM |
| **Maps** | OpenStreetMap tiles via Leaflet |

---

## Project Structure

```
TENeT/
├── frontend/                    → React app (the interactive Alaska map)
│   └── src/
│       ├── api/                 → Talks to the backend
│       ├── components/          → Map layers, legends, popups, controls
│       └── types/               → TypeScript definitions
│
└── backend/                     → Flask API server (port 5001)
    ├── routes/                  → API endpoints (regions, performance, affordability)
    ├── services/                → Core logic (desert scoring, season adjustments)
    ├── database/                → Models, seeders, DB config
    ├── config/                  → ISP pricing & thresholds
    └── data/
        ├── raw/                 → Original source datasets
        ├── processed_data/      → Cleaned CSVs ready for the database
        └── scripts/             → Data preprocessing pipelines
```

---

## Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9 or higher |
| Node.js | 18 or higher |
| npm | comes with Node.js |

### 1. Clone the repo and switch to the development branch

```bash
git clone https://github.com/KathiraveluLab/TENeT.git
cd TENeT
git checkout experimental-dakshhhhh16
```

> **Note:** All active development lives on the `experimental-dakshhhhh16` branch. The `main` branch may not have the latest features.

### 2. Start the backend

```bash
cd backend
pip3 install -r requirements.txt
python3 app.py
```

The API will be live at **http://localhost:5001**. You should see:

```
Database initialized successfully
Starting TENeT Backend on http://localhost:5001
```

### 3. Start the frontend (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

The app will be live at **http://localhost:5173**. Open it in your browser and the Alaska map loads automatically.

### 4. Verify it works

Open **http://localhost:5001/api/health** in your browser. You should see:

```json
{ "status": "ok", "message": "TENeT Backend is running" }
```

---

## Key API Endpoints

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/cat/regions?season=summer` | All communities with tier levels, adjusted for season |
| `GET /api/cat/telehealth-priority` | Telehealth priority rankings per community |
| `GET /api/cat/performance` | Measured broadband speeds (Ookla data) |
| `GET /api/cat/affordability` | Internet cost burden per community |
| `GET /api/health` | Backend health check |

---

## Data Sources

| Dataset | Source | What it covers |
|---------|--------|----------------|
| Transportation | Alaska DOT&PF | 421 communities - road, air, and water access profiles |
| Broadband | FCC National Broadband Map | 354 communities - coverage claims, ISP data |
| Broadband (measured) | Ookla Speedtest | Real-world download/upload speeds and latency |
| Healthcare | OpenStreetMap (Overpass Turbo) | 325 facilities - hospitals, clinics, pharmacies |
| Affordability | ZCTA Census income + ISP pricing | Cost burden as % of household income |

---

## How Scoring Works

### Healthcare Desert Score (0–100)

| Range | Meaning |
|-------|---------|
| 0–30 | Good access - clinics are nearby, multiple providers |
| 31–50 | Moderate challenges - some distance or limited specialists |
| 51–70 | Significant desert - far from facilities, few options |
| 71–100 | Severe desert - high telehealth priority, urgent need |

The score factors in distance to the nearest clinic, provider density, specialist availability, and seasonal transport friction.

### Community Access Tiers (CAT)

Each community is assigned a transport tier (1-4) based on available access modes (road, air, water). This tier is one input into the overall Telehealth Need Score - it is not the score itself.

| Tier | Transport Access Mode |
|------|----------------------|
| 1 | Full multimodal access - road plus at least one other mode |
| 2 | Dual mode without year-round road (e.g. air + water) |
| 3 | Single mode only (air only, road only, or water only) |
| 4 | No direct scheduled access - charter or seasonal only |

The transport tier feeds into the Telehealth Need Score alongside healthcare desert metrics, broadband quality, and affordability. The seasonal toggle adjusts the score by increasing the transport penalty for communities where winter cuts off road or water routes.

---

## Upcoming Features

- **Docker Setup** - One-command launch with `docker-compose`
- **Sidebar Search** - Find any community by name, fly-to on map
- **PDF Reports** - One-click downloadable summaries for grant applications
- **Region Comparison** - Compare 2–3 communities side by side
- **What-If Sliders** - Model "what happens if broadband improves here?"
- **Shareable URLs** - Bookmark and share specific map views
- **CI/CD Pipeline** - Automated tests via GitHub Actions
- **Cloud Deployment** - Public URL for direct stakeholder access

---


