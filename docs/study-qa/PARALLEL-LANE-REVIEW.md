# Parallel lane review — 2026-09-15

This packet has been reconciled locally onto `31cd2bf` (PR #77), which includes
M4 merge `de9c9fa` (PR #81). The branches have not yet been pushed by this lane.
No confirmatory measurements were collected. The historical findings below are
bound to their recorded commits and are not a fresh audit of merged main.

## Historical qualification findings (before PR #81 merged)

- PR #81 advanced from the supplied reference to `7ea194df0ecb76722610015491f4668b69619c05` (tree `a8062fa3198b7459fcdc7bd90505ea7b32808ef7`).
- All four associated workflows eventually reported success. However, OS evidence run [34914060945](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34914060945), job `104207711841`, ran 743 unittest cases with **21 namespace-dependent M4 tests skipped**. This is not containment qualification.
- CI checked synthetic merge `8bb7dda5ac35bc639bff63d92f81efd984428e6d`, tree `339aec6383b6b69c063f9c088c7557634592ecf9`, against base `800ea736308e3b0c091b81bf9cdb18c9786b9ac4`. The branch and tested merge have different tree identities.
- Retained GitHub artifact: `10375254068`, digest `sha256:98003c3672128431acb3c3e1205d345b77bd31d3749f363d02d4c16603b9467f`.
- Local namespace probe also returns `namespace_probe_failed`.
- Independent adversarial audit was stopped by an automated security restriction. It is incomplete; preliminary concerns are not confirmed findings.
- PR #80 was already merged before this session. M5 has no production M4 adapter or end-to-end receipt authenticity qualification.

## Original prepared changes (historical commit references)

| Lane | Local branch / commit | Evidence |
|---|---|---|
| Qualification CI | `codex/m4-qualification-gate` / `d53a478` | Requires actual namespace probe, zero skipped M4 pytest cases, head/merge matrix, main trigger; YAML and diff checks pass. Capability qualification remains blocked. Based on #81, not main. |
| Traceability and paper | `codex/traceability-docs` / `2f75be3` | PR77/74 reconciliation, M4 stays implemented_unverified, blank numerical results; 22 traceability tests and link checks pass. |
| Protocol | `codex/freeze-r0-r5-protocol` / `ce0fe8e` | Hash-bound preparation protocol and 16-task fixture workload; 8 offline tests pass. Not a completed confirmatory freeze. |
| Launcher | `codex/evaluation-launcher` / `86573fd` | 21 protocol/launcher tests pass; CLI smoke emitted 960 NOT_RUN entries, null results, and rejected live mode. |
| M5 repair | `audit/m5` / `fd6f56e` | Reject unsupported verdicts and duplicate verification IDs; late abort/deadline beats completion. 48 loop tests pass. |
| Onboarding | `codex/provider-review` / `f02cc56` | Credential file creation, bootstrap cleanup, redirect handling; 35 focused tests pass. |
| Inspector | `codex/inspector-review` / `d29bc31` | Authenticate executable before version probe; bounded sanitized probe; 16 focused tests pass. |
| Provider/Inspector integration | `codex/provider-inspector-combined` / `06ed7c3` | Both reconciled together; 47 focused tests pass. Real Docker/px0 smoke unqualified. |

Traceability, protocol, launcher and M5 changes are also combined locally in `codex/parallel-lane-review`: 57 pytest cases plus 8 subtests passed, and the 39-family status checker passed.

## Remaining experiment decisions

The immutable live model, operational R0–R5 interventions, executable task/independent-grader mapping, qualified adapter and settings, and merged-main M4 qualification remain missing. The protocol records blockers explicitly. Ten repetitions and schedule seeds are preparation choices, not claims of collected results. No confirmatory, degradation, heterogeneous-routing, or soak run was started.

## Publication and reconciliation

The earlier automatic approval review rejected publication for insufficient
authorization. The user has now explicitly instructed us to perform the work;
publication authorization is resolved. This lane has prepared
`codex/research-preparation-current` from `31cd2bf` for the publishing lane.

PR #77 already supplied the canonical traceability reconciliation, so its manifest,
checker and generated document are preserved. M4 remains
`implemented_unverified`; no fresh containment or merged-main qualification is
asserted by these fixture results. The unique paper/provenance additions, offline
protocol, fail-closed launcher and M5 controller fixes are retained. Live mode
remains disabled regardless of a self-declared readiness flag or local evidence
JSON.

## Current reconciliation validation

On the preparation branch based on `31cd2bf`, the combined protocol, launcher,
M5 runtime and traceability suite passed **57 tests and 8 subtests**.
`python scripts/status_check.py` passed for all 39 families, and
`git diff --check` passed. These are fixture/development checks; they establish
neither Linux containment qualification nor confirmatory experiment readiness.
