# mlops-platform-technical-assignment
Vertical‑slice MLOps prototype (FastAPI) implementing a Model Registry: model &amp; version CRUD, lifecycle governance (DRAFT→APPROVED→PRODUCTION), idempotent deployments, retry/rollback, in‑memory storage (documented ADRs), OpenAPI docs, Pytest tests, and a plain HTML/JS proof‑of‑concept UI.


# MLOps Model Registry & Deployment Platform — Submission Notes

## What this submission covers

A vertical slice covering the full lifecycle: register a model, register and
approve versions, deploy an approved version, retry a failed deployment,
roll back a succeeded one, and view monitoring data — end to end, through
both the API and the UI.

Implemented:

**Model Registry**
- `GET  /health` — liveness check
- `POST /models` — create a model
- `GET  /models` — list all models
- `GET  /models/{model_id}` — fetch one model (404 if missing)
- `POST /models/{model_id}/versions` — register a version (auto-numbered, starts as `DRAFT`)
- `GET  /models/{model_id}/versions` — list versions
- `POST /models/{model_id}/versions/{version_id}/approve` — approve a version
- `POST /models/{model_id}/versions/{version_id}/promote` — promote to a lifecycle
  stage; `STAGING`/`PRODUCTION` require the version to be approved first (409 otherwise)

**Deployment Management**
- `POST /deployments` — deploy an approved version to an environment.
  Unapproved versions are rejected (409). Accepts an optional
  `idempotency_key`; a repeat request with the same key returns the original
  deployment instead of creating a new one.
- `GET  /deployments` / `GET /deployments/{id}` — list / fetch deployments
- `POST /deployments/{id}/retry` — retry a `FAILED` deployment (409 otherwise)
- `POST /deployments/{id}/rollback` — roll back a `SUCCEEDED` deployment (409 otherwise)
- Each deployment runs through a simulated state machine —
  `REQUESTED → VALIDATING → DEPLOYING → SUCCEEDED/FAILED` — and every
  transition is recorded in the deployment's event history. There is no real
  deployment executor in this slice, so `simulate_failure` (a boolean on the
  request) is the hook used to deterministically exercise the FAILED →
  retry path, rather than mutating internal state in tests.

**Monitoring**
- `GET /models/{model_id}/metrics` — returns latency, throughput, error
  rate, quality score, drift score, availability, last successful inference
  time, and an overall status (`HEALTHY` / `DEGRADED` / `NO_DATA`).
  `error_rate`, `availability`, and `last_successful_inference` are computed
  from this model's real deployment history. `latency`, `throughput`,
  `quality_score`, and `drift_score` are **simulated** (deterministically
  seeded by model_id, since no live inference traffic exists in this slice)
  — flagged here and in the Architecture Doc so it isn't mistaken for real
  telemetry.

**UI (index.html)**
- Model inventory, version management (add/approve/promote)
- Deployment view: deploy a version, see status, retry/rollback actions
- Monitoring dashboard for a selected model
- Loading, empty, and error states on every panel

Engineering practices demonstrated:
- Typed request/response models with validation (Pydantic)
- Consistent error handling — 404 for missing resources, 409 for governance
  conflicts, both with clear messages, not stack traces
- Auto-generated API documentation at `/docs` (OpenAPI)
- Automated tests (`test_main.py`) — 19 tests covering the registry,
  lifecycle governance, deployment, idempotency, retry, rollback, and
  monitoring, mapped to the brief's acceptance scenarios

## How to run

- Ran on Python 3.9.5

```bash
pip install fastapi "uvicorn[standard]" pytest httpx
uvicorn main:app --reload      # then open http://127.0.0.1:8000/docs
pytest -v                      # run the tests
```

Then open `index.html` directly in a browser (it talks to
`http://127.0.0.1:8000` — make sure the backend is running first).

## What a fuller implementation would add

Being transparent about scope — see `ADR.docx` and `Architecture_Doc.docx`
for the reasoning behind each of these trade-offs:

- **Persistence:** SQLAlchemy + SQLite/PostgreSQL with Alembic migrations,
  replacing the in-memory store (ADR-001).
- **Idempotency keys with a TTL and a DB uniqueness constraint**, instead of
  an unbounded in-memory dict with no race-condition protection (ADR-002).
- **Angular frontend:** the current UI is plain HTML/JS as a proof of
  concept; production target is Angular + TypeScript + Angular Material +
  RxJS, with component/service tests (Karma/Jasmine).
- **Real monitoring:** OpenTelemetry + Prometheus, replacing the simulated
  latency/throughput/quality/drift values with live telemetry.
- **Async deployment execution** via a worker/queue (Celery + Redis), so
  deployments don't block the API and can genuinely fail asynchronously
  rather than via a `simulate_failure` flag.
- **Auth (OAuth2/JWT + RBAC)**, containerisation (Docker Compose), and CI
  (GitHub Actions running the test suite on push).

## A note on scope and honesty

The parts here are implemented and understood fully — governance rules,
state machine, idempotency, and the monitoring split between real and
simulated data were all deliberate decisions, documented in the ADR. What's
out of scope is named explicitly rather than glossed over.

