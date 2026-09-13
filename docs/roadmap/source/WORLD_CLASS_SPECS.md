# Residual Command Station — World-Class Architecture Specifications

**Version:** 2.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v0.3.0 → v1.0.0
**Depends on:** goalspec.py, verifier.py, brakes.py, quarantine.py, loop.py, integration.py, NETOPS_SECOPS_SPECS.md

---

## Part 1: Verifier-Receipt Binding Mechanics

### Purpose
Define the cryptographic binding between cache keys, verifier revisions,
and receipt propagation. This is the foundation that all other modules
depend on — it is what makes caching safe under dynamic policy change.

### Requirements

**VRB-R1.** A `StationReceipt` MUST bind exactly these fields:
`task_id`, `cache_key`, `value_hash`, `verifier_name`,
`verifier_revision`, `verdict`, `parent_receipts`. The receipt hash
MUST be computed over all fields including the concatenated parent
receipt hashes.

**VRB-R2.** The `cache_key` MUST be a deterministic function of:
protocol version, task ID, goal content hash, obligation contract hash,
verifier name, verifier revision, artifact content hashes, and parent
receipt hashes. Any change to any input MUST produce a different
cache key.

**VRB-R3.** When a module's verifier revision increments (e.g., NetOps
threshold change, SecOps pattern update), the cache key MUST
automatically invalidate for all dependent tasks. No manual cache
flush is permitted or required.

**VRB-R4.** On cache hit, the station MUST revalidate: the stored
receipt's `verifier_revision` MUST equal the currently active module
version. Mismatch MUST treat the cache entry as absent.

**VRB-R5.** Receipts MUST propagate up the DAG. A parent task's receipt
MUST include the hashes of all child receipts. A change to any child
receipt MUST invalidate all ancestor cache keys.

**VRB-R6.** The `verdict` field MUST be exactly one of `pass`, `fail`,
`unknown`. `unknown` MUST NOT be cached as `pass`. Cached `unknown`
entries MUST be re-evaluated on every access.

### Contract Binding Format

```python
verifier_binding = {
    "verifier_name": "netops:telemetry_stabilization_verifier",
    "verifier_revision": "v1.2.0-netops",
    "execution_order": "mechanical",
}
```

The `verifier_name` MUST use the `{domain}:{evaluator}` namespacing
convention. The `execution_order` MUST match the `CheckType` of the
registered evaluator.

---

## Part 2: Station Extension Registry

### Purpose
Define the unified plugin bus that allows operational modules to
register into the station without modifying core code.

### The Registry

```python
class StationExtensionRegistry:
    def __init__(self):
        self._quarantine_hooks: list[Callable] = []
        self._brake_hooks: list[Callable] = []
        self._verifiers: dict[str, tuple[CheckType, Callable]] = {}
        self._modules: dict[str, Any] = {}

    def register_module(self, module: Any, domain_name: str) -> None:
        """Register a module by inspecting its hook interfaces."""
        ...

    def intercept_quarantine(self, action: ProposedAction) -> Optional[str]:
        """Returns denial reason or None. Called by QuarantineStore."""
        ...

    def evaluate_extension_brakes(self, event: dict) -> Optional[BrakeTrip]:
        """Returns BrakeTrip or None. Called by LoopController."""
        ...

    def get_verifier(self, key: str) -> Optional[tuple[CheckType, Callable]]:
        """Resolves prefixed verifier names."""
        ...
```

### Requirements

**REG-R1.** The registry MUST be the sole integration point for
modules. No module MAY modify engine.py, station/service.py, loop.py,
quarantine.py, or verifier.py.

**REG-R2.** Quarantine hooks MUST conform to the `Policy` signature:
`(ProposedAction) -> Optional[str]`. Boolean returns MUST be rejected
at registration with `ContractError`.

**REG-R3.** Brake hooks MUST conform to the `Brake` protocol:
`update(event: dict) -> Optional[BrakeTrip]`. The draft's
`check_{domain}_brakes(run_state) -> tuple[bool, str]` signature MUST
be adapted via a wrapper that converts to the Brake protocol.

**REG-R4.** Verifier keys MUST be namespaced as `{domain}:{evaluator_name}`
at registration. Unprefixed names MUST be rejected.

**REG-R5.** Verifier name collisions across modules MUST raise
`ContractError` at registration time.

**REG-R6.** The registry MUST be immutable after LoopController
construction. `register_module` MUST raise `ContractError` if called
after `LoopController.run()` has been invoked.

**REG-R7.** Module observations MUST use the `custom` event kind with
`{domain}_{event_name}` namespacing.

