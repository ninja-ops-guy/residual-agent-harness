# RESIDUAL Doctor — Health Coordination R1

Status: **DESIGN-FROZEN / IMPLEMENTATION-DEFERRED**

This extends the existing read-only `residual doctor` from DF-CLI-002 into an operational health-coordination surface. It does not authorize mutation, repair, restart, provider configuration, runner enrollment, or scheduling decisions.

## Purpose

Doctor answers: what is unhealthy/unknown; where the first causal divergence occurred; whether safe useful work can continue; and what evidence/bounded remediation should be considered.

Health stages:

`DISCOVERY -> ENROLLMENT -> AUTHORITY -> SCHEDULING -> WAKEUP -> TRANSPORT -> EXECUTION -> PROVIDER -> EVIDENCE -> PROJECTION -> RECONCILIATION`

Downstream symptoms never replace a known upstream first failure.

## States

Check states: `PASS`, `DEGRADED`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`, `NOT_QUALIFIED`, `STALE`.

Overall states: `OPERATIONAL`, `OPERATIONAL_DEGRADED`, `BLOCKED`, `AUTHORITY_UNCERTAIN`.

DEGRADED does not automatically mean stop. Doctor supplies evidence; scheduler/policy retains action authority.

## Invariants

- **DOC-I01** Read-only by default.
- **DOC-I02** Every non-PASS classification cites evidence or states evidence unavailable.
- **DOC-I03** Preserve first causal divergence; downstream failures are impacts.
- **DOC-I04** Health PASS grants no enrollment, lease, readiness, ACK, acceptance, or mission authority.
- **DOC-I05** Missing evidence is UNKNOWN/NOT_QUALIFIED, never inferred green.
- **DOC-I06** Shared Comms/Mission Board projection health is separate from authoritative Station state.
- **DOC-I07** OpenClaw presence != runner enrollment.
- **DOC-I08** Provider CONFIGURED != READY.
- **DOC-I09** Timer fire != durable consumption.
- **DOC-I10** Historical receipts satisfy current health only when epoch/generation/freshness contracts permit.
- **DOC-I11** Credential values are never reported; presence/class/permissions only.
- **DOC-I12** Scheduler consumes Doctor evidence; Doctor does not schedule.

## CLI/API

Read-only:

```
residual doctor
residual doctor --json
residual doctor --scope station|runner|provider|comms|cluster
residual doctor --explain HC-015
```

`--explain` returns definition, evidence, impact, qualification boundary and remediation proposal without mutation.

`residual doctor --repair` is reserved for future work. R1 MUST NOT implement silent repair. A future repair mode requires explicit authorization, pre-state, declared mutations, and post-state receipt.

## Machine result

Each check emits fields:

```
check_id
component
stage
state
classification
first_divergence
mission_impact
safe_continuation
owner_gate_actionable_now
observed_at
freshness
evidence[]
downstream_impacts[]
remediation{status:"PROPOSAL_ONLY",actions:[]}
```

Top-level report:

```
schema_version
generated_at
host_identity
station_identity
station_epoch
overall_state
first_divergence
checks[]
causal_chains[]
unknowns[]
owner_gates[]
qualification_summary
```

Unknown Station identity/epoch stays null/UNKNOWN.

## Causal presentation

Wake example:

```
deadline registered PASS
-> fired PASS
-> durable event emitted PASS
-> consumer action FAIL
   -> HC-002 WAKEUP_FIRED_NO_ACTION
```

Runner example:

```
seat present PASS
-> runner enrolled PASS
-> Station sees runner PASS
-> exec contract FAIL
   -> HC-015 RUNNER_EXEC_CONTRACT_MISMATCH
   -> runner start NOT_REACHED
```

## Hierarchical Doctor

Local Doctor covers host/runtime identity, Station process/data root, runner/bridge, local coordinator, providers/readiness, deadlines/consumption, artifact admission, projection/outbox, and restart/fencing.

Future Cluster Doctor covers Station registry/epochs, cross-Station leases, replication/checkpoint portability, authority-transfer receipts, lag, split-brain indicators, and cluster scheduler health. Cluster Doctor does not create/transfer authority.

## Scheduler integration

Doctor MAY emit durable health evidence consumed by scheduling policy. Scheduler must cite health evidence when it changes eligibility. Doctor never reassigns work itself.

## Onboarding integration

Target flow:

`residual discover -> residual map -> residual doctor -> explicit remediation/qualification -> residual qualify -> ACTIVE`

Doctor distinguishes DISCOVERED, MAPPED, ENROLLED, QUALIFIED and ACTIVE; no stage is inferred from another.

## Research feedback loop

`real failure -> durable specimen -> Health Coordination Failure Register -> Workbench negative experiment -> generic repair -> Doctor detector -> qualification -> production health invariant`

A detector is not mature from one historical specimen; positive and adversarial controls are required.

## Compatibility

R1 should extend, not replace, DF-CLI-002. Existing package/source/Python/install/update/state-path diagnostics remain the installation/host-identity portion of the report. This spec does not change the v1 release boundary merely by existing.
