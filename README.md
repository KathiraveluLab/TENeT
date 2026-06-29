# TENeT - Telehealth Effectiveness & Necessity Tracker

> **No Alaskan family should be left in a healthcare desert simply because of where they live.**

TENeT is an interactive map-based tool that shows - community by community - where telehealth can actually work in Alaska and where it can't. It pulls together real data on roads, broadband, healthcare facilities, and affordability, then adjusts everything for Alaska's brutal seasonal swings so decision-makers get the full picture.

Built for **state administrators, healthcare planners, ISPs, and researchers** who need honest answers to two questions:

1. **Where does telehealth actually reach the people who need it most?**
2. **Where should we expand access next?**

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)

### Setup

```bash
git clone https://github.com/KathiraveluLab/TENeT.git
cd TENeT

cp .env.example .env
make dev
```

That's it. Open:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5001
- **Health check:** http://localhost:5001/api/health

`make dev` builds the containers, creates `backend/data/tenet.db` if it is missing,
seeds local development data, and starts the backend plus frontend together.

### Useful Commands

| Command | What it does |
|---------|-------------|
| `make dev` | Build, seed if needed, and start the full stack |
| `make stop` | Stop all containers |
| `make down` | Alias for `make stop` |
| `make build` | Rebuild containers without cache |
| `make seed` | Seed the database with local CAT, healthcare, broadband, income, and performance data |
| `make reset-db` | Delete and re-seed the database |
| `make test` | Run backend pytest and frontend Vitest |
| `make backend-test` | Run only backend pytest |
| `make frontend-test` | Run only frontend Vitest |
| `make frontend-build` | Run the frontend production build |
| `make frontend-typecheck` | Run TypeScript checks |
| `make docker-build` | Build backend and frontend Docker images |
| `make e2e` | Run Playwright smoke tests against a running app |
| `make smoke` | Run lightweight deployment smoke checks |
| `make logs` | Tail container logs |
| `make clean` | Remove containers, volumes, and images |
| `make help` | Show all available commands |

### Database Workflow

The local SQLite database lives at `backend/data/tenet.db` by default and is not
committed. The seed workflow is deterministic and works without private files or
external API keys:

```bash
make seed      # create or refresh local seed data
make reset-db  # remove backend/data/tenet.db, then seed from scratch
```

Seeded data includes:

- CAT community regions and access data from `backend/data/processed_data/clean_transport_profiles_1.csv`
- Healthcare facilities from `backend/data/processed_data/healthcare_facilities.csv`
- Broadband coverage from `backend/data/processed_data/broadband_data_gaps.csv`
- Local sample Census income records for affordability workflows
- Local sample Ookla-like performance records for the performance layer

### Environment

Start from the checked-in template:

```bash
cp .env.example .env
```

Common local variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_PORT` | `5001` | Host port for Flask |
| `FRONTEND_PORT` | `5173` | Host port for Vite |
| `FLASK_HOST` | `0.0.0.0` | Backend bind address inside Docker |
| `FLASK_PORT` | `5001` | Backend container port |
| `FLASK_DEBUG` | `1` | Flask debug mode for local Docker |
| `DB_PATH` | `/app/data/tenet.db` | SQLite path inside the backend container |
| `VITE_API_BASE_URL` | `/api/cat` | Frontend API base URL proxied by nginx in Docker |
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated frontend origins allowed by the API |

### Troubleshooting

If the map loads but has no markers, run:

```bash
make reset-db
make dev
```

If ports are already in use, change `BACKEND_PORT` or `FRONTEND_PORT` in `.env`.
If dependencies look stale, run `make clean` and then `make dev`.

### Local Development (without Docker)

<details>
<summary>Click to expand</summary>

**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev
```

</details>

---

## What It Does

| Feature | What you see on the map |
|---------|------------------------|
| **Community Access Tiers (CAT)** | Every community is color-coded by its Telehealth Need Score (0-100) - a composite of healthcare access gaps, broadband quality, transport limitations, and seasonal effects |
| **Healthcare Desert Score (0–100)** | How far people are from clinics, how many providers exist nearby, whether specialists are reachable, and how transport disruptions make things worse |
| **Broadband Reality Check** | Side-by-side comparison of FCC-claimed speeds vs. Ookla-measured speeds - exposing the real connectivity gap |
| **Internet Affordability** | Monthly broadband cost as a percentage of local household income - because 25 Mbps means nothing if no one can afford it |
| **Seasonal Adjustment** | Toggle between summer and winter to see how access changes when roads freeze and rivers shut down |
| **Sidebar Discovery** | Search, filter, sort, pin, and inspect communities without moving heavy map geometry |
| **Research Reports** | Download community PDF summaries with safe missing-data labels |
| **Region Comparison** | Compare 2–3 pinned communities side by side |
| **Shareable URLs** | Restore selected region, layer, season, pins, map view, and scenario state |
| **What-If Scenarios** | Model broadband, clinic proximity, and affordability thresholds without changing baseline data |

---

## Tech Stack

| Layer | What we use |
|-------|-------------|
| **Frontend** | React 18 · TypeScript · Leaflet · Vite |
| **Backend** | Flask 3.0 · Python |
| **Database** | SQLite · SQLAlchemy ORM |
| **Maps** | OpenStreetMap tiles via Leaflet |
| **Infra** | Docker · Docker Compose |

---

## Project Structure

```
TENeT/
├── docker-compose.yml           → Single-command startup
├── Makefile                     → Developer shortcuts
├── .env.example                 → Environment template
│
├── frontend/                    → React app (the interactive Alaska map)
│   ├── Dockerfile
│   └── src/
│       ├── api/                 → Talks to the backend
│       ├── components/          → Map layers, legends, popups, controls
│       └── types/               → TypeScript definitions
│
└── backend/                     → Flask API server (port 5001)
    ├── Dockerfile
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

## Key API Endpoints

| Endpoint | What it returns |
|----------|-----------------|
| `GET /api/cat/regions?season=summer` | All communities with tier levels, adjusted for season |
| `GET /api/cat/regions/summary` | Lightweight sidebar community summaries without geometry |
| `GET /api/cat/regions/search` | Search/filter community summaries |
| `GET /api/cat/regions/<region_code>/research-profile` | Export-ready profile for one community |
| `GET /api/cat/regions/research-profiles` | Batch profiles for pinned comparison |
| `POST /api/cat/scenarios/preview` | Modeled scenario preview for selected thresholds |
| `GET /api/cat/telehealth-priority` | Telehealth priority rankings per community |
| `GET /api/cat/performance` | Measured broadband speeds (Ookla data) |
| `GET /api/cat/affordability` | Internet cost burden per community |
| `GET /api/health` | Backend health check: `{"status":"ok","service":"tenet-api"}` |

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

## Quality, Deployment, and Contribution Docs

- [Testing guide](./TESTING.md) - backend, frontend, E2E, smoke, accessibility, and performance checks
- [Deployment guide](./DEPLOY.md) - public demo deployment with seeded SQLite data
- [Contribution guide](./CONTRIBUTING.md) - local workflow and PR checklist

## Known Limitations

- Scenario Mode shows modeled estimates based on selected thresholds. It does not represent observed ground truth and does not modify baseline data.
- Gap Hunter remains raw observed measurement data and is not recolored by Scenario Mode.
- Public demo deployments use deterministic seeded SQLite data and should not depend on local untracked database files.
- Dynamic Weather API integration is a stretch exploration item only unless mentors approve implementation.

---

## License

See [LICENSE](./LICENSE) for details.
