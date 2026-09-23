import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.models.models import EnvironmentType

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_application_lifecycle():
    # 1. Create Application
    create_payload = {
        "name": "Integration Test CRM",
        "description": "App created during automated unit tests"
    }
    create_res = client.post("/api/applications", json=create_payload)
    assert create_res.status_code == 201
    app_data = create_res.json()
    app_id = app_data["id"]
    assert app_data["name"] == "Integration Test CRM"

    # 2. Get Application
    get_res = client.get(f"/api/applications/{app_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == app_id

    # 3. Create Environment
    env_payload = {
        "name": "Local Dev",
        "base_url": "http://localhost:3000",
        "environment_type": "development"
    }
    env_res = client.post(f"/api/applications/{app_id}/environments", json=env_payload)
    assert env_res.status_code == 201
    env_data = env_res.json()
    env_id = env_data["id"]
    assert env_data["base_url"] == "http://localhost:3000"

    # 4. List Environments
    env_list_res = client.get(f"/api/applications/{app_id}/environments")
    assert env_list_res.status_code == 200
    assert len(env_list_res.json()) >= 1

    # 5. Create Exploration Run
    expl_payload = {
        "application_id": app_id,
        "environment_id": env_id,
        "max_pages": 10,
        "max_depth": 2
    }
    expl_res = client.post("/api/explorations", json=expl_payload)
    assert expl_res.status_code == 201
    expl_data = expl_res.json()
    run_id = expl_data["id"]
    assert expl_data["status"] == "pending"

    # 6. Check Status
    status_res = client.get(f"/api/explorations/{run_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["id"] == run_id
