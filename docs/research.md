# RESIDUAL research status

This document summarizes retained research evidence without converting bounded experiments into broader capability claims. Exact revisions, workflow artifacts, experiment records, and verifier outputs are more authoritative than prose.

Current accepted repository baseline for this status is **`main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb`**.

## Claim discipline

Research outcomes use the same evidence vocabulary as the implementation:

- **PASS** — the declared bounded experiment/criterion passed on the named revision and evidence.
- **FAIL** — the declared bounded experiment/criterion failed.
- **BLOCKED** — the intended claim could not be exercised validly because a prerequisite/intervention/environment was unavailable or invalid.
- **UNKNOWN** — retained evidence is insufficient to assign PASS or FAIL to the intended claim.

A workflow completing successfully only proves that the workflow executed. A provider timeout or apparatus defect before a valid proposal is produced is an experiment-execution failure, not evidence that the unexercised scientific hypothesis is false. A single accepted proposal is bounded positive evidence, not a general reliability claim. An integrity-valid receipt proves the recorded decision/context was bound as specified; it does **not** convert a semantically ambiguous scientific decision into PASS.

## Current-main qualification context

Current `main@3cff6bcd...` was produced by merged #197, which changes advisory PR-review workflow/configuration only. Exact current main has six successful ordinary push workflows in their named scopes.

The newest retained production Pages acceptance remains run `35363306307` on parent `main@de7d9774...` and is **FAIL**. Generated desktop+narrow proof and deployment passed; the published flow failed during provider bootstrap. Retained evidence says `cloud_inference: NOT_RUN`. This browser failure is separate from the research claims below and is not paid/live Puter semantic evidence.

PR #253 is closed unmerged. Its current-main replacement #260 is technically green on its exact head, including PR-head Pages, but remains unaccepted pending exact-head maintainer approval. PR-head proof is not production proof.

## Earlier heterogeneous-DAG evidence — #202

#202 retains two different exact-head outcomes:

- an earlier heterogeneous DAG run: **FAIL**, with only 1/3 tasks integrated and no successful recovery of the dependent branch;
- a later bounded corrected run: **PASS**, using real local Ollama models across a three-task heterogeneous DAG with forced repair, 3/3 integrated, verification receipts present, and release export produced.

The later PASS does not erase the earlier FAIL and does not establish general DAG/recovery reliability, production readiness, or provider-independent model quality.

## M6 repair/self-host evidence

The historical M6 evidence remains deliberately mixed:

- **#203** — first authoritative ImprovementSpec self-host trial: **FAIL**.
- **#204 / M6-SPEC-002** — **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt/release.
- **#215 / M6-SPEC-003** — **FAIL** after exercising prior-candidate repair context.
- **#217 / M6-SPEC-004** — **FAIL** after transport/source clarification.
- **#220 / M6-SPEC-006** — bounded **PASS** on corrected #218 runtime using Qwen2.5-Coder 7B. Attempts 1–2 were rejected; attempt 3 passed frozen checks, Station review approved it, 1/1 integrated, a verification receipt was issued, and release export completed.

Interpretation: the repair loop has retained positive evidence after several negative trials. General repair reliability and autonomous self-maintenance remain **UNKNOWN / not established**.

## M6.2 first roadmap shipment — #231 and production #243

M6-ROADMAP-001B exercised the first M6.2 production contract against a detached clean copy of exact `main@260b5f9...`.

Authoritative retained outcome included one implementation attempt, 3/3 immutable checks **PASS**, independent local review **APPROVED**, exact reviewed head integrated, verification receipt issued, and release export succeeded. Status of that bounded experiment: **PASS**.

Production PR **#243** remains open/unmerged. The original generated implementation was imported, but independent review found that a frozen dataclass could still expose a mutable nested `acceptance` graph. The current #243 head therefore includes maintainer deep-immutability hardening and production tests. **It no longer claims byte-for-byte identity with the generated source.**

Current #243 exact-head status:

- applicable technical workflows: **PASS**;
- exact-head maintainer approval: **FAIL / awaiting matching attestation**;
- accepted production contract on main: **UNKNOWN / unaccepted**.

