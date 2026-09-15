# Factory ownership gate (rebuilt on post-#63-closure main)

The gate pins the exact git blob SHA of every protected Factory M2/M3/M4
trust-surface file at a named main commit and fails closed on any deviation.

| Component | Path |
| --- | --- |
| Baseline manifest | `verifier/v3/factory_ownership_baseline.json` |
| Checker | `verifier/v3/check_factory_ownership.py` |
| CI workflow | `.github/workflows/factory-ownership.yml` |
| Regression tests | `tests/test_factory_ownership_gate.py` |

## Why a rebuild

PR #69 pinned a synthetic merge of PRs #66+#68. That baseline is invalid:
#66 was closed as superseded, and main commit `de9c9fa8` ("M4 trust-boundary
closure (#63)") rewrote the M4 trust surface directly on main, adding
`residual/factory/m4_sandbox.py`, `residual/factory/m4_git_evidence.py`, and
`residual/factory/_isolated_child.py` and reconciling the canonical API
(ConnectorReceipt rename; evidence under `runs/m4-trust/`). PR #86 also added
`residual/eval_frozen/` (a separate lane, out of scope here). This gate is
pinned to current main tip `50646c93ff5772e9ee1182ca6b4c290b1a5e7cba`, not
to any synthetic ancestor.

## Protected inventory (current main, verified to exist)

Core implementation surface (enforced in `CORE_PROTECTED`):

- `residual/factory/__init__.py`
- `residual/factory/_isolated_child.py` (new on main via #63 closure)
- `residual/factory/_sandbox_child.py` (retained from the #69 set; still present)
- `residual/factory/evidence_bus.py`
- `residual/factory/evidence_receipts.py`
- `residual/factory/m4_evidence.py`
- `residual/factory/m4_git_evidence.py` (new on main via #63 closure)
- `residual/factory/m4_integrator.py`
- `residual/factory/m4_safety.py`
- `residual/factory/m4_sandbox.py` (new on main via #63 closure)
- `residual/factory/m4_scheduler.py`
- `residual/factory/runtime.py`
- `residual/factory/runtime_journal.py`
- `residual/factory/runtime_workspace.py`
- `residual/factory/station_issuer.py`
- `residual/factory/worker_contract.py`

Also pinned in the manifest: `scripts/status_check.py` and all
`tests/test_factory_*` files (15 files) — the test surface that pins the
behavior of the protected modules.

Excluded (documented judgment calls):

- `residual/factory/cli.py`, `compiler.py`, `models.py` — Factory compile/CLI
  pipeline, not part of the M2/M3/M4 trust boundary; same exclusion as #69.
- `residual/factory/loop_runtime/` — loop runtime lane, outside the M4 trust
  boundary.
- `residual/eval_frozen/` (PR #86) — separate frozen-eval lane; it has its own
  evidence and is not part of the Factory ownership surface.

## Fail-closed semantics

Missing or invalid manifest, a core protected path missing from the manifest,
a protected file missing from the tree, any blob-SHA mismatch, an empty
justification, or any git error all FAIL the check. Unavailable evidence is
never reported as "no change".

## Authorized change procedure

To change a protected file, the same reviewed commit must update
`verifier/v3/factory_ownership_baseline.json` with the new blob SHA and a
`justification` naming the authorizing review/PR. No protected trust-boundary
path may be changed merely to make the gate green.

## Non-claims

This gate does not qualify PR #71, does not close issue #63 or any other
issue, does not prove an OS sandbox, and does not replace full test,
packaging, M4/EVAL, or production qualification. CI must be green before
merge.
