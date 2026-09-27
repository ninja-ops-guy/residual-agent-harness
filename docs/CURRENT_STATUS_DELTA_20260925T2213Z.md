# RESIDUAL current-status delta — 2026-09-25 22:13 UTC

This file is a documentation-only reconciliation. PASS, FAIL, UNKNOWN, and BLOCKED claims are revision-bound. No candidate inherits qualification, review, execution, canary, RC, soak, or release authority from another revision.

- Accepted `main` remains `d796f36b75e730a0bab71bdba564206174393719`; no pull request has merged since the preceding status snapshot.
- AUD-1 issue #353 remains **OPEN** with no milestone. No new #353 or #455 comment after 2026-09-25 21:14 UTC establishes physical F6 authority.
- Selected AUD-1 product candidate #448 remains `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`.
- F6 evidence-hardening successor #455 remains `a2567103c7e634310d696e421692fa1f86624e3b`.
  - Exact-head hosted technical qualification remains **PASS**: Qualification v1 `36145155644`, controller/provider `36145155698`, Command Station `36145155628`, clean install `36145155632`, Factory ownership `36145155563`, measured-evaluation binding `36145155541`, and Control Plane `36145156020`.
  - Exact-head maintainer approval remains **PASS** via issue-comment run `36189004164`.
  - PR-Agent `36145155585` remains **FAIL** and is not acceptance evidence.
  - Physical F6-A/F6-B remain **BLOCKED / NOT EXECUTED**. #455 still has no successor-bound physical F6 authorization and does not inherit #453 execution authority.
- Master-readiness PR #427 remains **OPEN / DRAFT / UNMERGED** at `72f668d1988a78709ecc5821a8bc3a0104ec043f`; no newer #427 head was observed.
- Documentation PR #454 remained **OPEN / DRAFT / UNMERGED** at pre-update head `7a7a0fc06e0d55bf06e0445bf9669a9e5650c3bc`. That exact head has now reached terminal CI:
  - Qualification v1 `36190771991`: **PASS**, including deterministic, M4, lifecycle, browser, adversarial, soak and aggregate jobs.
  - Retained final artifact `10888411064` (`qualification-v1-final-0f5aed8c1682af676cb327749836ab91e2e95338`) has digest `sha256:c3cd0147ba201b7067c06fdb9cf097d238977abbc4c4b9631ff0f5b57afd5708`.
  - Controller/provider `36190771945`, Command Station `36190771988`, clean install `36190771682`, Factory ownership `36190771675`, measured-evaluation binding `36190771938`, and Control Plane `36190771947`: **PASS**.
  - Maintainer approval `36190772012`: **FAIL**.
  - PR-Agent `36190771724`: **FAIL**.
  - Vercel: **PASS**. Snyk: **PASS**.
  These results qualify only exact documentation head `7a7a0fc0...`; they do not qualify #455, accepted `main`, or any release candidate by inheritance.
- R4-02 predecessor PR #457 remains **OPEN / DRAFT / UNMERGED** at `2b75b42cd8cf1a7f13eac64a77d86ddfb619d169` on non-main base `security/r4-02-base-r4-01`.
- New stacked successor PR #458, `security(r4-02): make TAR link confinement promotion-invariant`, is **OPEN / DRAFT / UNMERGED** at `e8894c443936710b86efc85e9cbcc29a5f70840e`, based on #457 exact head `2b75b42c...`.
  - Its only changed files are `residual/station/archive.py` and `tests/security/test_r4_02_archive_authority.py`; it targets the B1 promotion-invariant TAR link-confinement defect identified against #457.
  - Qualification v1 `36192236577`: **PASS**, including deterministic `108259822569`, M4 `108259822451`, and aggregate `108260552291`.
  - Retained final artifact `10889275126` (`qualification-v1-final-f34fbaf215bc319bf04802df5362773e7ae45efb`) has digest `sha256:ab0ed0303409ca5c0b8ec44f45d93cb85fd5a802955b6f411ae81e1dcf65dae8`.
  - Controller/provider `36192236653`, Command Station `36192236672`, clean install `36192236573`, Factory ownership `36192236592`, measured-evaluation binding `36192236658`, Control Plane `36192236599`, and Pages `36192236744`: **PASS**.
  - Maintainer-approval status: **FAIL**. PR-Agent `36192236667`: **FAIL**. Submitted GitHub reviews: zero. Vercel: **PASS**. Snyk: **PASS**.
  - Therefore #458 has exact-head automated qualification but no human/independent review or merge authority. R4-03 remains **BLOCKED**. Because #458 is stacked on an unmerged non-main security base, its accepted-main applicability and whether R4-02 is a v1 release prerequisite remain **UNKNOWN** until explicitly reconciled.
- New draft PR #459, `ops: add idempotent hardening and swarm recovery runners`, is **OPEN / DRAFT / UNMERGED** at `b2a11aa7739d047ea883f480f8fff80bc7e126e1` on accepted `main`.
  - Its seven changed files are confined to `scripts/automation/` and `tests/test_automation_scripts.py`.
  - Qualification v1 `36194415119`: **PASS**, including deterministic `108266869446`, M4 `108266869561`, and aggregate `108267757343`.
  - Retained final artifact `10890015867` (`qualification-v1-final-82224d2ba521bcb7d7b667fe2b59dc00407e4cbb`) has digest `sha256:0e90abd92cd9b79ec4fb2654561cd7d4188efbc45cc3cc2e7e9c6c7059e4a598`.
  - Controller/provider `36194415033`, Command Station `36194415078`, clean install `36194415095`, Factory ownership `36194415036`, measured-evaluation binding `36194415049`, and Control Plane `36194415053`: **PASS**.
  - Maintainer approval `36194415120`: **FAIL**. PR-Agent `36194415066`: **FAIL**. Submitted GitHub reviews: zero. Snyk: **PASS**. Vercel: **FAIL** from the deployment free-tier rate limit, not a product-qualification failure.
  - #459 is automation tooling only. Its own stated boundary does not authorize physical F6, merge #458, or widen SC-MESH claim/result authority. Its Shared Comms recovery runner therefore does not close the separate Shared Comms disposition gate by itself.
- Snyk PR #456 remains **OPEN / UNMERGED** and non-authoritative for accepted-main or the v1 support matrix.

`README.md`, `HARNESS.md`, `START-HERE.md`, and `implementation-status.yaml` remain materially accurate at this snapshot because accepted `main` did not move and those documents do not promote the new candidate branches into accepted state.

Release remains **BLOCKED** on successor-bound F6 authorization for #455, separately retained F6-A/F6-B evidence, post-F6 independent Mason/LEGION re-audit, Shared Comms disposition, PR-G26 direct-source verification, PR-G27 supply-chain closure, PR-G28 release-matrix/offline-reproducibility evidence, final claims/deployment-profile approval, accepted-main integration plus resulting-main qualification, exact-RC recovery/incident/provenance/elapsed-soak evidence, and explicit final release authorization. The R4-02/#458 security lane requires explicit disposition before it can be treated as either a v1 prerequisite or post-v1 work; that relationship remains **UNKNOWN**.

This delta modifies documentation only. It does not modify Factory/M4 implementation, ownership baselines, qualification anchors, protected implementation bytes, evidence schemas, candidate product bytes, or release authority.
