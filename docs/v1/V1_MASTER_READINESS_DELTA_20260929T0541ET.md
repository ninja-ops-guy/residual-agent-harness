# V1 master readiness delta — 2026-09-29 05:41 ET

Review-only additive delta. This does not rewrite prior evidence, select an RC, authorize F6/canary/production, attest, approve, merge, tag, or release.

## Fresh source snapshot

- Accepted `main`: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
- Master PR #427 pre-write head: `130d4c5be82b6fd5a8872b03bfad815202c8f756`.
- PR-G26 source successor #447: `ad524c461aa60426695f226f541e172c557b8e98`, stacked on #443 `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`.
- Current-main integration branch `integrate/v1-pr-g26-main-8369`: `495b88e94bf9973aa2f3d7fffad92e6547e9be3f`, 2 commits ahead / 0 behind accepted main.
- No PR exists for the integration branch.

## PRE-CANARY — PR-G26 current-main integration

**Requirement / acceptance criterion:** provide a current-main-bound, reviewable repository implementation of the PR-G26 seal-manifest verifier and its complete retained regression set without changing frozen Seal v2 or claiming private direct-source verification.

**Classification:** observed missing integration evidence / repository implementation preparation.

**Source / exact evidence:** production audit #423 requires PR-G26 direct-source verification. #443 provides the handoff/cardinality base. #447 exact `ad524c461aa60426695f226f541e172c557b8e98` adds the strict JSON-boundary repair. Comparing accepted main directly to #447 yields six added repository files total; #447 itself changes two files relative to its #443 parent (`scripts/r4_seal_manifest.py` and `tests/test_seal_json_boundary_supplement.py`), while the handoff plus three inherited regression files originate from the #443 lineage.

**Dependencies:** accepted main remains `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`; private Seal v2 and authoritative `runtime-20260924T025450Z` remain untouched; PR-G26 private semantic/package-closure verification remains a separate human/operator gate.

**Owner:** release-convergence repository lane for current-main integration; independent reviewer and authorized private-source operator remain separate.

**Implementation branch:** `integrate/v1-pr-g26-main-8369`.

**Current integrated payload:**
- `docs/v1/V1_PR_G26_DIRECT_SOURCE_HANDOFF.md`
- `scripts/r4_seal_manifest.py`

**Still required before opening a review PR:**
- `tests/test_r4_seal_manifest.py`
- `tests/test_r4_seal_manifest_adversarial.py`
- `tests/test_r4_seal_manifest_schema.py`
- `tests/test_seal_json_boundary_supplement.py`

**Test command after payload completion:** `python -W error::ResourceWarning -m unittest -v tests.test_r4_seal_manifest tests.test_r4_seal_manifest_adversarial tests.test_r4_seal_manifest_schema tests.test_seal_json_boundary_supplement`.

**Verification status:** `IN_PROGRESS`. The branch is current-main-bound and cleanly isolated, but it is incomplete, has no PR, and has no fresh exact-head CI. Historical #447 PASS results do not transfer.

**Required human action:** none yet for the partial branch. After the complete six-file payload is published and fresh exact-head CI is green, request independent review. Separately, PR-G26 still requires authorized read-only direct-source verification against the private artifacts; repository tooling cannot satisfy that gate by itself.

## Readiness movement

No release-authority gate is cleared. This delta distinguishes the six-file current-main projection from #447's two-file PR-local diff and records the integration successor as incomplete rather than review-ready. Historical R4.1 READY_FOR_CANARY remains historical only. AUD-1/F6, receipt/recovery disposition, topology/trust-boundary/SLO/RPO/RTO authority, immutable RC composition, exact-RC qualification, operational/provider/recovery evidence, and final human release authorization remain open.
