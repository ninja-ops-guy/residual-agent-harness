# NetOps & SecOps Module Specifications for Residual Command Station v0.3.0

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-command-station v0.3.0
**Depends on:** goalspec.py, verifier.py, brakes.py, quarantine.py, loop.py, integration.py

---

## SPEC-NETOPS-001: NetOps Station Module

### Purpose
Manage infrastructure state changes with pre-change baseline stability,
post-change telemetry verification, and circuit-breaker brakes on
operational anomalies.

### Module Boundary

The NetOps module is a First-Class Station Module. It does not modify
engine.py, station/service.py, or loop.py. It registers into three
existing extension points:

| Extension Point | What NetOps Registers |
|---|---|
| QuarantineStore policies | `maintenance_window_policy`, `topology_permission_policy` |
| Verifier registry | `telemetry_stabilization` (mechanical), `config_syntax_valid` (mechanical), `bgp_adjacency_assert` (structural) |
| LoopController brakes | `TelemetryAnomalyBrake`, `TopologyDriftBrake` |

### Requirements

**NETOPS-R1.** The module MUST implement the `StationModule` protocol
(see SPEC-MODULE-001). It MUST NOT subclass or monkey-patch any
existing engine, station, or loop class.

**NETOPS-R2.** `evaluate_quarantine_policy` MUST return `Optional[str]`
(None = allow, reason string = deny). Boolean returns are non-conformant.
The draft's `-> bool` signature MUST be corrected at integration time.

**NETOPS-R3.** The maintenance window policy MUST deny any mutation
action targeting a device with `tier == "core"` unless the action
carries a valid `maintenance_receipt`. Receipt validation MUST be
mechanical: receipt ID format, expiry timestamp, and device ID match.
Receipt validation MUST NOT call external services during quarantine
evaluation (side-effect-free per SPEC-004-R7).

**NETOPS-R4.** The `telemetry_stabilization` verifier MUST be
registered as `CheckType.MECHANICAL`. It MUST evaluate a synchronous
post-execution window (default 15s, configurable per task). It MUST
poll at fixed intervals (default 3s). It MUST return
`(CheckResult.FAIL, reason)` on the first threshold breach without
waiting for the window to complete.

**NETOPS-R5.** The `telemetry_stabilization` verifier MUST NOT sleep
in the quarantine evaluation path. It runs post-execution as a
verification stage, not pre-execution as a policy gate. This preserves
the synchronous constraint: the engine blocks on verification, not on
policy evaluation.

**NETOPS-R6.** `TelemetryAnomalyBrake` MUST implement the `Brake`
protocol. It MUST trip when any metric exceeds
`safety_thresholds[metric] * 1.5` (hard emergency ceiling). It MUST
recommend `BrakeAction.ABORT`. It MUST NOT trip on threshold breach
alone — that is the verifier's job. The brake is for emergencies only.

**NETOPS-R7.** `TopologyDriftBrake` MUST trip when the observed
network topology hash differs from the baseline topology hash recorded
at run open, and the drift is not attributable to a declared task
action. Undeclared topology change is a brake condition. Declared
change is not.

**NETOPS-R8.** All telemetry reads MUST go through the injected
`telemetry_client`. The module MUST NOT construct its own HTTP clients,
open sockets, or read from the network directly. This keeps the
disclosure lattice intact: the telemetry client is host-registered and
its data flows are governed by the existing evidence packet compiler.

**NETOPS-R9.** The module MUST emit observations for every policy
evaluation, every verifier poll cycle, and every brake check. Event
kinds: `custom` with `event: netops_policy_evaluated`,
`netops_telemetry_poll`, `netops_brake_checked`.

---

## SPEC-SECOPS-001: SecOps Station Module

### Purpose
Govern security validation, vulnerability posture, secret hygiene, and
runtime threat isolation during task execution.

### Module Boundary

Same three extension points:

| Extension Point | What SecOps Registers |
|---|---|
| QuarantineStore policies | `secret_exfiltration_policy`, `dependency_disclosure_policy`, `prohibited_pattern_policy` |
| Verifier registry | `sast_scan` (mechanical), `sbom_check` (structural), `policy_as_code_eval` (structural) |
| LoopController brakes | `VulnerabilityDeltaBrake`, `SecretExposureBrake` |

### Requirements

**SECOPS-R1.** The module MUST implement the `StationModule` protocol.
It MUST NOT subclass or monkey-patch any existing class.

**SECOPS-R2.** `secret_exfiltration_policy` MUST scan the canonical
serialization of `ProposedAction.arguments` — not `str(payload)`.
The draft's `str(proposed_action.get("payload", ""))` is incorrect:
`ProposedAction` has an `arguments` dict, not a `payload` field.
Scanning the string representation of a dict misses nested values
and produces false positives on dict syntax.

