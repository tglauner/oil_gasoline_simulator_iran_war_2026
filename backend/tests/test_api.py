from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_and_simulation_endpoints():
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert "current" in payload
    assert "model" in payload

    target_wti = payload["history"]["latest_basis"]["crude"] + 12.0
    simulation = client.post(
        "/api/simulate",
        json={"target_wti": target_wti, "horizon_weeks": 10, "transition_weeks": 3},
    )
    assert simulation.status_code == 200
    assert len(simulation.json()["comparison"]) == 10
