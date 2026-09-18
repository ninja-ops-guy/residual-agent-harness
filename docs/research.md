# RESIDUAL research status

This document summarizes retained research evidence without converting bounded experiments into broader capability claims. Exact revisions, workflow artifacts, experiment records, and verifier outputs are more authoritative than prose.

Current accepted repository baseline for this status is **`main@de7d9774cfd63c77ef5645ca43aa0be1a604887f`**.

## Claim discipline

Research outcomes use the same evidence vocabulary as the implementation:

- **PASS** — the declared bounded experiment/criterion passed on the named revision and evidence.
- **FAIL** — the declared bounded experiment/criterion failed.
- **BLOCKED** — the intended claim could not be exercised validly because a prerequisite/intervention/environment was unavailable or invalid.
- **UNKNOWN** — retained evidence is insufficient to assign PASS or FAIL to the intended claim.

A workflow completing successfully only proves that the workflow executed. It does not automatically make every scenario inside it PASS. Likewise, a provider timeout before a hypothesis/proposal is produced is an experiment-execution failure, not evidence that the unexercised scientific hypothesis is false.

## Current-main qualification context

Exact `main@de7d9774...` has six successful ordinary push workflows and one failure: Deploy GitHub Pages run `35363306307` failed in published desktop live acceptance. Generated desktop+narrow artifact proof and deployment passed; the retained desktop proof reached real guest/demo/reload/repository and workbench/provider-contract stages before the sign-in button remained disabled.

The retained report says `cloud_inference: NOT_RUN` and identifies the provider path as a test double. The trace supports a provider-frame bootstrap race: `Load Puter` was clickable while the new frame still said no SDK was loaded, while the later terminal state said the bridge was ready and sign-in remained disabled. This browser failure is separate from the research claims below and is not paid/live Puter semantic evidence.

## Earlier heterogeneous-DAG evidence — #202

#202 retains two different exact-head outcomes:

- an earlier heterogeneous DAG run: **FAIL**, with only 1/3 tasks integrated and no successful recovery of the dependent branch;
- a later bounded corrected run: **PASS**, using real local Ollama models across a three-task heterogeneous DAG with forced repair, 3/3 integrated, verification receipts present, and release export produced.

The later PASS does not erase the earlier FAIL and does not establish general DAG/recovery reliability, production readiness, or provider-independent model quality.

## M6 repair/self-host evidence

The historical M6 evidence set remains deliberately mixed:

- **#203** — first authoritative ImprovementSpec self-host trial: **FAIL**.
- **#204 / M6-SPEC-002** — **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt/release.
- **#215 / M6-SPEC-003** — **FAIL** after exercising prior-candidate repair context.
- **#217 / M6-SPEC-004** — **FAIL** after transport/source clarification.
- **#220 / M6-SPEC-006** — bounded **PASS** on corrected #218 runtime using Qwen2.5-Coder 7B. Attempts 1 and 2 were rejected by frozen checks; attempt 3 passed, independent Station review approved it, 1/1 integrated, a verification receipt was issued, and release export completed.

Interpretation: the repair loop has at least one retained positive trial after several negative trials. General repair reliability and autonomous self-maintenance remain **UNKNOWN / not established**.

## M6.2 first roadmap shipment — #231 and production #243

M6-ROADMAP-001B exercised the first M6.2 production contract against a detached clean copy of exact `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`.

Authoritative retained outcome:

- 1 implementation attempt;
- 3/3 immutable checks **PASS**;
- independent local review **APPROVED**;
- exact reviewed head integrated;
- Station verification receipt hash `880fbacee5fdfb13aded09e2297c14d7006f4da2c208ac292f8283a936199695`;
- release export succeeded;
- 2 model calls, 4,384 reported tokens, 435.182 seconds;
- generated `residual/improvement/__init__.py` SHA-256 `3981e064c31f85763e872c47129975a61cc8d6ab8e00f1851d216eeb269ba623`;
- generated `residual/improvement/spec.py` SHA-256 `0bdcb3b7f86aad5d684f7437df88f3342055bbc08a9df6b51cbe859656ca7616`;
- retained artifact ID `10546904820`, ZIP SHA-256 `908b3b748b7d4841bdf92330e2cee5708bc65547663788dd5d0de29a4477effc`.

Status of the bounded experiment: **PASS**.

Production PR **#243** remains open and unmerged on current `main@de7d9774...`. The original generated implementation from #231 was imported, but review found that a frozen dataclass could still expose a mutable nested `acceptance` graph. The current #243 head therefore includes maintainer hardening for deep immutability, detached serialization and stable canonical identity, plus independent production tests. **It no longer claims byte-for-byte identity with the generated source.**

Current #243 exact-head status:

- applicable technical workflows, including Pages: **PASS**;
- exact-head maintainer approval: **FAIL / awaiting matching attestation**;
- accepted production contract on main: **UNKNOWN / unaccepted**.

