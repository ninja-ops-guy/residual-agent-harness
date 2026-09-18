# RESIDUAL current status

_Current-state check: 2026-09-18 UTC against `main@de7d9774cfd63c77ef5645ca43aa0be1a604887f`._

This document is a human-readable status summary. Exact code at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`de7d9774cfd63c77ef5645ca43aa0be1a604887f`**, produced by merged PR **#248**.

Relevant accepted changes in the current sequence are:

- **#200** — setup hardening. Accepted onboarding behavior; not blank-environment qualification.
- **#205** — session-scoped provider-channel recovery across Mission Control reload/remount. Accepted lifecycle behavior; not live-provider semantic proof.
- **#218** — bounded Station repair-context transport and a shared five-attempt ceiling. Accepted behavior; no verifier/review/receipt/integration/promotion/Factory authority expansion.
- **#201** — guided frontend and inline Puter setup UX. Accepted frontend/provider-boundary behavior; not paid/live inference proof.
- **#233** — preserves actionable failure-tail context for Station repair attempts and detects repeated failed patches. Accepted diagnostic/repair-loop behavior; no authority expansion.
- **#248** — provider-load lifecycle qualification repair. Accepted load-generation/lifecycle and negative-network-path behavior; no real-login or paid/live inference proof.

Exact merged `main@de7d9774...` has seven ordinary push workflows: **six success, one FAIL**. The failure is **Deploy GitHub Pages run `35363306307`**. The generated Pages artifact passed desktop+narrow browser proof, provider-session/publication contracts passed, and deployment itself succeeded. Published desktop acceptance then reached served-artifact identity, guest attachment/shell readiness, real demo verification, warm reload, repository audit, workbench artifact/revision verification, real-guest provider transport, CLI→UI projection, conversation reload, and guided-provider prompt preservation before timing out because the provider frame's `#signin` button remained disabled.

Retained `report.json` binds that failure to exact `de7d9774...` and records:

- `status: FAIL`;
- `cloud_inference: NOT_RUN`;
- provider evidence `REAL_GUEST_WITH_TEST_DOUBLE_SDK_NOT_PAID_INFERENCE`;
- authorization evidence `USER_GESTURE_AND_POPUP_CONTRACT_TEST_DOUBLE_NOT_REAL_PUTER_LOGIN`;
- failed request `https://js.puter.com/v2/` with the intentionally induced `net::ERR_INTERNET_DISCONNECTED` negative path;
- terminal failure: Playwright timed out waiting for disabled `#signin` to become clickable.

The retained Playwright trace narrows the new failure further. On the fresh provider iframe after the guided setup was opened, `#load` was visible and enabled while the frame still displayed `Not connected. No provider SDK has been loaded.`; the acceptance clicked it successfully. At the later terminal snapshot the frame displayed `Bridge ready. Load Puter when you are ready` and `#signin` was still disabled. That evidence supports the focused repository/UI bootstrap-race diagnosis in open **#253**. It is **not** evidence of a Puter outage, a real authentication failure, provider/model quality, or paid/live inference success/failure.

## Accepted #248 provider lifecycle behavior

#248 is accepted main behavior.

The accepted provider-load lifecycle tracks a monotonically increasing in-frame load generation and explicit `requested → loading → failed|loaded` states, keeps activation bound to the intended credentialless provider frame, and tests both generation advancement and terminal failure. Its negative path requires evidence that the provider SDK network request was attempted and intentionally aborted rather than allowing a no-op click to masquerade as a qualified failure.

Claim discipline:

- accepted #248 bytes on current main: **PASS**;
- exact merged-main non-Pages ordinary push workflows: **PASS/success** in their named scopes;
- exact merged-main Pages live acceptance: **FAIL** (`35363306307`);
- provider lifecycle behavior in the accepted tests: **PASS** in its declared scope;
- real Puter authentication on exact current main: **UNKNOWN / not established**;
- paid/live semantic inference on exact current main: **UNKNOWN / not run in the retained Pages failure**.

#248 does not modify protected Factory/M4 authority or turn provider/test-double proof into live-provider qualification.

## Current Pages repair — #253

PR **#253**, `fix(pages): fail closed before provider bridge bootstrap`, is a focused follow-up to the authoritative first merged-main failure above.

Its repair keeps `#load` disabled from the first byte of `provider.html` and allows only successful private MessagePort bridge initialization to enable provider loading. It adds a regression pinning that bootstrap contract. The current exact head `1fe2ff49a826c595024621f325ef284431ff7fca` has the applicable technical workflows **PASS**, including:

- Browser VM Demo CI: **PASS**;
- Deploy GitHub Pages: **PASS**;
- Controller/provider contracts: **PASS**;
- Command Station checks: **PASS**;
- Control Plane: **PASS**;
- Factory ownership gate: **PASS**;
- measured-evaluation acceptance binding: **PASS**;
- clean-install qualification: **PASS**.

The exact-head maintainer approval gate remains **FAIL / pending matching attestation**. Therefore #253 is **open/unaccepted**. If it merges, the first production Pages attempt on the resulting merged SHA must be treated as authoritative; the unchanged `de7d9774...` failure must not be rerun away.

## Exact-current-main qualification boundary

Required interpretation for `main@de7d9774...`:

- ordinary push gates: **six PASS/success, one FAIL — Pages live acceptance**;
- generated Pages desktop+narrow artifact proof: **PASS**;
- GitHub Pages deployment: **PASS**;
- published desktop acceptance: **FAIL** at the provider sign-in bootstrap sequence after the earlier retained stages passed;
- current Pages root-cause classification: **repository/UI bootstrap race supported by retained trace; repair open in #253**;
- real-account Puter sign-in/inference in this run: **NOT RUN / UNKNOWN**;
- historical exact-revision FAIL results: **retained evidence**;
- universal/capable-runner M4 qualification: **not established**;
- true blank-environment install: **not established**;
- production long-run reliability: **not established**;
- physical iPhone heavyweight-WebVM reliability: **not established**;
- live-provider candidate→verifier→receipt success: **not established**.

Do not flatten the Pages failure into a broader provider, model, WebVM, Factory or M4 claim.

## Retained M6 repair/self-host evidence

The M6 evidence set remains mixed.

- **#203** first authoritative ImprovementSpec self-host trial: **FAIL**.
- **#204** M6-SPEC-002: **FAIL**.
- **#215** M6-SPEC-003: **FAIL**.
- **#217** M6-SPEC-004: **FAIL**.
- **#220** M6-SPEC-006 on the corrected #218 runtime: bounded **PASS**. Attempts 1 and 2 were rejected; attempt 3 passed the frozen checks, Station review approved it, 1/1 integrated, a verification receipt was issued, and release export completed.

The #220 PASS does not erase the earlier negative cells or establish general autonomous self-maintenance.

## M6.2 roadmap progress

Roadmap issue **#222** remains open. The first M6.2 implementation deliverable has materially advanced, but acceptance boundaries remain explicit.

### #231 / M6-ROADMAP-001B — research PASS

Against a detached clean copy of exact `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`, the authoritative run retained:

- 1 implementation attempt;
- 3/3 immutable checks **PASS**;
- independent local review **APPROVED**;
- exact reviewed head integrated;
- verification receipt hash `880fbacee5fdfb13aded09e2297c14d7006f4da2c208ac292f8283a936199695`;
- release export succeeded;
- retained artifact ID `10546904820` with ZIP SHA-256 `908b3b748b7d4841bdf92330e2cee5708bc65547663788dd5d0de29a4477effc`.

Interpretation:

- exact #231 roadmap-shipment experiment: **PASS**;
- evidence that RESIDUAL can complete this bounded implementation contract under that exact setup: **PASS**;
- general self-shipping reliability: **UNKNOWN / not established**.

### #243 — production candidate, not accepted

PR **#243**, `feat(m6): ship ImprovementSpec contract generated by RESIDUAL`, remains open and unmerged. Its current exact head is **`6e65015f3a590fbe6885cae03825d0e4cc11ccf6`** on current `main@de7d9774...`.

The original implementation generated and qualified in #231 was imported into #243, but independent backlog review found that the frozen dataclass still exposed a mutable nested `acceptance` graph. #243 therefore now includes a deliberate maintainer hardening patch that recursively freezes that graph, prevents caller-owned structures from drifting canonical identity, keeps `to_dict()` detached/JSON-compatible, rejects unsupported non-JSON values, and adds independent production tests. **The current head no longer claims byte-for-byte identity with the generated source.**

Current exact-head workflows:

- applicable technical workflows, including Deploy GitHub Pages: **PASS**;
- exact-head maintainer approval gate: **FAIL / pending matching attestation**;
- merge state: **open/unmerged**.

Therefore:

- #231 source provenance/experiment evidence: **retained**;
- #243 current production candidate: **derived from #231 plus maintainer hardening**;
- technical PR-head CI: **PASS in named scopes**;
- maintainer gate: **FAIL/pending**;
- accepted main capability: **UNKNOWN / unaccepted**.

### #232 / M6-EPI-001 — successful experiment with verifier findings

Both experiment arms integrated after one repair. The insufficient-evidence arm correctly produced a MeasurementGap rather than inventing absent baseline/hypothesis/acceptance data, but left `preserve_invariants` empty. The sufficient-evidence arm grounded its measured 2.4 baseline but used free-form acceptance prose and conflated a performance metric with a protected invariant.

Interpretation:

- experiment execution and evidence-sufficiency fork: **PASS in this bounded research scope**;
- candidate outputs satisfying the intended stricter M6.2 verifier contract: **not established**;
- production deterministic HypothesisVerifier: **not established**.

These findings remain explicit rejection requirements for the planned HypothesisVerifier rather than evidence to broaden the Scientist claim.

## Autonomous discovery attempts

### #244 / M6-SPEC-007

The authoritative attempt failed before discovery: Qwen2.5-Coder 7B timed out at roughly 300 seconds on the initial request before producing a proposal. There was no candidate proposal, checker result, review, receipt, or integration.

Status: **FAIL in experiment-execution scope / discovery not reached**. This is not evidence against the Scientist hypothesis because the hypothesis was not exercised to a proposal.

### #246 / M6-SPEC-007B

The lean-snapshot retry reduced the initial request from 15,566 to 12,927 bytes but again timed out at roughly 300 seconds before a proposal. No checker/review/receipt stage was reached.

Status: **FAIL in experiment-execution scope / discovery not reached**.

### #249 / M6-SPEC-007C

Authoritative workflow run **`35354978034`** reached the local model and completed five model calls without the earlier provider timeout. Attempts 1–4 produced invalid JSON proposals, later attempts repeated prior failed patches, attempt 5 was truncated, and the run exhausted its five-pass brake with **0 integrated**, no approved review, no verification receipt, and no release.

Retained artifact ID **`10551768764`**, ZIP SHA-256 **`50398a007fb67aee739d81b9b726ebf0d5caf0a45fac1599b74cc31ae40ff782`**.

Status: **FAIL in bounded autonomous-discovery qualification scope**. The experiment reached discovery but did not produce a mechanically admissible, verifier-accepted proposal.

### #250 / M6-SPEC-007D — typed proposal, mechanical admission FAIL

Authoritative workflow run **`35363776938`** completed the local model call and returned typed structured output rather than free-form JSON. That eliminated the prior malformed-JSON failure class, but the candidate was a `MeasurementGap` claiming `provider_timeout_rate` was missing even though the frozen EvidenceSnapshot explicitly included `provider_timeout_rate: 0.2` in both its metric catalog and metrics.

Retained outcome:

- typed proposal serialization: **completed**;
- deterministic mechanical admission: **FAIL** — `missing_metric is not actually missing`;
- semantic review: **not approved because mechanical admission failed**;
- admission receipt: **none**;
- artifact ID `10555509851`, ZIP SHA-256 `50a1999791069de03bb9e65db7e7537ff831c8a7a3f1218c6f2587376207cdf5`.

Status: **FAIL in bounded mechanical-admission/discovery scope**. Typed output is useful narrowing, not autonomous discovery success.

### #251 / M6-SPEC-007E — bounded repair FAIL

This follow-up allowed up to three typed Scientist attempts and fed later attempts only the prior proposal plus exact deterministic verifier findings. All three attempts returned the same proposal SHA and again claimed already-measured `provider_timeout_rate` as a missing metric, despite the verifier explicitly reporting `provider_timeout_rate` was already measured at `0.2` and instructing the Scientist to choose an ImprovementSpec or a genuinely absent metric.

Retained outcome:

- three model calls completed;
- three mechanically rejected proposals;
- same rejected proposal repeated on attempts 1–3;
- semantic review: not reached/approved after mechanical admission failure;
- admission receipt: none;
- artifact ID `10554449651`, ZIP SHA-256 `b705aabb937a361d13293d3d9d44c7c62258dd42bb9d809c54b0e1f0fb25554e`.

Status: **FAIL in bounded typed-repair scope**. The deterministic verifier held its boundary; the model did not repair the evidence-grounding defect within the frozen attempt budget.

### #252 / M6-SPEC-007F — evidence-aware schema FAIL

The schema moved mechanically known evidence constraints closer to the typed response boundary. The authoritative run still produced a MeasurementGap for `provider_timeout_rate`, which remained an already-measured metric.

