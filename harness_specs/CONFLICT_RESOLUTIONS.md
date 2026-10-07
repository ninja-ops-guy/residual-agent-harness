# Contract Conflict Resolutions & Delegation Boundaries

**Date:** 2026-09-13
**Status:** RESOLVED — binding for all parallel tracks
**Owner:** Receipt Binding + Extension Registry track
**Authority:** This document supersedes conflicting language in
NETOPS_SECOPS_SPECS.md, WORLD_CLASS_SPECS.md, and SPECS.md where
they disagree.

---

## Conflict 1: Registry Has Two Freeze Points

### The Problem

WORLD_CLASS_SPECS.md MODULE-R5 states:
> "The registry MUST be immutable after the LoopController is
> constructed. Modules MUST NOT be added or removed mid-run."

But REG-R6 states:
> "`register_module` MUST raise `ContractError` if called after
> `LoopController.run()` has been invoked."

These are two different freeze points:
- MODULE-R5: freeze at construction time
- REG-R6: freeze at first run

A module registered between construction and first run would be
legal under REG-R6 but illegal under MODULE-R5.

### Resolution

**The freeze point is LoopController construction.**

Rationale: The LoopController captures `brakes`, `verifier`, and
`quarantine_policies` at construction. A module registered after
construction would not be reflected in any of these. Allowing
registration between construction and run would create a false
expectation that the module is active when it is not.

**Binding text (replaces both MODULE-R5 and REG-R6):**

> The registry MUST be frozen when `LoopController.__init__` returns.
> `register_module` MUST raise `ContractError` if called after
> `LoopController` construction begins. The `LoopController` MUST
> capture all registry state (policies, verifiers, brakes) at
> construction time. No module may be added, removed, or modified
> after this point.

### Impact on Other Tracks

- **TUI track:** Read-only consumer. No impact.
- **Trajectory track:** Hooks `on_run_closed`. Must be registered
  before LoopController construction.
- **Memory track:** Hooks `on_run_closed`. Same constraint.
- **HITL track:** Hooks `on_brake_trip`. Same constraint.
- **Mesh track:** Mesh layer is above LoopController. Mesh devices
  join/leave independently of the registry freeze.

---

## Conflict 2: Receipt Propagation Reverses DAG Direction

### The Problem

WORLD_CLASS_SPECS.md VRB-R5 states:
> "Receipts MUST propagate up the DAG. A parent task's receipt MUST
> include the hashes of all child receipts. A change to any child
> receipt MUST invalidate all ancestor cache keys."

But the residual engine's actual DAG execution flows downward:
root tasks execute first, their outputs feed child tasks. The
engine's existing receipt propagation (from engine.py `_accept`)
binds parent receipts into child cache keys — receipts flow
downward, from parent to child.

VRB-R5 says the opposite: child receipts flow upward into parents.

### Resolution

**Receipts propagate downward, matching the engine's data flow.**

Rationale: The engine's execution model is top-down. A root task
produces a value. Child tasks consume that value as input. The
child's cache key must incorporate the parent's receipt because
the parent's output is the child's input. This is what the engine
already does correctly.

VRB-R5's "propagate up" language was describing provenance
attribution (a parent is accountable for its children), not cache
invalidation direction. Conflating these creates an impossible
requirement: a parent task's cache key cannot depend on child
receipts because children haven't executed when the parent runs.

**Binding text (replaces VRB-R5):**

> Receipts MUST propagate in the direction of data flow. A child
> task's cache key MUST incorporate the receipts of all tasks it
> depends on (its parents). A change to any parent receipt MUST
> invalidate all descendant cache keys. Provenance attribution
> (which tasks contributed to a result) is a separate concern from
> cache invalidation and MUST NOT reverse the dependency direction.

### Correction to VRB-R2

The cache key formula in VRB-R2 already says "parent receipt
hashes" — this was correct. VRB-R5 contradicted it. VRB-R2 stands.
VRB-R5 is corrected above.

### Impact on Other Tracks

- **NetOps track:** Telemetry verifiers run post-execution on a
  single task. Receipt direction does not affect them.
- **SecOps track:** SAST/SBOM verifiers run on a single task's
  outputs. Same.
- **Mesh track:** Receipt exchange between devices assumes
  downward propagation. A device receiving a receipt verifies it
  against its local verifier. No change.
- **Trajectory track:** Records execution order. Downward
  propagation is the natural execution order. No change.

---

## Conflict 3: SecOps References a Result State the Verifier Lacks

### The Problem

NETOPS_SECOPS_SPECS.md SECOPS-R6 states:
> "It MUST return `CheckResult.UNKNOWN` (not FAIL) when the policy
> engine is unavailable. Per the existing verifier, UNKNOWN never
> accepts — the check blocks without asserting failure."

But `verifier.py` `CheckResult` only has PASS and FAIL:
```python
class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
```

There is no UNKNOWN state. SECOPS-R6 references a state that
does not exist in the implementation.

The original engine (pre-v0.3.0) had a three-state Verdict
(pass/fail/unknown). The v0.3.0 Verifier reduced this to two
states. SECOPS-R6 was written against the three-state model.

### Resolution

**Add UNKNOWN to CheckResult.**

Rationale: The three-state model is correct for the domain.
UNKNOWN means "the check could not be evaluated" — distinct from
FAIL which means "the check was evaluated and the result did not
meet the criterion." A policy engine that is unavailable, a
mechanical check that cannot access its target, or a judge that
times out are all UNKNOWN conditions. They are not FAILures of
the criterion itself.

