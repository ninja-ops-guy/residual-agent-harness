# Combined qualification execution plan

Owner: integration coordinator. Preparation only; no qualification or merge approval is implied.

The governing completion target and reviewed 17-step status are recorded in
[COMPLETION_TRACKER.md](COMPLETION_TRACKER.md): Residual 1.0 plus Experimental Release 1.

## Reviewed snapshot — 2026-09-15

- Current main: eefee6ac005c93278f483e002e38a768920f0fae, including #104.
- #107 source head: ee48ccf29eb069b141aeeb23515c7b1580ad4141.
- Read-only Git merge-tree check of those revisions: no conflicts;
  prospective tree 36c4a76f5e8f774c5b0a33e81bb13e4c08aa7d46.
  This is structural compatibility evidence, not combined-suite qualification.
- #108 last observed head: b3b2a5a18ce28bd1249725c7529228acca7d498e.
  Factory runtime evidence run 34940491451 failed while the lease-revocation
  test read observations: SQLite database locked at PRAGMA synchronous=FULL.
  Its repair and independent review remain separate lane responsibilities.
- Initial protection was absent. A subsequent 2026-09-15 check confirms main
  is protected by active ruleset 23436488 with 12 required checks, strict
  up-to-date validation and no bypass actors. Approving-review count is still
  0; current-status and measured-eval-binding remain optional. Complete those
  maintainer settings independently of runtime repair; see INTEGRATION_HANDOFF.md.
- Thirty open PRs were observed. Their count is not a completion metric.
  Refresh branch heads, review comments and check runs before any decision.

## Coordination boundaries and overlaps

The coordinator owns this plan and #107's status/diagnostic changes.
Runtime repair, independent adversarial review, backlog audit, runner preparation,
protocol/corpus preparation, release preparation and demo development retain their
assigned owners. Do not duplicate those implementations.

| Intersection | Integration decision required |
| --- | --- |
| #106 and #107 | Both activate measured-binding CI. Compare their final contents and preserve one canonical workflow; the backlog lane proposes disposition. |
| #94 and #107 | Preserve broader family coverage and the supplemental active-summary guard. Resolve shared status prose once; retain ownership restrictions on the pinned checker. |
| #108 and #107 | Confirm the diagnostic hook still observes the final runtime fixture API; verify emitted termination fields retain their intended meaning. |
| #108 and #97 | Preserve cross-lane runtime/DSM regressions when integrating the runtime repair. |
| #90 and #91 | Select one protocol/corpus authority and explicitly account for unique work from each draft. |
| #88 and #108 | Run actual M4 qualification on the accepted repair revision; results from the old boundary do not qualify a changed one. |
| Demo and candidate | Record deployed demo revision separately. If demo changes affect packaged/runtime code, assess their impact on the candidate's qualification. |

This table is a dependency review, not authority to close, merge, or rewrite another PR.

## Integration entry checklist

- [ ] Select release scope: research preview, Experimental Release 1, or production release.
- [ ] Receive lane deliverables with exact head/base/tree revisions and retained failures.
- [ ] Resolve every blocking finding through an implementer-independent review.
- [ ] For #108, cover receipt compatibility, absolute lease-read bounds/resource enforcement,
      reap-timeout lifecycle, per-attempt diagnostic attribution, fixture timeout semantics,
      and the retained SQLite failure. Reversion/mutation tests must demonstrate protection.
- [ ] Review protected-file and shared-schema changes explicitly, including compatibility behavior.
- [ ] Require the agreed checks and review policy on main; retain configuration evidence.
- [ ] Integrate approved changes in a disposable candidate branch in dependency order.
- [ ] Run the full combined suite and relevant workflow gates. Branch results alone are insufficient.
- [ ] Record the candidate commit, tree, artifact digest and environment before parallel qualification.

#107's proposed local commands, after it is included in the candidate:

```bash
python scripts/status_check.py
python scripts/check_current_status.py
python verifier/v3/check_factory_ownership.py
python -m pytest -q
python scripts/qualification_test_runner.py --output runs/candidate-attempt-001/events.jsonl
```

Choose a fresh attempt directory for every execution. The ownership gate checks
committed HEAD, so commit the assembled candidate before treating its report as
candidate evidence. Preserve nonzero exits, skips and incomplete artifacts.

## Parallel qualification after integration

| Lane | Entry condition | Required output |
| --- | --- | --- |
| M4 containment | Candidate fixed; capable runner prerequisites passed | Real isolation/adversarial execution, including timeout behavior, with all mandatory cases executed |
| Blank-environment installation | Candidate package built and hashed | Clean install, dependency checks, startup/configuration/CLI results and environment record |
| Recovery/fault execution | Candidate fixed; isolated test environment ready | Crash/restart, interrupted execution, contention and resource-failure evidence preserving accepted state |
| Demo acceptance | Owner supplies deployed revision | Complete user-journey evidence tied to that revision; no inference from a development screenshot |
| Experiment rehearsal | Draft protocol/corpus and fixture inputs available | End-to-end artifact capture, accounting and report regeneration, labeled as rehearsal data |

Rehearsal and environment setup may start earlier. Final qualification must bind
to the accepted candidate. Use separate hosts or documented resource isolation
so fault tests, soak and benchmarks do not distort each other's observations.

## Confirmatory execution and parallelism

1. Clear the required trust, installation and experiment-readiness gates.
2. Freeze and hash code, workload/splits, model/provider configuration, seeds,
   repetitions, budgets, metrics, missing/UNKNOWN policy and statistical analysis.
3. Start fixed-model R0-R5 execution. Independent repetitions may run in parallel
   under predetermined allocation and comparable resource conditions.
4. In separate infrastructure, run the approved operational soak. Audit completed
   experimental batches and reproduce reports concurrently.
5. Run degradation/routing studies under their approved protocol. They may run
   independently when preregistered that way; otherwise review the baseline first.
6. Populate empirical paper/release claims only from retained, independently
   reviewed evidence. Preserve negative results and failed attempts.

No live provider spend, infrastructure purchase, protocol freeze, release
publication or elapsed-time qualification has been performed by this plan.

## Evidence record required for each lane

Record: candidate commit/tree; package/corpus/config hashes; lane and test scope;
environment and capabilities; run id/attempt/job; start/end times; command and
exit status; pass/fail/error/skip counts; raw artifact locations and digests;
known limitations; reviewer identity and disposition.

A run is complete only when its required end record and artifacts exist.
A green job with skipped mandatory isolation cases does not qualify M4.
A signature authenticates its signer and payload; it does not independently
establish a report's truth or operator-supplied timestamps.

## Changes, failures and release decision

- Retain failed attempts. A retry does not erase an unexplained failure.
- After a code/config/environment fix, identify affected claims and repeat the
  relevant qualification on the new candidate. Document any evidence reuse.
- Restart affected soak qualification when its execution assumptions change.
  Parallel workers cannot shorten the required elapsed observation period.
- Keep performance comparisons free of unaccounted co-located workloads.
- Declare a release only when the selected release scope's gates pass and an
  independent reviewer accepts the complete evidence package.

This plan defines work to perform during active sessions. It does not configure
a background watcher, automatically start other agents, or authorize merges.
