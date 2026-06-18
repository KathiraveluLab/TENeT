# TENeT Deployment Guide

This guide describes a public demo deployment for TENeT. The app should not depend on a local laptop database or untracked files.

## Deployment Decision

For the public demo, SQLite is treated as read-only seeded data.

Use one of these reproducible strategies:

1. Run the deterministic seed command during deployment startup/build.
2. Ship a stable seeded database artifact produced by the same seed workflow.

Do not deploy by copying an untracked local `backend/data/tenet.db` from a developer machine.

## Recommended Shape

- Backend: Dockerized Flask API web service.
- Frontend: static Vite build served by a static host.
- Frontend API base URL points to the deployed backend.
- Backend CORS allows the deployed frontend origin.

This can be hosted on common student-friendly platforms such as Render, Vercel, Fly.io, Railway, or a university-provided container host. Confirm platform and free-tier constraints with mentors before final deployment.

## Required Environment Variables

Backend:

| Variable | Example | Purpose |
|----------|---------|---------|
| `FLASK_DEBUG` | `0` | Disable debug mode in production |
| `FLASK_HOST` | `0.0.0.0` | Bind inside the container |
| `FLASK_PORT` | platform-provided or `5001` | API port |
| `DB_TYPE` | `sqlite` | Current database backend |
| `DB_PATH` | `/app/data/tenet.db` | SQLite path inside backend container |
| `CORS_ALLOWED_ORIGINS` | `https://tenet.example.org` | Comma-separated frontend origins |

Frontend:

| Variable | Example | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `https://tenet-api.example.org/api/cat` | Deployed CAT API base URL |

## Backend Deployment Steps

1. Build the backend Docker image from `backend/Dockerfile`.
2. Set production environment variables.
3. Seed the database if the deployed DB path is empty:

   ```bash
   python -c "from database.init_db import main; main()"
   ```

4. Start the API:

   ```bash
   python app.py
   ```

5. Verify:

   ```bash
   curl -fsS https://<backend-host>/api/health
   ```

Expected response:

```json
{
  "status": "ok",
  "service": "tenet-api"
}
```

## Frontend Deployment Steps

1. Set `VITE_API_BASE_URL` to the deployed backend CAT API base.
2. Install dependencies:

   ```bash
   npm ci
   ```

3. Build:

   ```bash
   npm run build
   ```

4. Serve the `frontend/dist` directory as a static site.
5. Open the live frontend and verify the map loads communities.

## Smoke Test Checklist

- Backend health returns `status: ok`.
- `/api/cat/regions/summary` returns communities.
- Frontend loads without console-breaking API errors.
- Search/sidebar works.
- PDF export downloads a report.
- Comparison panel opens with pinned communities.
- Shareable URL reload restores state.
- Scenario Mode opens and updates the impact summary.
- Gap Hunter still displays observed data.

## Rollback

If deployment fails:

1. Revert to the previous platform deployment.
2. Confirm the backend health endpoint.
3. Confirm `VITE_API_BASE_URL` points to the working API.
4. Re-run the seed command only if the database path is empty or intentionally reset.

## Known Limitations

- Free-tier services may cold start.
- SQLite public demo data is seeded/read-only.
- Scenario Mode is modeled analysis, not observed field data.
- Gap Hunter remains raw observed measurement data.
- Weather API integration is not part of core Phase 5 deployment unless mentors approve it.