**SECOPS-R3.** Prohibited patterns MUST be compiled at module
construction, not at evaluation time. Patterns MUST be applied to
every string value in the arguments tree (recursive descent, same
traversal as `redact_payload` in the observation layer).

**SECOPS-R4.** The `sast_scan` verifier MUST be registered as
`CheckType.MECHANICAL`. It MUST run before any file is staged for
Git commit. It MUST return `CheckResult.FAIL` on detection of:
- `BEGIN PRIVATE KEY` or `BEGIN RSA PRIVATE KEY` blocks
- Hardcoded credential assignments (`api_secret`, `api_key`, `password`,
  `token` followed by assignment and string literal)
- Base64-encoded strings longer than 64 characters in source files
  (heuristic for embedded secrets)

**SECOPS-R5.** The `sbom_check` verifier MUST be registered as
`CheckType.STRUCTURAL`. It MUST parse the task's dependency manifest
and verify every dependency's license against `allowed_licenses`.
It MUST return `CheckResult.FAIL` with the offending package names
on violation.

**SECOPS-R6.** The `policy_as_code_eval` verifier MUST be registered
as `CheckType.STRUCTURAL`. It MUST evaluate the task's declared
configuration against the module's Rego/OPA policy bundle. It MUST
return `CheckResult.UNKNOWN` (not FAIL) when the policy engine is
unavailable. Per the existing verifier, UNKNOWN never accepts — the
check blocks without asserting failure.

**SECOPS-R7.** `VulnerabilityDeltaBrake` MUST trip when
`run_state.vuln_count_delta > 0`. It MUST recommend
`BrakeAction.ESCALATE`. It MUST NOT trip on delta == 0 even if the
absolute vulnerability count is high — the brake detects regression,
not pre-existing posture.

**SECOPS-R8.** `SecretExposureBrake` MUST trip when any observed
event contains a string matching a prohibited pattern in its payload.
It MUST recommend `BrakeAction.ABORT`. It MUST scan observation
payloads, not just proposed actions — a secret in a tool result is
as serious as a secret in a tool call.

**SECOPS-R9.** The module MUST emit observations for every policy
evaluation, every scan, and every brake check. Event kinds: `custom`
with `event: secops_policy_evaluated`, `secops_scan_completed`,
`secops_brake_checked`.

---

## SPEC-MODULE-001: Unified Module Registration Interface

### Purpose
Define the protocol that NetOps, SecOps, and all future station modules
implement, and the mechanism by which they register into the harness
without modifying existing code.

### The StationModule Protocol

```python
class StationModule(Protocol):
    """Contract for all First-Class Station Modules."""

    name: str                    # closed vocabulary: "netops", "secops", ...
    version: str                 # semver

    # --- Quarantine policies ---
    def quarantine_policies(self) -> tuple[Policy, ...]: ...

    # --- Verifiers ---
    def verifiers(self) -> dict[str, tuple[CheckType, Evaluator]]: ...
    # Returns {evaluator_name: (check_type, callable)}

    # --- Brakes ---
    def brakes(self) -> tuple[Brake, ...]: ...

    # --- Lifecycle ---
    def on_run_opened(self, spec: GoalSpec) -> None: ...
    def on_run_closed(self, result: RunResult) -> None: ...
```

### The ModuleRegistry

```python
class ModuleRegistry:
    """Collects modules and dispatches registration to the harness."""

    def __init__(self):
        self._modules: dict[str, StationModule] = {}

    def register(self, module: StationModule) -> None: ...

    def policies(self) -> tuple[Policy, ...]:
        """All quarantine policies from all modules, in registration order."""
        ...

    def verifiers(self) -> dict[str, tuple[CheckType, Evaluator]]:
        """Merged verifier registry. Later modules MUST NOT override
        earlier modules' evaluator names. Name collision is an error."""
        ...

    def brakes(self) -> tuple[Brake, ...]:
        """All brakes from all modules, appended to the standard set."""
        ...
```

### Registration Flow

```
ModuleRegistry.register(module)
        │
        ▼
┌─────────────────────────────────────┐
│ 1. Collect policies                 │
│ 2. Merge verifier registry          │
│    (collision = ContractError)      │
│ 3. Append brakes to standard set    │
│ 4. Wire on_run_opened/closed        │
│    to LoopController lifecycle      │
└─────────────────────────────────────┘
        │
        ▼
QuarantineStore(policies=registry.policies())
Verifier(evaluators=registry.verifier_evaluators())
LoopController(brakes=standard_brakes + registry.brakes())
```

### Requirements

