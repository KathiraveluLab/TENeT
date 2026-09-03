# TENeT — Telehealth Effectiveness & Necessity Tracker

TENeT is an interactive decision-support platform for understanding where telehealth can work in Alaska—and where people face the greatest barriers to care. It brings together community access, broadband availability and affordability, measured network performance, healthcare infrastructure, and seasonal travel conditions in one map-based workspace.

It is built for public-sector planners, healthcare organizations, broadband providers, researchers, and community advocates who need to prioritize telehealth investment with transparent, place-level evidence.

## What TENeT provides

- A statewide map of Alaska communities, with season-aware access context.
- Community search, filtering, sorting, selection, and pinning for comparison.
- Community Access Tier (CAT) and telehealth-status views.
- **Gap Hunter**, which displays observed Ookla network-performance data and highlights connectivity gaps.
- An affordability view that relates estimated internet costs to local income.
- Research profiles that combine access, connectivity, healthcare, affordability, and data-quality signals for a community.
- Downloadable PDF community reports and shareable map URLs.
- A statewide insights dashboard covering telehealth status, healthcare, performance, affordability, and data quality.
- **Scenario Mode** for testing broadband, latency, clinic-proximity, and affordability assumptions without changing baseline data.

## Quick start

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) with Docker Compose v2
- Git

### Run the full stack

```bash
git clone https://github.com/KathiraveluLab/TENeT.git
cd TENeT
git checkout dev

cp .env.example .env
make dev
```

`make dev` builds the containers, creates and seeds the local SQLite database when needed, then starts both services.

Open:

- Frontend: http://localhost:5173
- Backend health check: http://localhost:5001/api/health
- Backend readiness check: http://localhost:5001/api/ready

To stop the application, run `make stop`.

## How to use the application

1. Start on the map and use the left sidebar to find a community by name or refine the list by access tier, telehealth status, healthcare need, or data confidence.
2. Select a community to inspect its evidence, including access conditions, affordability, healthcare proximity, and data-quality notes.
3. Pin up to three communities to compare their research profiles side by side.
4. Switch between map views:
   - **CAT** shows community access tiers and baseline telehealth context.
   - **Gap Hunter** shows observed Ookla performance measurements and service gaps.
   - **Affordability** focuses on estimated internet burden and access conditions.
   - **Scenario Mode** shows modeled classifications under user-selected assumptions.
5. Open **Statewide Insights** for aggregate evidence and links back to the relevant map view or community.
6. Download a PDF report or copy the shareable URL to preserve the current map state, selected community, season, pins, and scenario settings.

## Interpreting the evidence

TENeT keeps baseline evidence and modeled analysis separate.

### Baseline telehealth status

Baseline classifications are calculated from the project's canonical telehealth-classification service. A community may be shown as:

| Status | Meaning |
| --- | --- |
| Telehealth Ready | Video-capable broadband and affordable home access meet the baseline inputs. |
| Community Anchor | Home access is not ready, but a nearby clinic provides a care-access safety net. |
| Critical Gap | Home access is not ready and no clinic is accessible within the applicable threshold. |
| Data Unavailable | Required classification inputs are missing. |

Community Access Tiers describe transport and service-access conditions:

| Tier | Meaning |
| --- | --- |
| 1 | Full multimodal access |
| 2 | Dual-mode access |
| 3 | Limited access |
| 4 | Extreme or no direct access |

Season selection adjusts the transport context used throughout the map, sidebar, summaries, and classification views.

### Observed performance vs. scenarios

**Gap Hunter** is an observed-data view. It uses Ookla measurements and should not be read as a simulated result.

**Scenario Mode** is a planning tool. It lets users adjust download, upload, latency, clinic-proximity, and affordability thresholds, then compares the resulting modeled status with the baseline. It does not modify database records, report measured infrastructure changes, or replace observed data.

## Data and methodology

The local seed workflow combines checked-in project data for:

- Community access and transport profiles
- Healthcare facilities and healthcare-access calculations
- Broadband coverage and data-gap indicators
- Local Census income records for affordability analysis
- A small offline sample of real Ookla Open Data tiles for useful first-run network-performance context

The checked-in Ookla sample keeps a fresh, offline installation useful. For broader performance coverage, ingest an appropriate Ookla dataset with `backend/data/scripts/ingest_ookla.py`, then reseed or refresh the database as needed.

Data availability is part of the product: missing or low-confidence inputs are shown explicitly rather than treated as evidence of access or need.

## Architecture

- **Frontend:** React, TypeScript, Vite, React Leaflet, and Leaflet
- **Backend:** Flask, SQLAlchemy, Gunicorn, and SQLite
- **Operations:** Docker, Docker Compose, nginx, and GitHub Actions
- **Testing:** pytest, Vitest/React Testing Library, and Playwright

