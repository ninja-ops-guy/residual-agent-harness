# Swarm ownership gate

The gate evaluates committed HEAD against two explicit history baselines:

| Scope | Baseline | Policy |
| --- | --- | --- |
| Original swarm reporting and legacy directories | `98c12f0` (resolved to a full commit in output) | Preserve `residual/swarm`, `residual/evidence`, `residual/scheduler`, and `residual/integrator`. |
| Canonical Factory M2/M3/M4 trust surface | `9aa29001c7bb5fc533ae3524017c9b4efdaed837` | Preserve the exact `PROTECTED_FILES` set in `verifier/v3/check_swarm.py`. |

The Factory baseline is an exact synthetic integration commit whose parents are
#68 (`0c931c7f92ddd31387f3a076de5d907a5ab026f0`) and #66
(`3961f52b45c4d5a167b5e346790451392572646d`). It combines the independently
reviewed current-main M2 lifecycle repair with the independently reviewed M4
accepted-state safety repair. The synthetic commit is review evidence only: it
does not move `main`, deploy Pages, close issue #63, or prove an OS sandbox.

The canonical protected Factory set is:

- `residual/factory/_sandbox_child.py`
- `residual/factory/evidence_bus.py`
- `residual/factory/evidence_receipts.py`
- `residual/factory/m4_evidence.py`
- `residual/factory/m4_integrator.py`
- `residual/factory/m4_safety.py`
- `residual/factory/m4_scheduler.py`
- `residual/factory/runtime.py`
- `residual/factory/runtime_journal.py`
- `residual/factory/runtime_workspace.py`
- `residual/factory/station_issuer.py`
- `residual/factory/worker_contract.py`

Missing commits, non-commit objects, non-ancestor baselines, Git errors, and
failed diffs are failures. An unavailable comparison is JSON `null`, never a
false zero-change result. Output records the resolved baselines and actual HEAD.
NUL-delimited paths and disabled rename detection preserve deleted, renamed,
and whitespace-bearing paths. Git replacement objects are disabled for these
comparisons. Original legacy protections remain in addition to Factory paths.

This baseline transition supersedes the stale #59/#61 ownership stack. In
particular, obsolete `residual/factory/integrator.py` and
`residual/factory/scheduler.py` placeholders are not used as substitutes for the
current M4 trust surface; `m4_integrator.py`, `m4_safety.py`, and
`m4_scheduler.py` are explicitly protected. No protected trust-boundary path may
be changed merely to make the ownership gate green.

After #68 and #66 are human-reviewed and merged, this gate must be reconciled to
the actual merged ancestry before landing on `main`. A squash/rebase merge can
change ancestry: do not retain a baseline SHA that is no longer an ancestor.
Reconcile against the byte-identical reviewed merged tree and rerun qualification.
The downstream clean-install gate remains separate and must be requalified after
this ownership transition.

## Execution and evidence

`python verifier/v3/check_swarm.py --ownership-only` runs the history/ownership
preflight and explicitly reports that full qualification was NOT RUN.

`python verifier/v3/check_swarm.py` also checks deliverable paths, then runs the
full pytest suite and verifier v2 only after the preflight succeeds. Test-tool
stderr is retained on failure. This requires the repository test dependencies.

The `Swarm ownership preflight` workflow checks out full history and preserves
commit/tree IDs, a Git bundle of the tested commit and its ancestors, regression
output, and the preflight result. A successful preflight alone does not imply
full test, packaging, Factory M4/EVAL, measured benchmark, or production
qualification. Branch protection/ruleset configuration is outside this change.

## Regression coverage

`tests/test_swarm_ownership_gate.py` covers unchanged and allowed edits, the
exact canonical protected set, every protected path, deletion, rename escape,
legacy paths, whitespace and similar-prefix filenames, unavailable reporting
and ownership baselines, blobs used as commits, unrelated histories, a real
shallow clone, failing diffs, missing Git, timeouts, stderr propagation, and
preflight/full-qualification separation.

This is the ownership-only successor to the useful portion of stale PR #59.
Packaging and clean-install qualification remain a separate reconstruction of
PR #50. The definitive black-and-green Pages presentation is outside this gate
and is unchanged by this transition.
