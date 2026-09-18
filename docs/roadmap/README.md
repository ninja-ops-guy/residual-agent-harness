# RESIDUAL roadmap

This roadmap describes planned work and current evidence boundaries. It is not a release-qualification certificate. Exact source, workflow runs, retained experiment artifacts, and protected governance remain authoritative.

Current accepted repository baseline for this status is **`main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb`**.

## Current capability boundary

| Area | Current state | Evidence / limitation |
| --- | --- | --- |
| Core harness | Implemented | Verifier-owned acceptance, bounded obligations, receipts and evidence handling exist; broad model reliability is not implied |
| Command Station | Implemented and actively hardened | #218 repair context and #233 actionable failure/repeated-patch diagnostics are accepted; general repair reliability remains unproven |
| Mission Control / WebVM | Implemented with bounded fallback/recovery | #248 provider-load lifecycle behavior is accepted; retained production Pages acceptance on parent de7 remains FAIL; #260 is the current-main repair candidate and is not yet accepted |
| Factory M2/M3/M4 | Implemented | Qualification remains exact-revision/environment bound; implementation is not every-host qualification |
| M6 repair loop | Mixed research evidence | #203/#204/#215/#217 FAIL; #220 bounded PASS |
| M6.2 first contract shipment | Research PASS, production pending | #231 self-shipped the first `ImprovementSpec` implementation; #243 is derived from that source plus maintainer hardening and remains open/unaccepted |
| M6.2 evidence-sufficiency fork | Bounded research PASS with defects surfaced | #232 exercised MeasurementGap vs grounded hypothesis behavior and exposed deterministic rejection requirements |
| M6.2 autonomous discovery | One bounded formal-admission PASS; later FAIL/UNKNOWN cells | #257/007J formally admitted one genuinely absent MeasurementGap; #259/#262/#263 fail evidence use; #264 workflow passed but semantic adequacy is UNKNOWN after metric-identity audit |
| M6.2 metric semantics | **BLOCKED pending trust infrastructure** | #265 requires a versioned Metric Registry; #266 specifies typed metric definitions, identity/duplicate gates, semantic-overlap review, and registry/evidence revision binding; M6-008 remains blocked |
| General recursive self-improvement | **UNKNOWN / not established** | No repeated autonomous-discovery → implementation → verifier → champion/challenger success chain exists |
| Paid/live provider success on exact current deployed main | **UNKNOWN / not established** | Retained production Pages proof records `cloud_inference: NOT_RUN`; historical real-account protocol failure remains |

## Accepted current changes

The current accepted sequence includes:

- #200 setup hardening;
- #205 session-scoped provider-channel recovery;
- #218 bounded Station prior-candidate repair context and shared five-attempt ceiling;
- #201 guided frontend and inline Puter setup;
- #233 actionable repair failure-tail retention and repeated failed-patch detection;
- #248 provider-load generation/lifecycle qualification on the credentialless embedded provider path;
- **#197** advisory PR-review workflow/configuration hardening only.

Current `main@3cff6bcd...` has six successful ordinary push workflows in their named scopes. The latest retained **production Pages acceptance** remains first run `35363306307` on parent `main@de7d9774...` and is **FAIL**. Generated desktop+narrow proof and deployment passed; published acceptance failed during provider bootstrap and retained `cloud_inference: NOT_RUN`.

PR #253 is closed unmerged. Open **#260** is rebuilt directly on current main and has all applicable exact-head technical workflows **PASS**, including Browser VM Demo CI and Deploy GitHub Pages; exact-head maintainer approval remains **FAIL / pending matching attestation**. If #260 is accepted, the resulting merged SHA still requires its own first published Pages acceptance. PR-head proof is not production proof.

## M6.2 roadmap issue #222

Issue #222 remains open. Its objective is to move from a repair loop that executes supplied improvement hypotheses toward a system that can originate evidence-grounded, falsifiable ImprovementSpecs while keeping authority outside the model.

The target decomposition remains:

1. `ImprovementSpec` production contract;
2. `EvidenceSnapshot` production contract;
3. `MeasurementGap` production contract plus governed metric identity/semantics;
4. analysis-only `Scientist`;
5. deterministic `HypothesisVerifier`;
6. experiment ledger;
7. champion/challenger evaluator;
8. autonomous discovery experiments and successors.

### Deliverable 1 — ImprovementSpec

**Research status: PASS in #231. Production status: open/unaccepted in #243.**

