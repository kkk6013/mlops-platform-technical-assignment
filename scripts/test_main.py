"""

Tests for the Model Registry backend.

 

Run locally:

    pip install pytest httpx

    pytest -v

 

FastAPI's TestClient lets us call the API in-process, without running a server.

Each test checks one behaviour and reads like a small acceptance scenario.

"""

 

import pytest
from fastapi.testclient import TestClient
from main import app, _models, _deployments, _idempotency_keys

 

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_state():
    """Runs before every test to ensure a clean slate."""
    _models.clear()
    _deployments.clear()
    _idempotency_keys.clear()
    yield

 

 

def test_health():

    """Health endpoint returns ok."""

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "ok"

 

 

def test_create_and_get_model():

    """A created model can be fetched back with the same name."""

    create = client.post("/models", json={"name": "fraud-detector"})

    assert create.status_code == 201

    model_id = create.json()["model_id"]

 

    fetched = client.get(f"/models/{model_id}")

    assert fetched.status_code == 200

    assert fetched.json()["name"] == "fraud-detector"

 

 

def test_get_missing_model_returns_404():

    """Fetching an unknown model gives a clear 404, not a crash."""

    response = client.get("/models/does-not-exist")

    assert response.status_code == 404

 

 

def test_register_two_versions():

    """Two versions register under a model and are numbered 1 then 2."""

    model_id = client.post("/models", json={"name": "demand-forecast"}).json()["model_id"]

 

    v1 = client.post(f"/models/{model_id}/versions", json={

        "framework": "sklearn", "algorithm": "xgboost", "artifact_uri": "s3://a/1",

    })

    v2 = client.post(f"/models/{model_id}/versions", json={

        "framework": "sklearn", "algorithm": "xgboost", "artifact_uri": "s3://a/2",

    })

 

    assert v1.json()["version_number"] == 1

    assert v2.json()["version_number"] == 2

    assert v1.json()["stage"] == "DRAFT"        # new versions start as DRAFT

    assert v1.json()["approved"] is False


def test_unapproved_version_cannot_go_to_production():

    """Governance: promoting an unapproved version to PRODUCTION is rejected."""

    model_id = client.post("/models", json={"name": "risk-model"}).json()["model_id"]

    version_id = client.post(f"/models/{model_id}/versions", json={

        "framework": "sklearn", "algorithm": "xgboost", "artifact_uri": "s3://a/1",

    }).json()["version_id"]

 

    blocked = client.post(

        f"/models/{model_id}/versions/{version_id}/promote",

        json={"stage": "PRODUCTION"},

    )

    assert blocked.status_code == 409

 

 

def test_approved_version_can_go_to_production():

    """After approval, the same version can be promoted to PRODUCTION."""

    model_id = client.post("/models", json={"name": "risk-model-2"}).json()["model_id"]

    version_id = client.post(f"/models/{model_id}/versions", json={

        "framework": "sklearn", "algorithm": "xgboost", "artifact_uri": "s3://a/1",

    }).json()["version_id"]

 

    approve = client.post(f"/models/{model_id}/versions/{version_id}/approve")

    assert approve.status_code == 200

    assert approve.json()["approved"] is True

 

    promote = client.post(

        f"/models/{model_id}/versions/{version_id}/promote",

        json={"stage": "PRODUCTION"},

    )

    assert promote.status_code == 200

    assert promote.json()["stage"] == "PRODUCTION"


