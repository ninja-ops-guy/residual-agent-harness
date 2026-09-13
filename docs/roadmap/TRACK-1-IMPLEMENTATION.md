# Track 1 implementation — 0.4.0

Track 1 is implemented on `feat/receipt-extension-foundation`. The uploaded Tracks 2–8 have been merged as new files, with integration and integrity fixes. Older core files in that archive did not replace the already integrated provider, observation, control, or web code. Original import hashes are in `TRACKS-SOURCE.json`.

## Interfaces other tracks can use now

```python
from residual import (
    StationReceipt, ReceiptReference, StationExtensionRegistry,
    StationModule, VerifierDescriptor, VerifierRevision,
    CheckResult, CheckType, LoopController,
)
```

A `StationReceipt` has seven immutable payload fields. `to_dict()` produces the versioned SHA-256 envelope; `from_dict()` / `from_json()` reject altered, unknown-profile, duplicate-key, or noncanonical envelopes. `parent_receipts` references prerequisites, sorted by task ID. `validate_receipt_graph()` checks an exact DAG. A receipt hash establishes integrity, never execution authority.

`VerifierRevision(implementation_hash, configuration_hash, policy_hash, proof_hash=None)` requires full lowercase SHA-256 identities. `from_artifact(path, configuration=..., policy=...)` hashes an explicitly host-selected implementation artifact and immutable JSON configuration. Descriptors also bind the declared check type. Hosts must include all implementation dependencies and policy identities that can change semantics; Python cannot discover or freeze arbitrary external services or mutable closures reliably.

Modules return local verifier names. Registration prefixes them exactly once (`secops:sast_scan`); fully prefixed declarations and duplicate domains fail. `register_module(module, revisions={...})` adapts the uploaded `(CheckType, callable)` tuples only with explicit revision material. `policies()`, `verifiers()`, `brakes()` expose validated composition surfaces. `register_checks(legacy_registry)` adapts descriptors to the obligation harness.

`LoopController(spec, Verifier({}), harness, extensions=registry)` freezes and composes the registry at construction. Registered verifiers augment host evaluators without shadowing them. Every run creates fresh extension brakes and invokes lifecycle hooks in registration order. Open-hook/factory/enforcement failures abort before another dispatch; close-hook and read-only observation failures become safe diagnostics. A registry cannot be shared by concurrent active runs. Registry registration and metadata are frozen; trusted host Python objects and clients are still the host's responsibility.

There is no dynamic plugin discovery, arbitrary Python loading from chat, or annotation-based assumption that a runtime return is valid. Policies still run through `QuarantineStore`; registration alone does not guard an executor. The station applies them before file writes and provider calls. Invalid policy values deny, and invalid brake behavior aborts. `UNKNOWN` preserves the first non-pass finding and prevents later judges from running.

## What runs in the web station

The default per-project registry contains SecOps, station acceptance/integration/review checks, a dashboard collector, trajectory recording, and memory indexing. Pass an explicit `Station(root, extension_factory=...)` to add host-configured modules. Start from `default_registry(station, project_id)` to retain the built-in station criteria.

- File proposals go through quarantine before writing; SecOps scans declared candidate files before Git staging and again before integration. This is a credential heuristic, not a complete SAST engine. Legitimate test fixtures containing credential assignments may require a custom host policy.
- Integration re-runs local checks and binds the exact candidate, check receipt, reviewer receipt, original Markdown manifest and prerequisite receipt hashes. Stale prerequisites block dispatch. Release export revalidates station receipt context as well as existing Git revision gates.
- Task drawers show the receipt identity and prerequisite count; full envelopes are downloadable evidence. Markdown and deterministic reports contain compact receipt references.
- Durable run-open/close events precede lifecycle hooks even when optional observations are disabled. Run-control evidence includes the module inventory and diagnostic failures.
- Structural trajectories record host criterion order/results without inference. They normalize duration, compare fingerprints, and verify stored content hashes. This is comparison of observed structure, not a full replay of external tools.
- Memory uses full goal-description hashes and receipt-bound values, with a versioned integrity envelope. `retrieve_verified(..., verifier_revision=..., verify=host_callback)` requires active context-aware host verification. The station indexes results; it does not inject memories into prompts automatically.