The frontend is served by nginx in the Docker stack and proxies `/api/cat` to the Flask backend. The backend exposes liveness and database-readiness health checks, while the local database is seeded deterministically from tracked data.

## Repository layout

```text
TENeT/
├── frontend/                 React application, map UI, reports, and E2E tests
├── backend/
│   ├── routes/               CAT and network-performance API routes
│   ├── services/             Classification, profiles, scenarios, and data logic
│   ├── database/             Models, initialization, and seeders
│   ├── data/                 Tracked inputs, samples, and ingestion scripts
│   └── tests/                Backend unit and API tests
├── docker-compose.yml        Local multi-container stack
├── Makefile                  Development, test, and maintenance commands
├── CONTRIBUTING.md           Contribution workflow
├── TESTING.md                Test strategy and checks
└── DEPLOY.md                 Deployment guidance
```

## API overview

All application endpoints, except health checks, are under `/api/cat`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Process liveness check |
| `GET /api/ready` | Database-readiness check |
| `GET /api/cat/regions` | Community access-tier data, optionally by season or tier |
| `GET /api/cat/regions/summary` | Lightweight community summaries for the sidebar |
| `GET /api/cat/regions/search` | Filtered community discovery |
| `GET /api/cat/regions/<region_code>/research-profile` | Consolidated community research profile |
| `GET /api/cat/regions/research-profiles` | Profiles for pinned-community comparison |
| `GET /api/cat/telehealth-status/all` | Statewide baseline telehealth classifications |
| `GET /api/cat/performance` | Observed Ookla performance tiles |
| `GET /api/cat/performance/gaps` | Network service-gap analysis |
| `GET /api/cat/performance/affordability` | Broadband affordability analysis |
| `GET /api/cat/healthcare/summary` | Healthcare infrastructure summary |
| `POST /api/cat/scenarios/preview` | Non-persistent scenario analysis |

Explore the frontend API clients in `frontend/src/api/` and the backend route implementations in `backend/routes/` for request parameters and response shapes.

## Development commands

| Command | Description |
| --- | --- |
| `make dev` | Build, seed if necessary, and start the full application |
| `make stop` | Stop the running stack |
| `make build` | Rebuild images without cache |
| `make seed` | Initialize and seed the SQLite database |
| `make reset-db` | Remove the local database and seed it again |
| `make test` | Run backend and frontend test suites |
| `make backend-test` | Run pytest in the backend container |
| `make frontend-test` | Run the Vitest suite |
| `make frontend-typecheck` | Run TypeScript checks |
| `make frontend-build` | Build the production frontend |
| `make docker-build` | Build backend and frontend images |
| `make e2e` | Run Playwright smoke tests against a running app |
| `make smoke` | Check Compose config, frontend build, and core live API routes |
| `make logs` | Tail Compose service logs |
| `make clean` | Remove local containers, volumes, and images |

Run `make help` to list the available targets. `make clean` and `make reset-db` remove local Docker or SQLite state; use them only when that reset is intended.

## Configuration

Copy `.env.example` to `.env` before starting the stack. Common options are:

| Variable | Default | Description |
| --- | --- | --- |
| `BACKEND_PORT` | `5001` | Backend host port |
| `FRONTEND_PORT` | `5173` | Frontend host port |
| `DB_PATH` | `/app/data/tenet.db` | SQLite path inside the backend container |
| `FLASK_DEBUG` | `0` | Enable only for local debugging |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated allowed cross-origin frontend URLs |
| `VITE_API_BASE_URL` | `/api/cat` | API base embedded in the frontend build |
| `WEB_CONCURRENCY` | `2` | Gunicorn worker count |
| `GUNICORN_THREADS` | `4` | Threads per Gunicorn worker |

For the checked-in Docker and nginx setup, leave `VITE_API_BASE_URL` at `/api/cat` and leave `CORS_ALLOWED_ORIGINS` empty. Set an explicit CORS allowlist only when the frontend is served from a different origin.

## Quality and deployment

GitHub Actions runs backend tests, frontend type checks, frontend tests, production builds, Docker build validation, and Playwright smoke coverage for pull requests. See [TESTING.md](./TESTING.md) for the full test strategy and [DEPLOY.md](./DEPLOY.md) for production deployment, readiness checks, and rollback guidance.

## Limitations

- TENeT is a planning and decision-support tool; it is not a clinical service or a substitute for local community consultation.
- Public-demo data is seeded into SQLite and should be treated as read-only.
- Network coverage and performance are incomplete where measurements are absent; missing data is not proof of adequate service.
- Scenario results are modeled estimates, not observed outcomes or predictions.
- Weather data is not part of the core application workflow.