### Draft Code Corrections

| Draft Pattern | Correct Pattern | Reason |
|---|---|---|
| `quarantine_hooks: List[Callable[[Dict], bool]]` | `List[Policy]` where `Policy = (ProposedAction) -> Optional[str]` | SPEC-004-R2: silent denial needs reason strings |
| `brake_hooks: List[Callable[[Dict], Tuple[bool, str]]]` | `List[Brake]` protocol implementations | SPEC-003-R1: brakes are event-driven, not state-polling |
| `intercept_quarantine(proposed_action: Dict) -> bool` | `(ProposedAction) -> Optional[str]` | QuarantineStore evaluates ProposedAction, not raw dicts |
| `evaluate_extension_brakes(run_state: Dict) -> Tuple[bool, str]` | `Brake.update(event) -> Optional[BrakeTrip]` | Brakes subscribe to observations, not poll run state |

---

## Part 3: Four Pillars — World-Class Additions

### Pillar 1: Interactive TUI Control Station

**Purpose:** Real-time operational visibility for NetOps and SecOps
execution.

**Requirements:**

**TUI-R1.** The TUI MUST be a read-only consumer of the observation
bus. It MUST NOT inject events, modify state, or send control signals
to the LoopController. Abort signals MUST go through the existing
`BrakeAction.ABORT` path, not through the TUI.

**TUI-R2.** The TUI MUST render from observed events, not from direct
access to engine or station internals. It subscribes to the same
observation stream that the LoopController emits.

**TUI-R3.** The TUI MUST display at minimum: run ID, current pass
number, token budget usage, brake states, quarantine hold count,
per-task verdicts, and NetOps/SecOps module status.

**TUI-R4.** The TUI MUST NOT block the synchronous execution path.
It runs in a separate thread or process, consuming events
asynchronously. The engine MUST NOT wait for the TUI.

**TUI-R5.** TUI refresh rate MUST be configurable (default 4 Hz).
The TUI MUST NOT emit observations at a rate that overwhelms the bus.

**TUI-R6.** If the TUI crashes, the station MUST continue executing.
TUI failure MUST NOT propagate to the LoopController.

### Pillar 2: Trajectory Regression Test Suites

**Purpose:** Capture and replay execution traces to prevent behavioral
regressions across module, verifier, and model updates.

**Requirements:**

**TRJ-R1.** A trajectory MUST be recorded for every run, regardless
of outcome. The trajectory MUST include: ordered tool calls with
fingerprints, inputs, outputs, verifier verdicts per check, brake
trips, and final RunOutcome.

**TRJ-R2.** Trajectories MUST be content-addressed by the SHA-256 of
their canonical serialization. The trajectory hash MUST be emitted
as a `checkpoint` observation at run close.

**TRJ-R3.** A trajectory MUST be loadable as a regression test. The
regression engine MUST replay the trajectory against the current
verifier set and compare outcomes.

**TRJ-R4.** A regression test MUST FAIL if any of the following change:
- Tool call sequence (names or order)
- Verifier verdicts for any check
- Brake trip decisions
- Final RunOutcome

**TRJ-R5.** The regression engine MUST NOT compare raw model outputs
(text). Model outputs are non-deterministic. The regression surface
is the structural trace: calls, verdicts, brakes, outcome.

**TRJ-R6.** Trajectories MUST be stored in the golden store with their
GoalSpec content hash. A regression test MUST only run against
trajectories with matching GoalSpec hashes.

### Pillar 3: Cross-Session Epistemic Memory

**Purpose:** Index past run receipts and validated solutions for
retrieval across execution windows.

**Requirements:**

**MEM-R1.** The memory store MUST be content-addressed. Keys MUST be
derived from the SHA-256 of the goal description, truncated to 16
hex characters.

**MEM-R2.** Memory entries MUST include: goal description, receipt
hash, artifact payload, verifier revision, and timestamp. Entries
MUST NOT include raw model outputs, chain-of-thought, or unverified
agent claims.

**MEM-R3.** Memory retrieval MUST be read-only during a run. The
memory store MUST NOT be written to during active execution. Writes
occur at run close, after final verification.

**MEM-R4.** Memory entries MUST be validated before retrieval. An
entry whose receipt hash does not verify against the stored receipt
MUST be treated as absent.

**MEM-R5.** The memory store MUST NOT replace the observation layer's
event log. It is a derived index, not a primary store. The event log
remains the authoritative record.

### Pillar 4: Cryptographic HITL Escalation Gateways

**Purpose:** Graceful human escalation for borderline quarantine
denials and brake trips, replacing hard aborts with signed review
workflows.

