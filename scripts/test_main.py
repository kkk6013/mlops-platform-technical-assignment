"""

Tests for the Model Registry backend.

 

Run locally:

    pip install pytest httpx

    pytest -v

 

FastAPI's TestClient lets us call the API in-process, without running a server.

Each test checks one behaviour and reads like a small acceptance scenario.

"""

 

from fastapi.testclient import TestClient

from main import app

 

client = TestClient(app)

 

 

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
