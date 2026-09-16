# Implementation Status

<!-- GENERATED FILE. Source of truth: implementation-status.yaml.
     Regenerate with: python3 scripts/status_check.py --generate -->

Requirement families: 39 total - 23 implemented, 0 implemented (closure unverified), 12 partial, 4 not started.

| Family | Title | Status | Spec | Code | Tests |
|---|---|---|---|---|---|
| SPEC-001 | GoalSpec | implemented | `harness_specs/SPECS.md` | `residual/goalspec.py` | `tests/test_foundation.py`, `tests/test_loop_layer.py` |
| SPEC-002 | Verifier | implemented | `harness_specs/SPECS.md` | `residual/verifier.py` | `tests/test_foundation.py`, `tests/test_harness.py` |
| SPEC-003 | Brakes | implemented | `harness_specs/SPECS.md` | `residual/brakes.py` | `tests/test_loop_layer.py`, `tests/test_harness.py` |
| SPEC-004 | QuarantineStore | implemented | `harness_specs/SPECS.md` | `residual/quarantine.py` | `tests/test_loop_layer.py`, `tests/test_foundation.py` |
| SPEC-005 | ContextCurator | partial | `harness_specs/SPECS.md` | `residual/loop.py` | `tests/test_loop_layer.py` |
| SPEC-006 | SubAgentPool | partial | `harness_specs/SPECS.md` | `residual/loop.py` | `tests/test_loop_layer.py` |
| SPEC-007 | LoopController | implemented | `harness_specs/SPECS.md` | `residual/loop.py`, `residual/lifecycle.py` | `tests/test_loop_layer.py` |
| SPEC-008 | HarnessPass | implemented | `harness_specs/SPECS.md` | `residual/engine.py`, `residual/core.py` | `tests/test_harness.py`, `tests/test_foundation.py` |
| NETOPS | NetOps Station Module | partial | `harness_specs/NETOPS_SECOPS_SPECS.md` | `residual/modules/netops.py` | `tests/test_tracks_2_8.py`, `tests/modular/test_adapters.py` |
| SECOPS | SecOps Station Module | implemented | `harness_specs/NETOPS_SECOPS_SPECS.md` | `residual/modules/secops.py` | `tests/test_tracks_2_8.py`, `tests/modular/test_adapters.py` |
| MODULE | Unified Module Registration Interface | implemented | `harness_specs/NETOPS_SECOPS_SPECS.md` | `residual/modules/adapters.py`, `residual/extensions.py` | `tests/test_tracks_2_8.py`, `tests/test_extension_integration.py` |
| VRB | Verifier-Receipt Binding | implemented | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/receipts.py` | `tests/test_foundation.py`, `tests/test_harness.py` |
| REG | Station Extension Registry | implemented | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/station/extensions.py` | `tests/test_extension_integration.py` |
| HITL | Human-in-the-Loop Gateway | implemented | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/hitl/gateway.py` | `tests/test_loop_layer.py`, `tests/test_extension_integration.py` |
| MEM | Verified Memory | partial | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/memory/store.py` | `tests/test_loop_layer.py` |
| TRJ | Trajectory Recording | partial | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/trajectory/recorder.py` | `tests/test_loop_layer.py` |
| TUI | Operator TUI Dashboard | implemented | `harness_specs/WORLD_CLASS_SPECS.md` | `residual/tui/dashboard.py` | `tests/test_loop_layer.py` |
| GAP1 | Engine Adapter Layer | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `residual/engines/protocol.py`, `residual/engines/langgraph_adapter.py`, `residual/engines/crewai_adapter.py`, `residual/engines/sdk_adapter.py`, `residual/engines/_isolated.py` | `tests/test_gap_closure.py`, `tests/test_tracks_2_8.py` |
| GAP2 | Async I/O Integration | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `residual/async_io/coordinator.py`, `residual/async_io/server.py`, `residual/async_io/sink.py`, `residual/async_io/telemetry.py` | `tests/test_gap_closure.py`, `tests/test_tracks_2_8.py` |
| GAP3 | Prometheus Metrics Export | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `residual/observability/metrics.py`, `residual/observability/exporter.py`, `residual/observability/http.py` | `tests/test_gap_closure.py`, `tests/test_extension_integration.py` |
| GAP4 | Module Lifecycle Wiring | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `residual/station/extensions.py`, `residual/extensions.py` | `tests/test_gap_closure.py`, `tests/test_extension_integration.py` |
| GAP5 | Module Marketplace | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `residual/marketplace/registry.py`, `residual/marketplace/install.py`, `residual/marketplace/loader.py`, `residual/marketplace/signing.py`, `residual/marketplace/validate.py` | `tests/test_gap_closure.py`, `tests/test_publish.py` |
| GAP6 | Documentation and Onboarding | implemented | `harness_specs/GAP_CLOSURE_SPECS.md` | `docs/quickstart.md`, `docs/module-tutorial.md`, `docs/faq.md` | `tests/test_gap_closure.py` |
| ECO | Ecosystem (Engine Adapters, Marketplace, Docs) | implemented | `harness_specs/PHASE_4_5_SPECS.md` | `residual/engines/protocol.py`, `residual/engines/langgraph_adapter.py`, `residual/engines/crewai_adapter.py`, `residual/engines/sdk_adapter.py`, `residual/marketplace/registry.py` | `tests/test_gap_closure.py`, `tests/test_publish.py` |
| PROD | Production Hardening (Validation, Async, Observability) | partial | `harness_specs/PHASE_4_5_SPECS.md` | `residual/async_io/coordinator.py`, `residual/observability/metrics.py`, `residual/observability/exporter.py` | `tests/test_gap_closure.py`, `tests/enterprise/test_integrations.py` |
| PQC | Post-Quantum Cryptographic Agnosticism | not_started | `harness_specs/RESILIENCE_SPECS.md` | - | - |
| MAI | Model-Agnostic Reasoning Interface | partial | `harness_specs/RESILIENCE_SPECS.md` | `residual/providers.py`, `residual/engines/provider_bridge.py` | `tests/test_providers.py` |
| FMV | Formal Methods & Program-Synthesized Verifiers | not_started | `harness_specs/RESILIENCE_SPECS.md` | - | - |
| APC | Autonomous Policy Auto-Calibration | partial | `harness_specs/RESILIENCE_SPECS.md` | `residual/assurance/quality.py` | `tests/test_adaptive_assurance.py` |
| FED | Federated Multi-Station Trust Meshes | not_started | `harness_specs/RESILIENCE_SPECS.md` | - | - |
| MESH | Mesh Networking | partial | `harness_specs/MESH_SPECS.md` | `residual/mesh/node.py` | `tests/test_control_integrity.py`, `tests/test_tracks_2_8.py` |
| STUDIO | Residual Studio Platform | partial | `harness_specs/STUDIO_SPECS.md` | `residual/factory/compiler.py`, `residual/factory/models.py`, `residual/station/server.py`, `residual/station/service.py` | `tests/test_factory_compiler.py`, `tests/station/test_station.py` |
| M2 | Worker Contract + Swarm Runtime | implemented | `harness_specs/M2_M3_M4_SPECS.md` | `residual/factory/worker_contract.py`, `residual/factory/runtime.py`, `residual/factory/runtime_journal.py`, `residual/factory/runtime_workspace.py` | `tests/test_factory_worker_contract.py`, `tests/test_factory_runtime.py` |
| M3 | Evidence Bus + Receipts | implemented | `harness_specs/M2_M3_M4_SPECS.md` | `residual/factory/evidence_bus.py`, `residual/factory/evidence_receipts.py` | `tests/test_factory_evidence_bus.py` |
| M4 | Deterministic Integrator + Scheduler Intelligence | implemented | `harness_specs/M2_M3_M4_SPECS.md` | `residual/factory/m4_integrator.py`, `residual/factory/m4_scheduler.py`, `residual/factory/m4_evidence.py` | `tests/test_factory_m4_integrator.py`, `tests/test_factory_m4_scheduler.py`, `tests/test_factory_m4_evidence.py` |
| EVAL | Evaluation Framework | implemented | `harness_specs/M2_M3_M4_SPECS.md` | `residual/eval/runner.py`, `residual/eval/workload.py`, `residual/eval/stats.py`, `residual/eval/report.py`, `residual/eval/measured_factory.py` | `tests/test_eval_runner.py`, `tests/test_eval_workload.py`, `tests/test_eval_stats.py`, `tests/test_measured_factory_eval.py` |
| CP | Control Plane (Engine Protocol, Routing, Sandbox) | partial | `harness_specs/CONTROL_PLANE_SPECS.md` | `residual/engines/protocol.py`, `residual/engines/router.py`, `residual/engines/_isolated.py`, `residual/engines/probe.py` | `tests/test_gap_closure.py`, `tests/test_control_integrity.py` |
| N9 | Path to 9.5 (Engines, Soak, Async, Cluster, Docs) | partial | `harness_specs/PATH_TO_10_SPECS.md` | `residual/engines/protocol.py`, `residual/async_io/coordinator.py`, `residual/mesh/node.py`, `docs/quickstart.md`, `docs/module-tutorial.md`, `docs/faq.md` | `tests/test_gap_closure.py`, `tests/test_control_integrity.py` |
| T10 | Path to 10 (Research Frontiers) | not_started | `harness_specs/PATH_TO_10_SPECS.md` | - | - |

## Notes

### SPEC-001 - GoalSpec (implemented)

Immutable GoalSpec with ordered success criteria and amendment versioning in residual/goalspec.py.

### SPEC-002 - Verifier (implemented)

Ordered mechanical/structural/judge evaluation with structured verification reports.

### SPEC-003 - Brakes (implemented)

Token/time brakes operate between waves.

### SPEC-004 - QuarantineStore (implemented)

Provider-call quarantine is wired; routing of EVERY arbitrary side-effecting action through the quarantine gateway is Swarm 6 (track D) scope and remains open.

### SPEC-005 - ContextCurator (partial)

Goal-directed context curation is specification-level; scoped packet compilation exists in the loop layer.

### SPEC-006 - SubAgentPool (partial)

Isolated sub-agent pool is specification-level; worker leases already exist in the loop layer.

### SPEC-007 - LoopController (implemented)

Station loop controller with lifecycle adapters.

### SPEC-008 - HarnessPass (implemented)

Core harness pass with verifier-defined acceptance.

### NETOPS - NetOps Station Module (partial)

Imported and integrated; requires a host telemetry client and has no live device executor.

### SECOPS - SecOps Station Module (implemented)

Runs before staging; integrated with the module registry.

### MODULE - Unified Module Registration Interface (implemented)

Unified module registration with station extension registry.

### VRB - Verifier-Receipt Binding (implemented)

Versioned envelopes, prerequisite propagation, exact-revision receipts and cache revalidation (v0.4.0).

### REG - Station Extension Registry (implemented)

Freeze at controller construction, fresh brakes, isolated diagnostics (v0.4.0).

### HITL - Human-in-the-Loop Gateway (implemented)

Authenticated-host HITL API; automatic resume after HITL is Swarm 6 (track E) scope and remains open.

### MEM - Verified Memory (partial)

Local indexing implemented; verified retrieval with provenance binding is Swarm 6 (track E) scope.

### TRJ - Trajectory Recording (partial)

Recorder and structural comparison implemented; full tool replay and deterministic resume remain absent (Swarm 6 scope).

### TUI - Operator TUI Dashboard (implemented)

Operator dashboard with lifecycle adapters.

### GAP1 - Engine Adapter Layer (implemented)

ExecutionEngine protocol with LangGraph/CrewAI/SDK adapters and isolated-process execution.

### GAP2 - Async I/O Integration (implemented)

Async periphery with buffered observation sink; synchronous verification core unchanged.

### GAP3 - Prometheus Metrics Export (implemented)

Metrics export implemented; SLO definitions and alert rules are Swarm 7 (track N) scope.

### GAP4 - Module Lifecycle Wiring (implemented)

Host lifecycle dispatch with frozen registry.

### GAP5 - Module Marketplace (implemented)

Registry, install, loader, signing and validation.

### GAP6 - Documentation and Onboarding (implemented)

Quickstart, module tutorial and FAQ exist; executable docs tests are Swarm 8 (track O) scope.

### ECO - Ecosystem (Engine Adapters, Marketplace, Docs) (implemented)

ECO-001..006 covered by the engines and marketplace packages plus docs/quickstart.md and docs/module-tutorial.md.

### PROD - Production Hardening (Validation, Async, Observability) (partial)

PROD-002 async I/O and PROD-003 observability export implemented; PROD-001 production validation protocol remains partially manual (scripted validation only).

### PQC - Post-Quantum Cryptographic Agnosticism (not_started)

Crypto migration is future work; no abstraction layer exists. KMS/HSM abstraction is Swarm 7 (track L) scope.

### MAI - Model-Agnostic Reasoning Interface (partial)

Bounded provider adapters exist; the formal intention-adapter interface from RESILIENCE_SPECS Layer 2 is specification only.

### FMV - Formal Methods & Program-Synthesized Verifiers (not_started)

Specification only; no formal verifier certificates exist.

### APC - Autonomous Policy Auto-Calibration (partial)

Adaptive assurance with verifier-quality profiles exists; autonomous policy auto-calibration per RESILIENCE_SPECS Layer 4 is not complete.

### FED - Federated Multi-Station Trust Meshes (not_started)

Federation and fork reconciliation remain future work per docs/roadmap/README.md.

### MESH - Mesh Networking (partial)

Local in-memory mesh protocol and receipt-export adapter implemented; authenticated network transport is Swarm 3 (track F) scope.

### STUDIO - Residual Studio Platform (partial)

Requirement compiler (STUDIO-002) and station surfaces exist. The canonical Factory swarm runtime, evidence bus and deterministic integrator (STUDIO-003/004/008 mechanisms) are merged under residual/factory/ - see families M2/M3/M4 (M4 closure verified; issue 63 closed by PR 81). Still partial rather than complete - cluster (STUDIO-006), IDE (STUDIO-007) and the Studio frontend (residual/studio_frontend/) remain stubs/prototypes and must not be conflated with the canonical Factory runtime.

### M2 - Worker Contract + Swarm Runtime (implemented)

Canonical Factory swarm runtime merged under residual/factory/ (worker contract, runtime, journal, workspace); covered by factory runtime/worker-contract tests. This is the merged M2 mechanism, not the open swarm lanes in PRs 39-44.

### M3 - Evidence Bus + Receipts (implemented)

Canonical Factory evidence bus and evidence receipts merged under residual/factory/ with fixture test coverage. Git evidence semantics for the M4 integrator remain part of the open trust-boundary closure tracked in issue 63 (see family M4).

### M4 - Deterministic Integrator + Scheduler Intelligence (implemented)

Closure: #63 closed by #81 (de9c9fa): verified-tree binding, NOFOLLOW writes, Linux-userns isolated verifier, typed git evidence - independently reviewed

Canonical M4 deterministic integrator, scheduler and M4 evidence modules merged under residual/factory/ with fixture test coverage. Trust-boundary closure verified - issue 63 (accepted-tree binding, filesystem safety, OS-isolated verification, git evidence semantics) was closed by PR 81 (de9c9fa) - verified-tree binding, NOFOLLOW writes, Linux-userns isolated verifier, typed git evidence - independently reviewed.

### EVAL - Evaluation Framework (implemented)

residual/eval/ exists (runner, workload, stats, report, measured factory evaluation) with unit coverage. residual/evaluation.py remains the frozen controlled study, a different artifact. Fixture-level green runs are not live empirical closure of research claims.

### CP - Control Plane (Engine Protocol, Routing, Sandbox) (partial)

CP-001 adapter protocol, CP-002 capability routing and CP-003 cross-engine verification implemented; CP-004 sandbox isolation is process-level only - cgroup/FS/network enforcement is Swarm 2 (track B) scope.

### N9 - Path to 9.5 (Engines, Soak, Async, Cluster, Docs) (partial)

N9-R1..R8 engine adapters, N9-R13..R17 async I/O and N9-R24..R28 docs implemented; N9-R9..R12 soak harness is Swarm 5 (track Q) scope; N9-R18..R23 cluster wire protocol and CLI are Swarm 3 (tracks F/G) scope.

### T10 - Path to 10 (Research Frontiers) (not_started)

Research tracks (zk proofs, hardware-rooted attestation, adversarial hypothesis quality, epistemic merging) per docs/roadmap/README.md; no production claim.

## Historical documents

The following are frozen point-in-time snapshots. Their claims do not reflect current code and are excluded from the stale-doc check:

- `harness_specs/V040_ASSESSMENT.md`
- `harness_specs/GAP_ANALYSIS.md`
- `docs/roadmap/source/DESIGN.md`
- `docs/roadmap/source/GAP_ANALYSIS.md`
- `docs/roadmap/source/MESH_SPECS.md`
- `docs/roadmap/source/NETOPS_SECOPS_SPECS.md`
- `docs/roadmap/source/RESILIENCE_SPECS.md`
- `docs/roadmap/source/SPECS.md`
- `docs/roadmap/source/WORLD_CLASS_SPECS.md`
