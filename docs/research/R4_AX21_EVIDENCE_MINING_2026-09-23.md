# R4/R4.1 and AX-21 evidence mining

This note indexes read-only retained evidence. It does not claim novelty and
does not modify or reinterpret sealed acceptance criteria.

## Observations and contradictions

- R4 first ended `BLOCKED`: G11 failed because qualification used a stale
  `Station.prepare()` snapshot; G13 failed because restart retransmitted before
  authoritative lookup. R4.1 separated the instrumentation defect from the
  candidate protocol defect and reached 17/17 PASS after the bounded candidate
  repair and full regression replay.
- Receiver idempotency preserved one receiver event in the original lost-ACK
  scenario, yet did not satisfy the sender-side requirement. The contradiction
  was between “no duplicate observed” and “safe restart protocol proven.”
- Generation, tool execution, Shared Comms persistence, delivery ACK, and useful
  work were explicitly separated. Tool-call-shaped text was a negative control,
  not evidence of execution.
- Fail-closed qualification worked as governance: two unresolved gates forced
  `BLOCKED`; missing evidence did not become PASS; acceptance criteria were
  frozen before repair and rerun.
- Seal attempt v1 was semantically corrupt because derived metadata said 44/44
  while the authoritative manifest contained 50 entries. Hashes of authoritative
  files remained valid. Seal v2 recomputed 50/50 and retained v1 unchanged.
