# Contributing to TENeT

TENeT is a public-facing planning dashboard for Alaska telehealth access. Changes should keep the app reproducible, readable, and honest about missing or modeled data.

## Local Setup

```bash
cp .env.example .env
make dev
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:5001/api/health

The Docker workflow is the primary development path. It builds both services and seeds `backend/data/tenet.db` when the local database is missing.

## Before Opening a PR

Run the checks that match your change:

```bash
make backend-test      # backend logic and API tests
make frontend-test     # frontend component and hook tests
make frontend-build    # production build
make smoke             # lightweight running-app verification
```

For UI workflow changes, also run:

```bash
make e2e
```

`make e2e` expects the app to already be running at http://localhost:5173.

## PR Checklist

- Existing formulas are preserved unless the PR explicitly changes them.
- Missing API values remain `null`; UI/PDF labels render them as `Data unavailable`.
- Scenario outputs are clearly labeled as modeled estimates.
- Gap Hunter remains raw observed measurement data.
- New tests fill coverage gaps and do not duplicate existing tests for the same function or component behavior.
- Any new user-facing control has an accessible label or clear text.
- Docker startup still works from a fresh clone.

## Branch and Commit Guidance

Use short human-readable branch names that describe the work, for example:

- `testing-quality-gates`
- `deployment-docs`
- `scenario-e2e-smoke`

Keep commits grouped by behavior. Avoid mixing unrelated docs, UI, backend, and CI changes in one commit when they can be reviewed separately.

## Known Project Constraints

- SQLite is the current database and public demo data is seeded/read-only.
- The frontend should not duplicate backend data-quality logic.
- Scenario Mode must not mutate baseline TENeT data.
- Dynamic Weather API integration is a stretch item and should not be added without mentor approval.
