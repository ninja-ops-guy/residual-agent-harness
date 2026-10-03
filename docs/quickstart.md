# Residual source-checkout quickstart

This is a development-monorepo example, not the installation guide for a released
Open Core package. Check [licensing](../LICENSING.md) before evaluating reserved
runtime code. For the shortest guided path and troubleshooting, use the
[first-run guide](adoption/README.md).

The bounded-task and trace examples below run offline with scripted provider
configuration. The sample is solved deterministically with no model calls.
`tests/test_onboarding.py` executes the Bash command blocks; that source test is
not blank-machine or release-artifact qualification.

## 1. Prepare your checkout

Use Python 3.11+ and a complete, authorized source checkout at the revision being
evaluated. Run `python3 -m residual ...` from its root. The offline example does
not require an account, model download, or Station service. Record `git rev-parse
HEAD` with your results. On Windows, use `py -3` in place of `python3`; the Bash
blocks below require Bash. The guided first-run tool also works without Bash.

A package-index installation is intentionally not prescribed here: an installed
package would also need a qualified artifact identity, license scope and the
example files. Follow the actual release's installation instructions when one is
published.

## 2. Run a bounded task

The sample project in `examples/onboarding/sample_project` declares two
obligations over a local artifact, each with a mechanical `json_sum` check.
Residual keeps verification host-owned: provider output is only a candidate,
and each obligation is recomputed from the declared evidence.

```bash
python3 -m residual run examples/onboarding/sample_project/task.json \
  --config examples/onboarding/config.toml --output runs/quickstart
```

The command exits 0 only when every obligation passes verification. The run
writes `runs/quickstart/result.json` and an evidence trace at
`runs/quickstart/trace.jsonl`.

## 3. Verify the evidence trace

A receipt binds the task, cache key, value hash, verifier identity/revision,
parent receipts, and execution-engine identity. Receipt integrity does not
replace re-verification — so verify the trace, then re-check it against the
expected root and the bound result:

Here the expected root is read from the same local trace. This checks consistency;
it does not independently authenticate the trace's origin or prevent replacement
of both trace and result. An independent trust claim needs a separately trusted
anchor and the corresponding verification policy.

```bash
ROOT=$(python3 -m residual verify-trace runs/quickstart/trace.jsonl | python3 -c "import sys, json; print(json.load(sys.stdin)['root'])")
python3 -m residual verify-trace runs/quickstart/trace.jsonl --expected-root "$ROOT"
python3 -m residual verify-trace runs/quickstart/trace.jsonl --expected-root "$ROOT" --result runs/quickstart/result.json
```

## 4. One-command demo

`examples/onboarding/demo.sh` performs steps 2–3 in one shot and exits 0 on
success:

```bash
bash examples/onboarding/demo.sh
```

## 5. Metrics (optional)

The following Station/Studio paths are optional reserved development surfaces,
not part of the Open Core distribution or the offline first-run requirement.
Start the local command station with `python3 -m residual serve`, open the
printed URL, and the async station periphery exposes `/metrics` in Prometheus
text format. Slow telemetry refreshes are cached and never block verifier
execution. The Studio development surface (stubbed swarm API) launches with
`python3 -m residual.studio_frontend.stub_server` — see
`residual/studio_frontend/README.md`.

## 6. Author a module

See `docs/module-tutorial.md` for the `StationModule` contract, then validate
your module before publication:

```bash
python3 examples/onboarding/validate_tutorial.py
```

That script generates a module per the tutorial, checks its quarantine /
verifier / brake semantics, and runs `residual-module validate` on it.