M6-ROADMAP-001B (#231) ran against a detached clean copy of exact `main@260b5f9...` and retained one implementation attempt, 3/3 immutable checks PASS, independent local review APPROVED, exact reviewed head integrated, a verification receipt, and successful release export.

Production PR **#243** imports the generated implementation but also contains maintainer hardening after review found mutable nested `acceptance` state. Its current head recursively freezes that graph, protects canonical identity from caller-owned mutation, keeps serialization detached, rejects unsupported non-JSON values, and adds independent production tests. The current #243 source therefore **does not claim byte-for-byte identity with the generated #231 source**.

Current #243 status:

- applicable technical PR-head workflows: **PASS**;
- exact-head maintainer approval gate: **FAIL / pending matching attestation**;
- merge/production status: **open, unaccepted**.

Until #243 is accepted, the production contract remains **UNKNOWN / unaccepted**.

### Evidence-sufficiency experiment — #232

M6-EPI-001 completed both experiment arms after one repair and validated the high-level distinction between insufficient and sufficient evidence, while exposing stricter verifier requirements:

- an insufficient-evidence result must not leave required protected invariants empty;
- acceptance criteria must be structured rather than free-form prose;
- performance metrics must not be silently treated as protected invariants.

These remain deterministic HypothesisVerifier rejection cases. #232 does not itself establish the production Scientist or verifier.

## Autonomous discovery — #244 through #264

The retained sequence materially narrows both the failure modes and the first bounded positive result:

- **#244 / 007:** provider timeout before proposal — **FAIL in experiment-execution scope / discovery not reached**.
- **#246 / 007B:** smaller context, provider again timed out — **FAIL in experiment-execution scope / discovery not reached**.
- **#249 / 007C:** provider completed, but free-form candidates were malformed/repeated/truncated — **FAIL in bounded discovery qualification scope**.
- **#250 / 007D, #251 / 007E, #252 / 007F, #254 / 007G:** typed output removed malformed JSON, but deterministic admission rejected false MeasurementGaps for already-measured metrics — bounded **FAILs**.
- **#255 / 007H:** a genuinely absent-metric-shaped proposal reached semantic review but was rejected for causal overclaim, non-falsifiable acceptance, and preservation defects — **FAIL in bounded semantic-review scope**.
- **#256 / 007I:** stale task-ID apparatus defect — **FAIL in experiment-execution/apparatus scope**, not Scientist-hypothesis evidence.
- **#257 / 007J:** local `qwen2.5:7b` proposed genuinely absent `context_bytes_non_success_max`; semantic review approved and an admission/verification receipt was issued — **PASS in bounded autonomous MeasurementGap formal-admission scope**. Receipt `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`; artifact `10558781593`; ZIP SHA-256 `ea74dce1d0706a880566e694d872c76e305b8d28da0eee4dd89801e1232ad26e`.
- **#258 / 007K:** pre-model variable-name apparatus defect — **FAIL in experiment-execution/apparatus scope**.
- **#259 / 007L:** corrected apparatus derived `context_bytes_non_success_max=32652`, but the Scientist continued asking for already-present evidence — **FAIL in bounded post-gap-closure evidence-use scope**.
- **#262 / 007M:** host EvidenceResolver returned exact present values, but the Scientist repeated an already-resolved request — **FAIL in bounded resolver-assisted discovery/repair scope**.
- **#263 / 007N:** active evidence selection exposed trusted metrics, then the Scientist requested `mean_runner_attempts=3.0`, `mean_first_request_bytes=16414.0`, and repeated the already-resolved runner-attempt request — **FAIL in bounded active-evidence-query discovery scope**. Artifact `10558852392`; ZIP SHA-256 `db5eb7e5eba32147c55f7dd54e5dd32d41d14d381ce5140ef12a646eeabb548e`.
- **#264 / 007O:** split Evidence Scout / Hypothesis Scientist / Measurement Planner workflow completed and issued receipt `674513d7e3b82c747bdbea408094ad2c08342943bb05a544e29a6d07727a5359`, but post-hoc audit could not establish that `mean_wall_clock_s_basline` is semantically distinct from already-inspected `successful_mean_wall_clock_s=786.123333` — **workflow PASS; research conclusion UNKNOWN pending metric-identity/semantic validation**. Artifact `10559527734`; ZIP SHA-256 `7a28d6367d91af99dca8ea1a66c0128b136665955a3d273d86a5afb988df895e`.

The important current gain is bounded, not general: **#257 proves one autonomous missing-measurement proposal can cross formal admission under the exact experiment contract.** The later FAIL/UNKNOWN cells show that closing the gap and supplying/resolving evidence does not yet make the Scientist reliably reason from those values, and that receipt integrity alone cannot establish scientific nonredundancy when metric semantics are underspecified.

Therefore general autonomous improvement discovery remains **UNKNOWN / not established** and general recursive self-improvement remains **UNKNOWN / not established**.

## Metric Registry gate — #265 / #266

#264 exposed a new trust requirement: discovery cannot safely call a proposed metric “absent” or “nonredundant” from a free-form identifier alone. Issue **#265** therefore requires a versioned discovery Metric Registry before MeasurementGap admissions can advance the recursive loop.

Open spec PR **#266** defines the intended trust infrastructure:

- versioned `MetricDefinition` and `MetricDefinitionProposal` contracts;
- canonical metric IDs plus description, unit, aggregation, population/observation unit, domain, directionality/interpretation, collection reference, and revision/hash;
- EvidenceSnapshot and admission-receipt binding to registry revisions;
- deterministic naming and exact-duplicate gates;
- semantic-overlap review against existing definitions;
- missing/ambiguous semantics => **UNKNOWN**, never PASS;
- executable negative-path acceptance requirements.

#266 is design/specification only. It does **not** authorize M6-008, metric registration, autonomous writes, or broader acceptance authority. Until the Metric Registry path is implemented, independently reviewed, and qualified, **M6-008 remains BLOCKED**.

## Current build order

1. **Close deliverable 1 correctly:** review and qualify #243; require exact-head maintainer attestation before merge. Preserve the distinction between #231-generated research source and the human-hardened production candidate.
2. **Preserve the #257 admission boundary:** treat 007J as one bounded PASS, not a general discovery claim. Retain its proposal, snapshot, review, receipt, model/provider identity, and artifact as a positive regression fixture.
3. **Implement the Metric Registry trust boundary:** land the #266 design only after review, then implement versioned metric definitions, typed proposals, registry/evidence revision binding, deterministic naming/duplicate gates, semantic-overlap review, and fail-closed UNKNOWN semantics. Do not resume M6-008 until this is qualified.
4. **Evidence contracts:** make `EvidenceSnapshot` and `MeasurementGap` deterministic production contracts with canonical identity, explicit measured-vs-missing semantics, provenance, defensive serialization, and registry-backed metric identity.
5. **Evidence-use semantics:** after a metric is resolved, require the Scientist to incorporate the exact value into the next proposal rather than requesting it again. Repeated resolved requests should terminate/stagnate deterministically.
6. **Scientist boundary:** keep the Scientist analysis-only — no Git/write/integration/promotion authority and no ability to redefine protected invariants.
7. **HypothesisVerifier:** encode #232, #250–#255, #259/#262/#263, and #264 rejection/UNKNOWN cases. A MeasurementGap must name a genuinely absent required measurement; an available bad value is not a missing measurement; causal/acceptance claims must remain falsifiable and evidence-grounded; semantically ambiguous metric identity must remain UNKNOWN.
8. **Experiment ledger:** retain hypothesis/proposal identity, evidence identity, metric-registry revision, code/revision identity, model/provider identity, checks, review, receipts, outcomes, apparatus failures, and negative/UNKNOWN cells.
9. **Champion/challenger:** compare accepted candidate changes against an exact retained baseline with frozen metrics and reject regressions in protected invariants.
10. **Repeat autonomous discovery:** require repeated retained verifier-accepted proposals and complete improvement cycles before making reliability claims. One formal-admission PASS is insufficient for a general claim.
11. **Repair independent governance defects:** refresh and requalify the #207/#208/#212 accounting/release-ordering path on current main.
12. **Confirmatory evaluation:** freeze R0–R5 and planned degradation/routing protocols before paper-facing outcome collection.

## Parallel qualification work

The M6.2 roadmap does not replace other blockers:

- preserve production Pages run `35363306307` as retained FAIL for exact `main@de7d9774...`; complete #260 review/attestation and, if accepted, qualify the resulting merged SHA with its own first production Pages acceptance;
- retain a fresh exact-deployed-revision real-account Puter candidate→verifier→receipt success or keep paid/live provider success UNKNOWN;
- physically validate the #186 mobile fallback without claiming heavyweight-WebVM iPhone reliability;
- complete true blank-environment, recovery/host-loss, and selected elapsed-soak qualification;
- continue #120/#126 WebVM long-run reliability work;
- preserve the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence;
- resolve the #133/#132 retirement-versus-restoration discrepancy explicitly.

## Trust-boundary constraints

Roadmap work must preserve the existing authority split:

- models propose; host-owned checks decide acceptance;
- review, receipt, integration, promotion and release authority remain outside the Scientist/runner;
- protected Factory/M4 implementation, ownership baselines, qualification anchors, protected bytes and evidence schemas require their own reviewed process;
- metric identity/semantics must be versioned and reviewable before a discovery admission can claim nonredundancy;
- `implementation-status.yaml` is an implementation-presence manifest, not a release-qualification manifest;
- historical FAIL/BLOCKED/UNKNOWN cells are not erased by later PASS results.

## Exit criteria for stronger self-improvement claims

Do not describe RESIDUAL as generally self-improving until retained evidence demonstrates, across repeated frozen trials:

1. the system originates defensible ImprovementSpecs from evidence without a supplied hypothesis;
2. a deterministic verifier accepts the hypothesis before execution;
3. protected invariants are explicit and retained;
4. proposed/observed metrics have registry-backed identity and semantics sufficient to distinguish absent, duplicate, overlapping, and merely bad measurements;
5. a bounded implementation/review/integration path executes the accepted hypothesis;
6. a champion/challenger evaluator shows the declared improvement against an exact baseline;
7. failures, apparatus defects, regressions, semantic ambiguities, and UNKNOWN cells are retained rather than filtered from the dataset;
8. the process repeats across more than one task/model/environment cell;
9. no autonomous merge authority is inferred from the experiment.

#257 satisfies only a bounded proposal-admission slice of this larger chain. #264 demonstrates why receipt integrity and workflow success are insufficient without governed metric semantics. Until the full criteria repeat successfully, autonomous discovery reliability and general recursive self-improvement remain **UNKNOWN / not established**.