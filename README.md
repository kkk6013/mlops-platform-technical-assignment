# **MLOps Model Registry — Submission Notes**



### What this submission covers

Given the time available, I focused on delivering a clean, functional vertical slice rather than broad, incomplete coverage. This slice covers the Model Registry, Lifecycle Governance, and Deployment Management, proving the core state machine and API logic.



1\. Backend Implementation (FastAPI)

Model Registry: POST and GET endpoints for models and versions.



Lifecycle Governance: POST /approve and POST /promote endpoints with state validation (e.g., ensuring a version cannot be promoted to PRODUCTION without prior approval).



Deployment Management: POST /deployments with state tracking (REQUESTED, SUCCEEDED, FAILED, ROLLED\_BACK).



Idempotency: The deployment endpoint accepts and processes idempotency keys to safely handle duplicate deployment requests.



Retry \& Rollback: Endpoints that validate current deployment states before allowing a retry or rollback transition.



2\. Frontend Implementation (Vanilla HTML/JS)

While the prompt requested an Angular GUI, web frontend frameworks are currently outside my core stack. Rather than delivering an incomplete or broken Angular application, I built a lightweight, vanilla JavaScript/HTML prototype. This successfully demonstrates that the REST API works end-to-end, surfacing dynamic state changes, handling CORS, and displaying clear error messages from the backend.





### Engineering practices demonstrated

Typed request/response models with validation (Pydantic) — invalid input is rejected automatically with clear errors.



Consistent error handling — invalid state transitions (e.g., rolling back a failed deployment) return a 409 Conflict, and missing resources return 404 Not Found.



Idempotency design — ensuring safe API retries for deployment creation.



Auto-generated API documentation — available at /docs (OpenAPI).



Automated tests (test\_main.py) — covering the core happy paths and governance rules for the Model Registry.





### How to run

1\. Start the Backend



Bash

pip install fastapi "uvicorn\[standard]" pytest httpx

uvicorn main:app --reload      

The interactive API documentation will be available at http://127.0.0.1:8000/docs



2\. Run the Tests



Bash

pytest -v                      

3\. View the Frontend

Simply open index.html in any modern web browser. It is configured to automatically point to the local FastAPI server on port 8000.





### What a fuller implementation would add (with more time)

I want to be transparent about scope. The following are deliberately not implemented here, and I'd approach them as follows in a production scenario:



Persistence: Replace the in-memory store (\_models and \_deployments dicts) with SQLAlchemy + PostgreSQL and Alembic migrations. In-memory was chosen to keep the slice focused on API and state logic.



Monitoring: Add the GET /models/{model\_id}/metrics endpoint to expose latency, throughput, error rate, drift, and quality.



Test Coverage Expansion: While the Model Registry is tested, I would add Pytest fixtures to clear the in-memory state between tests, and write tests to cover the idempotency and deployment state machine logic.



Angular Integration: Rebuild the vanilla UI prototype using Angular, TypeScript, and RxJS as requested in the target architecture.



Containerisation \& CI: Add a Dockerfile, Docker Compose, and a GitHub Actions workflow to run the tests on push.





### A note on scope and honesty

I built the parts I could implement well and architect soundly in the time available. I prioritized robust backend validation, proper HTTP status codes, and a working end-to-end prototype over checking every box with fragile code. I'd rather submit a functional, well-reasoned core that I can stand behind.

