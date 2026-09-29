# V1 master readiness delta — PR #487 security-review convergence

Observation boundary refreshed: 2026-09-29 14:44 ET. Review-only; not release authority.

- accepted main: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`
- master predecessor: `20bc39a8b2469a966637f2b8136253a39f6769b3`
- #487 live head: `b0c04f546810ca8cf30a86538cec8b257a12b695`
- #487 source predecessor: `9a0c2e0fe91b1bc68d2cbf3c776484892e991523`
- invalid abandoned successor: `repair/security-review-followup-b0c04@66c8c392bf085feaba764eb9a6f1873f1a6ade2d` — INVALID / DO NOT USE
- clean replacement successor: `repair/security-secret-guard-b0c04` — exact-byte match to #487 head at refresh time; 0 ahead / 0 behind before attempted repair

## PRE-CANARY

### V1-PC-SEC-487-A — tracked-secret guard self-match
**Classification:** observed finding.  
**Requirement:** the tracked-secret guard must reject credential signatures without its own positive fixture making the tracked repository fail.  
**Source/evidence:** #487 exact `b0c04f5...`; workflow `36577020959` is terminal FAIL while Qualification-v1 `36577020925`, Command Station `36577020850`, Browser VM `36577020922`, controller/provider `36577020828`, clean install `36577020794`, Factory ownership `36577021043`, Control Plane `36577020819`, measured binding `36577021028`, Open Core Boundary `36577020985`, Pages and Vercel are green on the same head. The exact remaining scanner finding is the scanner's own positive test source.  
**Dependencies:** #487 security candidate.  
**Owner:** this release-preparation lane for repository-only successor; independent human reviewer for acceptance.  
**Implementation:** the earlier `66c8c392...` successor is invalid and must not be used. The clean successor `repair/security-secret-guard-b0c04` remains byte-identical to #487 because the bounded test-only write was blocked before repository mutation. Production scanner code is unchanged.  
**Status:** BLOCKED on repository write; not READY_FOR_REVIEW.  
**Acceptance:** one focused test-only successor must (1) construct its synthetic positive sentinel without leaving a scanner signature in tracked source, (2) prove the guard test source itself scans clean, (3) leave `scripts/check_tracked_secrets.py` unchanged, and (4) obtain fresh exact-head tracked-secret and surrounding technical CI PASS. Independent review remains required.  
**Test evidence:** disposable stdlib-only replay of the proposed five-test file against the current scanner passed 5/5 before repository write. This is preparation evidence only and does not transfer to a GitHub head.  
**Human action:** none until a valid successor commit/PR exists; do not review or merge the invalid `66c8c392...` branch.

### V1-PC-SEC-487-B — credential-destination policy consistency
**Classification:** observed scope/policy discrepancy.  
**Requirement:** credential-bearing custom qualification destinations must match the owner-approved trust boundary and the PR's stated acceptance contract; synthetic test transport must not silently weaken production policy.  
**Source/evidence:** #487 changed from strict HTTPS+allowlist at `9a0c2e0...` to allow same-host loopback HTTP at `b0c04f5...`, while the PR description still states explicit custom destinations require HTTPS and allowlisting. Qualification is green on the latter policy.  
**Dependencies:** explicit scope/threat-model disposition.  
**Owner:** owner/security review; this task must not invent the scope decision.  
**Implementation:** none accepted.  
**Status:** BLOCKED.  
**Acceptance:** owner-approved policy is explicit, code/tests and public claim text match it, synthetic mission fixtures are isolated from production credential policy where necessary, and fresh exact-head qualification passes.  
**Human action:** decide whether same-host loopback HTTP is an intended supported exception. Until then, do not treat #487's green qualification as proving the earlier HTTPS+allowlist claim.

## Existing gates unchanged

Historical R4.1 READY_FOR_CANARY remains historical only. #423/#426 findings, PR-G26 private direct-source verification, AUD-1/F6, topology/trust-boundary/SLO/RPO/RTO authority, immutable RC composition, exact-RC qualification, operational/provider/recovery evidence, and final human release authorization remain open.

No merge, approval, attestation, canary, physical test, private Seal execution, live credential/service change, deployment, tag, or release is authorized or performed by this delta.
