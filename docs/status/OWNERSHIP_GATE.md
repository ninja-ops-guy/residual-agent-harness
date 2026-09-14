# Swarm ownership gate

The gate evaluates committed HEAD against two explicit history baselines:

| Scope | Baseline | Policy |
| --- | --- | --- |
| Original swarm reporting and legacy directories | `98c12f0` (resolved to a full commit in output) | Preserve `residual/swarm`, `residual/evidence`, `residual/scheduler`, and `residual/integrator`. |
| Canonical Factory M2/M3 and reserved M4 files | `aa7685d165c787a636c4d2e30c132d27b1eabf54` | Preserve the exact `PROTECTED_FILES` set in `verifier/v3/check_swarm.py`. |

Missing commits, non-commit objects, non-ancestor baselines, Git errors, and
failed diffs are failures. An unavailable comparison is JSON `null`, never a
false zero-change result. Output records the resolved baselines and actual HEAD.
NUL-delimited paths and disabled rename detection preserve deleted, renamed,
and whitespace-bearing paths. Git replacement objects are disabled for these
comparisons. Original legacy protections remain in addition to Factory paths.

The proposed Factory baseline transition in this PR depends on reviewing #61,
which restores the lifecycle guards lost in #58 before admitting its watchdog
repair. The preceding baseline was `412b66c35f7c0e1ac479fe60a5b7d33d5510e3af`.
Among the protected paths, the transition changes only `runtime.py` and adds
`m4_evidence.py`. All other previously protected files are unchanged. The new
`m4_integrator.py` path from #60 is reserved and protected while absent from this
baseline: its eventual addition needs a separate reviewed transition. This gate
change does not approve or qualify #60. No protected paths have been removed.

Review/merge order is #61 -> #59 -> #50. Retarget dependent PRs after their
parents land and qualify the resulting integration refs again. A squash/rebase
merge can change ancestry: do not keep a baseline commit that was not retained
as an ancestor; reconcile it explicitly with the byte-identical reviewed tree.
Any future authorized M4 integration must coordinate a baseline update with the
canonical Factory owner (#22/#60), in the same reviewed change. A baseline advance must not hide an
unrelated trust-boundary modification. The check is a committed-tree guard, not
an OS sandbox or proof of the correctness of Factory implementations.

## Execution and evidence

`python verifier/v3/check_swarm.py --ownership-only` runs the history/ownership
preflight and explicitly reports that full qualification was NOT RUN.

`python verifier/v3/check_swarm.py` also checks deliverable paths, then runs the
full pytest suite and verifier v2 only after the preflight succeeds. Test-tool
stderr is retained on failure. This requires the repository test dependencies.

The `Swarm ownership preflight` workflow checks out full history and preserves
commit/tree IDs, a Git bundle of the tested commit and its ancestors, regression
output, and the preflight result. A successful preflight alone does not imply
full test, packaging, Factory M4/EVAL, or production qualification. Branch
protection/ruleset configuration is outside this change.

## Regression coverage

`tests/test_swarm_ownership_gate.py` covers unchanged and allowed edits, every
canonical protected path, deletion, rename escape, legacy paths, whitespace and
similar-prefix filenames, unavailable reporting/ownership baselines, blobs used
as commits, unrelated histories, a real shallow clone, failing diffs, missing
Git, timeouts, stderr propagation, and preflight/full-qualification separation.

This is the ownership-only successor to the useful portion of PR #45. Packaging
and clean-install qualification remain a separate repair of PR #50. Neither this
change nor its path-presence checks close implementation-status issue #48.
