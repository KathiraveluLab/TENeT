import pytest

import routes.cat_routes as cat_routes
import routes.performance_routes as performance_routes

GENERIC_ERROR = {"error": "An internal error occurred"}
PRIVATE_DETAIL = "private database detail"


class FailingSession:
    def query(self, *args, **kwargs):
        raise RuntimeError(PRIVATE_DETAIL)

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture()
def client():
    from app import app

    return app.test_client()


@pytest.mark.parametrize("module, path", [
    (cat_routes, "/api/cat/regions"),
    (cat_routes, "/api/cat/healthcare/summary"),
    (performance_routes, "/api/cat/performance"),
])
def test_database_errors_do_not_expose_details(client, monkeypatch, module, path):
    monkeypatch.setattr(module, "SessionLocal", FailingSession)

    response = client.get(path)

    assert response.status_code == 500
    assert response.get_json() == GENERIC_ERROR
    assert PRIVATE_DETAIL not in response.get_data(as_text=True)


def test_scenario_preview_errors_do_not_expose_details(client, monkeypatch):
    from services.scenario_engine import ScenarioEngine

    def failing_preview(*args, **kwargs):
        raise RuntimeError(PRIVATE_DETAIL)

    monkeypatch.setattr(ScenarioEngine, "preview", failing_preview)

    response = client.post("/api/cat/scenarios/preview", json={
        "mode": "preview",
        "season": "year_round",
        "thresholds": {
            "min_download_mbps": 25,
            "min_upload_mbps": 3,
            "max_latency_ms": 150,
            "clinic_proximity_km": None,
            "affordability_burden_pct": 2,
        },
    })

    assert response.status_code == 500
    assert response.get_json() == GENERIC_ERROR
    assert PRIVATE_DETAIL not in response.get_data(as_text=True)
