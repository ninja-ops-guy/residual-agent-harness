# Factory ownership gate (rebuilt on post-#63-closure main)

The gate pins the exact git blob SHA of every protected Factory M2/M3/M4
trust-surface file at a named reviewed commit and fails closed on any deviation.

| Component | Path |
| --- | --- |
| Baseline manifest | `verifier/v3/factory_ownership_baseline.json` |
| Checker | `verifier/v3/check_factory_ownership.py` |
| CI workflow | `.github/workflows/factory-ownership.yml` |
| Regression tests | `tests/test_factory_ownership_gate.py` |

## Why a rebuild

PR #69 pinned a synthetic merge of PRs #66+#68. That baseline became invalid:
#66 was closed as superseded, and main commit `de9c9fa8` ("M4 trust-boundary
closure (#63)") rewrote the M4 trust surface directly on main, adding
`residual/factory/m4_sandbox.py`, `residual/factory/m4_git_evidence.py`, and
`residual/factory/_isolated_child.py` and reconciling the canonical API.
PR #95 rebuilt the gate on that post-#63 Factory tree.

PR #96 is an authorized follow-on transition for the M2 runtime termination
provenance work. It changes `runtime.py` and its runtime tests and introduces
`termination_provenance.py`. The new module is trust-critical, so PR #96 adds it
to `CORE_PROTECTED` and advances the corresponding blob pins rather than
excluding it to make the gate green.

## Protected inventory

Core implementation surface (enforced in `CORE_PROTECTED`):

- `residual/factory/__init__.py`
- `residual/factory/_isolated_child.py`
- `residual/factory/_sandbox_child.py`
- `residual/factory/evidence_bus.py`
- `residual/factory/evidence_receipts.py`
- `residual/factory/m4_evidence.py`
- `residual/factory/m4_git_evidence.py`
- `residual/factory/m4_integrator.py`
- `residual/factory/m4_protocol.py`
- `residual/factory/m4_safety.py`
- `residual/factory/m4_sandbox.py`
- `residual/factory/m4_scheduler.py`
- `residual/factory/runtime.py`
- `residual/factory/runtime_journal.py`
- `residual/factory/runtime_workspace.py`
- `residual/factory/station_issuer.py`
- `residual/factory/termination_provenance.py` (added to the protected core by PR #96)
- `residual/factory/worker_contract.py`

Also pinned in the manifest: `scripts/status_check.py` and the retained
`tests/test_factory_*` surface that pins behavior of the protected modules.

Excluded (documented judgment calls):

- `residual/factory/cli.py`, `compiler.py`, `models.py` — Factory compile/CLI
  pipeline, not part of the M2/M3/M4 trust boundary.
- `residual/factory/loop_runtime/` — loop runtime lane, outside the M4 trust
  boundary.
- `residual/eval_frozen/` — separate frozen-eval lane; it has its own evidence
  and is not part of the Factory ownership surface.

## Fail-closed semantics

Missing or invalid manifest, a core protected path missing from the manifest,
a protected file missing from the tree, any blob-SHA mismatch, an empty
justification, or any git error all FAIL the check. Unavailable evidence is
never reported as "no change".

## Authorized change procedure

To change a protected file, the same reviewed change set must update
`verifier/v3/factory_ownership_baseline.json` with the new blob SHA and a
`justification` naming the authorizing review/PR. New trust-critical Factory
modules must be added to `CORE_PROTECTED`; the core set must not be weakened to
make CI green.

## PR #96 transition

The PR #96 baseline points at reviewed candidate `a19d2c3248c6180a566b6ff7b331e075a48518c7`,
which contains the exact protected runtime/test blobs being authorized. The
historical raw `SIGKILL` remains UNKNOWN; advancing this ownership baseline does
not convert that historical event into seccomp evidence or broaden the runtime
security claim.

## Non-claims

This ownership gate is change control, not runtime containment. It does not by
itself prove an OS sandbox, identify a historical process killer, establish
statistical determinism, or replace full test, packaging, M4/EVAL, or production
qualification. CI and the applicable evidence matrix must be green before merge.