The #231 research PASS remains valid in its exact experiment scope; the hardened production candidate is a subsequent human-maintained derivative, not evidence that RESIDUAL autonomously generated the final current PR bytes.

## Evidence-sufficiency fork — #232 / M6-EPI-001

Both experiment arms integrated after one repair, so bounded experiment execution was successful. The outputs also exposed deterministic verifier requirements: protected invariants cannot be silently omitted, acceptance criteria need structured semantics, and performance metrics must not be conflated with protected invariants.

Interpretation:

- evidence-sufficiency fork behavior in this experiment: **PASS in scope**;
- candidate conformance to the stricter intended verifier contract: **not established**;
- production Scientist/HypothesisVerifier stack: **UNKNOWN / not yet accepted**.

## Autonomous discovery — M6-SPEC-007 series

### #244 / M6-SPEC-007 and #246 / 007B — execution FAILs

Both authoritative trials timed out at the local provider before a discovery proposal was produced.

Status: **FAIL in experiment-execution scope / discovery not reached**. These cells do not establish that the Scientist hypothesis is false.

### #249 / 007C — representation/repair FAIL

Provider execution completed, but free-form candidate output was malformed/repeated/truncated and exhausted the five-pass brake with 0 integrated, no approved review, no receipt, and no release.

Status: **FAIL in bounded autonomous-discovery qualification scope**.

### #250 / 007D, #251 / 007E, #252 / 007F, #254 / 007G — evidence-grounding FAILs

Typed structured output eliminated the malformed-JSON class. Deterministic admission nevertheless rejected MeasurementGap proposals that described already-measured metrics as missing. #251 repeated the same invalid proposal over bounded repair attempts; #254 reproduced the same class with general `qwen2.5:7b`.

Status: bounded **FAILs** in their exact mechanical-admission/repair/model cells. No semantic approval or admission receipt was issued.

### #255 / 007H — semantic-review FAIL

#255 advanced beyond syntax and present-vs-missing admission. Local `qwen2.5:7b` produced a genuinely absent-metric-shaped MeasurementGap, but semantic review rejected the proposal for causal overclaim, non-falsifiable acceptance, and incoherent preservation criteria.

Retained outcome:

- model/provider execution: completed;
- semantic review: **FAIL**;
- admitted: false;
- admission receipt: none;
- artifact ID `10557259640`;
- ZIP SHA-256 `149c1f56e32d8f23df2f53b739bfafb4e4567138bf3e796c9831ffc2c9d9552f`.

Status: **FAIL in bounded semantic-review scope**.

### #256 / 007I — apparatus FAIL

The trial failed because of a stale task-ID apparatus defect before a valid authoritative proposal evaluation.

Status: **FAIL in experiment-execution/apparatus scope**. This is not evidence against the Scientist hypothesis.

### #257 / 007J — bounded formal-admission PASS

Authoritative run **`35370173939`** completed local `qwen2.5:7b` proposal and semantic review successfully. The Scientist proposed a `MeasurementGap` for genuinely absent `context_bytes_non_success_max`, grounded in the frozen evidence rather than calling an already-measured metric missing.

Retained outcome:

- typed proposal generation: completed;
- semantic review: **APPROVED**;
- admitted: **true**;
- admission/verification receipt hash `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`;
- artifact ID `10558781593`;
- ZIP SHA-256 `ea74dce1d0706a880566e694d872c76e305b8d28da0eee4dd89801e1232ad26e`.

Status: **PASS in this bounded autonomous MeasurementGap formal-admission scope**.

This is the first retained PASS at formal autonomous proposal admission in this sequence. It establishes that one evidence-originated missing-measurement proposal crossed the deterministic/semantic admission boundary under this exact setup. It does **not** establish general autonomous discovery, successful implementation of an improvement, champion/challenger improvement, recursive self-improvement, or autonomous merge authority.

### #258 / 007K — apparatus FAIL

The intended gap-closure trial failed pre-model due to a variable-name apparatus defect.

