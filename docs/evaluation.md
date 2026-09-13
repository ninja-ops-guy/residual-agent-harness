# Reproduction and interpretation

## Offline verification

```bash
python3 -m unittest discover -s tests -v
python3 -m residual demo --output runs/demo
python3 -m residual verify-trace runs/demo/trace.jsonl --result runs/demo/result.json
python3 -m residual run examples/incident/task.json --config examples/demo.toml --output runs/incident
python3 -m examples.python_api
```

HTTP contract tests start loopback servers and exercise the actual native Ollama
and compatible transports. They test framing, output caps, usage parsing,
redirect refusal, malformed responses, credentials confined to request headers,
and missing usage. They do not start an Ollama model or call a cloud LLM.

## Scripted controller experiments

```bash
python3 -m residual benchmark --cases 8 --noise-lines 256 --output docs/benchmark-simulation.json
python3 -m scripts.scale_study
```

The [raw benchmark](benchmark-simulation.json) contains every run, accepted values,
unresolved outcomes, receipts, and per-call accounting. Its
[table](benchmark-simulation.md) and [size study](scale-study.md) are generated
from the same code. Timestamps, UUID-derived trace roots, and elapsed times vary
between runs. Workload data and serialized request-byte counts are deterministic.

| Mode | Local tools/model | Expert evidence | Purpose |
| --- | --- | --- | --- |
| `local_only` | Enabled | No expert | Establish the local fixture's baseline |
| `full_cloud` | Disabled | All permitted task evidence | Isolate broad cloud processing |
| `cascade` | Enabled | All permitted task evidence | Simple fallback after local attempts |
| `residual_fixed` | Enabled | Failed frontier, seed windows, explicit pulls | Isolate residual context and evidence negotiation |
| `residual` | Enabled | Failed frontier, adaptive small-capsule planning, pulls | Default design |
| `no_pull` | Enabled | Fixed seed windows, pulls denied | Missing-evidence ablation |

All use the same checks, per-run budgets, and scripted workers. Cache reuse is
disabled, and the order of modes rotates across cases. Full-cloud keeps the same
DAG scheduling and verifier boundary: it is not an unconstrained monolithic
chatbot. The incident family has four probe patterns, two instances each.

Modeled request bytes include system messages, protocol and adapter framing. The
demo providers report `simulation` usage, so aggregate provider-reported token
counts are zero with `usage_complete: false`, and cloud price is `null`. These
zeros mean no measured usage is available; they do not mean free inference.

The verifier is an oracle for this deliberately simple incident family. It is
possible to implement an entirely deterministic solver. The benchmark tests
routing and evidence handling only. The maintenance example provides a different
check structure, but is not included in the scripted incident worker's claimed
completion rate.

## Live evaluation

Edit a model configuration and supply its credential environment variable. An
explicit configuration is required for `run`; the harness does not silently
switch to a scripted model after an error.

```bash
python3 -m residual benchmark --config config.local.toml \
  --task-suite examples/suite.json --modes cascade residual_fixed residual \
  --repeats 3 --output runs/live-benchmark.json
```

Each task/mode/repeat has its own call and byte budget. A benchmark with two tasks,
three modes and three repeats can start eighteen runs. It has no shared global
dollar cap. Current provider prices are supplied in your TOML; no API pricing is
hard-coded. A two-Ollama configuration reports local placement and zero remote
calls, even when the expert tier is used.

Interpret cost per success across *all* attempted runs, including failures and
unknown usage. Remote cost stays null if any relevant usage or prices are missing.
Do not compare latency from scripted workers to network/model latency. No energy
or hardware-amortization measurements are included.

## Remaining empirical work

Real model generation was not available in the development environment: there
was no Ollama installation and no configured provider credentials. The next gate
is live cross-model evaluation with held-out task families and independent gold
or hidden checks. A CI workflow is included, but its remote execution is pending
creation and publication of the GitHub repository.
