# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`3cff6bcd52e352a6ba048c958949a7bbb2a039eb`**, produced by merged PR **#197** on top of #248.

#197 hardens the PR Agent as advisory review through `.github` workflow/configuration changes only. It does **not** change RESIDUAL runtime behavior, provider behavior, verifier authority, Factory/M4 implementation, evidence schemas, protected bytes, or acceptance authority.

Exact current main has **six successful ordinary push workflows** in their named scopes, but it does **not** have an authoritative production Pages qualification attempt. Issue **#267** records the trigger gap: the Pages workflow's push `paths:` filter allowed #197 to advance `main` without starting the required production Pages run. The newest retained production Pages acceptance therefore remains first attempt `35363306307` on parent `main@de7d9774...` and remains **FAIL**. That parent result cannot qualify `main@3cff6bcd...`; exact-current-main production Pages qualification is **UNKNOWN / BLOCKED by missing authoritative attempt**, not PASS. Open **#276** now carries the protected trigger repair at exact head `813b6123c69640cd2584f99ba7192d3c77f68345`. After retaining earlier failing heads, the current head's required technical qualification is **PASS**, including Deploy GitHub Pages run `35389534189`, Browser VM Demo CI, Controller/provider contracts, Command Station, Control Plane, Factory ownership, measured-evaluation binding, and clean install. The advisory PR Agent run is **CANCELLED** and is not treated as an acceptance PASS. Maintainer approval remains **FAIL / pending matching exact-head attestation**. #276 is unmerged, so the repair is not active on `main`; its PR-head Pages PASS is not production Pages acceptance.

PR **#260** remains the focused provider-bootstrap repair on exact current main. Its applicable technical exact-head workflows, including PR-head Pages, are **PASS**, but it is **HOLD / unaccepted**. Issue **#268** establishes a separate maintainer-approval event-wiring defect: a valid approval comment can pass an `issue_comment` run without publishing the required status on the exact PR head. Open **#275** now carries the reviewed exact-head status-publishing repair at current head `328c3b784b7561e5b39260058ab54c38bf64c66f`. The previous `87afd4d...` head remains historical after advisory review found malformed GitHub-response normalization that required another fix. On `328c3b7...`, measured-evaluation binding, Factory ownership, Control Plane, Controller/provider contracts, clean install, Command Station, and the advisory PR Agent are **PASS**; maintainer approval remains **FAIL / pending matching exact-head attestation**. Because #275 is unmerged, #268 remains unresolved on `main`. PR-head technical PASS is not a substitute for the protected exact-head maintainer status.

The M6.2 discovery evidence also advanced. **#257 / M6-SPEC-007J remains the first retained bounded autonomous-discovery PASS at formal admission**. #264 later showed that an integrity-valid receipt can still leave the scientific conclusion **UNKNOWN** when metric identity/semantics are not governed. Open **#270**, stacked on unapproved #266, now implements the proposed versioned/content-addressed Metric Registry and is technically green in its reported exact-head qualification scope; production acceptance remains **UNKNOWN / unaccepted**. **#274 / M6-SPEC-007S is a bounded PASS for registry/receipt semantic-binding controls.** Registry-aware discovery attempts #272, #273, and #277 retain apparatus/transcription FAILs; #277 positively demonstrates host-owned provenance binding while the overall experiment still FAILs at Planner transcription. #286 is pending with no authoritative result. General autonomous discovery and recursive self-improvement therefore remain **UNKNOWN / not established**, and **M6-008 remains BLOCKED** pending acceptance of the metric-semantics trust boundary and a valid registry-aware discovery result.

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

There is **no authoritative production Pages run for exact `main@3cff6bcd...`**. Issue **#267** identifies the cause: `.github/workflows/pages.yml` filters `push` by paths, and #197 changed paths outside that filter. Therefore current-main production qualification is **UNKNOWN / BLOCKED by missing required attempt**. Open **#276** now carries the protected trigger repair at exact head `813b6123c69640cd2584f99ba7192d3c77f68345`: production `push` is unfiltered on `main`, PR path filters remain a cost optimization, production attempts remain non-cancelling, and the generated/published proof contract is retained. Earlier activation heads `a134a7ce...` and `d5c647ff...` remain authoritative **FAIL** history for stale/comment-sensitive publication-contract tests and were not rerun away. On current head `813b612...`, the required technical workflows are **PASS**, including Deploy GitHub Pages run `35389534189`, Browser VM Demo CI, Controller/provider contracts, Command Station, Control Plane, Factory ownership, measured-evaluation binding, and clean install. The advisory PR Agent run is **CANCELLED**, not PASS; the protected maintainer-approval gate is **FAIL / pending matching exact-head attestation**. Because #276 remains unmerged, this is repair-branch evidence only. Current-main production Pages qualification remains **UNKNOWN / BLOCKED** until the repair is accepted and the resulting new `main` SHA receives its own authoritative production attempt.

