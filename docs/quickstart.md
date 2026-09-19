# Residual 10-minute quickstart

Every command below runs fully offline; the demo providers are scripted and
make no model calls and no network requests. The commands in the
`quickstart-verify` block are executed end-to-end by
`tests/test_onboarding.py`, so this document cannot silently drift.

## 1. Install

From a source checkout, no installation is needed — run everything as
`python3 -m residual ...` from the repository root. For an installed
environment:

```bash
pip install residual-agent-harness
```

### Update an existing installation

Run `residual update` to update safely. When RESIDUAL is running from a Git
source checkout, the command requires a clean, attached branch with a configured
upstream and performs only a fast-forward update. For an installed package, it
uses the current Python interpreter to run pip with `--upgrade`.

Use `residual update --dry-run` to validate the selected update path without
changing the checkout or environment. `--method source` and `--method package`
can override automatic detection; `--pre` is package-only.


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