def test_deployment_idempotency_and_rollback():
    """Tests deploying an approved version, checking idempotency, simulating success, and rolling back."""
    # 1. Setup: Create model, version, approve it, and promote it to PRODUCTION
    model_id = client.post("/models", json={"name": "churn-model"}).json()["model_id"]
    version_id = client.post(f"/models/{model_id}/versions", json={
        "framework": "sklearn", "algorithm": "xgboost", "artifact_uri": "s3://a/1",
    }).json()["version_id"]
    
    client.post(f"/models/{model_id}/versions/{version_id}/approve")
    client.post(f"/models/{model_id}/versions/{version_id}/promote", json={"stage": "PRODUCTION"})
    
    # 2. Deploy with idempotency key
    dep_req = {
        "model_id": model_id, 
        "version_id": version_id, 
        "environment": "production",
        "idempotency_key": "deploy-key-123"
    }
    dep_1 = client.post("/deployments", json=dep_req)
    assert dep_1.status_code == 201
    dep_id = dep_1.json()["deployment_id"]
    
    # 3. Duplicate request safely returns same deployment ID (Idempotency check)
    dep_2 = client.post("/deployments", json=dep_req)
    assert dep_2.status_code == 201
    assert dep_2.json()["deployment_id"] == dep_id
    
    # 4. Simulate a successful deployment (so we can test rollback)
    sim = client.post(f"/deployments/{dep_id}/simulate", json={"success": True})
    assert sim.status_code == 200
    assert sim.json()["status"] == "SUCCEEDED"
    
    # 5. Rollback the successful deployment
    rollback = client.post(f"/deployments/{dep_id}/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "ROLLED_BACK"


def test_strict_promotion_lifecycle():
    # 1. Create model and version
    model_res = client.post("/models", json={"name": "Lifecycle", "description": "Test"})
    mid = model_res.json()["model_id"]
    ver_res = client.post(f"/models/{mid}/versions", json={
        "framework": "sklearn", "algorithm": "rf", "artifact_uri": "s3://path"
    })
    vid = ver_res.json()["version_id"]

    # 2. Try promoting to STAGING without approval -> Should fail (409)
    res = client.post(f"/models/{mid}/versions/{vid}/promote", json={"stage": "STAGING"})
    assert res.status_code == 409

    # 3. Approve and Promote to STAGING -> Should succeed (200), and consume ticket
    client.post(f"/models/{mid}/versions/{vid}/approve")
    res = client.post(f"/models/{mid}/versions/{vid}/promote", json={"stage": "STAGING"})
    assert res.status_code == 200
    assert res.json()["approved"] is False  # Ticket was consumed!

    # 4. Try promoting to PRODUCTION without a new approval -> Should fail (409)
    res = client.post(f"/models/{mid}/versions/{vid}/promote", json={"stage": "PRODUCTION"})
    assert res.status_code == 409


def test_deployment_environment_governance():
    # 1. Setup model and version
    model_res = client.post("/models", json={"name": "GovTest", "description": "Test"})
    mid = model_res.json()["model_id"]
    ver_res = client.post(f"/models/{mid}/versions", json={
        "framework": "sklearn", "algorithm": "rf", "artifact_uri": "s3://path"
    })
    vid = ver_res.json()["version_id"]

    # 2. Try deploying a DRAFT directly to PRODUCTION -> Should fail (409)
    res = client.post("/deployments", json={
        "model_id": mid,
        "version_id": vid,
        "environment": "production"
    })
    assert res.status_code == 409
    assert "PRODUCTION stage" in res.json()["detail"]



def test_deployment_idempotency_mismatch():
    # 1. Setup and fully promote a model to PRODUCTION
    model_res = client.post("/models", json={"name": "IdempTest"})
    mid = model_res.json()["model_id"]
    ver_res = client.post(f"/models/{mid}/versions", json={
        "framework": "sklearn", "algorithm": "rf", "artifact_uri": "s3://path"
    })
    vid = ver_res.json()["version_id"]
    
    client.post(f"/models/{mid}/versions/{vid}/approve")
    client.post(f"/models/{mid}/versions/{vid}/promote", json={"stage": "PRODUCTION"})

    # 2. Deploy to STAGING with an idempotency key
    key = "deploy-key-123"
    client.post("/deployments", json={
        "model_id": mid,
        "version_id": vid,
        "environment": "staging",
        "idempotency_key": key
    })

    # 3. Try to use the SAME key but change environment to PRODUCTION -> Should fail (409)
    res = client.post("/deployments", json={
        "model_id": mid,
        "version_id": vid,
        "environment": "production",  # Mismatch!
        "idempotency_key": key
    })
    assert res.status_code == 409
    assert "Idempotency key reused" in res.json()["detail"]