Open **#260** applies the focused fail-closed provider-bootstrap guard to current main. On its exact head, Controller/provider contracts, Command Station checks, Control Plane, Factory ownership, measured-evaluation binding, clean install, Browser VM Demo CI, and Deploy GitHub Pages are **PASS**. However, issue **#268** records that the maintainer-approval `issue_comment` path does not reliably publish the protected status onto the exact PR head. Open **#275** now carries the reviewed status-publishing repair at exact head `328c3b784b7561e5b39260058ab54c38bf64c66f`. Its previous `87afd4d...` head is historical after advisory review found malformed GitHub-response normalization; current-head qualification restarted rather than reusing prior approval/evidence. On `328c3b7...`, measured-evaluation binding, Factory ownership, Control Plane, Controller/provider contracts, clean install, Command Station, and the advisory PR Agent are **PASS**; maintainer approval run `35389474375` remains **FAIL / pending a matching exact-head attestation**. The fix is unmerged, so #268 remains unresolved on `main` and #260 remains **HOLD / unaccepted**.

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

Applicable technical PR-head workflows are **PASS**. Accepted production behavior on main remains **UNKNOWN / unaccepted**. Maintainer-approval handling is additionally subject to the repository-level #268 exact-head status-wiring defect until that governance repair is accepted.

### #232 — evidence-sufficiency fork

M6-EPI-001 completed both research arms after one repair and exposed deterministic HypothesisVerifier rejection requirements, including protected-invariant completeness and structured acceptance semantics.

Experiment execution/evidence-sufficiency fork: **PASS in bounded research scope**. Production Scientist/HypothesisVerifier qualification: **UNKNOWN / not established**.

## Autonomous discovery — M6-SPEC-007 series

The retained sequence separates execution, representation, evidence-grounding, semantic-review, evidence-use, metric-identity, provenance, and Planner-transcription failures rather than flattening them into one claim.

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

### #264 / 007O — workflow PASS, research conclusion UNKNOWN

The split-role architecture separated evidence scouting, hypothesis formation, measurement planning, and host evidence resolution. The workflow completed: Evidence Scout selected five metrics; Hypothesis Scientist returned `insufficient_evidence`; Measurement Planner proposed a new baseline metric; the host classified it absent; branch-aware review approved it; and receipt `674513d7e3b82c747bdbea408094ad2c08342943bb05a544e29a6d07727a5359` was issued.

Post-hoc semantic audit found that the requested metric ID, `mean_wall_clock_s_basline`, is misspelled/undefined and may overlap the already-inspected `successful_mean_wall_clock_s=786.123333`. Because the EvidenceSnapshot carries IDs/values but no governed metric definitions, the reviewer's claim that the gap was genuinely absent and nonredundant cannot be established from retained evidence.

Retained artifact ID `10559527734`, ZIP SHA-256 `7a28d6367d91af99dca8ea1a66c0128b136665955a3d273d86a5afb988df895e`.

Status: **workflow PASS; research conclusion UNKNOWN pending metric-identity/semantic validation**. The receipt proves integrity/context of the recorded decision, not semantic correctness, and must not be used as authority to advance the recursive loop.

Issue **#265** requires a versioned discovery Metric Registry. Open spec PR **#266** defines typed `MetricDefinition` / `MetricDefinitionProposal` contracts, registry/evidence revision binding, canonical naming and duplicate gates, semantic-overlap review, and fail-closed `UNKNOWN` behavior. #266 is trust-infrastructure design only.

### #270 / Metric Registry implementation — technical PASS, unaccepted

