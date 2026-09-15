# PR #108 — Lane 2 independent review

**Verdict: REQUEST CHANGES / BLOCKED at `b127d000`.** The original adversarial
battery passes, and eight independent reversion attacks are caught. The PR is
still not ready to merge: two CI failures remain and five additional regression
probes fail. This review does not modify the runtime, protected tests or pins.

- Reviewed head: `b127d000dbac7d75723969840491be5f44ec7c4e`.
- Reviewed tree: `46c4146e9afcc9bbfd474d3d7b738970a10e0253`.
- Original base: `a8082109e01aff9eda72030b837103c09d1393d3`.
- Latest observed main: `326eb2af47a4635c75c81735738801dd065fdd81`.
- Local Python: 3.12.14; Linux x86_64. See `environment.json`,
  `dependencies.txt`, `host-capabilities.json` and `seccomp-probe.json`.
- The reviewed checkout was clean before and after testing. Both handed-off
  test blobs match GitHub: determinism `eae62d8360c749cc0684accaadfae73b0c775ba0`,
  adversarial `fb1b16dbae474c58a0a8bcad0ad4d02fba69a388`.

## Independently observed results

| Check | Result | Scope |
| --- | --- | --- |
| Lane 2 original/adapted adversarial battery | **12 passed, 0 skipped** | All five original blockers plus reader contention exercised |
| Determinism module | **19 passed, 2 failed, 7 skipped** | Local host cannot qualify the complete process/isolation lane |
| Focused compatibility, ownership and watchdog tests | **13 passed, 2 failed** | Both remaining CI failures reproduced on the exact PR head |
| Independent reversion attacks | **8/8 caught**, no collection errors or skips | B1–B5, reader retry, deadline snapshot and typed reap timeout |
| Additional deadline/provenance/recovery probes | **4 failed** | Real SQLite locks/children, with explicitly bounded fault injection |
| Original-main vs PR declared-timeout comparison | **1 failed** | No mocks: a 2-second payload passes a declared 1-second timeout on the PR |
| Receipt payload comparison with original main | **Identical bytes/hash** | Fixed normal-result example, not a claim about all possible receipts |
| Writer-only contention control | **116 writer lock errors**, zero readers | Supports excluding raw-writer errors from the reader-specific regression |

The two local determinism failures are not presented as independently established
production defects. One injected lease error never reached its seam; the other
worker was stopped with `rss_meter_unavailable`. The seccomp handshake probe
exits 122 without `SandboxReady`; namespace probing reports
`namespace_probe_failed`. Six seccomp-dependent tests, including N=10, and one
isolated-timeout test skip. No fallback, capability override or skipped PASS is
used. Full local qualification remains **UNKNOWN**.

GitHub provides distinct, retained evidence: [Factory run 34972037232](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34972037232)
checked out synthetic merge `15f9a7a3c7f7abe6332ff4fc2de524bca475dc61`
(this head into `1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`), and ran **967 tests,
2 failures, 22 skips**. Its log records the N=10 and closed-FD/spin tests passing;
the isolated timeout test skips. Those are observed CI results on that combined
tree, not this reviewer's successful local N=10 reproduction, nor qualification
of the later `326eb2a` integration. See `ci-evidence.json` and the two log excerpts.

## Original blocker dispositions

| Blocker | Mechanism verdict | Remaining qualification |
| --- | --- | --- |
| B1: mutate signed v2 payload in place | **Resolved in implementation.** `timed_out` remains outside `to_dict`; a fixed receipt matches original main byte-for-byte. Reversion caught. | A stale protected test still expects v3, failing both the test and ownership gate. Restore its original v2 expectation; this also restores the already-pinned blob. Do not repin the incorrect v3 test. |
| B2: first lease read outside the 2-second budget | **Resolved for the lease gate itself.** Real contention and slow-read cases are bounded; reversion caught. | The watchdog blocks in that gate and misses an earlier worker deadline: R2 below. |
| B3: `stopped` before consuming reap | **Resolved invariant and typed timeout.** Reversions caught. | Automatic finalizer recovery is not implemented: R3. The PR body's daemon-reaper claim does not match source. |
| B4: cross-attempt diagnostic mutation | **Resolved per-call binding.** Both attribution directions pass and a shared-diagnostic mutant fails. | Retry exhaustion can erase the last real diagnostic: R4. |
| B5: timeout/exit collision | **Resolved for executed fixture and integrator paths.** Timeout is 124/typed; a genuine exit 124 stays FAIL. Reversion caught. | Isolated execution remains unqualified on this host; ordinary sandbox timeout enforcement separately regresses in R1. |
| CI: reader-side SQLite lock failures | **Improved and reproduced.** Reader storm and retry tests pass; single-shot mutant fails. Writer-only control justifies the narrowed assertion. | The total reader retry budget restarts at each connection: R5. |

The battery adaptations to the atomic `lease_read` API are appropriate. The
reader-only assertion is a scope narrowing, supported by the independent
writer-only control; it should not be described as proof that all journal
writers are contention-safe. Some older startup/lifecycle tests still patch
`lease_state` even though runtime now calls `lease_read`; refresh those seams
when touching the tests so `assert_not_called` checks the actual dependency.

## Required repairs

### R1 — P1: a declared wall-clock limit no longer limits the payload

