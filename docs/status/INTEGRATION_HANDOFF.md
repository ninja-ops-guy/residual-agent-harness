# Qualification convergence handoff

Current authorized triage and dispositions are recorded in
[PR_TRIAGE_2026-09-15.md](PR_TRIAGE_2026-09-15.md), based on main
`1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`. #106 has merged; #107 preserves
that exact binding workflow and retains its diagnostics/status contribution.
#109 has a published execution-prerequisite repair; #117 now gates its three
missing runtime/DSM guarantees in required CI. Both remain blocked on their
specific acceptance conditions. The older read-only snapshots below are
retained as history. The owner's subsequent triage/advancement instruction
authorizes these scoped coordinator actions, not a global unfreeze of other lanes.

Reviewed baseline: `a8082109e01aff9eda72030b837103c09d1393d3`, 2026-09-15.
This is a dated integration queue, not a live tracker or authorization to merge
other tracks. The owner's new implementation instruction authorizes this
non-demo PR; it does not lift issue #79's restrictions for all agents.

## One queue, distinct completion evidence

| Track | Current disposition / next action | Completion evidence |
| --- | --- | --- |
| Enforcement | Active main protection verified; independent approval and two additional required checks still needed | Complete required-check/review policy on `main`, including a rejected failing merge attempt in a safe test PR |
| Current-status integrity | This PR: repair the active summaries and add a narrow offline guard | Both status guards and their regressions pass on the proposed tree |
| Runtime reproducibility | #96 merged; retain ordinary-suite provenance; #97 remains its own regression track | Classified original SIGKILL evidence plus a reviewed fix and exact-tree requalification; no retry laundering |
| Measured binding | #103 and #106 merged; this PR preserves main's canonical workflow | Negative/contract tests plus separate real-boundary qualification and retained chain/reports |
| M4 qualification | #88 stays with its owner; needs a capable runner | Namespace isolation actually executed, no skip/UNKNOWN substituted for pass |
| Traceability | #94 stays with its owner; rebuild against current main | Reviewed family inventory and regenerated output; reconcile residual M3 note referring to issue #63 as open |
| Economics / observability | #93 stays with its owner | Rebased, non-conflicting tests and measured-vs-fixture claim boundaries |
| Experimental protocol / corpus | #90/#91 require owner disposition of overlapping draft scope | One frozen protocol, acquired/hashed corpus, selected evidence path, then retained R0–R5 runs |
| Demo / product | Owner handles demo; #104/#102 and product tracks untouched | Owner's submitted PRs and deployed-revision evidence |
| Release / soak | #100 tooling is merged; operational runs remain | Blank-VM RC and elapsed soak evidence at the chosen revision; tags alone do not qualify a release |

At this snapshot there were 28 open PRs. This is not a completion percentage:
closing a superseded PR is administrative convergence, not experimental evidence.
Do not merge, close, or supersede another track without an owner disposition.
Use Class A (independent/current), B (salvage/rebase/overlap decision), or C
(superseded with replacement rationale) at the reconvened review. This table
does not assign historical PRs to C merely because they are old.

## Historical facts and sources

