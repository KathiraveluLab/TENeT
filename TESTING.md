# TENeT Testing Guide

TENeT uses layered testing: unit tests for formulas, integration tests for API contracts, component tests for UI behavior, Playwright smoke tests for full journeys, and CI checks for repeatability.

## Test Coverage Audit

Before adding new tests, check existing coverage so we do not duplicate the same behavior:

- Backend formula tests: affordability and healthcare desert calculations.
- Backend API tests: discovery, research profiles, scenario preview, cache behavior.
- Frontend tests: sidebar discovery, legends/tooltips, missing-data labels.

New tests should cover gaps or distinct edge cases only.

## Local Commands

The Docker workflow should match CI as closely as possible.

```bash
make backend-test       # pytest in the backend Docker environment
make frontend-test      # Vitest in the frontend Docker environment
make test               # backend + frontend tests
make frontend-build     # production frontend build
make frontend-typecheck # TypeScript typecheck
make docker-build       # Docker image build checks
make smoke              # lightweight running-app smoke checks
make e2e                # Playwright smoke suite against a running app
```

`make smoke` expects the backend to be running at `http://127.0.0.1:5001` unless `API_URL` is overridden.

## Backend Testing

Backend tests should verify:

- `/api/health` returns:

  ```json
  {
    "status": "ok",
    "service": "tenet-api"
  }
  ```

- Summary/search endpoints avoid heavy geometry.
- Invalid filters do not crash.
- Missing values remain `null` in API responses.
- Research profiles include data quality and missing-field metadata.
- Scenario default thresholds preserve baseline statuses.
- Scenario cache behavior is tested functionally, not with strict timing.
- Season behavior uses fixed known communities instead of asserting every community changes.

Avoid brittle timing assertions such as "must respond under 50ms."

## Frontend Testing

Vitest/React Testing Library should cover:

- Sidebar search, filters, sort, reset, selection, and pinning.
- Missing data renders as `Data unavailable`, `Unknown`, or `Data incomplete`.
- PDF report generation does not emit blank/null/undefined fields.
- Shareable URL state serializes/restores scenario parameters.
- Comparison math and best/worst labels.
- Scenario panel off/calculating/active states.
- Gap Hunter remains observed data and unaffected by Scenario Mode.

## Playwright E2E Smoke

Playwright tests live under `frontend/e2e`.

The smoke suite verifies:

- Search -> select community -> download PDF.
- Scenario slider -> impact summary -> shareable URL params.
- Pin communities -> comparison panel opens.

PDF E2E checks only that a download is triggered, the file is non-empty, and the filename is reasonable. Detailed PDF content belongs in unit/component tests.

Use stable selectors for E2E:

- `data-testid="community-search"`
- `data-testid="sidebar-result"`
- `data-testid="download-report"`
- `data-testid="comparison-panel"`
- `data-testid="scenario-button"`
- `data-testid="scenario-summary"`
- `data-testid="copy-share-link"`

## Accessibility Smoke Checks

TENeT does not claim full WCAG certification, but the final app should pass basic checks:

- Important statuses are not color-only.
- Buttons have accessible labels.
- Sidebar controls are keyboard reachable.
- Scenario controls are keyboard reachable.
- PDF/share/comparison buttons are readable by screen readers where practical.

## Performance Sanity Checks

Do not add strict benchmarks in CI. Instead verify obvious regressions:

- Sidebar search remains responsive with all communities.
- Scenario slider debounce prevents excessive API calls.
- PDF generation does not freeze the UI for normal reports.
- Comparison panel remains usable with 3 pinned communities.

## CI Expectations

GitHub Actions should run:

- Backend pytest.
- Frontend typecheck, Vitest, and build.
- Docker Compose validation and image build checks.
- Playwright smoke tests after the browser suite is stable.

If Playwright fails in CI, screenshots, videos, and traces should be uploaded as artifacts.

## Final Demo Checklist

- Fresh clone setup works.
- `make dev` or documented Docker startup works.
- `make test` passes.
- `make smoke` passes.
- CI is green.
- Live demo URL works.
- Search/sidebar works.
- Filters and reset work.
- PDF export works.
- Comparison panel works.
- Shareable URL restore works.
- Scenario Mode works.
- Gap Hunter still shows observed data correctly.
- Basic accessibility smoke checks pass.
- Performance sanity checks pass.
- README links are current.
- Deployment docs are usable by a maintainer.
- Known limitations are documented.