**MODULE-R1.** The `StationModule` protocol MUST be the sole interface
for module integration. No module MAY require changes to engine.py,
station/service.py, loop.py, or quarantine.py.

**MODULE-R2.** Verifier name collisions across modules MUST raise
`ContractError` at registration time, not at evaluation time.

**MODULE-R3.** Brake evaluation order MUST be: standard brakes first
(max iteration, budget, no progress, completion), then module brakes
in registration order. Within a pass, all brakes are evaluated; the
LoopController's existing priority rule (abort > escalate > continue)
applies across the combined set.

**MODULE-R4.** `on_run_opened` MUST be called after the LoopController
emits `run_opened` and before the first pass. `on_run_closed` MUST be
called after the LoopController emits `run_closed`. Modules MUST NOT
emit their own run lifecycle events — they hook into the existing ones.

**MODULE-R5.** The registry MUST be immutable after the LoopController
is constructed. Modules MUST NOT be added or removed mid-run.

**MODULE-R6.** Module observations MUST use the `custom` event kind
with a namespaced `event` field: `{module_name}_{event_name}`. This
prevents event kind collisions across modules.

---

## Architecture Integration Map

### How NetOps Works With the Current Architecture

```
Agent proposes config change to core router
            │
            ▼
    QuarantineStore.hold(action)
            │
            ▼
    maintenance_window_policy evaluates
    (no receipt? → deny silently, observe fully)
            │
            ▼
    release → engine executes via provider
            │
            ▼
    telemetry_stabilization verifier runs
    (15s window, 3s polls, fail on first breach)
            │
            ▼
    If all checks pass → obligation accepted
    If telemetry breach → FAIL, primary_failure recorded
            │
            ▼
    TelemetryAnomalyBrake monitors throughout
    (metric > 1.5x threshold → ABORT run)
```

**Key architectural fit:** The NetOps verifier runs post-execution as
a `CheckType.MECHANICAL` check in the GoalSpec. It blocks the harness
pass until the telemetry window completes. This is consistent with the
synchronous constraint — the engine already blocks on verification.

**What changes in existing code:** Nothing. The verifier is
host-registered via the `Verifier` constructor's `evaluators` dict.
The brake is appended to the `LoopController`'s brake tuple. The
policy is passed to `QuarantineStore`'s constructor.

### How SecOps Works With the Current Architecture

```
Agent proposes file write
            │
            ▼
    QuarantineStore.hold(action)
            │
            ▼
    secret_exfiltration_policy scans arguments tree
    (recursive descent, compiled patterns)
    (match? → deny silently, observe fully)
            │
            ▼
    release → engine executes
            │
            ▼
    sast_scan verifier runs on modified files
    (before Git staging)
            │
            ▼
    sbom_check verifier runs on dependency manifest
            │
            ▼
    policy_as_code_eval verifier runs on config
            │
            ▼
    VulnerabilityDeltaBrake monitors across passes
    (new vulns introduced? → ESCALATE)
```

**Key architectural fit:** SecOps verifiers are ordered correctly by
the existing `GoalSpec` construction constraint (mechanical before
structural). SAST runs first, catches secrets before staging. SBOM
and policy-as-code run after, catch dependency and config issues.

**What changes in existing code:** Nothing. Same registration pattern
as NetOps.

### The Disclosure Lattice and Modules

Both modules receive data through host-registered interfaces:
- NetOps receives telemetry through the injected `telemetry_client`
- SecOps receives file contents through the task context's declared
  read paths

Neither module opens its own network connections or reads undeclared
files. The transitive disclosure lattice is preserved: a module can
only see what the task contract declares, and what the host injects.

### The Synchronous Constraint and Modules

Both modules are synchronous by design:
- Quarantine policies are pure functions (no I/O)
- Verifiers block until complete (telemetry window, SAST scan)
- Brakes evaluate on observed events (no polling threads)

No module introduces async, threading, or event loops. The engine's
single-process synchronous model is preserved.

---

## Draft Code Corrections Required

The draft modules have four non-conformant patterns that MUST be
corrected before integration:

| Draft Pattern | Correct Pattern | Spec Ref |
|---|---|---|
| `evaluate_quarantine_policy -> bool` | `-> Optional[str]` (None=allow, str=deny) | SPEC-004-R2, NETOPS-R2 |
| `str(proposed_action.get("payload", ""))` | Recursive descent over `ProposedAction.arguments` | SECOPS-R2 |
| `time.sleep()` in verifier | Acceptable post-execution; never in policy path | NETOPS-R5 |
| `check_netops_brakes(run_state) -> tuple[bool, str]` | `Brake.update(event) -> Optional[BrakeTrip]` | NETOPS-R6 |
