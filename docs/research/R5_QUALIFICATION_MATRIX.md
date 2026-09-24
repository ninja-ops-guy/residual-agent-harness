# R5 qualification matrix

Status: planning and test design only

Source baseline: PR #410 at `1c0f6015ca6be160efcf3a4f530f148e015403aa`

Frozen R4.1 candidate: `8701367db6d3202f24b3eb9f4696b0cadf657985`

This matrix translates the PR #410 backlog into independently qualifiable requirements. It neither changes R4.1 nor authorizes its canary. Requirement dependencies and complete machine-readable contracts are authoritative in `R5_DAG.json`.

## Requirement coverage

| Gate | Phase | Category | Requirement | Positive fixture | Negative fixture | Adversarial fixture | Deterministic pass condition |
|---|---|---|---|---|---|---|---|
| R5-G15 | P0 | G | SC-015 frozen qualification contracts | valid manifest | missing artifact | post-hoc oracle swap | all inputs pinned before outcomes; mismatch fails |
| R5-G16 | P0 | D | SC-016 evidence governance | complete bundle | omitted failure | summary tamper | raw graph and summary reproduce; failures retained |
| R5-G11 | P1 | A | SC-011 protocol versioning | compatible matrix | unknown major | downgrade strips binding | only declared compatible pairs mutate |
| R5-G02 | P1 | C | SC-002 receipt authenticity/binding | valid bound receipt | unsigned/wrong project | mutation and foreign-epoch replay | only authorized, fully bound receipt ACKs |
| R5-G04 | P1 | C | SC-004 malformed/cross-bound receipts | valid bound receipt | truncated/wrong operation | parser and project-collision corpus | zero false ACK; stable rejection reason |
| R5-G03 | P1 | A | SC-003 durable reconciliation states | happy path/receipt found | illegal transition | crash-point matrix | journal is a legal graph path; ambiguity persists |
| R5-G01 | P2 | B | SC-001 ownership and fencing | single owner | stale token | pause/takeover/resume | only current fence advances or sends |
| R5-G09 | P2 | B | SC-009 topology contract | supported failover | unsupported shared FS | split-brain partition | single fenced advancement or pre-send rejection |
| R5-G05 | P3 | B | SC-005 crash-safe ACK persistence | durable ACK | unverified receipt | commit crash/stale-owner race | prior safe state or complete verified ACK |
| R5-G06 | P3 | F | SC-006 corruption quarantine | unaffected valid row | digest corruption | SQLite corruption corpus | corrupt data causes no action; evidence preserved |
| R5-G07 | P3 | F | SC-007 contention/storage errors | contention recovers | full before send | SQLite error-boundary matrix | no unjournaled send or false success |
| R5-G08 | P3 | A | SC-008 stale-operation policy | authorized resume | age-only resend | clock anomaly matrix | age alone causes no disposition or network action |
| R5-G10 | P4 | E | SC-010 reconciliation observability | mixed recovery | missing transition | hostile labels/exporter outage | metrics equal journal; labels bounded/redacted |
| R5-G13 | P4 | C | SC-013 receipt retention/GC | tombstoned expiry | early delete | GC race plus old restore | uniqueness survives replay horizon; growth bounded |
| R5-G12 | P5 | A | SC-012 distributed lookup authority | authoritative found/absent | stale-replica absence | partition/failover matrix | ambiguous absence never authorizes POST |
| R5-G14 | P5 | A | SC-014 external-effect claim boundary | idempotent consumer | non-idempotent consumer | consumer crash model | checked property holds only within published scope |
| R5-G17 | P5 | G | SC-017 convergence controller | all phases pass | missing upstream gate | retry-to-green/DAG cycle | DAG valid and every requirement/phase gate passes |

## Phase qualification matrix

| Phase gate | Inputs | Required requirement gates | Independent exit condition | Downstream unlocked |
|---|---|---|---|---|
| R5-PG0 | pinned planning candidate, harness plan, corpus registry | G15, G16 | qualification inputs immutable; evidence packaging negative controls pass | P1 implementation may begin |
| R5-PG1 | P0 manifest plus protocol/receipt candidate | G11, G02, G04, G03 | version negotiation, receipt authority, parser rejection, and explicit ambiguity all pass | P2 implementation may begin |
| R5-PG2 | qualified P1 lineage plus ownership/topology candidate | G01, G09 | stale owners cannot advance; topology matrix either fences or fails closed | P3 implementation may begin |
| R5-PG3 | qualified P2 lineage plus durability candidate | G05, G06, G07, G08 | ACK crashes, corruption, contention/storage failures, and stale policy pass | P4 implementation may begin |
| R5-PG4 | qualified P3 lineage plus telemetry/lifecycle candidate | G10, G13 | telemetry reconciles to state and receipt uniqueness survives lifecycle races | P5 implementation may begin |
| R5-PG5 | qualified P4 lineage plus distributed/convergence candidate | G12, G14, G17 | all 17 requirement gates and all six phase gates pass with no unresolved evidence | bounded R5 qualification disposition may be issued |

## Oracle rules shared by every gate

1. The candidate, harness, corpus, fault schedule, and oracle identities are fixed before execution.
2. Safety and liveness are scored separately. A fail-closed unavailable outcome may satisfy safety but cannot be relabeled as liveness success.
3. Every network action is captured in order and correlated to operation, project, owner fence, state transition, and receipt decision without retaining message bodies.
4. `PASS` requires all named positive, negative, and adversarial fixtures. Missing, skipped, malformed, unsupported, or unverifiable evidence is not `PASS`.
5. Expected negative controls must fail for the expected reason. A negative control that unexpectedly passes invalidates the gate.
6. Retried runs receive new run identities. A later pass cannot replace or delete an earlier failure.
7. The candidate cannot author its own final gate decision. Gate classification is performed by the external deterministic oracle.
8. Phase gates bind the exact upstream lineage. Any upstream change invalidates downstream qualification until replayed.

## Evidence minimum

Every requirement gate emits:

- `gate.json` with status, reason codes, candidate/harness identities, fixture inventory, and timestamps;
- ordered action and transition traces;
- pre/post durable-state hashes and relevant snapshots;
- fixture/corpus and oracle hashes;
- raw command/process outcomes, including expected failures;
- redaction and schema validation results;
- `SHA256SUMS` covering every retained artifact.

Every phase gate additionally emits a phase manifest, dependency lineage, unresolved inventory, counterexample index, and an explicit `PASS`, `FAIL`, `BLOCKED`, or `INDETERMINATE` disposition.

## Claim boundary

Passing this matrix would support only the invariants and deployment topology named by the frozen R5 protocol and qualification manifests. It would not retroactively modify the R4.1 finding, establish universal exactly-once delivery, establish production readiness, or establish novelty. Novelty requires literature review.