- AX-21 distinguishes the contemporaneous source log (#350) from derived maps
  (#360/evidence map). The map explicitly says the source log wins on divergence.
- AX-21 records large operator reconciliation costs: approximately 11 agent
  queries for a cold status reconstruction and 15+ manually synthesized reports.
- AX-21 retained a local 7B claim-to-verified-candidate observation around 16.4s,
  but evidence gaps remained for one remote host and live Station DB snapshots.
- Credential interface misuse (`export ...=` consuming a file) independently
  produced HTTP 403 on two workers; this is an operator/interface boundary, not
  evidence of provider outage.
- The continuity R1 research note falsified an assumption that route-local
  identity checks covered persisted failure-domain circuits; a later operation
  invoked an incompletely identified route when expected calls were zero.
- R1 also reproduced receiver commit/caller non-observation with explicit
  `DELIVERY_UNKNOWN`, lookup, and one receiver message, foreshadowing R4-G13.
- Organic outage summaries remain weaker than raw provider/gateway, installed
  source, fallback configuration, and delivery records. Synthetic continuity
  results must not be substituted for organic causal evidence.

## Operator and agent boundary

Operators froze criteria, authorized bounded actions, supplied credentials and
topology, interpreted ambiguous evidence, and decided disposition. Agents built
fixtures, ran bounded checks, and summarized results. Neither model narration nor
agent self-report could authorize execution or replace independently observed
postconditions. Human/assistant engineering must be reported as such rather than
as autonomous unavailable-swarm behavior.

## Potential research claims (not novelty claims)

### RC-01 — Receiver idempotency is insufficient evidence for restart safety

- **EVIDENCE:** original R4-G13 failure; R4.1 lookup-before-repost repair and PASS;
  R1 lost-response/subprocess reconciliation fixtures.
- **ALTERNATIVE_EXPLANATIONS:** the original receiver's idempotency may make the
  tested topology operationally safe despite protocol noncompliance; mocks may
  omit downstream effects.
- **REQUIRED_ABLATION:** sender lookup removed vs enabled; receiver idempotency
  removed vs enabled; crash timing crossed at every boundary.
- **REQUIRED_LITERATURE_REVIEW:** transactional outbox, idempotency keys,
  exactly-once/effectively-once semantics, crash recovery, two-generals problem.
- **CONFIDENCE:** high for the tested protocol distinction; low for generality.

### RC-02 — Direct recomputation prevents a class of evidence-authority drift

- **EVIDENCE:** 44/44 derived seal claim contradicted a 50-entry authoritative
  manifest; Seal v2 and PR #415 directly recompute 50.
- **ALTERNATIVE_EXPLANATIONS:** this may be an isolated manual transcription error,
  not a systematic failure mode; direct recomputation can share generator bugs.
- **REQUIRED_ABLATION:** manual/template/configured counts vs direct manifest
  derivation; shared vs independent verifier implementations; semantic mutations.
- **REQUIRED_LITERATURE_REVIEW:** reproducible builds, in-toto/SLSA provenance,
  evidence graphs, measurement validity, diverse double compilation/verifiers.
- **CONFIDENCE:** high for this incident; medium for broader governance effect.

### RC-03 — Frozen fail-closed gates constrain post-hoc success narratives

- **EVIDENCE:** R4 remained BLOCKED with 15/17 PASS; G11 instrumentation failure
  was not silently retyped; full R4.1 rerun used the predeclared 17 gates.
- **ALTERNATIVE_EXPLANATIONS:** extra process cost may not improve validity if
  gates are incomplete or correlated with the implementation.
- **REQUIRED_ABLATION:** frozen vs editable criteria under seeded failures; measure
  false acceptance, repair scope, and time-to-resolution.
- **REQUIRED_LITERATURE_REVIEW:** preregistration, specification gaming,
  Goodhart's law, safety cases, independent verification.
- **CONFIDENCE:** medium-high for governance behavior; causal benefit unmeasured.

### RC-04 — Stale snapshots can invert qualification conclusions

- **EVIDENCE:** G11 used a pre-persistence snapshot lacking `candidate_dir` while
  authoritative task state contained it; reload corrected instrumentation.
- **ALTERNATIVE_EXPLANATIONS:** narrow harness bug rather than a general stale-state
  pattern; a different API contract might intentionally return pre-write state.
- **REQUIRED_ABLATION:** snapshot-return vs authoritative reload across delayed,
  concurrent, and replicated state updates.
- **REQUIRED_LITERATURE_REVIEW:** linearizability, read-your-writes consistency,
  TOCTOU, test oracle validity.
- **CONFIDENCE:** high for the incident; medium for broader applicability.

### RC-05 — Independent verification needs identity reconciliation, not only rerun

- **EVIDENCE:** AX-21 PR #357 review reconciled human-reviewed head with CI
  synthetic merge by proving identical trees; Seal v2 pins candidate tree and
  authoritative manifest digest.
- **ALTERNATIVE_EXPLANATIONS:** tree equality omits environment/runtime variation;
  reviewer independence may be social rather than implementation-diverse.
- **REQUIRED_ABLATION:** commit-only, tree-only, and full environment identity;
  same-code and diverse verifier comparisons.
- **REQUIRED_LITERATURE_REVIEW:** reproducibility, hermetic builds, N-version
  programming, software attestation.
- **CONFIDENCE:** high for identity necessity; medium for sufficiency boundaries.

### RC-06 — Human reconciliation load is an observable system property

- **EVIDENCE:** AX-21 cold status reconstruction required ~11 queries and normal
  operation synthesized 15+ reports into external ledgers.
- **ALTERNATIVE_EXPLANATIONS:** counts depend on swarm size, UI, task phase, and
  operator practice; retained logs may under/over-count meaningful interventions.
- **REQUIRED_ABLATION:** dashboard/shared journal on vs off, matched tasks and team
  size, blinded coding of intervention/report events.
- **REQUIRED_LITERATURE_REVIEW:** common operational picture, coordination theory,
  cognitive load, human-in-the-loop multi-agent systems.
- **CONFIDENCE:** medium for the baseline, low for causal attribution.

## RES-UP candidates and questions

- `RES-UP-R5-01`: durable fenced recovery ownership with explicit
  `INDETERMINATE` state and direct receipt binding.
- `RES-UP-EG-01`: typed evidence DAG whose derived claims terminate at named
  authoritative artifacts and are independently recomputed.
- `RES-UP-OPS-01`: authoritative swarm-status projection designed to reduce
  manual query/synthesis load while preserving source-event links.
- `RES-UP-QUAL-01`: qualification APIs return post-write authoritative identity
  or force explicit reload; stale snapshots are never implicit oracles.
- Research whether receipt lookup unavailability should preserve `PENDING`, use
  a distinct `INDETERMINATE`, or require operator disposition under each topology.
- Research how independent a verifier must be (code, team, runtime, parser,
  infrastructure) for each class of evidence claim.

## Paper-ready observations (descriptive only)

1. A qualification run with 15 passing gates and two failures remained BLOCKED;
   after one harness correction and one protocol repair, the exact 17-gate suite
   passed with frozen regression evidence.
2. One observed receiver event did not prove the sender had reconciled before
   retransmission; network-action order was necessary evidence.
3. A seal could be byte-integrity-consistent yet semantically invalid because a
   derived count disagreed with its authoritative manifest.
4. Retained AX-21 records separate source logs, derived ledgers, independently
   reviewed identities, and preliminary evidence gaps rather than flattening all
   artifacts into equal authority.

Evidence sources: authoritative R4/R4.1 runtime summaries and gate records, Seal
v2, retained AX-21 baseline map/claim review/independent review, and continuity R1
research note. Candidate modified: no. Blockers: literature review and ablations
above. Pre-canary: preserve direct-source verifier and review the separately
reported receipt-binding finding. Pre-production: R5 recovery/receipt gates.
Canary execution status: **NOT EXECUTED**.