Status: **FAIL in experiment-execution/apparatus scope**; not a Scientist-hypothesis result.

### #259 / 007L — gap-closure/evidence-use FAIL

The corrected apparatus derived the admitted missing measurement `context_bytes_non_success_max=32652` and included it in the enriched evidence snapshot. The Scientist nevertheless continued to request measurements already present in the evidence.

Status: **FAIL in bounded post-gap-closure evidence-use scope**. No new admission receipt.

### #262 / 007M — resolver-assisted repair FAIL

The host EvidenceResolver correctly recognized requested present metrics and returned exact values, including `context_bytes_non_success_max=32652` and `context_bytes_non_success_mean=31629.0`. The Scientist then repeated an already-resolved request.

Retained outcome:

- host resolver present-vs-missing behavior: exercised successfully in scope;
- final mechanical error: `Scientist repeated already-resolved evidence request 'context_bytes_non_success_mean'`;
- admitted: false;
- review: not approved;
- receipt: none;
- artifact ID `10557804447`;
- ZIP SHA-256 `04ee76fd12e10d0d637311137453f3c1fef128c83d6620b566eb844fbd511f5b`.

Status: **FAIL in bounded resolver-assisted discovery/repair scope**.

### #263 / 007N — active evidence-query FAIL

Authoritative run **`35372809744`** exercised active trusted-evidence selection with local `qwen2.5:7b`. The host exposed selected values including `shipping_task_success_rate=0.6`, `provider_timeout_rate=0.2`, `mean_wall_clock_s=696.4382`, and `successful_mean_wall_clock_s=786.123333`.

The Scientist then requested `mean_runner_attempts`, which the resolver returned as `3.0`; requested `mean_first_request_bytes`, returned as `16414.0`; and finally repeated the already-resolved `mean_runner_attempts` request.

Retained outcome:

- local model calls: completed;
- provider error: none;
- active evidence selection/resolution: exercised in scope;
- final mechanical error: `Scientist repeated already-resolved evidence request 'mean_runner_attempts'`;
- admitted: false;
- review: not approved (`no admissible proposal`);
- admission receipt: none;
- artifact ID `10558852392`;
- ZIP SHA-256 `db5eb7e5eba32147c55f7dd54e5dd32d41d14d381ce5140ef12a646eeabb548e`.

Status: **FAIL in bounded active-evidence-query discovery scope**.

### #264 / 007O — split-role workflow PASS; semantic claim UNKNOWN

The split-role architecture worked operationally: Evidence Scout selected five metrics; Hypothesis Scientist explicitly returned `insufficient_evidence`; Measurement Planner requested a new baseline metric; the host EvidenceResolver classified it absent; branch-aware review approved; and receipt `674513d7e3b82c747bdbea408094ad2c08342943bb05a544e29a6d07727a5359` was issued.

Post-hoc audit found that the requested metric ID is misspelled/undefined (`mean_wall_clock_s_basline`) and may overlap the already-inspected `successful_mean_wall_clock_s=786.123333`. Because the discovery EvidenceSnapshot binds metric IDs/values but not governed definitions for unit, population, aggregation semantics, collection method, or equivalence/overlap, the claim that this was a genuinely absent and nonredundant metric cannot be established.

Retained outcome:

- split-role workflow execution: **PASS**;
- receipt issuance/integrity: **PASS in recorded-decision scope**;
- semantic adequacy of the MeasurementGap admission: **UNKNOWN**;
- artifact ID `10559527734`;
- ZIP SHA-256 `7a28d6367d91af99dca8ea1a66c0128b136665955a3d273d86a5afb988df895e`.

The receipt must not be used as scientific authority to advance the recursive loop. **M6-008 remains BLOCKED** pending metric-identity/semantic validation.

Issue **#265** records the required remediation: a versioned discovery Metric Registry. Open spec PR **#266** defines typed `MetricDefinition` and `MetricDefinitionProposal` contracts; registry/evidence revision binding; deterministic naming, identity, and exact-duplicate gates; semantic-overlap review; executable negative paths; and fail-closed `UNKNOWN` behavior when semantics are missing or ambiguous. #266 is trust-infrastructure design only and does not authorize metric registration or M6-008.

