# Shared Communications Mesh setup and rollback

This is W6 tooling documentation for SPEC-SC-MESH-001. It does not authorize a live deployment.

## Clean setup

1. Pin the exact RESIDUAL candidate commit and record its tree.
2. Back up the Station SQLite database with SQLite's backup API or a stopped consistent copy; record SHA-256.
3. Validate the worker host has the pinned Python runtime, OpenClaw version, systemd, `systemd-run`, and the restrictive OpenClaw mesh config.
4. Create a unique worker identity. Enroll it through the owner-authenticated Station endpoint. Store the returned token only in an approved host secret path suitable for systemd `LoadCredential`; never place it in the JSON worker config.
5. Write `/etc/residual/mesh/<instance>.json` mode 0600 using schema `residual.sc.mesh.worker/1`.
6. Run `python -m residual mesh-worker --config ... --preflight`. A preflight does not claim work or call a model.
7. Install the systemd template but leave it disabled until the owner authorizes the canary.
8. Start one isolated worker, synchronize, and verify Station reports READY before permitting claims.

Repeated setup must compare the exact config, enrollment identity and candidate digest. It must not silently rotate tokens, replace another worker, or overwrite a state database.

## Worker JSON

The non-secret JSON contains Station URL, project ID, worker ID, outbox path, poll period, explicit provider routes and adapter settings. Provider credentials are deliberately absent.

## Migration

Mesh tables are additive to the Station database. Run migrations against a disposable database copy first. Preserve the pre-migration database and event/artifact directories. An older runtime must not be started against a database after an incompatible migration.

## Rollback

1. Pause admission.
2. Request mesh stop, which increments project generation and revokes current mesh leases.
3. Stop mesh worker units and separately record requested cancellation versus observed process termination.
4. Preserve worker outboxes, Station events, artifacts, dead letters and qualification evidence.
5. Restore only to a runtime/storage pair declared compatible with the preserved database. Never delete event history to make an older runtime start.
6. If compatibility cannot be proven, remain stopped and require recovery rather than silently discarding work.

## Platform support

The candidate adapter's bounded execution path is Linux/systemd only. Windows execution is OUT_OF_SCOPE until an equivalent process-tree containment implementation is added and independently qualified.

## Qualification boundary

A successful preflight, active systemd unit, model response, or transport ACK is not MESH_QUALIFIED. Qualification requires the W7 evidence bundle and Q01-Q14 disposition.
