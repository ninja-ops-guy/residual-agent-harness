# TARGET_COMPOSITION — bounded runner/mesh binding, 2026-10-07

Reviewable byte-level binding for V1-PC-COMP-RUNNER-MESH. This supplements the Closure-owned target registry; it is not a final RC designation or a replacement for the other required composition rows. V1_RELEASE_HOLD remains in force. QUALIFIABLE_COMPOSITION is not established by this audit.

## Exact audited composition

- #527 HEAD `f9c1a82b381420d4337391f0803983fb178cd197`
- TREE `94f84922d9348b1422e549083a18ae428d12b0b2`
- Accepted main `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`
- Declared MC #524 `ec4df5a734054fd8f2fa0ef32f4061a42f5bdf82`, AUTH #519 `b16482bf589566197d970a30053fd3fea6b628ff`, OpenClaw #511 `7c35f72863e1631d4675c82f459b717a53b53bd9`.

**Binding: NO_SEPARATE_RUNNER_MESH_BYTES_REQUIRED for this exact composition.** No #400/#404/#493, SC-MESH or SC-E integration is selected or required by its declared package/import graph and exercised Station/Mission/OpenClaw paths. No broader D4 code is imported. Re-evaluate if the target source, packaging, required runtime path or deployment contract changes.

## Evidence and distinctions

`evidence/runner-mesh-20261007/audit.json` binds lineage HEAD/TREE values, ancestry checks, absent lineage-specific runtime paths, manifest Git blobs/SHA-256 values, complete local wheel member hashes and Node package member hashes.

All three historical heads are non-ancestors. #400's bridge module/service and #404/#493's Station mesh, mesh_cli, mesh_worker, mesh_runner, mesh_outbox, mesh_state, claw_adapter, continuity and service are absent. Ancestry alone is not the dependency proof: source/package membership, imports, declared dependencies and installed execution were also checked.

The wheel DOES contain `residual/mesh/__init__.py` and `residual/mesh/node.py`, identical by Git blob to accepted main. This earlier federated-mesh prototype is not the Station SC-MESH lineage. Therefore this audit does not claim that no mesh-named code exists. UI 'Shared comms' labels likewise do not establish a D4 dependency.

Python package discovery includes residual, ai_providers and observation_layer. Runtime dependency is defusedxml; factory extras add cryptography and PyYAML. No SC package, direct VCS dependency or SC entrypoint is declared. Both OpenClaw package manifests have no external npm dependencies; imports use local files and Node built-ins. The host OpenClaw runtime is still a native qualification dependency, not an inferred SC-E dependency. `station-worker.mjs` uses ordinary `/api/worker/` routes; OpenClaw compatibility explicitly excludes native SC-MESH and reports `sc_mesh:false`.

## Fresh bounded validation

- Python 3.12, Node 24.19.0; source tests: 21 passed plus 8 subtests.
- OpenClaw control suite: 185 passed.
- Unmodified `scripts/prove_mission_wheel.py`: PASS, fresh isolated install outside checkout with poisoned cwd; 360 source-matched installed files, matching kernel revision, entrypoints and missing-input rejection, five real Station/client scenarios.
- Installed proof wheel SHA-256: `052be4cbebec8b8c6af81aef6bf19b6c82af57ac02d8c57b0bba366b61bde312`.
- Separate no-build-isolation inventory wheel SHA-256: `d2738a25661e5122319f69953c8c17e35ff35ac6475aa55a98a75e87ae8a1b7e`. These are distinct builds, not a reproducibility claim. Both derive from the same clean candidate. Installed proof report and build/install logs identify its actual artifact separately.

No installed live-host inventory was available. This is a fresh package installation proof, not a statement about DELL/LEGION/DBOX deployments, arbitrary plugins or unexercised external configurations. Native hooks, physical lifecycle, independent review, protected Factory ownership and whole-composition release qualification remain unclosed. The earlier local missing-pytest attempt is retained as an environment limitation in the audit; the final source suite passed after installing the test dependency.

## Ledger disposition

READY_FOR_REVIEW for the bounded runner/mesh composition binding. Closure may consume this exact evidence without selecting historical D4 branches. This does not qualify the entire v1 product, change any frozen candidate, or transfer evidence to a successor. No merge, deployment, credential, release or gate change.
