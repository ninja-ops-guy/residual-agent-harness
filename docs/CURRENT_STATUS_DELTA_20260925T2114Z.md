# RESIDUAL current-status delta — 2026-09-25 21:14 UTC

This file is a documentation-only reconciliation. PASS, FAIL, UNKNOWN, and BLOCKED claims are revision-bound. No candidate inherits qualification, review, execution, canary, RC, soak, or release authority from another revision.

- Accepted `main` remains `d796f36b75e730a0bab71bdba564206174393719`; no pull request has merged since the preceding status snapshot.
- AUD-1 issue #353 remains **OPEN** with no milestone.
- Selected AUD-1 product candidate #448 remains `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`.
- F6 evidence-hardening successor #455 remains `a2567103c7e634310d696e421692fa1f86624e3b`.
  - Exact-head hosted technical qualification remains **PASS**: Qualification v1 `36145155644`, controller/provider `36145155698`, Command Station `36145155628`, clean install `36145155632`, Factory ownership `36145155563`, measured-evaluation binding `36145155541`, and Control Plane `36145156020`.
  - PR-Agent `36145155585` remains **FAIL** and is not acceptance evidence.
  - A corrected exact-head owner attestation, `RESIDUAL-MAINTAINER-APPROVAL: a2567103c7e634310d696e421692fa1f86624e3b`, was posted on #455 at 2026-09-25 20:59:30 UTC. Maintainer-approval issue-comment run `36189004164` completed **PASS**; its policy tests and exact-head approval publication step both passed. The immediately preceding malformed attestation with a trailing quote produced run `36188986193` **FAIL** and remains historical evidence.
  - Physical F6-A/F6-B remain **BLOCKED / NOT EXECUTED**. Exact-head maintainer approval is now present, but #455 explicitly does not inherit #453 physical-execution authority; a distinct successor-bound F6 authorization is still required before execution.
- Master-readiness PR #427 remains `72f668d1988a78709ecc5821a8bc3a0104ec043f`; no newer #427 head was observed in this check.
- Documentation PR #454 remained **OPEN / DRAFT / UNMERGED** at pre-update head `8fd29748664a4f433b14fecf915f83d0e0e6358d`. That head has now reached terminal CI:
  - Qualification v1 `36177742961`: **PASS**. Retained final artifact `10883426121` (`qualification-v1-final-389ba27370c3a167130dd7401acb883ed5d1d78c`) has digest `sha256:55248c9619c15b82991f8c30c3db26bcec103c8cd821aed471f5c6b93ef27f8c`.
  - Controller/provider `36177742937`: **PASS**.
  - Command Station `36177742907`: **PASS**.
  - Clean install `36177742968`: **PASS**.
  - Factory ownership `36177743080`: **PASS**.
  - Measured-evaluation binding `36177743016`: **PASS**.
  - Control Plane `36177743124`: **PASS**.
  - Maintainer approval status: **FAIL**.
  - PR-Agent `36177743005`: **FAIL**.
  - Vercel: **PASS**.
  - Snyk: **PASS**.
  These results qualify only exact documentation head `8fd29748...`; they do not qualify #455, accepted `main`, or any release candidate by inheritance.
- New draft security PR #457, `security(r4-02): confine runtime archive extraction authority`, is **OPEN / DRAFT / UNMERGED** at `2b75b42cd8cf1a7f13eac64a77d86ddfb619d169` on non-main base `security/r4-02-base-r4-01`.
  - Its exact-head Qualification v1 `36186684244`, Controller/provider `36186684303`, Command Station `36186684318`, clean install `36186684253`, Factory ownership `36186684295`, measured-evaluation binding `36186684290`, Control Plane `36186684396`, Browser VM Demo CI `36186684294`, Factory runtime evidence `36186684269`, Factory OS execution evidence `36186684560`, and Pages `36186684360` are **PASS**.
  - PR-Agent `36186684230` is **FAIL**. Submitted GitHub reviews are zero, and observed maintainer-approval issue-comment runs for #457 are **FAIL**; independent review and merge authority are therefore not established.
  - #457 changes security/runtime and evidence files, including `residual/station/archive.py`, but its own PR declares #448/#455 outside its change. Because it is stacked on a non-main security base and is unmerged, accepted-main applicability and whether it is a v1 release prerequisite remain **UNKNOWN** in this status record. Its green candidate CI does not qualify accepted `main`.
- Snyk PR #456 remains **OPEN / UNMERGED** at `77a556736aaa9ef0ba01fe3ee5b4f6194faa0e05` and remains non-authoritative for accepted-main or the v1 support matrix.

Release remains **BLOCKED** on successor-bound F6 authorization for #455, separately retained F6-A/F6-B evidence, post-F6 independent Mason/LEGION re-audit, Shared Comms disposition, PR-G26 direct-source verification, PR-G27 supply-chain closure, PR-G28 release-matrix/offline-reproducibility evidence, final claims/deployment-profile approval, accepted-main integration plus resulting-main qualification, exact-RC recovery/incident/provenance/elapsed-soak evidence, and explicit final release authorization. #457's relationship to the v1 release gate set is **UNKNOWN** until its stacked-base/security disposition is explicitly reconciled.

This delta modifies documentation only. It does not modify Factory/M4 implementation, ownership baselines, qualification anchors, protected implementation bytes, evidence schemas, candidate product bytes, or release authority.
