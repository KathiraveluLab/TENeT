# TENeT: Telehealth Effectiveness and Necessity Tracker

An interactive geospatial tool that maps telehealth readiness across **421 Alaska communities** by combining real-world data on transportation access, broadband connectivity, healthcare proximity, and affordability — adjusted for Alaska's extreme seasonal conditions.

TENeT helps state administrators, healthcare network planners, and researchers answer two critical questions:
- **Where does telehealth actually reach the people who need it most?**
- **Where should providers expand telehealth access next?**

---

## What It Does

- Classifies every Alaska community into a **CAT (Community Access Tier)** from 1 (road-connected, well-served) to 4 (fly-in only, critically underserved)
- Calculates a **Healthcare Desert Score** (0–100) based on facility distance, provider density, specialist availability, and seasonal transport disruptions
- Compares **FCC-claimed broadband speeds vs. Ookla-measured speeds** to expose the real connectivity gap
- Scores **internet affordability** as a percentage of local median household income
- Adjusts all metrics for **summer vs. winter** — because roads freeze, rivers close, and access changes dramatically

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Leaflet, Vite |
| Backend | Flask 3.0 (Python) |
| Database | SQLite with SQLAlchemy ORM |
| Map | OpenStreetMap |

---

## Project Structure

```
TENeT/
├── frontend/               # React app — interactive Alaska map
│   └── src/
│       ├── api/            # API client layer
│       ├── components/     # Map layers, legends, selectors, popups
│       └── types/          # TypeScript type definitions
│
└── backend/                # Flask API (Port 5001)
    ├── data/
    │   ├── raw/            # Source datasets (transport, broadband, healthcare)
    │   ├── processed_data/ # Cleaned & merged CSVs
    │   └── scripts/        # Data preprocessing pipelines
    ├── database/           # Models, seeders, handlers
    ├── routes/             # API endpoints
    └── services/           # Business logic (desert scoring, season adjustments)
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+

### Quick Start

```bash
# Backend
cd backend
pip3 install -r requirements.txt
python3 app.py                    # → http://localhost:5001

# Frontend (new terminal)
cd frontend
npm install
npm run dev                       # → http://localhost:5173
```

---

## Data Sources

| Dataset | Source | Coverage |
|---------|--------|----------|
| Transportation | Alaska DOT&PF | 421 communities — road, air, water access profiles |
| Broadband | FCC National Broadband Map | 354 communities — coverage, speeds, ISP data |
| Healthcare | OpenStreetMap (Overpass Turbo) | 325 facilities — hospitals, clinics, pharmacies |
| Affordability | ZCTA income data + ISP pricing | Cost burden as % of household income |

---

## Upcoming Features

- **Dockerization** — Single-command setup with `docker-compose` for easy deployment and onboarding
- **Sidebar Navigation & Search** — Filterable community list with autocomplete search and map fly-to
- **PDF Report Export** — One-click downloadable region summary for grant applications and policy briefs
- **Region Comparison** — Side-by-side metric comparison of 2–3 communities
- **What-If Scenario Sliders** — Model broadband, clinic proximity, and affordability changes in real time
- **Shareable URLs** — Bookmarkable links that preserve selected region, season, and map state
- **Full Test Suite & CI/CD** — Backend unit tests, frontend component tests, and GitHub Actions pipeline
- **Cloud Deployment** — Live public URL for stakeholder access

