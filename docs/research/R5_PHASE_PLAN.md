# R5 phased convergence plan

Status: planning only; no R5 runtime implementation is included

## Ordering rationale

The six phases are ordered by proof dependency, not by component ownership. Qualification contracts and evidence governance come first so later outcomes cannot define their own oracle. Protocol versioning precedes signed receipts because canonical bytes and mandatory feature negotiation must be stable before receipt authenticity is meaningful. Explicit reconciliation states precede fencing because ownership must condition named transitions rather than an ambiguous `PENDING` row. Durability, observability, retention, and distributed claims then build on those foundations.

This ordering resolves the cycle implicit in PR #410 between the state machine and malformed-receipt handling: the state machine depends on the versioned protocol contract, while receipt validation independently depends on the authenticated receipt envelope. Their interaction is qualified together at the P1 phase gate rather than expressed as a circular requirement dependency.

## R5-P0 — Qualification and evidence foundations

Requirements: `R5-SC-015`, `R5-SC-016`

Purpose: freeze qualification manifests, corpus identities, deterministic oracles, evidence schemas, provenance, redaction, and counterexample-retention rules before any R5 runtime candidate is assessed.

Deliverable boundary:

- qualification schemas and fixture registry;
- external harness interfaces and negative controls;
- evidence manifest and provenance specification;
- no product protocol or runtime behavior.

Independent qualification: `R5-G15`, `R5-G16`, then phase gate `R5-PG0`.

Exit: both requirement gates pass, the phase evidence bundle reproduces from raw records, and post-hoc oracle substitution fails closed.

Rollback: replace the qualification package only through a new pinned version. Never rewrite earlier bundles or reuse their run identity.

## R5-P1 — Protocol and receipt authority

Requirements: `R5-SC-011`, `R5-SC-002`, `R5-SC-004`, `R5-SC-003`

Purpose: establish a versioned wire/storage contract, authenticated request-bound receipts, bounded parsing and semantic validation, and explicit durable reconciliation states including `INDETERMINATE`.

Suggested merge units:

1. version registry and compatibility contract;
2. receipt envelope, canonical binding, and verifier;
3. malformed/cross-project receipt rejection and quarantine reason codes;
4. durable state schema and transition engine.

Each merge unit must have its own targeted tests. The phase is not qualified until the integrated exact head passes `R5-G11`, `R5-G02`, `R5-G04`, and `R5-G03` under `R5-PG1`.

Exit: incompatible versions create no effect; only an authentic fully bound receipt can ACK; malformed or cross-project receipts cannot ACK; every crash-point outcome maps to a declared durable state.

Rollback: unknown versions or states fail closed. No rollback may collapse `INDETERMINATE` to `PENDING` or remove mandatory receipt bindings.

## R5-P2 — Recovery ownership and topology

Requirements: `R5-SC-001`, `R5-SC-009`

Purpose: add lease ownership and monotonically fenced transitions, then declare and qualify supported single-process, multi-process, and multi-host topologies.

Suggested merge units:

1. lease/fence persistence and conditional send/transition operations;
2. stale-owner takeover and resume rejection;
3. topology capability detection and fail-closed unsupported-topology handling;
4. distributed lease adapter only for topologies explicitly selected for support.

Independent qualification: `R5-G01`, `R5-G09`, then `R5-PG2`.

Exit: only the current fence can send or mutate; stale owners have zero effect; every supported topology demonstrates single advancement under partition/failover; unsupported topology is rejected before send.

Rollback: quiesce owners and advance authority epoch before downgrade. Never run an unfenced recovery binary beside fenced recovery.

## R5-P3 — Failure durability and stale operations

Requirements: `R5-SC-005`, `R5-SC-006`, `R5-SC-007`, `R5-SC-008`

Purpose: qualify crash during ACK persistence, corrupted outbox handling, SQLite contention/storage failures, and durable stale/indeterminate operator policy.

Suggested merge units:

1. ACK transaction durability and restart verification;
2. byte-preserving corruption quarantine;
3. bounded SQLite contention and persistence-error semantics;
4. versioned stale policy and authenticated inspect/reconcile/cancel/resume dispositions.

Independent qualification: `R5-G05` through `R5-G08`, then `R5-PG3`.

Exit: every injected ACK crash produces the prior safe state or complete verified ACK; corruption causes no network action; contention and disk errors cannot create unjournaled effects; age alone never authorizes resend, success, or deletion.

Rollback: preserve quarantines, receipts, explicit storage-error outcomes, and policy versions. Unknown records remain indeterminate.

## R5-P4 — Observability and evidence lifecycle

Requirements: `R5-SC-010`, `R5-SC-013`

Purpose: make reconciliation health measurable and control receipt/idempotency-data retention without erasing uniqueness evidence.

Suggested merge units:

1. transition observations and bounded metrics;
2. deterministic alerts for stuck indeterminate work and lease contention;
3. retention policy and authenticated tombstones;
4. GC race control and restored-client defense.

Independent qualification: `R5-G10`, `R5-G13`, then `R5-PG4`.

Exit: metrics exactly reconcile to durable journals with bounded, redacted labels; receipt GC preserves uniqueness over the declared replay horizon while satisfying the storage bound.

Rollback: journal truth remains authoritative. Dashboard compatibility and tombstone readability are mandatory downgrade checks.

## R5-P5 — Distributed authority and convergence

Requirements: `R5-SC-012`, `R5-SC-014`, `R5-SC-017`

Purpose: distinguish authoritative absence from lag/partition, bound any external-effect claim, and produce a fail-closed final qualification from all prior phase evidence.

Suggested merge units:

1. authority-aware distributed receipt lookup outcomes;
2. formal state model, refinement map, and downstream consumer adapters;
3. convergence controller that validates the DAG and exact phase lineage.

Independent qualification: `R5-G12`, `R5-G14`, `R5-G17`, then `R5-PG5`.

Exit: ambiguous or non-authoritative absence cannot trigger repost; the published effect claim is no broader than model and executable evidence; all 17 requirement gates and six phase gates pass with no unresolved or missing evidence.

Rollback: any upstream rollback invalidates the downstream convergence disposition until the affected suffix of the DAG is requalified.

## Critical path

Two equal-depth safety paths converge at `R5-SC-017`:

```text
SC-015 → SC-016 → SC-002 → SC-004 → SC-005 → SC-006 → SC-010 → SC-017
```

```text
SC-015 → SC-011 → SC-003 → SC-001 → SC-009 → SC-012 → SC-014 → SC-017
```

The first path is evidence/receipt/durability/observability constrained. The second is protocol/state/ownership/distributed-authority constrained. Work may proceed in parallel only after its declared dependencies pass; phase gates remain integration barriers.

## Merge discipline

- Use a separate PR for each suggested merge unit or another comparably small review surface.
- Bind tests to the exact head of each unit and rerun the phase gate on the integrated phase head.
- Do not merge a later phase into a branch whose prerequisite phase gate is unresolved.
- Retain failed attempts and counterexamples; do not force-push them out of the evidence lineage.
- Keep qualification harness code external to candidate runtime code.
- Never amend R4.1 or its evidence to represent R5 behavior.

## Recommended first post-canary implementation phase

Begin with **R5-P0 qualification and evidence foundations**. It is the first dependency root and contains no runtime behavior. After P0 independently passes, the first runtime-bearing phase should be **R5-P1 protocol and receipt authority**. Starting with leases or concurrency before versioned states and receipt contracts would attach ownership semantics to an unstable protocol surface.

No phase in this plan is authorized to begin before the R4.1 canary is separately authorized and the coordination process explicitly opens post-canary R5 implementation.
