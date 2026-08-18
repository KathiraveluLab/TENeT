def test_health_endpoint_contract():
    from app import app

    response = app.test_client().get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "tenet-api",
    }


def test_readiness_endpoint_checks_database():
    from app import app

    response = app.test_client().get("/api/ready")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ready",
        "service": "tenet-api",
        "database": "available",
    }


def test_cors_origins_require_an_explicit_allowlist():
    from app import parse_cors_origins

    assert parse_cors_origins(None) == []
    assert parse_cors_origins("") == []
    assert parse_cors_origins("https://one.example, https://two.example ") == [
        "https://one.example",
        "https://two.example",
    ]


def test_default_health_response_does_not_enable_cross_origin_access():
    from app import app

    response = app.test_client().get(
        "/api/health",
        headers={"Origin": "https://unexpected.example"},
    )

    assert "Access-Control-Allow-Origin" not in response.headers


def test_readiness_returns_503_without_exposing_database_errors(monkeypatch):
    import app as app_module

    class UnavailableDatabase:
        def execute(self, _query):
            raise RuntimeError("private database detail")

        def close(self):
            pass

    monkeypatch.setattr(app_module, "SessionLocal", UnavailableDatabase)
    response = app_module.app.test_client().get("/api/ready")

    assert response.status_code == 503
    assert response.get_json() == {
        "status": "unavailable",
        "service": "tenet-api",
        "database": "unavailable",
    }