Open **#270**, stacked on #266, implements immutable/content-addressed metric definitions and registry identity, duplicate/ambiguity handling, snapshot/unit validation, and binding helpers using existing StationReceipt v2 rather than changing the protected receipt schema. The owner-retained qualification report records the exact head green across the relevant Command Station Python 3.11/3.12/3.13 discovery, wheel build, Docker, browser UI, Control Plane, clean install, Factory ownership, controller/provider contracts, and measured-evaluation acceptance checks; downstream 007P also passed the 16 focused registry tests plus three preregistered controls.

Status: **PASS in bounded implementation/qualification scope on the open stacked PR; production acceptance UNKNOWN / unaccepted**. This does not register a metric, authorize promotion, or unblock M6-008 by itself.

### #272 / 007Q — apparatus FAIL before model execution

The registry-aware trial passed 16 focused registry tests but failed syntax compilation before model execution because the generated import edit contained literal escaped newline characters. No Scientist, Planner, reviewer, proposal, or admission event occurred.

Status: **FAIL in experiment-execution/apparatus scope; registry-aware discovery not exercised**.

### #273 / 007R — provenance-transcription FAIL

The corrected apparatus passed syntax, registry tests/preflight, Ollama setup, and Evidence Scout. The Scientist generated a grounded `insufficient_evidence` observation but copied the EvidenceSnapshot hash incorrectly. Deterministic verification rejected `evidence_snapshot_hash mismatch` before Planner/reviewer execution; no receipt was issued.

Retained artifact ID `10562515080`, ZIP SHA-256 `a0f86bb813f903696f95a1c1bb3aafa79c328d59f7d1874f798978659ff96e7e`.

Status: **FAIL in bounded provenance-transcription/mechanical-verification scope**.

### #274 / 007S — registry/receipt binding PASS

All seven preregistered binding controls passed after the 16 focused registry tests. Changing metric semantics under the same metric ID and revision label changed the registry content hash and admission/verifier bindings, invalidated the old receipt context, and registry-hash/unit tampering failed closed. StationReceipt v2 remained unchanged.

Retained artifact ID `10560939948`, ZIP SHA-256 `2a9a7e7a63c381e3b48577e2bfc393fc19c43be45a48f593f073e2e66f575ea1`.

Status: **PASS in bounded registry/receipt binding-control scope**. No metric registration, implementation acceptance, or promotion authority follows from this result.

### #277 / 007T — host provenance PASS; Planner transcription FAIL

The host-provenance intervention worked: immutable snapshot/registry/human-gate facts were removed from model-authored schemas and attached deterministically by the host. The Scientist's host-bound proposal then passed mechanical verification with exact identity, eliminating the #273 provenance-transcription failure class.

The Planner failed at a different transcription boundary by proposing already-registered `context_bytes_non_success_mean` while re-authoring an observation value belonging to `context_bytes_success_mean`. Deterministic verification stopped before registry assessment/review. No receipt was issued.

Retained artifact ID `10562057488`, ZIP SHA-256 `fa2b2329473e38bccc5d8b74ac44cd985857bc699367a34efbdfbeb348602ef6`.

Status: **host provenance mechanism PASS in bounded scope; overall experiment FAIL at Planner transcription**.

### #286 / 007U — pending

#286 further minimizes Planner authorship so verified Scientist context and immutable provenance are carried forward by the host. At this check there is no authoritative owner result comment; the only retained PR comment is an external Vercel rate-limit notification.

Status: **UNKNOWN / pending authoritative experiment result**. External preview-service rate limiting is not research evidence.

### Discovery interpretation

The correct current claim is:

- provider/discovery execution has been reached;
- typed output removed one representation failure class;
- deterministic present-vs-missing admission rejects false MeasurementGaps;
- semantic review can reject syntactically/mechanically plausible but scientifically weak proposals;
- **one bounded genuinely absent MeasurementGap was formally admitted in #257 / 007J — PASS in that exact scope**;
- #264 exposed that receipt integrity alone does not govern metric semantics;
- #270/#274 provide positive bounded evidence for content-addressed metric identity and receipt-context binding, but #270 is unaccepted and stacked on unapproved #266;
- #272 failed before model execution, #273 failed closed on model-copied provenance, and #277 showed host provenance fixes that class while still failing at Planner transcription;
- #286 remains UNKNOWN pending an authoritative result.

Therefore **general autonomous improvement discovery remains UNKNOWN / not established**, general recursive self-improvement remains **UNKNOWN / not established**, and **M6-008 remains BLOCKED pending acceptance of the Metric Registry trust boundary and a valid registry-aware discovery result**.

