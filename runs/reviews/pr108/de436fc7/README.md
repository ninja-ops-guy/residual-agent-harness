# PR #108 repair evidence — de436fc7

**Repairs delivered; fresh independent acceptance required.** This continuation
implemented the fixes requested by the independent [b127d000 review](../b127d000/README.md).
It does not approve its own implementation, authorize a merge, or qualify M4.

## Source identity

- PR head: `de436fc7b6eaabee93ac5a734e3c71d9f2fecd12`.
- Tree: `7907b6f5857d8ad3c3c7e1c74eee2d12c565cdfe`.
- Parents: reviewed head `b127d000dbac7d75723969840491be5f44ec7c4e` and
  main `326eb2af47a4635c75c81735738801dd065fdd81`.
- Local full runs and final probes used the clean, published head.
- CI checked out merge `12406a5c1eb3f8f7811a5ed9740bfce1add13dcb`.
  GitHub's Git commit record confirms its tree equals the published head's tree.
- The GitDB publication tree matched local implementation commit `664ee8ac`
  exactly. This coordination PR stores evidence separately so adding this bundle
  does not change the tested runtime head.

## Finding-by-finding repair

| Finding | Change | Regression coverage |
| --- | --- | --- |
| R1: launcher allowance extends payload timeout | Remove the extra five seconds from both subprocess execution paths | Two real sleeping payloads cannot pass after their declared one-second limit |
| R2: lease gate blocks watchdog for two seconds | One bounded lease read per watchdog poll; carry retry state across polls and keep resource checks live | Real SQLite contention with a real child and short wall deadline; memory enforcement during unknown lease state |
| R3: timed-out reap loses finalization | Retain active ownership, report UNKNOWN/reap_pending, recover through the existing single reap owner, then clean resources and publish the original outcome | Persistent pending state/fencing, eventual cleanup and exactly one terminal event, failed publication diagnostic, watchdog/cancellation cause preservation |
| R4: synthetic exhausted read erases diagnostic | Preserve the last actual SQLite diagnostic and check the deadline again after backoff | Lock error survives retry-budget exhaustion |
| R5: reader retry restarts timeout | Share an absolute deadline across connections and SQL; cap remaining busy budget; retry only lock/busy errors | Delayed first failure, slow connection crossing deadline, non-contention error not retried |
| C1: stale receipt assertion breaks Factory/ownership | Restore the original v2 safety assertion | Safety file blob is again `b13fdb1af9bfca2eb8b73889a1f89eac6c0498a5`; Factory and ownership CI pass |

