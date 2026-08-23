# **MLOps Model Registry — Submission Notes**





### **What this submission covers**

**Given the time available, I focused on delivering a clean, functional vertical slice rather than broad, incomplete coverage. This slice covers the Model Registry, Lifecycle Governance, and Deployment Management, proving the core state machine and API logic.**



#### **1. Backend Implementation (FastAPI)**



**Model Registry: POST and GET endpoints for models and versions.**



**Lifecycle Governance: POST /approve and POST /promote endpoints featuring a strict state machine. Approvals act as "consumable, single-use tickets" (e.g., promoting to STAGING consumes the ticket, requiring a fresh approval before PRODUCTION) to prevent unauthorized environment jumps.**



**Deployment Management: POST /deployments with state tracking (REQUESTED, SUCCEEDED, FAILED, ROLLED\_BACK). Includes strict environment governance (e.g., rejecting attempts to deploy unpromoted models to production).**



**Idempotency: The deployment endpoint accepts idempotency keys and strictly validates the request payload hash, rejecting altered payloads with a 409 Conflict to prevent distributed state bugs.**



**Retry \& Rollback: Endpoints that validate current deployment states before allowing a retry or rollback transition.**





#### **2. Frontend Implementation (Vanilla HTML/JS)**

**While the prompt requested an Angular GUI, web frontend frameworks are currently outside my core stack. Rather than delivering an incomplete or broken Angular application, I built a lightweight, vanilla JavaScript/HTML prototype. This successfully demonstrates that the REST API works end-to-end, surfacing dynamic state changes, handling CORS, and displaying clear error messages from the backend.**







### **Engineering practices demonstrated**

**State-Machine Security — ensuring single-use approvals and environment-aware deployments.**



**Containerization \& CI/CD — fully Dockerized environment with automated GitHub Actions workflows to run the test suite on push, ensuring code quality and preventing regressions.**



**Typed request/response models with validation (Pydantic) — invalid input is rejected automatically with clear errors.**



**Consistent error handling — invalid state transitions, idempotency mismatches, or governance bypasses return a 409 Conflict, and missing resources return 404 Not Found.**



**Auto-generated API documentation — available at /docs (OpenAPI).**



**Automated tests (test\_main.py) — achieving full coverage of the happy paths, 409 Conflict governance rules, idempotency payload mismatches, state-clearing fixtures, and strict state-machine constraints.**







### **How to run**

**Option 1: Using Docker (Recommended)**

**The project is containerized for easy execution.**



**Bash**

**docker-compose up --build**

**The interactive API documentation will be available at http://localhost:8000/docs**





**Option 2: Running locally (Python environment)**



**Bash**

**pip install fastapi "uvicorn\[standard]" pytest httpx**

**uvicorn main:app --reload**

**The interactive API documentation will be available at http://127.0.0.1:8000/docs**



**Run the Tests (Local)**



**Bash**

**pytest -v**

**View the Frontend**

**Simply open index.html in any modern web browser. It is configured to automatically point to the local FastAPI server on port 8000**







### **What a fuller implementation would add (with more time)**

**I want to be transparent about scope. The following are deliberately not implemented here, and I'd approach them as follows in a production scenario:**



**Asynchronous Processing: To keep this vertical slice focused and runnable without complex infrastructure, deployment triggers currently operate synchronously. In a production environment, the /deployments endpoint would immediately return a 202 Accepted and publish a deployment event to a message broker (like RabbitMQ or Kafka) for asynchronous execution by background worker pods.**



**Persistence: Replace the in-memory store (\_models and \_deployments dicts) with SQLAlchemy + PostgreSQL and Alembic migrations. In-memory was chosen to keep the slice focused on API and state logic.**



**Monitoring: Add the GET /models/{model\_id}/metrics endpoint to expose latency, throughput, error rate, drift, and quality.**



**Angular Integration: Rebuild the vanilla UI prototype using Angular, TypeScript, and RxJS as requested in the target architecture.**







### **A note on scope and honesty**

**I built the parts I could implement well and architect soundly in the time available. I prioritized robust backend validation, distributed systems safety mechanisms, proper HTTP status codes, and a working end-to-end prototype over checking every box with fragile code. I'd rather submit a functional, well-reasoned core that I can stand behind.**