The #231 research PASS remains valid in its exact experiment scope; the hardened production candidate is a subsequent human-maintained derivative, not evidence that RESIDUAL autonomously generated the final current PR bytes.

## Evidence-sufficiency fork — #232 / M6-EPI-001

Both experiment arms integrated after one repair, so the bounded experiment execution was successful. The outputs also exposed requirements that a deterministic HypothesisVerifier must reject:

- the insufficient-evidence arm correctly emitted a MeasurementGap instead of inventing absent baseline/hypothesis/acceptance information, but left `preserve_invariants` empty;
- the sufficient-evidence arm grounded the measured 2.4 baseline, but used free-form acceptance prose and conflated a performance metric with a protected invariant.

Interpretation:

- evidence-sufficiency fork behavior in this experiment: **PASS in scope**;
- candidate conformance to the stricter intended verifier contract: **not established**;
- production MeasurementGap/Scientist/HypothesisVerifier stack: **UNKNOWN / not yet accepted**.

These findings are useful because they convert ambiguous model behavior into explicit deterministic rejection cases.

## Autonomous discovery — M6-SPEC-007 series

### #244 / M6-SPEC-007

Authoritative result: **provider timeout before discovery**.

The initial Qwen2.5-Coder 7B call timed out at roughly 300 seconds on a 15,566-byte request. No candidate proposal, checker result, review, receipt, or integration was produced.

Status: **FAIL in experiment-execution scope / discovery not reached**. The Scientist hypothesis remains **UNKNOWN** because no discovery proposal was produced.

### #246 / M6-SPEC-007B

The lean evidence snapshot reduced the first request from 15,566 to 12,927 bytes, but the provider again timed out at roughly 300 seconds before a proposal. No checker, review, receipt, or integration stage was reached.

Status: **FAIL in experiment-execution scope / discovery not reached**.

### #249 / M6-SPEC-007C

Authoritative run **`35354978034`** cleared the earlier provider-timeout barrier and exercised the discovery path with local Qwen2.5-Coder 7B. The frozen evidence snapshot remained bound to exact `main@60d0c5a8...` and no improvement question, target metric, intervention, or hypothesis was supplied.

Retained outcome:

- all five local model calls completed; there was no provider timeout;
- attempts 1–4 generated `ImprovementSpec`-shaped candidates, but each was malformed JSON because the `operator` member syntax was invalid, so both the JSON-validity check and external checker failed;
- attempts 3 and 4 repeated previously failed candidate patches and accepted #233 repeated-patch detection recorded those repeats;
- attempt 5 produced a truncated model output and no new candidate;
- the run escalated at the frozen five-pass `max_iteration` brake after 12,840 reported tokens and 752.384 seconds;
- final result: **0 integrated**, `proposal: null`, no approved review, no verification receipt, and no release files;
- retained artifact ID **`10551768764`**, ZIP SHA-256 **`50398a007fb67aee739d81b9b726ebf0d5caf0a45fac1599b74cc31ae40ff782`**.

Status: **FAIL in bounded autonomous-discovery qualification scope**. Discovery execution was reached, but no mechanically admissible, verifier-accepted proposal survived the frozen budget.

### #250 / M6-SPEC-007D — typed proposal

#250 changed the proposal interface so the Scientist returned typed structured output under a response schema; RESIDUAL performed canonical serialization and external mechanical admission afterward.

Authoritative run **`35363776938`** completed one local Qwen2.5-Coder 7B call. The model returned a syntactically valid typed `MeasurementGap`, but claimed `provider_timeout_rate` was missing. The exact frozen EvidenceSnapshot included `provider_timeout_rate` in its metric catalog and bound it to `0.2`.

Retained outcome:

- typed proposal generation: completed;
- mechanical admission: **FAIL** — `missing_metric is not actually missing`;
- semantic review: **not approved** because mechanical admission failed;
- admission receipt: **none**;
- artifact ID `10555509851`, ZIP SHA-256 `50a1999791069de03bb9e65db7e7537ff831c8a7a3f1218c6f2587376207cdf5`.

Status: **FAIL in bounded mechanical-admission/discovery scope**. This is useful evidence that typed output removed the malformed-JSON class but did not guarantee evidence-grounded semantics.

### #251 / M6-SPEC-007E — typed repair

#251 kept the same evidence and admission semantics while permitting at most three typed Scientist attempts. Later attempts received only the previous proposal and exact deterministic verifier finding.

All three model calls completed. All three returned the same proposal SHA, again labeling already-measured `provider_timeout_rate` as missing, even after the verifier explicitly reported that the metric was already measured at `0.2` and required an ImprovementSpec or a genuinely absent metric.

Retained outcome:

- attempts: 3;
- mechanically admitted proposals: 0;
- repeated identical rejected proposal: attempts 1–3;
- semantic review approval: none;
- admission receipt: none;
- artifact ID `10554449651`, ZIP SHA-256 `b705aabb937a361d13293d3d9d44c7c62258dd42bb9d809c54b0e1f0fb25554e`.

