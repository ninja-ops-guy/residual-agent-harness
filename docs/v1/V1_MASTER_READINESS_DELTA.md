# RESIDUAL v1 master readiness delta

This file is an append-only status delta for `docs/v1/V1_MASTER_READINESS.md` on the same review-only branch. It does not authorize a canary, merge, deployment, physical test, attestation, release, or production mutation. Before any eventual merge of the master ledger, these deltas should be folded into the canonical rows without deleting retained historical evidence.

Observed repository main remains `d796f36b75e730a0bab71bdba564206174393719`.

## 2026-09-24 update

### V1-PP-002 / V1-PP-003 — AUD-1 successor advanced

The dedicated AUD-1 owner has produced stacked draft PR #431, exact head `a9c00474606b2bd5733ae5eef00a52d59b0aa89b`, on #416 exact parent `d41a9428e8667963f85526f44a9616be19ca9d7f`.

New retained finding: `AUD1-C4`. On the #416 parent, an explicit `/api/worker/result` HTTP 403 entered the generic transport retry path because `urllib.error.HTTPError` subclasses `OSError`; this permitted a second denied result attempt and generic empty-proposal fallback rather than immediate surrender. #431 reports a retained test-only first failure at `a980274c6a3d5b3b479a18466a7877d1207476ab`, then repairs the current head so result HTTP 401/403 is classified as authority loss before the broader retry handler. Non-authority transport failures retain bounded retry semantics.

Live exact-head GitHub Actions observed for `a9c00474606b2bd5733ae5eef00a52d59b0aa89b`:

- Measured evaluation acceptance binding: PASS (`35964699533`)
- Factory ownership gate: PASS (`35964699447`)
- Control Plane: PASS (`35964699419`)
- Clean install qualification: PASS (`35964699409`)
- Command Station checks: PASS (`35964699446`)
- Controller and provider contracts: PASS (`35964699456`)
- RESIDUAL Qualification v1: PASS (`35964699540`)
- Deploy GitHub Pages: PASS (`35964699453`)
- PR Agent advisory review: PASS (`35964699515`), advisory only

A separate Vercel preview later reported the account-level free deployment quota limit. That external preview quota event is not substituted for repository qualification and is not treated here as a product regression.

**Ledger update:**

- `V1-PP-002`: candidate implementation advances from #416/C1-C3 to stacked #431/C1-C4; status remains `READY_FOR_REVIEW`, not selected/accepted/merged.
- `V1-PP-003`: independent human review must now cover C1/C2/C3/C4 plus the admitted-operation drain/completion-barrier tradeoff. PR Agent does not satisfy this; status remains `BLOCKED`.
- `V1-PP-004` through `V1-PP-008`: unchanged and still blocked on deliberate successor selection, helper reconciliation, distinct real-host F6-A/F6-B evidence, Mason/LEGION re-audit, fresh exact-head qualification as required, and genuine owner attestation.

Issue #353 remains the governing release gate and still requires the ten adversarial regressions, physical inside/outside-window evidence, independent re-audit, exact-head qualification, owner attestation, merge, and authoritative new-main qualification.

### V1-REL-003 — corrected release receipt binding is review-ready

Draft stacked PR #428 is now at exact head `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43` and separates immutable R4.1 `canary_provenance` from the later selected post-convergence release candidate. It validates that RC/final tags point to the selected release commit instead of permanently binding `v1.0.0` to frozen R4.1.

Observed exact-head technical workflows for `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43` all completed successfully: Control Plane, Factory ownership, Measured evaluation binding, Clean install, Qualification-v1, Controller/provider contracts, Command Station, and PR Agent advisory.

**Ledger update:** `V1-REL-003` advances from `BLOCKED` to `READY_FOR_REVIEW`. This is unmerged review evidence only; it does not select an RC or create a tag.

### V1 release metadata — review-ready correction

Draft PR #429 exact head `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7` aligns `residual.__version__` with project metadata `0.5.0` and adds a regression preventing future declaration drift. Qualification-v1, Command Station, controller/provider, Pages, Factory ownership, measured binding, clean install and Control Plane are PASS on the exact head. The maintainer approval gate is expectedly red because no attestation was supplied.

This correction is `READY_FOR_REVIEW`; final `1.0.0` normalization remains an RC-creation action after release-critical convergence.

### PR-G29 / V1-RES-004 — ENV-G01 implementation is review-ready

Draft PR #430 exact head `756e540ca64fa953ca389e2d3441f9229d7969de` implements the machine-readable fail-closed environment capability preflight proposed by #425. Exact-head technical workflows are PASS: Control Plane, clean install, measured binding, Factory ownership, Command Station, controller/provider contracts and Qualification-v1. Maintainer approval is intentionally absent.

**Ledger update:** PR-G29 remains `READY_FOR_REVIEW`, now with implementation PR #430 and exact-head CI evidence. Do not wire ENV-G01 into active qualification until its contract is independently reviewed; no existing first failure is reclassified by this implementation alone.

### V1-PP-002 / V1-PP-003 — AUD-1 successor now includes C5

The dedicated AUD-1 lane advanced again to stacked draft PR #433, exact head `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`. It retains a first hosted failure on test-only head `9caaebe06214a7f8c280732eddbfdd18aeecd42c` for `AUD1-C5`: an authoritative HTTP 400 `Stale task lease` could enter generic result retry/fallback rather than surrender. The repair recognizes only that exact bounded Station denial as authority loss; other HTTP 400 contract/proposal errors retain their previous behavior.

