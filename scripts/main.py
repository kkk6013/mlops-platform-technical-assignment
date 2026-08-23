"""
MLOps Model Registry - Backend (vertical slice)
================================================
A minimal FastAPI backend for the Model Registry portion of the assignment.
 
Scope (intentional): implements model creation, listing, retrieval, version
registration, and a health check. Data is stored in memory for simplicity.
See NOTES.md for what a fuller implementation would add.
 
Run locally:
    pip install fastapi "uvicorn[standard]"
    uvicorn main:app --reload
 
Then open http://127.0.0.1:8000/docs  <- interactive API documentation
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Lifecycle stages
# ---------------------------------------------------------------------------
# The assignment suggests these lifecycle stages for a model version.
# An Enum makes the allowed values explicit and validated automatically.
class LifecycleStage(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"

# ---------------------------------------------------------------------------
# 2. Data shapes (Pydantic models)
# ---------------------------------------------------------------------------
# Pydantic models define the shape of data coming IN (requests) and going
# OUT (responses). FastAPI uses them to validate input automatically - if a
# client sends the wrong type or a missing field, FastAPI returns a clear
# error without us writing any checking code.

class ModelCreate(BaseModel):
    """What the client must send to create a model."""
    name: str = Field(..., min_length=1, description="Human-readable model name")
    description: Optional[str] = Field(None, description="Optional description")


class VersionCreate(BaseModel):
    """What the client must send to register a version of a model."""
    framework: str = Field(..., description="e.g. tensorflow, pytorch, sklearn")
    algorithm: str = Field(..., description="e.g. xgboost, cnn")
    artifact_uri: str = Field(..., description="Where the model artifact is stored")
    training_data_ref: Optional[str] = Field(None, description="Training data reference")

class Version(BaseModel):
    """A stored version, as returned to the client."""
    version_id: str
    version_number: int
    framework: str
    algorithm: str
    artifact_uri: str
    training_data_ref: Optional[str]
    stage: LifecycleStage
    approved: bool
    created_at: datetime


class Model(BaseModel):
    """A stored model, as returned to the client."""
    model_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    versions: list[Version] = []


class MonitoringStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILING = "FAILING"

class MetricsResponse(BaseModel):
    """Mock monitoring metrics returned for a model."""
    latency_ms: float
    throughput_rps: float
    error_rate: float
    quality_score: float
    drift_score: float
    availability: float
    last_successful_inference: datetime
    monitoring_status: MonitoringStatus


# ---------------------------------------------------------------------------
# 3. In-memory storage
# ---------------------------------------------------------------------------
# A real system would use a database (the assignment suggests PostgreSQL/SQLite
# via SQLAlchemy). For this vertical slice we use a simple dict keyed by
# model_id. This keeps the focus on API design and is honestly noted as a
# simplification in NOTES.md.
_models: dict[str, Model] = {}


# ---------------------------------------------------------------------------
# 4. The application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="MLOps Model Registry",
    description="Vertical slice: model and version registration.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Liveness check - confirms the service is up. Required by the brief."""
    return {"status": "ok", "time": datetime.now(timezone.utc)}


@app.post("/models", response_model=Model, status_code=201)
def create_model(payload: ModelCreate):
    """Create a new model. Returns the created model with a generated id."""
    model = Model(
        model_id=str(uuid4()),
        name=payload.name,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
        versions=[],
    )
    _models[model.model_id] = model
    return model


@app.get("/models", response_model=list[Model])
def list_models():
    """List all registered models."""
    return list(_models.values())


