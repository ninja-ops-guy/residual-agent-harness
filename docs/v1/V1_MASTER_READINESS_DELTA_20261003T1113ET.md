# RESIDUAL v1 master readiness delta — 2026-10-03 11:13 ET

**Scope:** review-only update to PR #427. No release, canary, merge, approval, physical-test, provider, soak, deployment, or tag authority.

## New material finding

### V1-PP-BROWSER-FIREFOX-WEBVM — BLOCKED

| Field | Value |
|---|---|
| Phase | PRE-PRODUCTION |
| Requirement / acceptance criterion | The selected exact RC must satisfy the owner-approved D3 Desktop Firefox browser/WebVM qualification requirement, or an owner-approved matrix amendment must explicitly redefine that requirement before outcome access. |
| Source | #465 exact head `d9e16bf92ba59b3d778666e11b0a948303b9475e`; `docs/v1/V1_RELEASE_MATRIX.md` records Desktop Firefox as SUPPORTED with “browser/WebVM qualification on exact RC”. Accepted main remains `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`. |
| Classification | missing qualification evidence / missing qualification tooling |
| Current evidence | On accepted main, `demo/vm/browser_smoke.py` only accepts `chromium` or `webkit`. `.github/workflows/pages.yml` installs Chromium only and executes the heavyweight generated-artifact WebVM proof in desktop Chromium plus narrow Chromium. Qualification-v1 does exercise Chromium/Firefox/WebKit, but its Firefox lane is the Station browser journey, not the heavyweight WebVM guest proof required by D3 wording. |
| Dependencies | exact selected RC; reviewed qualification-procedure proposal; existing WebVM reliability gate `V1-PP-WEBVM-120-126` |
| Owner | release/qualification owner + owner scope authority |
| Implementation proposal | Branch `qualification/v1-firefox-webvm-matrix` was created directly from current main for a bounded procedure proposal, but remains byte-identical to main because the repository write safety guard rejected the attempted source/workflow/test mutation before any repository change. No PR exists and no test result is claimed. |
| Test / evidence required | A distinct reviewed qualification proposal must add Firefox to the heavyweight WebVM driver and exact-RC Pages/browser proof, with structural regression coverage and its own exact-head CI. First failures must be retained; no unchanged rerun is authorized merely to obtain green. |
| Verification status | **BLOCKED** |
| Required human action | Permit/review a distinct qualification-tooling successor when repository writes are available, or explicitly amend D3 before results are known. Do not silently treat the Station Firefox browser contract as satisfying the recorded Firefox WebVM requirement. |

## Relationship to existing WebVM blocker

`V1-PP-WEBVM-120-126` remains independently BLOCKED. The #516 Pages recurrence and the retained #120/#126 impossible-constructor failures concern guest-runtime reliability. This new Firefox item is a separate coverage/tooling gap: it does not establish Firefox failure and it does not attribute the Chromium runtime recurrence to Firefox.

## Readiness movement

No applicable v1 gate becomes MERGED_AND_REQUALIFIED in this delta. The master now distinguishes:
1. WebVM runtime reliability on the selected RC; and
2. missing exact-RC heavyweight Firefox WebVM qualification coverage required by the owner-approved D3 matrix.

The shortest safe path is to close both with reviewed, exact-head evidence rather than narrowing the support claim after observing results.