The implementation and limits are documented in
[the repair design](https://github.com/ninja-ops-guy/residual-agent-harness/blob/de436fc7b6eaabee93ac5a734e3c71d9f2fecd12/docs/factory/sandbox-timing-repair-2026-09-15.md).
Four existing ownership pins change for runtime/journal and their affected
lifecycle/startup tests; the new 12-test repair module is added. The ownership
checker itself is unchanged. Matching 38 pins is integrity evidence, not review.

## Validation and retained failures

| Scope | Result | Evidence limit |
| --- | --- | --- |
| Original protected adversarial battery | 12/12 pass | Implementer reproduction of the earlier independent battery |
| New protected repair module | 12/12 pass | Included in local full/focused runs and CI |
| Five original review probes | All assertions pass; cleanup-adjusted run 5/5 pass | Initial unchanged run is retained as 28 passed / 1 failed across the combined 29-test selection; see cleanup explanation below |
| Five repair reversions | All caught on the exact published head | R1: 2 failures; R2: 2; R3: 4; R4: 1; R5: 3; every run exits 1 with zero errors/skips |
| Eight original reversion attacks | All caught on the exact published head | Each exits 1 through assertions; zero errors/skips |
| Local full pytest | 1,625 passed, 15 failed, 62 skipped; 342 subtests passed | Nonzero exit retained; this host is not qualified |
| Local full unittest | 946 run, 5 failures, 1 error, 29 skips | Nonzero exit retained; class-level capability skips affect discovery/run counts |
| GitHub Factory CI | 980 unittest cases, 22 skips, success | Synthetic merge has identical source tree; namespace skips remain |
| Required ordinary Python matrices, ownership, clean-install checks | Success | Development CI scopes; clean-install checks are not blank-VM RC qualification |
| Termination matrix: normal, CPU, I/O | Each: 500 repetitions per test, two tests, zero failures/errors/skips | Raw syscall SIGSYS and blocked-audit termination only; no universal determinism or soak claim |
| Termination matrix: combined | Pending at this evidence snapshot | No full-matrix acceptance inferred; consult the exact run below |

The 15 local pytest failures are the same selectors previously retained for
this host: nine bubblewrap namespace-permission failures, one AF_UNIX permission
error, two startup `rss_meter_unavailable` outcomes, one startup stopped-event
timeout whose cause remains unclassified, and the two earlier b127d000
determinism failures (lease injection never reached; worker exits 122 without
completion). This is a historical selector comparison, not a fresh causal
classification or a reason to waive a gate. CI executes and passes those
unittest cases on its different host; 22 namespace tests still skip there.
Its N=10 three-worker determinism test executes and passes. N=20 was not rerun
in this continuation, and historical N=20 reports do not qualify this head.

The unchanged reap probe observed `reaped=true` and its assertions passed, then
its manual `workspace.discard()` raced the runtime's asynchronous cleanup.
`review_probes_cleanup.py` changes only the `finally` block to join the pending
owner before manual cleanup. Assertions, fault injection and thresholds are
unchanged; `probe-cleanup.diff` and both runs are retained. Recovery assertions
are evaluated before probe cleanup. The protected repair tests additionally
verify final journal state, resource cleanup and exact terminal provenance.

An initial pre-publication R3 mutation attempt used old module globals and
bypassed fixture seams. Its `invalid-fixture-binding` logs are retained but
excluded from reversion counts. The corrected driver restores the old method
body with current module globals; the final exact-head run confirms four real
assertion failures. Pre-publication reversion logs remain historical beside it.

## CI sources

- [Factory run 34984911243](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34984911243).
- [Ownership run 34984911334](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34984911334).
- [Controller/provider matrix 34984911019](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34984911019).
- [Station matrix 34984911022](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34984911022).
- [Termination matrix 34984910992](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/34984910992).

CI logs, artifact metadata/digests and the synthetic merge record are retained
in `raw-evidence.zip`; the matrix JSON is also retained separately. The normal
historical baseline had three blocked-audit failures in 100 repetitions; those
failures remain in its report and are not combined with candidate results.

## Reproduce and review

Run from a checkout of the exact PR head with test dependencies installed.
Extract `raw-evidence.zip` to a separate evidence directory. The mutation
drivers require git history containing b127d000 and a8082109.

```bash
python -m pytest tests/test_sandbox_timing_adversarial.py tests/test_sandbox_timing_repairs.py -q
python -m pytest /path/to/evidence/review_probes_cleanup.py /path/to/evidence/timeout_budget_probe.py -q
python /path/to/evidence/repair_mutations.py R3 /tmp/reverted-R3.xml
python /path/to/evidence/mutation_probe.py H2_recompute_deadline /tmp/reverted-H2.xml
```

The first two commands should pass; each deliberate mutant should fail through
an assertion. An import/collection error or a capability skip is not a caught
mutation. `evidence-manifest.json` hashes both the archive and every raw member.

The fresh reviewer should inspect pending ownership, repeated reap timeout,
failed cleanup/terminal writes, primary-reason preservation, deadline ownership,
receipt schema stability and all changed protected pins. Permanently unreapable
children remain pending. Unexpected cleanup/storage errors remain recorded for
operator reconciliation; this patch does not provide process-restart recovery.
Complete combined contention evidence is required before treating that matrix
as passed. Keep namespace qualification and elapsed 24h/72h soak separate.

The owner retains merge authority. Squash merge remains recommended because
the branch's historical commits contain temporary placeholder evidence files.