Live exact-head repository workflows for `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60` are all PASS: Measured evaluation `35979730148`, Factory ownership `35979730169`, Control Plane `35979730332`, clean install `35979730288`, PR Agent advisory `35979730323`, Command Station `35979730360`, Qualification-v1 `35979730294`, controller/provider `35979730308`, and Pages `35979730212`.

**Ledger update:** `V1-PP-002` remains `READY_FOR_REVIEW` as an unmerged successor chain now covering C1-C5. `V1-PP-003` remains `BLOCKED`: genuine independent human review must cover C1-C5 plus the admitted-operation drain/completion-barrier tradeoff. Candidate selection, helper reconciliation, physical F6-A/F6-B, Mason/LEGION re-audit, owner attestation, merge and authoritative resulting-main qualification remain separate gates.

### V1-PP-001 — deployment profile validator is review-ready; policy remains blocked

Draft PR #432 exact head `f6487c8430f03e930c3ae22c99f41117d310372e` provides the fail-closed machine-readable v1 deployment profile contract. Exact-head technical workflows are PASS: measured evaluation `35969379173`, Control Plane `35969379119`, clean install `35969379212`, PR Agent advisory `35969379174`, Factory ownership `35969379208`, Command Station `35969379284`, controller/provider `35969379110`, and Qualification-v1 `35969379161`. The maintainer approval gate is red because no human attestation was supplied.

**Ledger update:** the repository-side tooling for `V1-PP-001` is `READY_FOR_REVIEW`, but `V1-PP-001` itself remains `BLOCKED` until owner/operations explicitly approve the actual topology, trust boundary, supported platform/storage, SLO, RPO/RTO, backup/retention, HA claim and soak requirements. Existing enterprise documents are not silently promoted into the v1 product decision.

### PR-G30 — incident-response qualification contract is review-ready; drills remain unexecuted

Draft PR #434 exact head `76a2a69fa6c7c2959108de2369796a755d59ea84` adds a machine-readable five-scenario incident-response qualification plan, fail-closed validator, and focused tests. Exact-head repository workflows are PASS: Clean install `35980252600`, PR Agent advisory `35980252492`, measured evaluation `35980252529`, Control Plane `35980252603`, Factory ownership `35980252494`, controller/provider `35980252597`, Command Station `35980252544`, and Qualification-v1 `35980252543`. Maintainer approval remains absent. The Vercel preview failure is the account-level free deployment quota and is not reclassified as a product failure.

PR Agent's missing/unreadable-plan concern was independently dispositioned as a false positive because `read_text()` executes inside a `try` whose `except (OSError, json.JSONDecodeError, PlanError)` already returns fail-closed `BLOCKED` with `execution_claim: NONE`.

**Ledger update:** PR-G30 repository-side plan/tooling advances to `READY_FOR_REVIEW`; PR-G30 itself remains `IN_PROGRESS` until the credential-leak, database-corruption, runaway-work/resource-exhaustion, host-compromise, and evidence-breach drills are separately authorized and executed against the approved v1 profile and exact RC with retained evidence.

### PR-G07 / PR-G21 — recovery evidence validator opened

Draft PR #435 exact head `378207e511550532dbba60e8d4ae489666aa6c09` adds a fail-closed machine-verifiable evidence contract for v1 backup/restore and rollback qualification. A disposable stdlib-only reconstruction ran 10 focused unit tests PASS before push. Initial repository CI has Control Plane and Factory ownership PASS while clean install, controller/provider, Command Station, Qualification-v1 and PR Agent were still in progress at the last read; no current-head success is inferred before those runs complete.

The contract explicitly prevents existing HADR simulation/unit tests from being mistaken for v1 production recovery proof: main's `residual/hadr/backup.py` describes its stdlib encryption as an offline-simulation construction and keeps `BackupManager.backups` in process memory. #435 instead requires future observed evidence bound to the approved deployment profile and exact RC, including encrypted/readable backup metadata, durable component coverage, exact restore binding, receipt-chain/startup/critical-read verification, measured RPO/RTO, rollback data/authority/in-flight-work verification, immutable evidence retention, and human Qualification Lead approval.

**Ledger update:** repository-side PR-G07/PR-G21 tooling is `IN_PROGRESS` pending exact-head CI. The actual PR-G07 and PR-G21 gates remain `IN_PROGRESS` and cannot become `VERIFIED` until separately authorized production-shaped backup/restore and rollback exercises are executed and independently reviewed.

### Unchanged hard blockers

1. `V1-PC-002..004`: #426 receipt-binding, recovery-digest, and concurrent-recovery findings still require explicit bounded-canary threat/topology disposition. No live reproduction is claimed by this ledger.
2. `V1-CAN-001..003`: canary remains unauthorized and unexecuted.
3. `V1-PP-001`: supported deployment topology/trust boundary plus SLO/RPO/RTO remain owner/operations decisions; applicability of many #423 gates is still blocked on that scope.
4. `V1-PP-003..008`: independent AUD-1 review, selected-target helper qualification, physical F6-A/F6-B, Mason/LEGION re-audit, owner attestation and later authoritative main qualification remain outstanding.
5. `V1-REL-004..009`: exact RC artifact, clean-environment recovery, backup/rollback evidence, real elapsed soak, human GO, deployment and closure receipt/tag/archive remain unexecuted future gates.

No exact readiness percentage is asserted. These updates reduce repository-side preparation gaps but do not convert review-ready PRs into production acceptance.
