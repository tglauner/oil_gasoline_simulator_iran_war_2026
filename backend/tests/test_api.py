from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_dashboard_and_simulation_endpoints():
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert "current" in payload
    assert "model" in payload
    assert "diagnostics" in payload
    assert "sources" in payload["diagnostics"]
    assert payload["historical_event"]["date"] == "2026-02-28"

    target_wti = payload["history"]["latest_basis"]["crude"] + 12.0
    simulation = client.post(
        "/api/simulate",
        json={"target_wti": target_wti, "horizon_weeks": 10, "transition_weeks": 3},
    )
    assert simulation.status_code == 200
    assert len(simulation.json()["comparison"]) == 10
    assert simulation.headers["Cache-Control"] == "no-store"


def test_dashboard_failure_is_sanitized(monkeypatch):
    def fail_dashboard(*args, **kwargs):
        raise RuntimeError("sensitive upstream failure")

    monkeypatch.setattr(main, "build_dashboard_payload", fail_dashboard)
    response = client.get("/api/dashboard")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to build dashboard payload."
