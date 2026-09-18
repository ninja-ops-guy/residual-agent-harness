# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`3cff6bcd52e352a6ba048c958949a7bbb2a039eb`**, produced by merged PR **#197** on top of #248.

#197 hardens the PR Agent as advisory review through `.github` workflow/configuration changes only. It does **not** change RESIDUAL runtime behavior, provider behavior, verifier authority, Factory/M4 implementation, evidence schemas, protected bytes, or acceptance authority.

Exact current main has **six successful ordinary push workflows** in their named scopes. The newest retained **production Pages acceptance** remains first attempt `35363306307` on parent `main@de7d9774...` and remains **FAIL**. Its generated desktop+narrow proof and deployment passed; published acceptance later timed out because provider sign-in stayed disabled in the guided-provider flow. The retained report records `cloud_inference: NOT_RUN` and a test-double provider path. The retained trace supports a repository/UI provider-bootstrap race, not a Puter outage, real-authentication failure, model-quality failure, or paid/live inference result.

PR **#253** is now **closed unmerged**. Open **#260** is its current-main replacement, rebuilt directly on exact `main@3cff6bcd...`. #260's exact head has the applicable technical workflows **PASS**, including Browser VM Demo CI and Deploy GitHub Pages. Its exact-head maintainer approval gate remains **FAIL / pending matching attestation**. PR-head Pages PASS is not production evidence; if #260 is accepted, the resulting merged SHA requires its own first published Pages acceptance attempt.

The M6.2 evidence also changed materially. **#257 / M6-SPEC-007J is the first retained bounded autonomous-discovery PASS at formal admission in this sequence**: a genuinely absent measurement was proposed, semantic review approved it, and an admission/verification receipt was issued. Follow-up cells #259/#262/#263 still **FAIL** because the Scientist repeatedly requests metrics that the host already exposes or resolves. Therefore one bounded admission path is established, while **general autonomous discovery and recursive self-improvement remain UNKNOWN / not established**.

## Accepted current-main sequence

Relevant accepted changes remain:

- **#200** — setup hardening. Accepted onboarding behavior; not blank-environment qualification.
- **#205** — session-scoped provider-channel recovery across Mission Control reload/remount. Accepted lifecycle behavior; not live-provider semantic proof.
- **#218** — bounded Station repair-context transport and shared five-attempt ceiling. Accepted behavior; no verifier/review/receipt/integration/promotion/Factory authority expansion.
- **#201** — guided frontend and inline Puter setup UX. Accepted frontend/provider-boundary behavior; not paid/live inference proof.
- **#233** — preserves actionable failure-tail context and detects repeated failed patches. Accepted repair-loop diagnostics; no authority expansion.
- **#248** — provider-load generation/lifecycle qualification on the credentialless embedded provider path. Accepted lifecycle/test behavior; no real-login or paid/live inference proof.
- **#197** — advisory PR-review workflow/configuration hardening. Accepted repository-governance tooling only; no runtime or trust-boundary behavior change.

## Production Pages / provider boundary

Retained production Pages run **`35363306307`** on `main@de7d9774...` remains authoritative for that exact merged SHA:

- generated desktop+narrow artifact proof: **PASS**;
- deployment: **PASS**;
- published desktop acceptance: **FAIL**;
- `cloud_inference`: **NOT_RUN**;
- real Puter authentication/inference in that run: **UNKNOWN / not exercised**.

The failure trace supports a deterministic repository/UI bootstrap race in which provider loading could be clicked before the intended bridge-backed handler was ready. It does not support a broader provider, authentication, model-quality, WebVM, Factory, or M4 failure claim.

Open **#260** applies the focused fail-closed bootstrap guard to current main. On its exact head, Controller/provider contracts, Command Station checks, Control Plane, Factory ownership, measured-evaluation binding, clean install, Browser VM Demo CI, and Deploy GitHub Pages are **PASS**. Maintainer approval remains **FAIL / pending matching attestation**. The prior #253 results are historical and are not reused for #260 qualification.

Historical real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary. Exact-current-main paid/live candidate→verifier→receipt success remains **UNKNOWN / not established**.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Accepted #185/#187 protected-byte and ownership-baseline changes retain their exact reviewed scope. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. Namespace/capability-unavailable execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

This documentation refresh does **not** modify Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, or acceptance authority.

## Retained M6 repair/self-host evidence

The earlier M6 evidence remains deliberately mixed:

- **#203** — first authoritative ImprovementSpec self-host trial: **FAIL**.
- **#204 / M6-SPEC-002** — **FAIL**.
- **#215 / M6-SPEC-003** — **FAIL**.
- **#217 / M6-SPEC-004** — **FAIL**.
- **#220 / M6-SPEC-006** — bounded **PASS** on the corrected #218 runtime: attempts 1–2 rejected, attempt 3 passed frozen checks, review approved, 1/1 integrated, verification receipt issued, release export completed.

The #220 PASS does not erase the negative cells or establish general autonomous self-maintenance.

## M6.2 roadmap progress

### #231 — first roadmap shipment research PASS

M6-ROADMAP-001B ran against a detached clean copy of exact `main@260b5f9...` and retained one implementation attempt, 3/3 immutable checks PASS, independent local review APPROVED, exact reviewed head integrated, verification receipt issued, and release export succeeded.

Status: **PASS in that bounded research experiment**. General self-shipping reliability remains **UNKNOWN**.

### #243 — production candidate remains unaccepted

Production PR **#243** remains open. Its source derives from #231, but independent review found mutable nested `acceptance` state and the current head adds maintainer deep-immutability hardening plus production tests. The current production candidate therefore does **not** claim byte-for-byte identity with the RESIDUAL-generated #231 source.

Applicable technical PR-head workflows are **PASS**. Exact-head maintainer approval remains **FAIL / pending matching attestation**. Accepted production behavior on main remains **UNKNOWN / unaccepted**.

### #232 — evidence-sufficiency fork

M6-EPI-001 completed both research arms after one repair and exposed deterministic HypothesisVerifier rejection requirements, including protected-invariant completeness and structured acceptance semantics.

Experiment execution/evidence-sufficiency fork: **PASS in bounded research scope**. Production Scientist/HypothesisVerifier qualification: **UNKNOWN / not established**.

## Autonomous discovery — M6-SPEC-007 series

The retained sequence now separates execution, representation, evidence-grounding, semantic-review, and evidence-use failures rather than flattening them into one claim.

### #244 / 007 and #246 / 007B

Both authoritative attempts timed out at the local provider before a discovery proposal was produced.

Status: **FAIL in experiment-execution scope / discovery not reached**. These are not evidence that the Scientist hypothesis itself failed.

### #249 / 007C

Provider execution completed, but malformed/repeated/truncated candidate output exhausted the five-pass brake with 0 integrated, no approved review, no receipt, and no release.

Status: **FAIL in bounded autonomous-discovery qualification scope**.

### #250 / 007D, #251 / 007E, #252 / 007F, #254 / 007G

Typed structured output removed the malformed-JSON class, but deterministic admission rejected MeasurementGap proposals that called already-measured metrics missing. #251 repeated the same rejected proposal under exact verifier feedback; #254 reproduced the evidence-grounding failure with general `qwen2.5:7b`.

Status: bounded **FAILs** in their declared admission/repair/model cells. No semantic approval or admission receipt was issued.

### #255 / 007H — semantic review FAIL

The run reached semantic review with a genuinely absent-metric-shaped MeasurementGap rather than failing syntax or present-vs-missing admission. Review rejected the proposal for causal overclaim, non-falsifiable acceptance, and preservation-criteria defects.

- model/provider execution: completed;
- semantic review: **FAIL**;
- admitted: false;
- admission receipt: none;
- retained artifact ID `10557259640`, ZIP SHA-256 `149c1f56e32d8f23df2f53b739bfafb4e4567138bf3e796c9831ffc2c9d9552f`.

Status: **FAIL in bounded semantic-review scope**.

### #256 / 007I — apparatus FAIL

The trial failed due to a stale task-ID apparatus defect before a valid authoritative proposal evaluation.

Status: **FAIL in experiment-execution/apparatus scope**. Do not treat this as evidence against the Scientist hypothesis.

### #257 / 007J — bounded formal-admission PASS

Authoritative run `35370173939` completed local `qwen2.5:7b` proposal/review successfully. The Scientist proposed a MeasurementGap for genuinely absent `context_bytes_non_success_max`; semantic review approved it and formal admission issued a verification/admission receipt.

Retained evidence:

- admitted: **true**;
- semantic review: **APPROVED**;
- receipt hash `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`;
- artifact ID `10558781593`;
- ZIP SHA-256 `ea74dce1d0706a880566e694d872c76e305b8d28da0eee4dd89801e1232ad26e`.

Status: **PASS in this bounded autonomous MeasurementGap formal-admission scope**.

This is important positive evidence, but it is not proof of general autonomous discovery, implementation success, champion/challenger improvement, recursive self-improvement, or autonomous merge authority.

