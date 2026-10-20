# INT-007: Open Policy Agent (OPA) Integration Spec

## Metadata
- **ID**: INT-007
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-003 (admission), IE-006 (routing constraints)
- **Protected boundaries**: Scheduling/admission authority, verifier authority, disclosure policy, M4 evidence, budget authority

## Problem

Admission and routing constraints benefit from declarative policy and auditability. An unversioned dynamic policy service, however, could change a mission's eligibility semantics mid-run or become an unreviewed second authority.

## Goal

Use OPA as a **versioned policy evaluator**. RESIDUAL freezes the evaluated policy identity per mission/decision epoch and remains the enforcement authority.

## Non-Goals

- Giving OPA authority to accept work, issue receipts, integrate state, reserve budget or invoke providers
- Letting a policy update silently alter an in-flight frozen plan
- Allowing OPA to widen hard privacy/capability constraints established by RESIDUAL

## Design

### Policy snapshot

```python
@dataclass(frozen=True)
class PolicySnapshot:
    bundle_uri: str
    bundle_sha256: str
    policy_revision: str
    loaded_at: str
```

A mission binds one snapshot at admission. A later policy deployment affects new missions only unless RESIDUAL invokes an explicit, auditable re-evaluation boundary.

### Decision contract

OPA returns constraints/decision evidence, not an execution command:

```python
@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    permitted_engine_ids: tuple[str, ...]
    max_parallelism: int | None
    required_labels: tuple[str, ...]
    reason_codes: tuple[str, ...]
    policy_snapshot: PolicySnapshot
    input_sha256: str
```

RESIDUAL intersects this result with immutable host constraints. The result can only preserve or narrow the host-feasible set.

### Adapter

```python
class OPAAdapter:
    def evaluate(self, policy_input: dict, snapshot: PolicySnapshot) -> PolicyDecision: ...
    def load_snapshot(self) -> PolicySnapshot: ...
```

Policy updates are administrative operations outside a running mission. Update authorization/audit belongs to deployment governance, not this adapter.

## Test Plan

| Test | Description |
|---|---|
| T1 | Snapshot: policy bundle/revision is hash-bound |
| T2 | Narrowing: OPA may narrow but cannot widen host eligibility |
| T3 | Mid-run update: in-flight mission continues against frozen snapshot |
| T4 | Explicit re-evaluation: new snapshot is recorded as a new decision epoch |
| T5 | Failure: unavailable/mismatched policy returns BLOCKED/deny according to the frozen host policy, never allow-by-default |
| T6 | Replay: retained input + snapshot reproduces decision |
| T7 | Non-interference: policy evaluator cannot change verifier/receipt/integration authority |

## Failure Modes

| Failure | Behavior |
|---|---|
| OPA unavailable | use an already-retained local bundle only if its exact snapshot is the mission's frozen revision; otherwise BLOCKED |
| Bundle hash mismatch | fail closed |
| Invalid policy output | fail closed |
| Policy asks for ineligible engine/provider | host intersection rejects it |

## Exit Criteria

- [ ] Policy decisions are snapshot/hash bound
- [ ] Host remains enforcement authority
- [ ] No mid-run policy drift without explicit re-evaluation
- [ ] Replay reproduces decisions
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
