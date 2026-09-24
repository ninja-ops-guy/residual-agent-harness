# R5 gate specifications

Status: specifications only

## Common gate contract

Each gate is an external deterministic qualification. Before a run, it pins candidate HEAD/tree, harness HEAD/tree, requirement and phase revisions, fixture corpus, fault schedule, oracle, environment, and expected artifact inventory. It emits `PASS`, `FAIL`, `BLOCKED`, or `INDETERMINATE`; no other or missing status is acceptable. `PASS` requires every named fixture and artifact. Expected failures are evidence and must be retained.

The harness must not modify the candidate, use candidate self-attestation as an oracle, run against production data, or execute the R4.1 canary.

## Requirement gates

### R5-G01 — Recovery ownership and fencing

Run two or more independent owners on one disposable outbox. Deterministically pause the first owner, expire/take over its lease, then resume it. Pass only if every send and state transition carries the current fence, stale operations have zero effect, and final state converges. Retain process timelines, lease rows, action trace, receiver ledger, and final database.

### R5-G02 — Receipt authenticity and binding

Issue one valid receipt and mutate issuer, epoch, version, project, operation, request digest, event identity, sequence, outcome, and authenticator independently. Include cross-project and replay cases. Pass only if the valid receipt ACKs and every mutation leaves the operation non-ACKED with a deterministic reason code.

### R5-G03 — Reconciliation state machine

Inject a crash immediately before and after every durable write and network action in the frozen transition table. Restart from each image. Pass only if every journal is a legal graph path, ambiguity persists explicitly, illegal transitions reject, and no send originates in an ineligible state.

### R5-G04 — Malformed and cross-bound receipts

Apply the receipt parser corpus at both HTTP and stored-data boundaries under fixed size/time limits. Pass only if the valid control succeeds, every malformed/cross-bound vector produces its expected stable rejection, zero false ACKs occur, and logs contain neither raw hostile bodies nor unbounded labels.

### R5-G05 — Crash-safe ACK persistence

Inject kill, IOERR, short-write, and stale-owner races at each ACK transaction boundary on disposable storage. Pass only if restart observes the prior reconcilable state or a complete verified ACK, integrity checks pass or quarantine is explicit, and stale fences cannot ACK.

### R5-G06 — Corruption quarantine

Apply content-addressed page, WAL, schema, payload, digest, and receipt corruptions to copies of a known-valid outbox. Pass only if corrupted units cause no send/ACK/delete/silent repair, forensic bytes and hashes are preserved, quarantine scope is justified, and valid unaffected work proceeds only when isolation is proved.

### R5-G07 — SQLite contention and persistence errors

Schedule lock contention and inject BUSY, FULL, IOERR, read-only, inode, quota, and permission failures at enqueue, pre-send, state, ACK, and evidence boundaries. Pass only if behavior is bounded, no unjournaled effect or false success occurs, and recovery after restoration is deterministic.

### R5-G08 — Stale-operation policy

Cross policy age boundaries with wall-clock rollback/jump and delayed receipts. Exercise authorized inspect, reconcile, cancel, and resume. Pass only if age alone causes no send/success/delete, all actions are policy-versioned and audited, and unknown policy/disposition remains indeterminate.

### R5-G09 — Topology contract

Run every declared supported/unsupported process, host, and storage topology. Partition lease and Station paths independently and reboot a node. Pass only if supported topologies retain fenced single advancement and unsupported topologies reject before send.

### R5-G10 — Reconciliation observability

Replay a deterministic mixed-state journal including ACK, indeterminate, reconciliation, quarantine, contention, and stale-owner rejection. With exporter outage and hostile label data, pass only if recovered metrics exactly reconcile to journal truth, cardinality/redaction budgets hold, and frozen-clock alerts fire as specified.

### R5-G11 — Version and compatibility negotiation

Execute the frozen sender/Station/storage/receipt compatibility matrix through send, lookup, restart, rolling upgrade, and rollback. Pass only if supported pairs interoperate with all safety features and incompatible or downgrade pairs create no mutation or external effect.

### R5-G12 — Distributed lookup authority

Inject replica lag, stale cache, leader failover, partition, lost index, and disaster-recovery schedules. Pass only if found, authoritative absence, non-authoritative, and indeterminate remain distinct; no ambiguous absence authorizes POST; and authority metadata is retained.

### R5-G13 — Receipt retention and GC

Race lookup/recovery with GC, restore old outbox snapshots, cross policy boundaries, and apply storage pressure. Pass only if no second receiver event occurs, authenticated uniqueness proof survives the replay horizon, policy changes are audited, and storage growth meets the frozen bound.

### R5-G14 — External-effect claim boundary

Model-check the frozen safety property, then run the mapped consumer crash/replay/fanout cases. Pass only if executable traces refine the model, idempotent controls satisfy the scoped property, non-idempotent controls produce the expected retained counterexample, and published language does not exceed evidence.

### R5-G15 — Qualification manifest and corpus registry

Validate a complete manifest, then remove, alter, add, and swap required artifacts/oracles after freeze. Pass only if the valid manifest resolves and every mutation invalidates qualification before candidate execution.

### R5-G16 — Evidence governance

Build a complete evidence bundle, then omit a failure, tamper with a summary, break provenance, and insert secret-bearing content. Pass only if the complete bundle reproduces and each adversarial bundle fails for its expected reason while safe correlation remains.

### R5-G17 — DAG convergence

Topologically validate `R5_DAG.json`, bind all phase manifests to exact lineage, recompute all outcomes, and inject a missing gate, cycle, and retry-to-green replacement. Pass only if the complete lineage yields the same disposition and every adversarial mutation fails closed.

## Phase gates

### R5-PG0 — Foundations

Requires G15 and G16 PASS on one qualification-package revision. Confirms frozen inputs, complete expected gate inventory, reproducible evidence summaries, and retained negative controls.

### R5-PG1 — Protocol and receipt authority

Requires PG0 plus G11, G02, G04, and G03 PASS on one integrated P1 head. Replays a small cross-gate scenario: a compatible sender enters INDETERMINATE, rejects a cross-project receipt, accepts the correctly bound receipt, and reaches ACKED without POST.

### R5-PG2 — Recovery ownership

Requires PG1 plus G01 and G09 PASS. Replays lost ACK with two owners across a lease takeover in each supported topology and requires one authoritative lookup, zero stale-owner effects, and converged ACK.

### R5-PG3 — Failure durability

Requires PG2 plus G05, G06, G07, and G08 PASS. Runs a bounded composite sequence of ACK crash, restart, contention, stale threshold, and one quarantined unrelated row. Safety and recovery-liveness outcomes are reported separately.

### R5-PG4 — Observability and lifecycle

Requires PG3 plus G10 and G13 PASS. Reconciles telemetry before and after GC/restore scenarios and verifies that redacted observations retain enough identity to audit uniqueness decisions.

### R5-PG5 — Final convergence

Requires PG4 plus G12, G14, and G17 PASS and all preceding phase manifests. Produces the bounded R5 disposition only when all 23 gates are present and PASS. Any changed upstream lineage, unresolved result, or missing evidence prevents convergence.

## Gate non-equivalence

A phase gate is not a substitute for its requirement gates: it tests integration across already-qualified components. A requirement gate is not a substitute for its phase gate: it does not establish integrated lineage. Unit tests, mocks, and static validation may precede gates but cannot replace the real boundary named by a gate.
