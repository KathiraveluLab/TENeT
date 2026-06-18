def test_health_endpoint_contract():
    from app import app

    response = app.test_client().get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "service": "tenet-api",
    }
