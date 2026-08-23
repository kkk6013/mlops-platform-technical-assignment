# ADR-002: Payload-Aware Idempotency for Deployment Requests

## Status 
Accepted (initial implementation). Noted limitation: in-memory key storage. 

## Context 
The assignment explicitly requires safe handling of duplicate deployment requests. A deployment is a side-effecting operation, so if a client retries a request, the system must not create two separate deployments for what was intended as one action. 

## Decision 
Accept an optional idempotency_key field on the deployment creation request. On each request, check whether that key has been seen before: 
* If yes, and the payload matches: return the existing deployment associated with that key (no new deployment is created). 
* If yes, but the payload differs: reject the request with a 409 Conflict to prevent distributed state bugs where a client reuses a key for a completely different deployment.
* If no: create the deployment normally and record the key and payload hash against the new deployment's ID. 


## Alternatives Considered
* No idempotency handling — simplest, but explicitly fails the brief's acceptance scenario. Rejected. 
* Deduplicate by request content — avoids requiring the client to supply a key, but is fragile for genuine redeploys. Rejected in favor of explicit keys. 
* Client-supplied idempotency key (chosen) — the client controls what counts as "the same request," which correctly distinguishes retries from genuinely new requests. 

## Consequences
* Positive: Duplicate requests do not create duplicate deployments. Mismatched payloads using the same key are caught and rejected securely. The check is performed before any deployment object is created, preventing partial state writes. 
* Negative: Idempotency keys are stored in memory, lost on restart, and never expire. Does not yet handle the harder concurrency case: two requests with the same key arriving at nearly the same instant (race condition). 

## Follow-up Actions
* Persist idempotency keys in the database with a TTL (e.g., 24 hours). 
* Add a unique database constraint on idempotency_key to correctly handle race conditions. 
* Consider making idempotency_key mandatory for POST /deployments given it is a side-effecting operation. 
