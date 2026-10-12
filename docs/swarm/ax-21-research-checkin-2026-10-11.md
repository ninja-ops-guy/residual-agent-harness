# AX-21 research maintenance delta — 2026-10-11

**Disposition:** limited new *release/reproduction and governance* evidence; **no new AX-21 behavioral/autonomy experiment**. This is an append-only review-only record, not a qualification verdict or release authorization. Do not transfer historical component PASS to a final composition.

## Inspection boundary

- Public repository `ninja-ops-guy/residual-agent-harness`, accepted `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
- Current draft [#534](https://github.com/ninja-ops-guy/residual-agent-harness/pull/534), exact HEAD `3107b975a6b47bce2a520a359937542c37d8ec2e`, master readiness row `V1-PP-BROWSER-FIREFOX-WEBVM`, owner comment dated October 11, and exact-head hosted workflow statuses/logs.
- New *unmerged branch*, **not a pull request**, `repair/v1-firefox-webvm-probe-20261011` at `6970eb33686093b81f5419a077830fe6c8f4d827`, one commit ahead/zero behind accepted main. Its changed-file patch was inspected.
- [#538](https://github.com/ninja-ops-guy/residual-agent-harness/pull/538) remains draft at `c4dac3f6f8aeb9a390d563592c3a14f590f6e637`; no additional submitted GitHub reviews were found. This pass did **not** execute a physical host, browser/WebVM guest, model provider, swarm seat, native hook, F6 test, P5 after-condition, or final RC.

## Observed release/reproduction delta — Firefox full-WebVM matrix

The selected D3 Desktop Firefox WebVM acceptance requirement remains **BLOCKED** because Station Firefox browser qualification is not the same evidence subject as a heavyweight Firefox *WebVM guest* run.

The October 11 tooling branch changes exactly three files: `demo/vm/browser_smoke.py` (12 changed lines), new `demo/vm/browser_smoke_cli.py` (24 added lines), and `tests/test_webvm_firefox_cli.py` (48 added lines). It moves CLI parsing to a shared function and exposes `chromium`, `firefox`, and `webkit`, while retaining the rest of the full-WebVM acceptance runner. The checked-in tests cover engine selection, default/mobile behavior, unsupported engine rejection, and required CLI arguments. The readiness ledger records **four author-local CLI tests PASS** and syntax compilation; those measurements are *reported local results*, not independently rerun here.

**Negative/NOTRUN retained:** no Firefox full-WebVM guest execution, no hosted exact-head CI on the tooling branch, no approved modified procedure, no review PR, and no selected-RC composition qualification. The ledger explicitly reports that publication of the focused proposal was blocked by an action safeguard. Do not reinterpret a CLI option or four parser tests as matrix completion or browser support proven on a real guest.

**Interpretation:** tooling reachability, acceptance-procedure approval, executed scenario coverage, and final composition qualification are separate evidence classes. This is incremental preparation toward a previously known requirement, **not a newly demonstrated Firefox result**.

## Observed governance/evaluator delta — #534

- `#534@3107b975...` has seven substantive exact-head hosted workflows marked PASS, including Qualification-v1, Command Station, controller/provider, clean-install, Factory ownership, Control Plane, and measured-evaluation binding. They qualify the *readiness document branch*, not a final RC.
- The maintainer gate failed at approximately **2026-10-11 14:40 UTC** with no exact-head human approval at its evaluation moment. The owner posted the exact-head comment `RESIDUAL-MAINTAINER-APPROVAL: 3107b975a6b47bce2a520a359937542c37d8ec2e` at **14:54:18 UTC**, **after** the failed check. This is an observed human intervention. No subsequent successful gate rerun was found in the inspected exact-head workflow listing. Thus comment-existence is observed, but refreshed *status PASS* is not claimed.
- The same head's advisory-review action failed with provider HTTP **401 `invalid_api_key`** despite the configured-secret presence check passing. No substantive advisory review was published. This is an evaluator/authentication-dependency failure, **not a code-defect result**; it repeats an existing failure class rather than establishing a new one.
- There is no submitted review for #538; its previous exact-head owner comment and hosted software/browser qualifications remain bounded to its current draft subject.

**Interpretation:** an attestation made after an evaluation must not be projected backward into that evaluation's retained result. A subsequently rerun gate, if required, is a distinct evidence event. An advisory reviewer failing provider authentication must not become a product PASS or FAIL.

## Frozen/pre-release AX-21 baseline and negative preservation

The original P5 before-condition remains approximately **11 cold agent queries plus human synthesis**, **15+ manual reports per session** reconciled externally, and the observed B0-6 local 7B path of approximately **16.4 seconds** (without verifier exception). These are historical controls, not newly measured values. R2's 215-test green continuity receipt remains `PASS_SANDBOX_BOOTSTRAP_ONLY`. Prior stale producer-artifact selection, provider-result ambiguity, verifier emission/finalization, historical debugger predecessor failures, source-to-wheel applicability, and physical native-proof gaps remain retained; no result here supersedes their negative evidence.

The owner comment, local tooling construction, safeguard-blocked proposal publication, and reviewer credential failure are human/evaluation interventions and cannot be omitted from a future autonomy-burden denominator. **No valid P5 after-condition, new fleet-status receipt, autonomous-runner proof, native MissionSync, physical F6, final-composition qualification, independent no-help multi-host reproduction, security certification, or v1 release authorization was found.**

## Research maintenance disposition

This cycle adds a **release-procedure coverage boundary** and an **approval/status chronology correction**, not a new falsified runtime hypothesis. Reuse existing evaluator failure-provenance, qualification-subject, and browser-matrix traceability candidates rather than manufacturing a novel RES-UP or ImprovementSpec ID from four CLI tests. A future qualifying experiment would require a reviewed/approved frozen Firefox procedure, actual Firefox full-WebVM guest evidence on exact selected bytes, retained negative controls, and independent review; all remain **NOTRUN** here.

**Paper-safe conclusion:** allowing an experimental condition in a tool is not equivalent to observing its execution, and human approval recorded after a failed check does not retroactively alter the check's outcome. The v1 release hold remains intact.