**Requirements:**

**HITL-R1.** When a brake trip recommends `ESCALATE` and the
`AmendmentRule` does not resolve it, the LoopController MUST generate
a `HITLChallenge` containing: task ID, proposed action, denial/trip
reason, GoalSpec hash, and timestamp.

**HITL-R2.** The challenge MUST be HMAC-signed with the station's
signing key. The signature MUST cover the entire challenge payload.

**HITL-R3.** The challenge MUST be emitted as a `checkpoint`
observation and written to a durable queue. The queue MUST survive
process restart.

**HITL-R4.** Upon receiving an operator response, the station MUST
verify: (a) the challenge signature, (b) the operator's authorization
role against `AmendmentRule.authorized_roles`, (c) the response
timestamp is within the challenge validity window.

**HITL-R5.** A verified approval MUST produce an amended GoalSpec
with `amendment_reason` set to the HITL challenge ID. The run MUST
restart under the amended spec. The outcome MUST be `AMENDED`.

**HITL-R6.** A verified denial MUST produce `RunOutcome.ESCALATED`
with the HITL challenge ID in the trip reasons. The run MUST NOT
continue.

**HITL-R7.** HITL challenges MUST NOT be generated for
`BrakeAction.ABORT` trips. Abort is immediate and non-negotiable.
HITL applies only to `ESCALATE` decisions.

**HITL-R8.** The signing key MUST NOT be stored in the observation
log, the memory store, or any artifact that crosses the disclosure
lattice. Key management is out of scope for this spec.

---

## Part 4: Four Frontiers — Novel Research Directions

These are speculative capabilities that push beyond current practice.
Each is specified at the architecture level, not the implementation
level. Implementation requires research prototypes before production
integration.

### Frontier 1: zk-Verifier Proofs for Cloud Escalation

**Concept:** When a task escalates from local Ollama to a cloud
provider, require the cloud provider to return a cryptographic proof
of contract adherence without revealing intermediate reasoning.

**Current feasibility:** Low. zk-SNARK circuits for arbitrary LLM
computation are not practical. The draft's HMAC commitment is not a
zero-knowledge proof — it is a keyed hash. HMAC proves knowledge of
the key, not correctness of computation.

**Honest assessment:** This frontier requires either:
- A trusted execution environment (TEE) on the cloud side that
  produces attested execution traces (Intel SGX, AMD SEV, AWS Nitro)
- A verifiable computation framework (zkVM) applied to the specific
  verifier circuit, not the LLM itself
- A proxy re-encryption scheme where the cloud model operates on
  encrypted inputs and returns encrypted outputs with correctness
  proofs

**What CAN be built now:** The commitment wrapper from the draft.
Bind the task contract hash, verifier revision, and input hashes into
an HMAC commitment before sending to the cloud. On return, verify
the response against the commitment. This prevents tampering in
transit but does not prove the cloud model computed correctly.

**Spec level:** Architecture sketch only. Do not implement the
HMAC wrapper and call it zk. Label it `CloudEscalationCommitment`
and document its actual security properties honestly.

### Frontier 2: Popperian Self-Falsification Engine

**Concept:** Before QuarantineStore releases a proposed action, an
adversarial sub-agent generates falsification hypotheses and tests
the action against them in a sandbox.

**Feasibility:** Moderate. The mechanism is clear: a counter-agent
with sandbox access tries to break the proposed patch. The hard part
is generating meaningful falsification hypotheses, not running them.

**What CAN be built now:** The sandbox runner and the falsification
loop. The hypothesis generation is the research problem — it requires
a model capable of adversarial reasoning about the specific domain
(NetOps topology, SecOps attack surface).

**Architecture fit:** This is a QuarantineStore policy. The
falsification engine is a `Policy` that runs the proposed action
through N adversarial scenarios before returning ALLOW. It MUST run
in the quarantine evaluation path, which is side-effect-free. The
sandbox MUST be ephemeral and isolated.

**Spec level:** Define the `FalsificationPolicy` interface. Defer
hypothesis generation quality to the module implementation.

### Frontier 3: TPM-Bound Hardware Ledgers

**Concept:** Bind hash-chained event ledgers to a hardware Trusted
Platform Module so that even root users cannot forge history.

**Feasibility:** High, with caveats. TPM 2.0 PCR extend operations
are well-defined. The challenge is platform availability (not all
deployment targets have TPMs) and the PCR allocation strategy.

**What CAN be built now:** A `TPMLedgerSink` that wraps the existing
observation layer's `Sink` interface. Every observation emitted to
the bus is also extended into a TPM PCR. Verification reads the PCR
and compares against the expected chain.

