
from fastapi.testclient import TestClient

from api.main import app
from database.seed import seed_database

client = TestClient(app)


def setup_module():
    seed_database()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_cases():
    response = client.get("/cases")
    assert response.status_code == 200
    assert len(response.json()["cases"]) >= 5


def test_get_existing_case():
    response = client.get("/cases/CASE001")
    assert response.status_code == 200
    assert response.json()["case"]["case_id"] == "CASE001"


def test_unknown_case_returns_404():
    response = client.get("/cases/CASE999")
    assert response.status_code == 404


def test_approval_queue_endpoint():
    response = client.get("/approvals")
    assert response.status_code == 200
    assert "approvals" in response.json()


def test_resolve_unknown_case():
    response = client.post(
        "/resolve",
        json={"case_id": "CASE999"},
    )
    assert response.status_code == 404


def test_approve_unknown_case():
    response = client.post(
        "/approvals/CASE999/approve",
        json={"notes": "Test approval"},
    )
    assert response.status_code == 404


def test_reject_unknown_case():
    response = client.post(
        "/approvals/CASE999/reject",
        json={"notes": "Test rejection"},
    )
    assert response.status_code == 404
