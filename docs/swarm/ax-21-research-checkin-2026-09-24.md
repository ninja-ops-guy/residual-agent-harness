# AX-21 / RESIDUAL Research Check-in — 2026-09-24

**Status:** append-only research maintenance record  
**Accepted main observed:** `d796f36b75e730a0bab71bdba564206174393719`

This record preserves material observations without modifying AX-21-BASELINE-R0.

## Material findings

### 1. Continuity failure-domain assumption falsified

The retained R0 continuity reproduction showed that after a persistent quota circuit, a route with an unknown quota/failure domain could still be admitted on a later operation. Expected adapter calls were 0; observed calls were 1. The recorded root cause was that persistent blocking covered explicitly advertised domains while UNKNOWN was excluded only for current-operation failures.

R1/R2 added regressions for this class. R2 reports 215 tests with zero failures/errors/skips, but its own verdict remains `PASS_SANDBOX_BOOTSTRAP_ONLY`; it records no real model calls, no actual WSL/systemd qualification, no production Station integration, and no live deployment.

**Falsified assumption:** unknown-domain routes are automatically safe after a persistent quota circuit.

**Candidate RES-UP:** require independently established failure-domain identity before an alternate route can be admitted when independence from a failed domain matters. UNKNOWN remains fail-closed.

### 2. Synthetic lost-ACK reconciliation preserved one delivery without re-generation

The continuity lab retained a synthetic loopback case where ACK loss moved the sender to `DELIVERY_UNKNOWN`, later receipt reconciliation restored `ACKED`, send attempts remained one, receiver message count remained one, and generation events did not change.

This is evidence for bounded receipt reconciliation in the synthetic lab only. It is not a claim of exactly-once production delivery.

### 3. Hammer health checking is coupled to model availability

The supplied Hammer(LEGION) transcript contains repeated `residual-health-check` failures ending at `model-call-started`. Later messages often contain tool-intent JSON, but not corresponding execution-result receipts.

**Falsified assumption:** a model-mediated agent health check is an independent system-liveness probe.

**Candidate RES-UP:** introduce a deterministic, model-free health sentinel that records process/service/file/loopback/provider reachability and typed timeout results before any optional model-assisted diagnosis. Tool-intent text must not count as execution evidence.

### 4. Agent identity is part of experimental validity

The retained identity inventory records a pre-change bridge-credential collision across multiple runtime seats on different hosts. It explicitly separates that from shared provider-account identity and from RESIDUAL worker authority. The finding remains open pending controlled identity separation and replay.

**Candidate hypothesis:** per-seat credential separation reduces attribution ambiguity and cross-seat message contamination.

**Candidate RES-UP:** bind research observations to runtime seat + host + credential generation + session/operation identity where practical; room-display name alone is insufficient provenance.

### 5. Typed review findings landed on accepted main

Merged PR #304 makes reviewer authority structurally typed: blocking findings cannot coexist with an approved verdict, rejection requires a blocking finding, and malformed legacy free-form findings are rejected.

This is implementation evidence derived from earlier ambiguity, not a new experimental result. It supports the paper-level principle that authority-bearing review outputs should be structurally incapable of contradictory acceptance states.

### 6. v1 audit reproduced missing Station ownership/exposure coverage

Draft PR #446 reproduced two important bounded failures:

- two live Station processes could open the same data directory and observe shared mutation;
- the direct Server-constructor exposure path did not inherit the CLI non-loopback guard.

The audit explicitly did not demonstrate task duplication, credential theft, data corruption, or a live remote bind.

**Falsified assumptions:** one-owner-per-data-directory was already enforced on the tested paths; CLI exposure policy automatically covered programmatic construction.

**Candidate RES-UP:** maintain a closed-world manifest of every supported state-mutation, runtime/provider, ownership, and exposure entry path, and require an explicit lifecycle/authority guard for each.

### 7. A selected green AUD-1 candidate was later invalidated by broader review

PR #448 initially selected `7001bdf...` after technical qualification and owner review. A later mutation-surface security review discovered lifecycle-admission gaps and explicitly withdrew that selection.

The current live #448 head is `e9f5ba7eaba80a461c0676035a37c578e073f925`. Fresh workflows are green, including native Windows ownership qualification and sensitivity checks. However, the visible delta from the withdrawn candidate is primarily Windows ownership qualification/hardening and workflow identity binding. It does not itself demonstrate repair of every broader mutation-surface finding that caused the withdrawal.

This is a useful negative result: a candidate can be green for its tested boundary yet still be insufficient for a broader claim.