**Architecture fit:** This is an observation layer sink, not a
station module. It plugs into the existing `Sink` protocol.

**Spec level:** Define the `TPMLedgerSink` interface with graceful
degradation when TPM is unavailable (fall back to software hash chain
with a `hardware_rooted: false` flag in the receipt).

### Frontier 4: Epistemic CRDTs for Parallel Sub-Agents

**Concept:** Allow parallel sub-agents to merge their reasoning state
mathematically without locks or conflicts.

**Feasibility:** Low for the general case. CRDTs work for specific
data types (counters, sets, maps). "Epistemic state" is not a CRDT.
The draft's merge function (take max confidence per axiom) is not
associative in general — merging A+B then C can differ from merging
A with B+C depending on confidence update order.

**Honest assessment:** This frontier requires formalizing what
"epistemic state" means as a mergeable data structure. A G-Counter
for confidence scores per axiom is a CRDT. A set of validated axioms
with per-axiom confidence is two CRDTs (G-Set + G-Counter). That IS
implementable. The draft's `EpistemicStateCRDT` is close but the
merge function needs to be proven commutative, associative, and
idempotent.

**What CAN be built now:** A `GSet` for validated axioms and a
`GCounter` for confidence scores, composed into an
`EpistemicStateCRDT` with a formally verified merge function.

**Spec level:** Define the CRDT composition. Prove the merge
properties. Defer integration with sub-agent spawning until
SPEC-006 (SubAgentPool) is implemented.

---

## Part 5: Integration Architecture

### Module Registration Flow

```
StationExtensionRegistry()
        │
        ├── register_module(NetOpsModule(...), "netops")
        │       ├── quarantine_policies() → (maintenance_window_policy, topology_permission_policy)
        │       ├── verifiers() → {"telemetry_stabilization": (MECHANICAL, fn), ...}
        │       └── brakes() → (TelemetryAnomalyBrake(), TopologyDriftBrake())
        │
        ├── register_module(SecOpsModule(...), "secops")
        │       ├── quarantine_policies() → (secret_exfiltration_policy, ...)
        │       ├── verifiers() → {"sast_scan": (MECHANICAL, fn), ...}
        │       └── brakes() → (VulnerabilityDeltaBrake(), SecretExposureBrake())
        │
        ├── register_module(TrajectoryRecorder(...), "trajectory")
        │       └── on_run_closed() → record trajectory to golden store
        │
        ├── register_module(EpistemicMemoryModule(...), "memory")
        │       └── on_run_closed() → index receipt to memory store
        │
        └── register_module(HITLEscalationModule(...), "hitl")
                └── on_brake_trip() → generate HITLChallenge if ESCALATE
        │
        ▼
QuarantineStore(policies=registry.policies())
Verifier(evaluators=registry.verifier_evaluators())
LoopController(brakes=standard_brakes + registry.brakes())
```

### Observation Event Map

| Event | Kind | Source |
|---|---|---|
| Run opened | `checkpoint` | LoopController |
| Pass transition | `state.transition` | LoopController |
| Action quarantined | `state.transition` | QuarantineStore |
| Action denied | `tool.failed` | QuarantineStore |
| Action executed | `tool.completed` | QuarantineStore |
| Check evaluated | `custom` | Verifier |
| Brake tripped | `state.transition` | LoopController |
| Brake decision | `custom` | LoopController |
| Module policy evaluated | `custom` | Module (via emit) |
| Module brake checked | `custom` | Module (via emit) |
| Trajectory recorded | `checkpoint` | TrajectoryRecorder |
| Memory indexed | `checkpoint` | EpistemicMemoryModule |
| HITL challenge generated | `checkpoint` | HITLEscalationModule |
| HITL resolved | `checkpoint` | HITLEscalationModule |
| Run closed | `checkpoint` | LoopController |

### What Does NOT Change

| Component | Why Unchanged |
|---|---|
| `engine.py` | Modules register through QuarantineStore, Verifier, LoopController — not the engine |
| `station/service.py` | Station orchestration is above the module layer |
| `storage.py` | Ledger format is stable; TPM sink is additive |
| `core.py` | Obligation, Task, Verdict types are unchanged |
| `providers.py` | Provider interface is unchanged; zk wrapper is a separate concern |
| Synchronous constraint | No module introduces async, threading, or event loops |
| Host-authoritative verification | Verifiers are host-registered; modules register them, the host owns them |
| Disclosure lattice | Modules receive data through injected clients, not direct network access |
