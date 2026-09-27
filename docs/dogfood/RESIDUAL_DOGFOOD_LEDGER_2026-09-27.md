# RESIDUAL dogfooding ledger — 2026-09-27

This ledger is append-only dogfood evidence. A corrective PR is not closure; closure requires a post-fix reproduction.

| ID | Finding | State | Evidence / corrective action |
| --- | --- | --- | --- |
| DF-OC-001 | Required HOLD / human-gate state was misclassified as repair-required | CORRECTIVE_CHANGE / RETEST_PENDING | Phase-aware reviewer fix included in this PR; same GoalSpec must be rerun unchanged |
| DF-OC-002 | Gateway alias ambiguity was promoted directly to repair | CORRECTIVE_CHANGE / RETEST_PENDING | Reviewer now resolves aliases from current task/goal evidence before blocking |
| DF-UI-001 | Active Draft Spec job tray card could not be dismissed | CORRECTIVE_CHANGE / RETEST_PENDING | #480 merged into this PR's base; live UI retest still required |
| DF-SCMESH-001 | Relayed identity required explicit provenance and strict contradiction behavior | VALIDATED / RETAIN | RELAYED_FROM_RETAINED_RECEIPT; contradictory live evidence must fail closed |
| DF-SCMESH-002 | O1 live execution refused when required host realization could not initially be established | VALIDATED / FIRST_FAILURE_RETAINED | Preserve refusal and later append-only correction; never rewrite first failure |
| DF-SCMESH-003 | Fleet membership must be live, explicit, independently qualified, and removable | ACTIVE | Dynamic cohort / host-realization requirement |
| DF-SCMESH-004 | Onboard every currently active and eligible agent into Shared Comms | ACTIVE | Track onboarded / live-eligible / live-discovered |
| DF-SCMESH-005 | READY_FOR_OWNER_GATE terminology lacked explicit host-realization semantics | OPEN | Formalize readiness state machine and freshness rules |
| DF-SCMESH-006 | One absent/degraded independent seat must not invalidate unrelated members | OPEN | Add cohort-independence negative tests |
| DF-SCMESH-007 | Historical, relayed, derived, operator-asserted, and live evidence need machine-readable provenance | OPEN | Generalize provenance classes |
| DF-SCMESH-008 | Automatic cloud assessment may fail after deterministic work is preserved | OPEN / INVESTIGATE | Improve secondary failure diagnostics without changing mission truth |
| DF-CLI-001 | No first-class CLI self-update path | CORRECTIVE_CHANGE / RETEST_PENDING | Adds `residual update --check` and bounded `residual update` |
| DF-CLI-002 | No installation/runtime diagnostic command | CORRECTIVE_CHANGE / RETEST_PENDING | Adds read-only `residual doctor` |
| DF-CLI-003 | Runtime `__version__` drifted from package metadata | CORRECTIVE_CHANGE / RETEST_PENDING | Runtime version now derives from installed package metadata |

## Update safety contract

`residual update`:

- never resets, force-checks out, or stashes a source checkout;
- refuses a dirty source worktree;
- requires the source checkout to be on `main` for automatic latest updates;
- uses `fetch` + `merge --ff-only` for source updates;
- preserves the configured RESIDUAL state directory and does not modify mission/state data;
- reinstalls an editable checkout after the fast-forward so dependency/entry-point metadata stays current;
- uses the repository as the current development update channel;
- supports `--check` without modifying the checkout;
- supports a version target only for package installs until release-checkout semantics are separately qualified.

## Required retests after merge

1. `residual --version`
2. `residual doctor`
3. `residual update --check`
4. clean source checkout: `residual update`
5. dirty source checkout: update MUST refuse without modifying files
6. Draft Spec running card exposes and honors dismiss ×
7. rerun the unchanged OpenClaw onboarding GoalSpec and verify DF-OC-001/002 behavior