## Module integration boundaries

| Module | Delivered integration | Remaining host work / limits |
|---|---|---|
| TUI | `DashboardModule`, thread-safe collector snapshots, restartable portable renderer | Opt-in terminal rendering; web UI remains the main interface |
| Trajectory | `TrajectoryModule`, close hook, persisted structural artifact | Golden-suite selection and full witness/tool replay |
| Memory | `MemoryModule`, successful-close index, active-verifier retrieval API | Retrieval policy and model context curation |
| HITL | `HITLModule`, escalation-only challenge generation; signed full challenge, SQLite single-use consumption | Supply an authenticator bound to the exact operator/session/challenge. No default approval or automatic resume/amendment |
| Mesh | `MeshModule`, close-hook export of compact receipt references, immutable messages and host-injected signature validation | Single linear chain only; no transport, fork merge, membership quorum, E2E encryption, discovery or automatic execution |
| NetOps | Registry-compatible injected telemetry, scoped policies, bounded stabilization and emergency/drift brakes | Explicit host telemetry client and revision material; no live device executor. Config syntax checks remain heuristics |
| SecOps | Default station policy and pre-staging SAST hook; namespaced verifiers and brakes | Complete SAST/SBOM/policy engines and authoritative telemetry sources |

HITL approvals in the upload compared the response to the challenge's own signature. That path now denies unless a host authenticator returns literal `True`. IDs, expiry, allowed roles, spec/action and status are MAC-bound; approval consumption is atomic across processes. Callers must implement authenticated operator identity. The gateway never turns an abort into escalation or resumes work by itself. Existing JSON challenge records are not silently migrated into trusted approvals.

Mesh is explicitly a protocol prototype. Its legacy `revoker_signature` argument is not an authorization proof; revocation is a trusted local host operation. A received task result is an inert peer claim. Do not expose host admission/revocation methods directly as remote RPCs.

## Cache compatibility

The obligation harness emits new envelopes in the separate `station_receipts` map for verifiers with explicit identities and entirely modern prerequisite chains. Existing `receipts` remain the original format. Built-in JSON verifiers declare their source artifact identity; custom checks opt in using `Registry.check(..., identity=VerifierRevision(...))`. Legacy checks keep their documented legacy behavior and are not silently represented as modern receipts.

Modern cache entries contain the value and its receipt under `residual.station.cache.entry.v1`. Their keys include task/project scope, goal and obligation hashes, artifacts, effective verifier revision/type and prerequisite identities. Retrieval validates these before running the active host verifier again. Changing a root verifier invalidates dependent modern cache keys even if its resulting value is unchanged. A cache never grants acceptance. The obligation API binds its own Task/Obligation contract; station receipts bind the full original Markdown manifest. The schemas remain distinct from GoalSpec run-control evidence.

Old station projects can still be inspected. An integrated task without a current station receipt cannot be reused as a verified prerequisite or exported under the new gate; create a fresh mission from its specification to re-run checks and review. Old 16-character memory indexes and old HITL JSON approvals are not silently trusted or relabeled.

## Validation and remaining work

See `../station/FOUNDATION-VALIDATION.md` for executed tests, package checks and CI links. No paid cloud request, real Ollama/GPU inference, live network-device mutation, authenticated multi-device transport, or production deployment is claimed by these tests. Token/cost savings and long-horizon reliability still require measured workloads.

The research frontiers (zk/TEE, TPM, CRDT proof, PQC migration, formal-methods adapters and autonomous calibration) remain outside this implementation. ContextCurator and SubAgentPool remain future work. Existing provider async/streaming support is retained; Bedrock streaming is still explicitly unsupported.