The v0.3.0 Verifier's reduction to two states was an
oversimplification that SECOPS-R6 correctly identified as
insufficient.

**Binding change to verifier.py:**

```python
class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
```

**Binding addition to Verifier._evaluate_one:**

When an evaluator raises an exception, the result MUST be UNKNOWN
with reason `check_error`, not FAIL. FAIL is reserved for
evaluated-and-failed. UNKNOWN covers could-not-evaluate.

**Binding addition to VerificationReport:**

`overall_pass` MUST be True if and only if all checks return PASS.
Any FAIL or UNKNOWN produces `overall_pass = False`. The
`primary_failure` field MUST identify the first check that
returned FAIL or UNKNOWN.

**Binding text (replaces SECOPS-R6 and SPEC-002-R5):**

> `CheckResult` MUST have three states: PASS, FAIL, UNKNOWN.
> PASS means the check was evaluated and the criterion is met.
> FAIL means the check was evaluated and the criterion is not met.
> UNKNOWN means the check could not be evaluated. Evaluator
> exceptions, unavailable dependencies, and timeouts MUST return
> UNKNOWN, not FAIL. UNKNOWN never accepts. A verification report
> with any UNKNOWN check MUST have `overall_pass = False`.

### Impact on Other Tracks

- **NetOps track:** `telemetry_stabilization` verifier returns
  FAIL on threshold breach (evaluated-and-failed). Returns UNKNOWN
  if telemetry client is unreachable (could-not-evaluate). No code
  change needed — the distinction was already implicit.
- **Formal verifiers track (RESILIENCE_SPECS.md FMV-R4):** Already
  specifies UNKNOWN for unproven invariants. Now has a concrete
  enum value to use.
- **Trajectory track:** Records per-check results. UNKNOWN is a
  valid result to record. No change.
- **HITL track:** UNKNOWN checks may trigger HITL escalation if
  the AmendmentRule permits. No change.

---

## Delegation Boundaries

### Track 1: Receipt Binding + Extension Registry (owned)

**Scope:**
- VRB-R1 through VRB-R6 implementation
- StationExtensionRegistry implementation
- Module registration flow
- Receipt propagation (downward, per Conflict 2 resolution)
- CheckResult.UNKNOWN addition (per Conflict 3 resolution)
- Registry freeze at LoopController construction (per Conflict 1)

**Interfaces exposed to other tracks:**

```python
# Other tracks consume these, do not implement them.

class StationExtensionRegistry:
    def register_module(self, module: Any, domain_name: str) -> None: ...
    def policies(self) -> tuple[Policy, ...]: ...
    def verifiers(self) -> dict[str, tuple[CheckType, Evaluator]]: ...
    def brakes(self) -> tuple[Brake, ...]: ...

class StationReceipt:
    task_id: str
    cache_key: str
    value_hash: str
    verifier_name: str
    verifier_revision: str
    verdict: str          # "pass" | "fail" | "unknown"
    parent_receipts: tuple[StationReceipt, ...]
    receipt_hash: str

class CheckResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
```

**What other tracks MUST NOT do:**
- MUST NOT modify `verifier.py` CheckResult enum (Track 1 owns it)
- MUST NOT modify `loop.py` LoopController construction (Track 1
  owns the freeze point)
- MUST NOT create alternative registry implementations
- MUST NOT register modules after LoopController construction

### Track 2: TUI Dashboard

**Consumes:** Observation bus events (read-only)
**Must not:** Modify any core module, emit observations, send
control signals

### Track 3: Trajectory Regression

**Consumes:** `on_run_closed` hook, `RunResult`, per-check
`CriterionResult` tuples
**Must not:** Modify verifier, loop, or registry

### Track 4: Epistemic Memory

**Consumes:** `on_run_closed` hook, `StationReceipt`, GoalSpec
content hash
**Must not:** Modify storage.py, observation layer, or registry

### Track 5: HITL Escalation

**Consumes:** `BrakeTrip` events, `AmendmentRule`,
`StationExtensionRegistry` for `hitl` module registration
**Must not:** Modify brakes.py, quarantine.py, or loop.py

### Track 6: Mesh / Federation

**Consumes:** `StationReceipt` for cross-device verification,
`GoalSpec` for task broadcast, `CheckResult` for result verification
**Must not:** Modify engine, station, or any local execution module

### Track 7: NetOps Module

**Consumes:** `Policy` protocol, `Evaluator` protocol,
`Brake` protocol, `StationExtensionRegistry`
**Must not:** Modify quarantine.py, verifier.py, brakes.py, or
loop.py

### Track 8: SecOps Module

**Consumes:** Same as Track 7, plus `CheckResult.UNKNOWN` for
policy engine unavailability
**Must not:** Same as Track 7

---

## Summary of Binding Decisions

| # | Conflict | Resolution | Supersedes |
|---|---|---|---|
| 1 | Two registry freeze points | Freeze at LoopController construction | MODULE-R5, REG-R6 |
| 2 | Receipt direction reversed | Downward, matching data flow | VRB-R5 |
| 3 | Missing UNKNOWN state | Add UNKNOWN to CheckResult | SECOPS-R6, SPEC-002-R5 |

All other tracks build against these resolutions. Any spec
language that contradicts this document is void.
