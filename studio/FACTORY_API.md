# Residual Studio ↔ Factory API contract

Studio is not the Factory authority. It proxies a deliberately small API from the browser to the local/self-hosted Factory service.

## Read paths

### GET /v1/factory/snapshot
Returns the current authoritative projection used by Studio:

```json
{"runId":"run-...","status":"running","planHash":"...","accepted":3,"total":8,"ready":2,"blocked":1,"receipts":3,"model":"...","workers":[],"updatedAt":"..."}
```

### GET /v1/factory/events
Server-Sent Events. Each event is either a complete snapshot or `{"snapshot": ...}`. Events are observational; Studio reconciles periodically against the snapshot endpoint.

## Control path

### POST /v1/factory/control
Studio forwards one of: `plan`, `approve`, `run`, `cancel`, `integrate`.

The upstream Factory service MUST independently authenticate and authorize the request and MUST revalidate all authoritative invariants. Browser/UI state is never trusted. In particular:

- approve must bind the exact ExecutionPlan graph hash;
- run must require a valid FrozenPlan/approval and applicable WorkerContracts;
- cancel must operate on a live authoritative run/attempt and remain auditable;
- integrate must consume verified receipts and preserve M4 HITL conflict semantics;
- no endpoint may allow Studio to mint Station receipts or bypass Evidence Bus verification.

Studio sends its server-side `RESIDUAL_STUDIO_CONTROL_TOKEN` as a bearer token. The token is never exposed to browser JavaScript.

## Environment

```
RESIDUAL_FACTORY_API=http://127.0.0.1:8765
RESIDUAL_STUDIO_CONTROL_TOKEN=<local operator token>
```

If the control token is absent, Studio remains read-only.