### #270 / Metric Registry implementation — technical PASS, unaccepted

Open PR **#270**, stacked on unapproved spec PR #266, implements the versioned/content-addressed Metric Registry trust boundary without changing StationReceipt v2. Its exact head `ee879417bb66de9bcb3a5681e1be93417750456c` is green across the reported Command Station Python 3.11/3.12/3.13 discovery, wheel build, Docker, browser UI, Control Plane, clean install, Factory ownership, controller/provider contracts, and measured-evaluation acceptance checks. A dedicated downstream M6-SPEC-007P also ran the 16 focused registry tests plus three preregistered controls successfully.

Status: **PASS in implementation/qualification scope on the open stacked PR; production acceptance remains UNKNOWN / unaccepted**. The registry is not accepted on `main`, does not authorize metric registration, and does not unblock M6-008 by itself.

### #272 / 007Q — apparatus FAIL before model execution

The registry-aware discovery experiment passed all 16 focused registry tests but failed `py_compile` before model execution because the generated import edit contained literal escaped newline characters. No Scientist, Planner, reviewer, proposal, or admission event occurred.

Status: **FAIL in experiment-execution/apparatus scope; registry-aware discovery was not exercised**. The exact head was not rerun for green.

### #273 / 007R — provenance-transcription FAIL

The corrected apparatus passed syntax, registry tests/preflight, Ollama setup, and Evidence Scout. The Scientist produced a grounded `insufficient_evidence` observation but copied the 64-hex EvidenceSnapshot identity incorrectly. Deterministic verification rejected `evidence_snapshot_hash mismatch` before the Planner or reviewer ran. No receipt was issued.

Retained evidence: 2 model calls, 1,538 reported tokens; artifact ID `10562515080`; ZIP SHA-256 `a0f86bb813f903696f95a1c1bb3aafa79c328d59f7d1874f798978659ff96e7e`.

Status: **FAIL in bounded provenance-transcription/mechanical-verification scope**. The result supports moving immutable provenance out of model-authored schemas; it does not establish general discovery failure.

### #274 / 007S — registry/receipt binding PASS

All seven preregistered deterministic binding controls passed after the 16 focused registry tests. Changing `mean_wall_clock_s` semantics while preserving the metric ID and revision label changed the registry content hash and both admission/verifier bindings, causing the old receipt context match to fail. Direct registry-hash tampering and a seconds→milliseconds unit mismatch were also rejected.

Retained artifact ID `10560939948`, ZIP SHA-256 `2a9a7e7a63c381e3b48577e2bfc393fc19c43be45a48f593f073e2e66f575ea1`.

Status: **PASS in bounded registry/receipt binding-control scope**. StationReceipt v2 remained unchanged; this does not register a metric or grant implementation/promotion authority.

### #277 / 007T — host provenance envelope PASS; Planner transcription FAIL

The independent host-provenance change worked: the model-authored Scientist/Planner schemas contained no snapshot hash, registry hash, or human-gate field, and the host attached those facts deterministically. The Scientist proposal then passed mechanical verification with the exact host-bound identity.

The Planner failed at a different transcription boundary by proposing already-registered `context_bytes_non_success_mean` while re-authoring an observation value that actually belonged to `context_bytes_success_mean`. Deterministic verification stopped the run before registry assessment/review. No receipt was issued.

Retained evidence: 3 model calls, 4,306 reported tokens; artifact ID `10562057488`; ZIP SHA-256 `fa2b2329473e38bccc5d8b74ac44cd985857bc699367a34efbdfbeb348602ef6`.

Status: **host provenance envelope PASS in its bounded mechanism scope; overall experiment FAIL at Planner transcription**. M6-008 remains blocked.

### #286 / 007U — result pending

#286 further minimizes the Measurement Planner output so the host carries forward the verified Scientist observation, preservation invariants, provenance, registry identity, and human gate. At this status check there is no authoritative owner result comment yet; only an external Vercel rate-limit notification is retained.