- [Issue #63](https://github.com/ninja-ops-guy/residual-agent-harness/issues/63)
  is closed; [#81](https://github.com/ninja-ops-guy/residual-agent-harness/pull/81)
  landed the code-hardening closure. Live M4 qualification remains separate.
- [Issue #48](https://github.com/ninja-ops-guy/residual-agent-harness/issues/48)
  is closed. The manifest's M2/M3/M4/EVAL rows are implemented at this snapshot.
- [PR #71](https://github.com/ninja-ops-guy/residual-agent-harness/pull/71)
  is closed; [#103](https://github.com/ninja-ops-guy/residual-agent-harness/pull/103)
  rebuilt the measured binding against the current acceptance surface.
- [Command Station run 34927698993, job 104249155773](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34927698993/job/104249155773),
  attempt 1, Python 3.13: ptrace expected `-31`, observed `-9`, one failure
  among 895 tests and 21 skips. The old log does not establish the kill's cause.
- The initial branch API reported `protected=false` and no rulesets. A follow-up
  on 2026-09-15 reports `protected=true` and active ruleset `23436488`; see the
  policy snapshot below. Preserve the initial observation as history.

## Verified policy update — 2026-09-15

[Residual main protection](https://github.com/ninja-ops-guy/residual-agent-harness/rules/23436488)
targets `refs/heads/main`, is active, and was last updated at
`2026-09-15T06:48:20.024-04:00`. At read time main was
`eefee6ac005c93278f483e002e38a768920f0fae`.

Required checks: `tests (3.11)`, `tests (3.12)`, `tests (3.13)`,
`factory-ownership`, `qualify (3.11)`, `qualify (3.12)`, `qualify (3.13)`,
`python (3.11)`, `python (3.12)`, `python (3.13)`, `browser`, `docker`.
All are bound to integration id `15368`; strict up-to-date checks are enabled.
Deletion and non-fast-forward updates are restricted. Review threads must be
resolved; stale approvals are dismissed. No bypass actors are configured and
the connected user reports `current_user_can_bypass=never`.

Remaining settings: require at least one independent approving review
(currently **0**), and add `current-status` and `measured-eval-binding` to the
required checks. Copilot review-on-push/draft review is enabled; this is review
automation, not an independently enforced approval. Safe rejection testing of
the complete policy remains outstanding. This follow-up inspected settings;
it did not change them.

## Maintainer-only enforcement

The connected GitHub tool surface does not expose a branch-administration
write. A maintainer must finish the remaining settings without removing the
already-active protections:

1. Require PRs and at least one independent approving review; dismiss stale
   approvals after new commits and require resolved review conversations.
2. Require `factory-ownership`, `current-status`, `measured-eval-binding`,
   the clean-install matrix, and both ordinary Python matrices. Select the
   actual emitted check names from the latest PR (including Python versions)
   rather than guessing a workflow name. Preserve existing required checks.
3. Require up-to-date validation against the base, or use a properly configured
   merge queue. Review bypass permissions explicitly; do not leave the normal
   agent path able to bypass these requirements.
4. Keep the capable-runner M4 gate distinct from binding contract tests. Require
   it for any claim/release that depends on isolated verification only after
   the runner is configured; an unavailable lane remains blocked, not green.
5. Verify the policy on a safe test PR, and retain exact policy/check evidence.

These steps are a requested owner action, not a claim that settings were changed.
Workflow activation also requires workflow-write permission at push time.

## Ordinary-suite diagnostics

`scripts/qualification_test_runner.py` performs the same unittest discovery
once. The workflows retain the ordinary text log and incremental JSONL with:

- checked-out commit/tree, dirty-worktree flag, Python/platform and allowlisted
  CI run/attempt/job key, source-head and base SHAs (PR checkout may be a merge SHA);
- test start/stop, successes, failures, errors, skips, expected failures,
  unexpected successes, and subtest outcomes;
- returned `Fixture.run_source` runtime status, return code, process-reaping,
  resource usage and allowlisted termination fields before temporary cleanup.

No runtime source, candidate contents, contract body, environment dump or
credentials are added. Normal test tracebacks and skip reasons are retained as
in the existing test log; they are not a general-purpose secrets sanitizer.
The hook is instance-local, returns the original value and restores the original
method. Direct `runtime.run` calls are outside capture scope. Missing records,
aborted runners and skipped tests must remain visible evidence gaps. The
existing protected repetition matrix is unchanged and does not cover ptrace.

Writes are flushed after each event, and existing output paths are refused.
A complete run requires a `run-finish` event and the job exit status; a partial
file after a hard kill is not a pass. Diagnostic write/serialization failure,
test failure or zero discovered tests returns nonzero. No retries or relaxed
signals are introduced. Matrix fail-fast is disabled to preserve other Python
versions' results. Artifacts include run/attempt/version in their names.

Local example (choose a fresh output path each time):

```bash
python scripts/check_current_status.py
python scripts/qualification_test_runner.py --output runs/local-qualification/events.jsonl
```

This is unittest discovery, not full pytest coverage. The active binding
workflow explicitly runs its pytest-style tests; the final integration review
must also run the full pytest corpus. Fixture tests and signed artifacts alone
do not establish live reliability or economic results.
