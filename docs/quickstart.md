# Residual 10-minute quickstart

The core commands below run fully offline; the demo providers are scripted and
make no model calls and no network requests. The commands in the
`quickstart-verify` block are executed end-to-end by
`tests/test_onboarding.py`, so this document cannot silently drift. An optional
managed FreeLLMAPI path is documented in section 7 for real inference.

## 1. Install

From a source checkout, no installation is needed — run everything as
`python3 -m residual ...` from the repository root. For an installed
environment:

```bash
pip install residual-agent-harness
```

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

## 7. Managed FreeLLMAPI for real inference

`residual setup` turns the FreeLLMAPI dependency into a guided first-run flow.
Docker and Docker Compose v2 are the only service prerequisites. Residual creates
a localhost-only service under `~/.residual/services/freellmapi`, generates the
required encryption key, starts the qualified FreeLLMAPI v0.9.9 container pinned
by immutable image digest, and writes a Residual config at
`~/.residual/config.toml`.

```bash
residual setup
```

The listener is local, but model inference is not: Groq, Google AI Studio,
Cerebras, Mistral, OpenRouter, and similar upstreams receive the request over
the network. The generated Residual provider therefore uses `placement =
"remote"`, so local-only obligations and the normal remote evidence filtering
and budgets remain enforced. Do not change this to `local` merely because the
proxy endpoint is `127.0.0.1`.

The wizard gives direct signup links for Groq, Google AI Studio, Cerebras,
Mistral, and OpenRouter. If you paste an upstream key into the wizard, it is
passed to FreeLLMAPI through its declarative startup configuration and persisted
by FreeLLMAPI in its encrypted state. Residual then force-recreates the service
without the bootstrap environment. If readiness or credential scrubbing cannot
be established, setup fails; if scrubbing itself fails, the managed service is
stopped rather than leaving a long-lived container carrying the plaintext
bootstrap credential. The upstream key is never written to Residual's TOML
config.

After FreeLLMAPI starts, copy its unified `freellmapi-...` client key from the
local dashboard when prompted. Residual stores that client key in
`~/.residual/secrets.env` with private permissions and the generated TOML only
references the environment variable name. Explicit process environment values
take precedence over the managed secret file.

For CI, devcontainers, or scripted onboarding, use environment variables rather
than prompts:

```bash
export GROQ_API_KEY='...'
export FREELLMAPI_UNIFIED_KEY='freellmapi-...'
residual setup \
  --provider groq \
  --provider-key-env GROQ_API_KEY \
  --unified-key-env FREELLMAPI_UNIFIED_KEY \
  --non-interactive
```

Useful recovery and inspection commands:

```bash
residual providers list
residual services install freellmapi
residual services start freellmapi
residual doctor
residual doctor --fix
residual doctor --json
```

`residual doctor --fix` only applies deterministic local repairs such as
regenerating missing managed service files, writing the generated Residual
config, or starting an installed service. It never invents, rotates, or deletes
provider credentials. When a unified key is available, setup also performs a
live smoke test through Residual's normal hardened OpenAI-compatible provider
path and checks that the response satisfies the Residual worker contract.