Status: **FAIL in bounded typed-repair scope**. The external verifier held its boundary; repair did not correct the evidence-grounding error within the frozen budget.

### #252 / M6-SPEC-007F — evidence-aware response schema

#252 moved mechanically known evidence constraints closer to the typed response schema while preserving the external deterministic admission boundary. The authoritative local-model run still proposed a MeasurementGap for already-measured `provider_timeout_rate`.

Retained outcome:

- mechanical admission: **FAIL** — proposed missing metric was already present;
- semantic review: **not approved**;
- admission receipt: **none**;
- artifact ID `10556410450`, ZIP SHA-256 `e963dfcb8dab977557788332385b934feb354a95cd0d199f867a97b055903ab6`.

Status: **FAIL in bounded evidence-aware typed-discovery scope**.

### #254 / M6-SPEC-007G — alternate Scientist model

#254 changed the Scientist/reviewer model from `qwen2.5-coder:7b` to general `qwen2.5:7b` while retaining the same frozen evidence and mechanical admission boundary.

The authoritative call completed and returned a typed MeasurementGap for `context_bytes_non_success_mean`; that metric was already in the snapshot at `31629.0`.

Retained outcome:

- mechanical admission: **FAIL** — proposed missing metric was already measured;
- semantic review: **not approved**;
- admission receipt: **none**;
- artifact ID `10555728738`, ZIP SHA-256 `03b96137d623b58c18aaa0e43711904a71a1a6c4ac0dbd29e7cae8329d7ec15e`.

Status: **FAIL in bounded general-model discovery scope**. This single model substitution does not establish that one model class is better or worse; it only shows the same evidence-grounding failure class persisted in that cell.

### Current discovery interpretation

The series now separates four failure layers that should not be collapsed:

1. **#244/#246 — execution:** provider timed out before proposal.
2. **#249 — representation/repair:** provider completed, but free-form outputs were malformed/repeated/truncated.
3. **#250/#252/#254 — evidence grounding:** typed outputs were syntactically valid but mechanically inadmissible because they described already-measured metrics as missing.
4. **#251 — repair under verifier feedback:** the model repeated the same invalid typed proposal despite exact deterministic feedback.

The deterministic checker is doing useful work: it prevents a plausible-sounding but evidence-contradicted MeasurementGap from becoming an accepted hypothesis merely because the output is well formed.

General autonomous improvement discovery remains **UNKNOWN / not established** until a retained run produces a defensible mechanically admissible and verifier-accepted proposal from evidence without a supplied hypothesis. The current negative cells do not prove that the broader Scientist direction is false.

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

These are governance defects until a current-base repair is accepted and the same relevant scenarios are requalified.

### Failure matrix — #212

#212 retained several distinct fail-closed/recovery paths. Of particular importance, its missing-usage case remains **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` abort. This corroborates the #207 ordering defect family.

## Central research hypothesis

RESIDUAL's central research direction is that system-level reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable model computation rather than assuming each model call is reliable.

Current evidence supports individual mechanisms and bounded interventions, but it does **not** yet establish the central hypothesis as a general live-model result. In particular, the repository does not yet have retained evidence for all of the following together:

1. a frozen confirmatory workload and protocol established before outcome access;
2. repeated live-model runs across relevant models/providers/tasks;
3. a preregistered comparison against suitable baselines;
4. reliable exact-revision evidence and negative controls;
5. autonomous discovery of an ImprovementSpec from evidence without a supplied hypothesis;
6. deterministic rejection of malformed and evidence-contradicted hypotheses;
7. repeated improvement validation showing a durable champion/challenger gain rather than a one-off success.

Until those conditions are met, broad recursive/self-improvement claims remain **UNKNOWN / not established**.

## Current M6.2 research priorities

1. Review/qualify #243 without treating the #231 research PASS as automatic production acceptance or claiming the hardened production candidate is still byte-identical to generated source.
2. Implement and qualify EvidenceSnapshot and MeasurementGap contracts.
3. Implement the Scientist as analysis-only, without Git/write/integration/promotion authority.
4. Implement deterministic HypothesisVerifier rejection cases identified by #232 and the evidence-grounding cases now retained by #250/#251/#252/#254.
5. Preserve typed structured output, but add deterministic constraints that distinguish a genuinely absent measurement from an already-measured metric and require an ImprovementSpec when the evidence is sufficient.
6. Ensure bounded repair can react to exact verifier findings rather than repeat an identical semantically rejected proposal indefinitely.
7. Build the experiment ledger and champion/challenger evaluator.
8. Repeat autonomous discovery trials with frozen evidence and external checking; one future success would still be bounded evidence.
9. Preserve earlier negative cells and independent #207/#212 authority-ordering defects.
10. Freeze the paper-facing R0–R5 confirmatory protocol before outcome collection.

## Non-claims

Nothing in #220, #231, #232, #244, #246, #249, #250, #251, #252, #254, or the open #243 work establishes universal model reliability, production readiness, autonomous merge authority, general recursive self-improvement, or successful paid/live provider execution.