Status: **UNKNOWN / pending authoritative experiment result**. External preview-service rate limiting is not research evidence.

### Current discovery interpretation

The series now separates several failure layers:

1. **#244/#246 — execution:** provider timed out before proposal.
2. **#249 — representation/repair:** provider completed, but free-form output failed mechanical representation/repair.
3. **#250/#251/#252/#254 — evidence grounding:** typed outputs were well formed but contradicted the frozen evidence.
4. **#255 — semantic quality:** a mechanically plausible missing-measurement proposal failed scientific review.
5. **#257 — formal admission:** one genuinely absent MeasurementGap passed deterministic/semantic admission and received a receipt.
6. **#259/#262/#263 — post-admission evidence use:** after the missing measurement was closed and host-side resolution improved, the Scientist still failed to use resolved measurements coherently and repeated present requests.
7. **#264 — metric identity/semantics:** the split-role workflow completed and issued an integrity-valid receipt, but post-hoc audit could not establish that the admitted metric was semantically distinct/nonredundant, so the research claim is **UNKNOWN** rather than PASS.
8. **#270/#274 — registry trust mechanism:** the open implementation and bounded negative controls provide positive evidence that metric semantics can be content-addressed and bound into admission/receipt context without changing StationReceipt v2; acceptance on `main` remains unestablished.
9. **#272/#273/#277 — registry-aware discovery apparatus/transcription:** one apparatus failure and two fail-closed transcription-boundary failures show that moving immutable provenance to the host removes one failure class but does not yet make Planner behavior reliable.
10. **#286 — minimized Planner envelope:** authoritative result remains **UNKNOWN / pending**.

The deterministic checker/resolver is doing useful work: it prevents plausible-sounding but evidence-contradicted MeasurementGaps from becoming accepted merely because output is well formed. The #257 PASS remains meaningful positive evidence that this boundary can admit one defensible autonomous gap proposal. #274 provides bounded positive evidence for the new registry/receipt binding mechanism. The later FAIL/UNKNOWN cells show that proposal admission and trustworthy metric identity are not equivalent to reliable evidence-driven scientific iteration.

Therefore **general autonomous improvement discovery remains UNKNOWN / not established**, **general recursive self-improvement remains UNKNOWN / not established**, and **M6-008 remains BLOCKED pending acceptance of the Metric Registry trust boundary and a valid registry-aware discovery result**.

## Deterministic stress evidence

### Campaign A — #206

- STRESS-A4 repair pressure: **BLOCKED / invalid intervention** because zero intended faults were injected.
- STRESS-A5 DAG pressure: **FAIL / incomplete**; 3/6 tasks integrated before no-runnable-task escalation.
- STRESS-A6 real-model reliability: **FAIL in scope**; the frozen Qwen2.5-Coder 7B trials produced zero successes.

Later M6 PASS results are different interventions and do not erase these cells.

### Campaign B — #207

- STRESS-B1 budget ordering: **FAIL** — exhausted-budget accounting occurred after accepted integration/release.
- STRESS-B2 early convergence: **PASS** in its exact control.
- STRESS-B3 terminal verifier failure/release: **FAIL** — a non-empty release materialized after terminal verifier failure.
- STRESS-B4 repeated repair pressure: containment **PASS**, recovery **FAIL**.

These remain governance defects until a current-base repair is accepted and the relevant scenarios are requalified.

### Failure matrix — #212

#212 retains distinct fail-closed/recovery paths. Its missing-usage case remains **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` abort. This corroborates the #207 ordering-defect family.

## Central research hypothesis

RESIDUAL's central research direction is that system-level reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable model computation rather than assuming each model call is reliable.

Current evidence supports parts of the mechanism, including bounded verification, rejection, evidence resolution, one bounded autonomous formal-admission PASS, and bounded registry/receipt semantic-binding controls. It does **not** yet establish the broad hypothesis across repeated live-model tasks, environments, champion/challenger comparisons, or full autonomous improvement cycles. The #264 audit and the subsequent registry-aware failures show that scientific semantics and provenance must be governed without pushing immutable identity or already-verified context back onto the model as transcription work.