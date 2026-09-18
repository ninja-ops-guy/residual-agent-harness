# INT-000: Integration Authority Contract

## Metadata
- **ID**: INT-000
- **Status**: Draft
- **Spec family**: Integration foundation
- **Depends on**: IE-001 (qualified prototype contract), current RESIDUAL trust-boundary documentation
- **Protected boundaries**: Verifier authority, receipt authority, deterministic integration, disclosure policy, provider authorization, budget authority, M4 evidence and protected controls

## Problem

External systems can improve RESIDUAL's observability, execution, storage, deployment, identity and policy ergonomics. They can also accidentally create a second control plane that retries work, changes routing, accepts results, broadens disclosure, or mutates durable state outside RESIDUAL's evidence-first authority model.

## Goal

Define one contract that every INT-* adapter must obey so integrations add capability without acquiring RESIDUAL authority.

## Authority Invariants

1. **RESIDUAL owns acceptance.** External systems may compute, transport or report candidate results. They MUST NOT convert candidate output into PASS, accepted evidence, a canonical receipt, or integrated durable state.
2. **RESIDUAL owns deterministic integration.** No orchestrator, scheduler, storage engine or workflow system may directly mutate accepted project state.
3. **RESIDUAL owns disclosure.** An adapter may only receive evidence already authorized for that destination. Caching, federation, replication and retries MUST NOT widen disclosure.
4. **RESIDUAL owns budget authorization.** Provider, accelerator and external-service work requiring a budget reservation must be reserved before external I/O. An external retry is a new attempt unless the host explicitly authorizes replay under the same idempotency contract.
5. **RESIDUAL owns routing eligibility.** External placement systems may choose *where* an already-authorized workload executes. They may not make an otherwise-ineligible model, host, region or provider eligible.
6. **RESIDUAL owns verifier semantics.** External verifier compute may return raw observations/results, but authoritative PASS/FAIL/UNKNOWN interpretation stays in the host verifier boundary.
7. **RESIDUAL owns receipt semantics.** Identity/signing integrations may authenticate an issuer or sign an external attestation, but they MUST NOT silently replace or reinterpret canonical receipt schemas.
8. **UNKNOWN stays UNKNOWN.** Missing cost, latency, correctness, identity, provenance or policy data MUST NOT be converted to zero, false, empty, or success defaults.
9. **Derived stores are projections.** OTel, MLflow, Parquet, LanceDB, Zarr/TileDB and similar stores are non-authoritative projections unless a separate accepted spec explicitly promotes them and binds them to canonical evidence.
10. **Every authority-affecting external input is version-bound.** Policy bundle, model revision, tokenizer/runtime, identity trust bundle, deployment image and other external state that can affect a run must be hash/revision-bound to retained evidence.

## Integration Roles

| Role | Allowed | Forbidden |
|---|---|---|
| Observability | export spans/metrics/log projections | alter execution or acceptance |
| Compute substrate | execute host-authorized work | self-authorize retries, routing or acceptance |
| Placement/deployment | place/scale eligible workloads | broaden provider/privacy eligibility |
| Policy evaluator | return a decision + policy identity | become the sole unversioned enforcement authority |
| Identity provider | authenticate workload identity | redefine receipt semantics |
| Storage/analytics | persist/query derived projections | become canonical evidence implicitly |
| Outer orchestrator | submit/monitor whole RESIDUAL missions | own internal verifier/integration stages |
| Model catalog | discover candidates | promote metadata/popularity into measured capability |

## Retry and Replay Contract

External systems frequently retry automatically. For RESIDUAL integrations:

- retries of **read-only status/telemetry operations** may be adapter-owned;
- retries of **mission submission** require an idempotency key bound to the same request hash;
- retries of **worker/provider execution** require a new host-issued attempt/retry authorization and budget reservation;
- retries of **verification/integration** may only occur through the existing authoritative host path;
- side-effectful work with unknown completion state MUST remain UNKNOWN until reconciled; it must not be blindly replayed.

## Evidence Binding

Every integration event that can affect reproducibility MUST retain, as applicable:

- integration ID and adapter revision;
- external system/version;
- exact policy/model/image/runtime/trust-bundle revision or digest;
- host run/mission/obligation/attempt identity;
- input/request hash;
- result/response hash or external immutable reference;
- authoritative host decision produced afterward, if any;
- whether the record is live, replayed, simulated or derived.

## Failure Semantics

| Condition | Required behavior |
|---|---|
| External dependency unavailable before authorized execution | fail/hold according to host policy; never invent success |
| External state revision changed mid-run | keep frozen run revision; apply new revision only at an explicit host re-evaluation boundary |
| External retry occurs without host authorization | classify as protocol violation; do not accept resulting work |
| External result lacks provenance/identity required by the contract | UNKNOWN/BLOCKED |
| Derived analytics store disagrees with canonical evidence | canonical evidence wins; flag projection corruption/drift |
| Adapter proposes policy/route outside hard host constraints | reject before dispatch |

## Test Plan

| Test | Description |
|---|---|
| A1 | External compute cannot issue accepted state without host verifier decision |
| A2 | External placement cannot select an ineligible privacy/capability destination |
| A3 | Automatic duplicate execution without host retry token is rejected |
| A4 | Policy/model/trust-bundle revision drift is detected and frozen per run |
| A5 | Missing performance/cost/correctness fields remain UNKNOWN/null |
| A6 | Derived storage corruption cannot change canonical evidence |
| A7 | External identity cannot silently change receipt schema or signer authority |
| A8 | Outer orchestrator can submit/monitor a mission but cannot invoke private acceptance/integration authority |
| A9 | Adapter disabled path is behaviorally equivalent to the pre-integration baseline for authoritative outcomes |
| A10 | Exact replay reproduces the recorded adapter decision from retained configuration/revision evidence |

## Exit Criteria

- [ ] Every INT-* spec declares `Governed by: INT-000`
- [ ] Each implementation has a negative-path test proving it cannot acquire protected authority
- [ ] Retry/replay behavior is explicit and host-authorized
- [ ] External state affecting behavior is version/hash bound
- [ ] UNKNOWN/null semantics preserved
- [ ] Q11: exact-head maintainer attestation per merged solo-maintainer policy (#168)
