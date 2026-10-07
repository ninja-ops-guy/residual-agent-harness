# RESIDUAL Release Stabilization — 2026-09-17

## Baseline

Stabilization branch: `release/stabilization-2026-09-17`  
Frozen starting revision: `2e1341c99fd7b72452e3b8c5278b1f557871b783`

This branch is the integration and qualification lane for the next stable release candidate. `main` remains untouched until the exact stabilization head satisfies the exit criteria below.

## Operating rules

1. Retain first-failure evidence. Do not rerun a failed release/qualification attempt merely to obtain green.
2. Accept only release-critical changes: required-CI repairs, supported-demo behavior, install/onboarding/provider correctness, recovery, soak, release evidence and claim-discipline fixes.
3. Keep speculative feature work and inference-engineering expansion off this branch.
4. Preserve Factory/M4 ownership, verifier authority, evidence/result binding, UNKNOWN/BLOCKED semantics and provider authorization boundaries.
5. Every qualification claim must bind the exact stabilization commit, tree, artifact and environment.
6. Promotion to `main` happens only after one final exact-head qualification pass and maintainer attestation.

## Initial blocking evidence

### R1 — Python 3.11 runtime-journal/readiness contention

Current-main Command Station run `35219212073` failed only on Python 3.11. Python 3.12, Python 3.13, browser and Docker jobs passed.

Authoritative failure:

- test: `test_sandbox_timing_determinism.JournalContentionReadTests.test_readiness_polling_survives_concurrent_writer`
- expected status: `CANDIDATE`
- observed status: `AUDIT_FAILED`
- reason: `OperationalError`
- termination: `guard_contract_violation`, SIGKILL / return code `-9`

The failure must be root-caused and fixed or deterministically classified before release promotion. A later green rerun of unchanged code does not erase this evidence.

### R2 — iPhone/WebKit heavy WebVM boundary

Physical iPhone/Safari evidence shows that the heavyweight WebVM/CheerpX path can terminate while the desktop path succeeds. The lower-level WebKit/WebVM failure mechanism remains unproven. Release behavior must therefore be explicit: either qualify the physical iOS WebVM path or route iOS/iPadOS WebKit to the lightweight walkthrough before heavyweight guest boot.

### R3 — live Puter end-to-end acceptance

The release candidate still needs retained real-account evidence for the selected live-provider claim:

`provider dispatch -> valid worker envelope -> candidate -> verifier -> receipt/artifact`

If live-provider success is not part of the selected release claim, that exclusion must be explicit rather than inferred from test-double CI.

### R4 — release/recovery/soak evidence

The final RC still needs release evidence appropriate to the selected release tier. Procedure/simulation evidence must not be promoted into real environment or elapsed-time claims.

Required release-candidate evidence includes:

- clean/blank-environment installation of the exact promoted artifact;
- recovery/host-loss behavior for the selected deployment mode;
- an elapsed soak tier selected for the release candidate and bound to the exact RC;
- retained failure/recovery evidence rather than green-only summaries.

## Exit criteria

The stabilization branch is promotable only when all applicable items are satisfied on one final exact head:

- [ ] ordinary required CI green across supported Python/browser/container surfaces;
- [ ] capable-runner M4 qualification green with zero prohibited skips;
- [ ] Factory ownership and measured-evaluation binding green;
- [ ] generated desktop+narrow Pages/WebVM proof green;
- [ ] first production-style publication/acceptance attempt for the RC succeeds or is explicitly outside the release tier;
- [ ] supported-device behavior is explicit, including the iOS/WebKit fallback or qualified WebVM path;
- [ ] blank-environment install evidence retained for the exact artifact;
- [ ] recovery/host-loss evidence retained for the selected deployment mode;
- [ ] selected elapsed-soak tier completed and retained;
- [ ] live-provider acceptance retained, or the release claim explicitly excludes it;
- [ ] release notes/non-claims match the retained evidence;
- [ ] exact-head maintainer attestation recorded.

## Promotion rule

No release-hardening commit from this branch is merged to `main` piecemeal merely because an isolated test is green. The branch is the release candidate integration surface. Promotion occurs only after the final exact-head gate set is satisfied and the retained evidence package is reviewable as one RC.