**Candidate RES-UP:** transitive evidence invalidation. Candidate withdrawal should mechanically stale downstream approvals, helper pins, and qualification receipts until a replacement explicitly repairs the supersession findings and receives fresh exact-head evidence.

### 8. F6 helper #449 is stale relative to the withdrawn candidate

PR #449 remains bound to the withdrawn `7001bdf...` candidate and records physical F6 as not executed, with both F6-A and F6-B pending.

Its focused helper results remain evidence about those helper bytes, but it cannot qualify physical F6 against a replacement candidate.

### 9. Evidence identity required qualification

The current #448 workflow explicitly binds Windows evidence to the PR head. Earlier independent review work also had to reconcile human-reviewed heads with GitHub synthetic-merge execution by proving tree equivalence.

**Candidate RES-UP:** every authority-bearing qualification receipt should identify source head, executed checkout SHA/tree, artifact identity, and whether evidence is exact-head or tree-equivalent.

### 10. Release-governance DAG contained a circular dependency

Draft PR #445 retained a first failure showing that the original claims matrix required evidence from stages that depended on an RC before that RC could exist, and CV-18 depended on itself. The proposed correction separates selection, qualification, soak, and final authorization.

**Candidate RES-UP:** machine-validate research/release gate graphs for self-dependency, future-stage dependency, cycles, and missing mandatory terminal gates.

### 11. Evidence parsing remains an adversarial surface

PR #447 retains failures for ambiguous JSON metadata and proposes strict rejection of duplicate keys, non-finite numbers, malformed roots/parents, and invalid-primary fallback.

This extends the evidence-quality model:

1. byte/digest integrity;
2. containment/path integrity;
3. parser/canonical-syntax integrity;
4. membership/cardinality integrity;
5. semantic/provenance binding;
6. authority/release binding.

Passing one layer does not establish the later layers.

## Baseline comparison

The original AX-21 findings are strengthened, not replaced:

- **evidence over consensus:** strengthened by typed reviews, exact evidence identity, and supersession handling;
- **diagnostic quality constrains autonomy:** strengthened by repeated Hammer timeout-at-model-call observations;
- **telemetry is not evidence:** strengthened by the difference between tool-intent text and execution receipts;
- **identity must not be overstated:** strengthened by retained cross-host bridge-identity collision evidence.

No evidence here establishes whole-system security, live Kimi continuity from the R2 sandbox kit, post-#349 operator-friction reduction, physical F6 success, autonomous recursive development, or final baseline freeze.

## P5 and release state

PR #349 remains open/draft. The frozen before-condition remains the only valid operator-friction measurement: about 11 cold individual-agent queries plus human synthesis and external state.

No formal GitHub release exists at this observation. Therefore no release-tag cutover exists and AX-21-BASELINE-R0 remains a candidate pre-release baseline.

## Candidate RES-UP queue

- `RES-UP-CONT-FAILURE-DOMAIN-001` — persistent failure-domain provenance.
- `RES-UP-HEALTH-001` — model-independent health sentinel with execution receipts.
- `RES-UP-ID-001` — observation identity provenance.
- `RES-UP-AUTH-SURFACE-001` — closed-world mutation/exposure surface manifest.
- `RES-UP-SUPERSESSION-001` — transitive invalidation after candidate withdrawal.
- `RES-UP-EVIDENCE-ID-001` — claim-to-tree execution binding.
- `RES-UP-GATE-DAG-001` — acyclic evidence-gate validation.

These are research candidates, not accepted requirements.

## Paper-safe conclusions

Supported:

- fail-closed controls are surface-dependent;
- evidence systems require adversarial qualification of the evidence apparatus itself;
- later negative evidence can invalidate claim sufficiency without making earlier bounded tests false;
- operational health should be separated from model availability;
- agent identity is part of experimental validity.

Not supported:

- RESIDUAL is secure in general;
- #448 currently repairs every supersession finding;
- F6 has passed;
- R2 proves live distributed continuity;
- #349 has reduced operator friction;
- AX-21 proves autonomous recursive development;
- AX-21-BASELINE-R0 is release-frozen.

## Next high-value evidence

1. publish and exact-head qualify the repair that directly addresses the #448 supersession findings;
2. invalidate/rebind #449 before physical F6;
3. execute F6-A and F6-B separately and retain both;
4. perform post-F6 adversarial re-audit;
5. compare a model-free health sentinel with the current Hammer model-mediated cron path;
6. complete per-seat identity separation and replay the pre-change routing symptom;
7. run the frozen P5 question after #349 and record the before/after operator-friction delta;
8. perform release-tagged reproduction before final AX-21 baseline freeze.

**Disposition: MATERIAL UPDATE — PRESERVE.**