## Independent stress/governance defects

Draft #207 campaign B and #212 retain negative authority-ordering evidence, including budget/accounting and release-after-terminal-verifier-failure cases. Those defects remain **FAIL/open** until a current-base repair is accepted and the relevant scenarios are requalified.

Open draft **#288** is a current-main candidate repair for the pre-dispatch budget/accounting authority defect. It adds host-owned admission before runner/reviewer dispatch, conservative unknown-usage behavior, post-dispatch authority rechecks, and exact-head/spec-bound export gating, with five local negative regressions reported green on its head. It is **not accepted evidence on main**: exact-head CI/review remains the next gate, and it does not clear #207/#212 until the relevant scenarios are requalified after acceptance.

A later repair/self-host or discovery PASS does not clear an independent governance failure.

## Repository governance blockers

- **#267 / #276 — production Pages trigger:** current main has no authoritative production Pages attempt because path filtering skipped #197. Missing qualification remains **UNKNOWN / BLOCKED**, never PASS. The protected trigger repair is now on open #276 exact head `813b6123c69640cd2584f99ba7192d3c77f68345`. Earlier failing heads remain retained. On the current head, the required technical workflows are **PASS**, including PR-head Pages and Browser VM Demo CI; the advisory PR Agent run is **CANCELLED**, and maintainer approval remains **FAIL / pending matching exact-head attestation**. #276 is unmerged, so the trigger repair is not active on main and current-main production Pages remains UNKNOWN/BLOCKED.
- **#268 / #275 — maintainer approval status:** a valid approval comment does not reliably publish the required status on the exact PR head. The protected repair is now on open #275 exact head `328c3b784b7561e5b39260058ab54c38bf64c66f`; the earlier `87afd4d...` head is historical after an advisory malformed-response finding. Current-head technical qualification is **PASS** in the named scopes, but maintainer approval remains **FAIL / pending matching exact-head attestation**. #275 is unmerged and no branch-protection bypass is authorized.

These are governance/qualification defects, not evidence of Factory/M4, provider-model, or research-hypothesis failure.

## Current unresolved blockers

1. **Exact-current-main production Pages qualification** — issue #267: no authoritative Pages run exists for `main@3cff6bcd...`; status is **UNKNOWN / BLOCKED**. #276's current exact head `813b612...` now has required PR-head technical/Pages qualification **PASS**, but maintainer approval remains **FAIL / pending exact-head attestation** and the repair is unmerged/not active on main. Even after acceptance, the resulting merged SHA still requires its own first authoritative production Pages attempt.
2. **Exact-head maintainer approval publication** — issue #268: protected approval status wiring is defective on main. #275's current exact head `328c3b7...` has current-head technical qualification **PASS**, but maintainer approval remains **FAIL / pending exact-head attestation**; the PR is unmerged and no bypass is authorized.
3. **#260** — technically green provider-bootstrap candidate remains **HOLD / unaccepted** pending a valid governed exact-head maintainer status; if eventually accepted, its merged main SHA still requires its own first production Pages attempt.
4. **#243** — technically green production `ImprovementSpec` candidate remains unaccepted; current bytes include human hardening beyond #231-generated source, and acceptance remains subject to exact-head governance.
5. **Autonomous discovery** — #257 is a bounded formal-admission PASS; #274 is a bounded registry/receipt binding PASS; later registry-aware discovery cells still contain apparatus/transcription FAILs and #286 is UNKNOWN. General discovery/self-improvement remains UNKNOWN.
6. **Metric semantics / M6-008** — #265/#266 define the requirement and #270 is technically green but unaccepted; M6-008 remains BLOCKED pending accepted trust infrastructure plus a valid registry-aware discovery result.
7. **Accounting/release ordering** — #207/#212 negative evidence remains unresolved on main. Draft #288 is a repair candidate only; it has not cleared the retained failures.
8. **Paid/live provider success** — exact-current-main real-account candidate→verifier→receipt success remains UNKNOWN.
9. **Qualification breadth** — true blank-environment installation, recovery/host-loss, selected elapsed soak, every-host M4, and physical heavyweight-WebVM iPhone reliability remain unestablished.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities/revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, general autonomous recursive self-improvement, autonomous merge authority, or proof of the central live-model reliability hypothesis.