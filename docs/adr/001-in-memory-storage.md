# ADR-001: In-Memory Storage for the Vertical Slice

## Status
Accepted (for current scope). Superseded plan: migrate to SQLAlchemy + PostgreSQL. 

## Context 
The assignment brief suggested SQLAlchemy with PostgreSQL/SQLite and Alembic migrations for persistence. Given the time available, a decision was needed on whether to implement a full database layer or a simpler storage mechanism for the initial vertical slice, in line with the brief's guidance that "a complete vertical slice is preferred over broad but incomplete scope." 

## Decision 
Use a simple in-memory Python dictionary (keyed by model_id) as the storage layer for models, versions, and deployments, rather than implementing SQLAlchemy models and database migrations for this submission. 



## Alternatives Considered
* SQLAlchemy + SQLite — the most complete option, matching the brief's suggested stack exactly. Rejected for this submission due to time constraints: schema design, migrations (Alembic), and connection management would have consumed time better spent completing more API surface area and the governance/idempotency logic. 
* File-based storage (JSON) — a middle ground, persisting data to disk between restarts. Rejected because it adds complexity (file locking, serialization) without the real benefits of a database (querying, transactions, concurrent access). 
* In-memory dictionary (chosen) — fastest to implement, keeps focus on API design and business logic, and is explicitly and transparently documented as a simplification. 

## Consequences
* Positive: Allowed more time to be spent on API design, lifecycle governance, and the deployment/idempotency logic. Zero setup friction — the evaluator can run the application immediately via Docker or locally without provisioning a database. The storage access pattern is written so that swapping in a real repository/ORM layer later is a contained change. 
* Negative: Data does not persist across server restarts. No support for concurrent access, transactions, or complex queries. Does not demonstrate SQLAlchemy, migrations, or schema design skills that the brief explicitly asked for. 

## Follow-up Actions
Introduce a Repository interface with methods like get, save, list, so the in-memory implementation can be swapped for a SQLAlchemy-backed one without changing the API layer. 
Design the SQLAlchemy schema with foreign keys and appropriate indexes. 
Add Alembic for migrations before any schema change ships. 
Add integration tests against a test database (SQLite in-memory or a Dockerized PostgreSQL for CI). 