`residual/sandbox/subprocess_backend.py:run_contained` now adds
`LAUNCHER_ALLOWANCE_S = 5` to every declared timeout. For a direct `/bin/sleep 2`
with `timeout_seconds=1`, original main kills it at **1.004 s** with TIMEOUT;
the reviewed code returns **OK after 2.009 s**. There is no launcher in this
case. This is a runtime contract change, not merely a test scheduling margin.

Restore enforcement of the declared payload budget. If launch preparation needs
separate accounting, keep it distinct from worker execution and document that
contract. Keep the no-mock original-main control in `timeout_budget_probe.py`;
do not solve the failure by broadening the worker limit.

### R2 — P1: lease retries suspend the watchdog's resource deadline

`FactoryRuntime._watch` checks wall time, then synchronously calls the full
2-second `_lease_denial` gate. Under a real exclusive SQLite lock, a real child
with a **0.3 s** deadline is killed only at **2.024 s**, with
`lease_unreadable` rather than the elapsed wall-clock deadline. The injected RSS
sample only avoids this host's metering limitation; clock, database, poll loop,
pidfd, signal and reap remain real. This is not a full sandbox qualification.

Make lease retry scheduling subordinate to the guard-owned resource deadline;
poll resource limits while the store is uncertain and preserve the primary
termination owner. Include contention concurrent with the worker deadline in
the regression suite, not just a standalone 2-second lease-gate test.

### R3 — P1: a reap timeout escapes finalization and has no recovery driver

The `stopped => reaped` invariant now holds, but `FactoryRuntime.run`'s finalizer
still unconditionally asks for `termination_record()` after a timed-out kill.
An injected transient reap timeout with a real owned child yields
`RuntimeError: termination record requires a reaped process`; the journal stays
RUNNING, the active entry remains, and recovery does not occur during a 0.5-second
observation after injection ends. Source inspection finds no scheduled recovery
driver. The probe cleans up the child itself afterward; that cleanup is not
credited as runtime recovery.

Provide an explicit owner for pending reap/retry and finalization. Preserve
UNKNOWN/pending status until actual consuming reap; do not publish `stopped` or
success to hide the error. Ensure finalization cannot abandon later cleanup
because it requested a record too early. Test through `FactoryRuntime.run`, not
only by manually calling `control.reap()` from a test. Remove the PR body's
daemon-reaper claim unless an implemented and tested driver supports it.

### R4 — P2: exhausted retries replace SQLite provenance with a synthetic code

With actual SQLite contention and a shorter valid per-read cap, `_lease_denial`
observes eleven `OperationalError/SQLITE_BUSY (5)` results, then sleeps through
its remaining budget and calls `lease_read` once more. That final call does not
touch SQLite and returns `read_budget_exhausted/0`, overwriting the genuine
diagnostic in the emitted denial. The total gate remains bounded at **2.002 s**.

Check the remaining deadline before starting another read, and retain the last
actual store error alongside a separate budget-exhausted indication. Keep the
per-call immutable state/diagnostic binding; a journal-global field is not the fix.

### R5 — P2: the reader's advertised total budget is reused per retry

`RuntimeJournal._read` sets an outer deadline but `_connect()` always gets the
full configured timeout. A delayed first connection failure followed by a real
SQLite lock gives connection budgets **[0.3, 0.3] s** and **0.594 s** elapsed
for a scaled **0.3 s total** budget. This probe injects the first connection
failure/delay; the second operation really contends in SQLite. It does not
claim a measured default-budget duration.

Pass remaining time to each connection/busy handler, refuse new work after the
deadline, and retry only the intended transient lock failures. The existing
all-immediate-error test does not cover a later blocking retry.

### C1 — P1 merge gate: restore the protected safety test

`tests/test_factory_m4_safety.py:245` expects
`factory-integration-receipt-v3`, while implementation and canonical tests use
v2. The same one-line change produces the ownership mismatch:

- Pinned/original blob: `b13fdb1af9bfca2eb8b73889a1f89eac6c0498a5`.
- Current incorrect blob: `4b2b117a2f3323a73dafaf04c21ab5ed9a1f79c0`.

Restore the v2 assertion. The expected result is both failures cleared without
changing this file's ownership pin. Other protected runtime repairs require
their normal independently reviewed ownership update.

## Evidence and next review

`review.json` is the machine-readable verdict; `evidence-manifest.json` hashes
the retained files. `mutations.json` records each attack's assertions, error and
skip counts. No files under protected source/tests or the ownership manifest
were edited by this reviewer; mutations existed only inside isolated Python
processes. The new probe scripts are deliberately outside ordinary test
discovery and intentionally fail against the reviewed head.

From an exact checkout, the principal reproductions are:

```sh
python -m pytest tests/test_sandbox_timing_adversarial.py tests/test_sandbox_timing_determinism.py -vv -rA
python -m pytest /path/to/retained/review_probes.py /path/to/retained/timeout_budget_probe.py -vv -s
python /path/to/retained/mutation_probe.py B2_deadline_after_first_read /tmp/B2.xml
```

For the eight case names, see `mutations.json`. The original-main comparisons
also need commit `a8082109` available in Git. Logs and JUnit identify all tests
and injected boundaries. Retain this failed review when publishing the repair.

After implementation: rerun the five new probes and original 12-test battery,
the relevant reversion attacks, all protected checks and the full ordinary
suites on a capable Linux runner. Retain a new N=10 result on the repaired head,
then validate its combination with current main. Existing `d750c48` evidence is
historical; matching selected outcome hashes does not qualify changed code.
Refresh the PR body's head-bound counts and claims. Owner merge acceptance and
the required CI gates remain outstanding; no merge is performed by this review.