@app.get("/models/{model_id}", response_model=Model)
def get_model(model_id: str):
    """Fetch one model by id. Returns 404 with a clear message if not found."""
    model = _models.get(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model


@app.post("/models/{model_id}/versions", response_model=Version, status_code=201)
def add_version(model_id: str, payload: VersionCreate):
    """Register a new version under an existing model."""
    model = _models.get(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    version = Version(
        version_id=str(uuid4()),
        version_number=len(model.versions) + 1, # 1, 2, 3, ...
        framework=payload.framework,
        algorithm=payload.algorithm,
        artifact_uri=payload.artifact_uri,
        training_data_ref=payload.training_data_ref,
        stage=LifecycleStage.DRAFT, # new versions start as DRAFT
        approved=False,
        created_at=datetime.now(timezone.utc),
    )
    model.versions.append(version)
    return version


@app.get("/models/{model_id}/versions", response_model=list[Version])
def list_versions(model_id: str):
    """List all versions of a model."""
    model = _models.get(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model.versions


@app.get("/models/{model_id}/metrics", response_model=MetricsResponse)
def get_model_metrics(model_id: str):
    """Fetch monitoring metrics for a model (mock data for demonstration)."""
    if model_id not in _models:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    # Returning realistic mock data to fulfill the API requirement
    return MetricsResponse(
        latency_ms=42.5,
        throughput_rps=150.2,
        error_rate=0.005,
        quality_score=0.96,
        drift_score=0.012,
        availability=99.95,
        last_successful_inference=datetime.now(timezone.utc),
        monitoring_status=MonitoringStatus.HEALTHY
    )

# ---------------------------------------------------------------------------

# Lifecycle governance

# ---------------------------------------------------------------------------

def _find_version(model_id: str, version_id: str) -> Version:

    model = _models.get(model_id)

    if model is None:

        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    for version in model.versions:

        if version.version_id == version_id:

            return version

    raise HTTPException(status_code=404, detail=f"Version {version_id} not found")

 

 

_STAGES_REQUIRING_APPROVAL = {LifecycleStage.STAGING, LifecycleStage.PRODUCTION}

 

 

class PromoteRequest(BaseModel):

    stage: LifecycleStage

 

 

@app.post("/models/{model_id}/versions/{version_id}/approve", response_model=Version)
def approve_version(model_id: str, version_id: str):
    """Approve a version, granting a single-use ticket for the next promotion."""
    version = _find_version(model_id, version_id)
    
    # Grant the approval ticket, but leave the stage exactly as it is
    version.approved = True
    
    return version

 

 

@app.post("/models/{model_id}/versions/{version_id}/promote", response_model=Version)
def promote_version(model_id: str, version_id: str, payload: PromoteRequest):
    """Promote a version to a stage. STAGING/PRODUCTION require a fresh approval ticket."""
    version = _find_version(model_id, version_id)
    
    # Gatekeeper: Require an active ticket for high-stakes stages
    if payload.stage in _STAGES_REQUIRING_APPROVAL and not version.approved:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version_id} must be explicitly approved before moving to {payload.stage.value}.",
        )

    # Update the stage
    version.stage = payload.stage
    
    # Consume the ticket! Next major stage jump requires fresh approval.
    version.approved = False
    
    return version


# ---------------------------------------------------------------------------
# Deployment Management
# ---------------------------------------------------------------------------
class DeploymentState(str, Enum):
    REQUESTED = "REQUESTED"
    DEPLOYING = "DEPLOYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class DeploymentCreate(BaseModel):
    model_id: str
    version_id: str
    environment: str = Field(..., description="e.g. staging, production")


class Deployment(BaseModel):
    deployment_id: str
    model_id: str
    version_id: str
    environment: str
    status: DeploymentState
    created_at: datetime
    events: list[dict] = []

    
_deployments: dict[str, Deployment] = {}
_idempotency_keys: dict[str, str] = {}


class DeploymentRequest(BaseModel):
    model_id: str
    version_id: str
    environment: str
    idempotency_key: Optional[str] = None

    
@app.post("/deployments", response_model=Deployment, status_code=201)
def create_deployment(payload: DeploymentRequest):
    """Create a deployment with payload validation and strict stage governance."""
    
    # 1. Idempotency Payload Mismatch Check
    if payload.idempotency_key and payload.idempotency_key in _idempotency_keys:
        existing_id = _idempotency_keys[payload.idempotency_key]
        existing_dep = _deployments[existing_id]
        
        # Verify the payload matches the original request
        if (existing_dep.environment.lower() != payload.environment.lower() or 
            existing_dep.model_id != payload.model_id or 
            existing_dep.version_id != payload.version_id):
            raise HTTPException(
                status_code=409, 
                detail="Idempotency key reused with a different payload."
            )
        return existing_dep

    version = _find_version(payload.model_id, payload.version_id)
    
    # 2. Strict MLOps Governance: Environment must match Lifecycle Stage
    env = payload.environment.upper()
    if env == "PRODUCTION" and version.stage != LifecycleStage.PRODUCTION:
        raise HTTPException(
            status_code=409,
            detail="Cannot deploy to PRODUCTION. Model version has not reached the PRODUCTION stage."
        )
        
    if env == "STAGING" and version.stage not in [LifecycleStage.STAGING, LifecycleStage.PRODUCTION]:
        raise HTTPException(
            status_code=409,
            detail="Cannot deploy to STAGING. Model version has not reached the STAGING stage."
        )

    deployment = Deployment(
        deployment_id=str(uuid4()),
        model_id=payload.model_id,
        version_id=payload.version_id,
        environment=payload.environment,
        status=DeploymentState.REQUESTED,
        created_at=datetime.now(timezone.utc),
        events=[{"action": "REQUESTED", "time": datetime.now(timezone.utc).isoformat()}],
    )
    _deployments[deployment.deployment_id] = deployment

    if payload.idempotency_key:
        _idempotency_keys[payload.idempotency_key] = deployment.deployment_id

    return deployment


@app.get("/deployments", response_model=list[Deployment])
def list_deployments():
    """List all deployments."""
    return list(_deployments.values())


@app.get("/deployments/{deployment_id}", response_model=Deployment)
def get_deployment(deployment_id: str):
    """Get a specific deployment."""
    dep = _deployments.get(deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    return dep


@app.post("/deployments/{deployment_id}/retry", response_model=Deployment)
def retry_deployment(deployment_id: str):
    """Retry a failed deployment. Only FAILED deployments can be retried."""
    dep = _deployments.get(deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    if dep.status != DeploymentState.FAILED:
        raise HTTPException(status_code=409, detail=f"Only FAILED deployments can be retried. Current: {dep.status.value}")
    dep.status = DeploymentState.REQUESTED
    dep.events.append({"action": "RETRY", "time": datetime.now(timezone.utc).isoformat()})
    return dep


@app.post("/deployments/{deployment_id}/rollback", response_model=Deployment)
def rollback_deployment(deployment_id: str):
    """Roll back a deployment. Only SUCCEEDED deployments can be rolled back."""
    dep = _deployments.get(deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    if dep.status != DeploymentState.SUCCEEDED:
        raise HTTPException(status_code=409, detail=f"Only SUCCEEDED deployments can be rolled back. Current: {dep.status.value}")
    dep.status = DeploymentState.ROLLED_BACK
    dep.events.append({"action": "ROLLED_BACK", "time": datetime.now(timezone.utc).isoformat()})
    return dep


class SimulateCompletionRequest(BaseModel):
    """Payload to simulate a deployment succeeding or failing."""
    success: bool = True

@app.post("/deployments/{deployment_id}/simulate", response_model=Deployment)
def simulate_deployment_completion(deployment_id: str, payload: SimulateCompletionRequest):
    """
    Simulates a background worker finishing the deployment. 
    Allows testing of retry (on failure) and rollback (on success).
    """
    dep = _deployments.get(deployment_id)
    if dep is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    
    if dep.status not in [DeploymentState.REQUESTED, DeploymentState.DEPLOYING]:
        raise HTTPException(
            status_code=409, 
            detail=f"Can only simulate completion for REQUESTED/DEPLOYING deployments. Current: {dep.status.value}"
        )
    
    if payload.success:
        dep.status = DeploymentState.SUCCEEDED
        action_name = "SIMULATED_SUCCESS"
    else:
        dep.status = DeploymentState.FAILED
        action_name = "SIMULATED_FAILURE"
        
    dep.events.append({"action": action_name, "time": datetime.now(timezone.utc).isoformat()})
    return dep