### #258 / 007K — apparatus FAIL

The intended gap-closure trial failed pre-model because of a variable-name apparatus defect.

Status: **FAIL in experiment-execution/apparatus scope**; not a Scientist-hypothesis result.

### #259 / 007L — post-gap-closure evidence-use FAIL

The apparatus was corrected and preflight derived `context_bytes_non_success_max=32652`. The enriched snapshot included the admitted measurement, but the Scientist continued requesting metrics already present in the evidence.

Status: **FAIL in bounded post-gap-closure evidence-use scope**. No new admission receipt.

### #262 / 007M — EvidenceResolver FAIL at Scientist repair

The host EvidenceResolver correctly resolved requested present metrics, including `context_bytes_non_success_max=32652` and `context_bytes_non_success_mean=31629.0`. The Scientist nevertheless repeated an already-resolved request. Final evidence records `Scientist repeated already-resolved evidence request 'context_bytes_non_success_mean'`, `admitted=false`, review not approved, and no receipt.

Retained artifact ID `10557804447`, ZIP SHA-256 `04ee76fd12e10d0d637311137453f3c1fef128c83d6620b566eb844fbd511f5b`.

Status: **FAIL in bounded resolver-assisted discovery/repair scope**. The host resolver behavior is positive mechanism evidence; the Scientist proposal path still failed.

### #263 / 007N — active evidence-query FAIL

Authoritative run `35372809744` exercised active trusted-evidence selection. The host exposed selected metrics including `shipping_task_success_rate=0.6`, `provider_timeout_rate=0.2`, `mean_wall_clock_s=696.4382`, and `successful_mean_wall_clock_s=786.123333`. The Scientist then requested already-present `mean_runner_attempts=3.0`, requested already-present `mean_first_request_bytes=16414.0`, and finally repeated `mean_runner_attempts` after it had already been resolved.

Final retained evidence:

- local model calls completed; no provider error;
- host evidence resolution: exercised successfully in scope;
- mechanical error: `Scientist repeated already-resolved evidence request 'mean_runner_attempts'`;
- admitted: false;
- review: not approved (`no admissible proposal`);
- admission receipt: none;
- artifact ID `10558852392`;
- ZIP SHA-256 `db5eb7e5eba32147c55f7dd54e5dd32d41d14d381ce5140ef12a646eeabb548e`.

Status: **FAIL in bounded active-evidence-query discovery scope**.

### Discovery interpretation

The correct current claim is:

- provider/discovery execution has been reached;
- typed output removed one representation failure class;
- deterministic present-vs-missing admission rejects false MeasurementGaps;
- semantic review can reject syntactically/mechanically plausible but scientifically weak proposals;
- **one bounded genuinely absent MeasurementGap was formally admitted in #257 / 007J — PASS in that exact scope**;
- closing that gap and adding deterministic EvidenceResolver/active evidence selection did **not** make subsequent Scientist behavior reliable; #259/#262/#263 remain bounded FAILs.

Therefore **general autonomous improvement discovery remains UNKNOWN / not established**, and general recursive self-improvement remains **UNKNOWN / not established**.

## Independent stress/governance defects

Draft #207 campaign B and #212 retain negative authority-ordering evidence, including budget/accounting and release-after-terminal-verifier-failure cases. Those defects remain **FAIL/open** until a current-base repair is accepted and the relevant scenarios are requalified.

A later repair/self-host or discovery PASS does not clear an independent governance failure.

## Current unresolved blockers

1. **#260** — technically green on exact PR head, but maintainer approval remains pending; if merged, the resulting merged SHA still requires its own first production Pages acceptance.
2. **#243** — technically green production `ImprovementSpec` candidate remains unaccepted pending exact-head maintainer approval; current bytes include human hardening beyond #231-generated source.
3. **Autonomous discovery** — #257 is a bounded formal-admission PASS, but #259/#262/#263 retain follow-up FAILs; general discovery/self-improvement remains UNKNOWN.
4. **Accounting/release ordering** — #207/#212 negative evidence remains unresolved.
5. **Paid/live provider success** — exact-current-main real-account candidate→verifier→receipt success remains UNKNOWN.
6. **Qualification breadth** — true blank-environment installation, recovery/host-loss, selected elapsed soak, every-host M4, and physical heavyweight-WebVM iPhone reliability remain unestablished.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities/revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, general autonomous recursive self-improvement, autonomous merge authority, or proof of the central live-model reliability hypothesis.