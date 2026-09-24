# RESIDUAL v1 master readiness delta — 2026-09-24 12:38 UTC

This append-only delta updates the review-only v1 readiness ledger. It does not authorize a canary, merge, physical test, deployment, attestation, tag, release, paid-provider workload, elapsed soak, credential/topology mutation, or modification of frozen R4.1/Seal v2 evidence.

Observed accepted main remains `d796f36b75e730a0bab71bdba564206174393719`.

## PR-G27 — immutable GitHub Actions remediation is now in exact-head qualification

Draft successor PR #440 exact head `ecb598456637ea9b474c31f76c474dd7c071aa7c` is based on review-ready #437 head `46bdfd51c7ea1ff31ab7e3701b894b329010ff50`, so it carries the fail-closed immutable-ref audit forward and applies the proposed remediation.

The candidate pins the repository's existing major-version selections to immutable upstream commits across 29 active workflow files:

- `actions/checkout@v4` → `11d5960a326750d5838078e36cf38b85af677262`
- `actions/setup-python@v5` → `a26af69be951a213d495a4c3e4e4022e16d87065`
- `actions/upload-artifact@v4` → `ea165f8d65b6e75b540449e92b4886f43607fa02`
- `actions/download-artifact@v4` → `d3f86a106a0bac45b974a628896c90dbdf5c8093`
- `actions/setup-node@v4` → `49933ea5288caeca8642d1e84afbd3f7d6820020`
- `actions/configure-pages@v5` → `983d7736d9b0ae728b81ab479565c72886d7745b`
- `actions/upload-pages-artifact@v3` → `56afc609e74202658d3ffba0e8f6dda462b719fa`
- `actions/deploy-pages@v4` → `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e`

The existing immutable PR-Agent pin is retained. The proposed selection is recorded in `docs/v1/V1_GITHUB_ACTION_PIN_SET.json`. Checkout credential hardening remains enforced independent of floating-tag syntax, and the Pages structural gate now requires an immutable 40-hex deploy-pages ref.

A direct changed-workflow diff inspection found no newly added external `uses:` reference with a mutable ref. This is proposal-level evidence only; #437's repository audit and exact-head CI remain the acceptance authority.

At the latest read of exact head `ecb598...`, the maintainer-approval gate is red because no human attestation was provided; multiple technical workflows are queued/running and no exact-head technical failure has yet been accepted. Do not inherit #437's green checks onto #440.

**Ledger update:** PR-G27 remains `IN_PROGRESS`. #440 is the concrete remediation candidate. Promote only after exact-head technical CI, retained immutable-pin audit output on the final candidate tree, normal review, and later merged-main requalification.

## Environment triage — supporting classification remains bounded

Review-only PR #436 classified the retained 1121-test run's 129 non-passing outcomes as 38 environment-setup, 62 missing optional dependency, and 29 expected skips, with zero deterministic regressions at its tested stale SHA. That triage supports environment/capability diagnosis but does not clear current main, kernel-isolation capability, or production readiness.

## Unchanged release-authority blockers

1. `V1-PC-002..004`: explicit bounded-canary disposition remains required for reported #426 receipt-binding, recovery-digest, and concurrent-recovery findings.
2. `V1-CAN-001..003`: the canary remains unauthorized and unexecuted.
3. `V1-PP-001`: actual v1 topology/trust boundary plus SLO/RPO/RTO/backup/HA/soak policy remain owner/operations decisions; #432 is validation tooling, not approval.
4. AUD-1 remains owned by its separate closure lane; independent review, selected-target helper qualification, physical F6-A/F6-B, Mason/LEGION re-audit, owner attestation, integration and resulting-main proof remain outstanding.
5. `V1-REL-004..009`: exact RC selection/artifact, clean-environment recovery, real backup/rollback execution, elapsed soak, final human GO, deployment and closure remain future execution gates.

No exact readiness percentage is asserted. Unmerged green tooling and review candidates are not production acceptance.