- deterministic mechanical admission: **FAIL**;
- review: **not approved**;
- receipt: **none**;
- artifact ID `10556410450`, ZIP SHA-256 `e963dfcb8dab977557788332385b934feb354a95cd0d199f867a97b055903ab6`.

Status: **FAIL in bounded evidence-aware typed-discovery scope**.

### #254 / M6-SPEC-007G — alternate model-role FAIL

The Scientist/reviewer model changed from `qwen2.5-coder:7b` to general `qwen2.5:7b` while retaining the same evidence and mechanical boundary. The authoritative run completed, but proposed a MeasurementGap for `context_bytes_non_success_mean`, which the frozen snapshot already contained at `31629.0`.

- deterministic mechanical admission: **FAIL** — missing metric was not missing;
- review: **not approved**;
- receipt: **none**;
- artifact ID `10555728738`, ZIP SHA-256 `03b96137d623b58c18aaa0e43711904a71a1a6c4ac0dbd29e7cae8329d7ec15e`.

Status: **FAIL in bounded general-model discovery scope**. One alternate-model trial does not establish a model-role ranking; it only shows the same evidence-grounding failure class persisted in that cell.

### Discovery interpretation

The M6-SPEC-007 series has narrowed the failure mode materially:

- #244/#246: provider execution failed before proposal;
- #249: provider completed, but free-form output was malformed/repeated/truncated;
- #250/#251/#252/#254: typed structured proposals eliminated malformed JSON, but deterministic evidence grounding correctly rejected MeasurementGap claims about already-measured metrics.

General autonomous improvement discovery remains **UNKNOWN / not established**. No retained run yet has a mechanically admissible, verifier-accepted autonomous proposal originating from the frozen evidence without a supplied hypothesis. The newest failures are evidence that syntax constraints alone are insufficient; they do not falsify the broader Scientist direction.

## Deterministic stress and governance defects

Draft #207 campaign B and #212 retain independent negative authority-ordering evidence, including budget/accounting and release-after-terminal-verifier-failure cases. Those defects remain **FAIL/open** until a current-base repair is accepted and requalified.

A later repair/self-host PASS does not clear an independent governance failure.

## Live-provider evidence

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Claim discipline remains:

- historical live-provider result: **FAIL/BLOCKED**;
- candidate correctness: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact cause of the historical invalid responses: **UNKNOWN**;
- exact-current-main retained Pages cloud inference: **NOT RUN**;
- current-main live-provider semantic success after #201/#205/#218/#233/#248: **UNKNOWN / not established**.

A fresh retained real-account mission on an exact deployed accepted revision is required before paid/live provider success can become PASS.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

Accepted #185/#187 protected-byte/ownership-baseline changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent and must not be treated as cleared by unrelated green CI.

This documentation branch changes no Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, verifier/evidence schemas, provider authorization, or acceptance authority.

## Current priority blockers

1. Preserve exact `main@de7d9774...` Pages run `35363306307` as the first authoritative merged-SHA **FAIL**. Complete review/attestation on #253; if it merges, require a fresh first production Pages attempt on the resulting merged SHA.
2. Review and attest #243 before calling `ImprovementSpec` accepted production behavior. Its current candidate is derived from #231 plus maintainer hardening, not byte-identical generated source.
3. Continue M6.2 EvidenceSnapshot, MeasurementGap, Scientist, deterministic HypothesisVerifier, experiment ledger, and champion/challenger work without broadening #231/#232 research claims.
4. Treat #249 and #250/#251/#252/#254 as retained bounded discovery **FAIL** evidence. Harden evidence-grounded proposal selection and repair while keeping deterministic external admission authoritative.
5. Repair/requalify the #207/#208/#212 accounting/release-ordering defect family.
6. Retain a fresh exact-deployed-revision real-account Puter candidate→verifier→receipt success, or keep live-provider success UNKNOWN.
7. Physically validate the accepted #186 fallback without broadening it into a heavyweight-WebVM reliability claim.
8. Complete true blank-environment installation, recovery/host-loss qualification, and selected elapsed soak.
9. Continue #120/#126 WebVM root-cause and long-run reliability work.
10. Keep #139→ownership-baseline→fresh-qualification→#134 independent.
11. Freeze the confirmatory R0–R5 protocol before paper-facing outcome collection.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research, and evaluation prose are descriptive. `START-HERE.md` remains valid operator guidance and is intentionally unchanged. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.