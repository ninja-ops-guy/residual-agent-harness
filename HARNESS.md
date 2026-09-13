# RESIDUAL

**A hybrid agent harness that delegates the unresolved part of a task.**

RESIDUAL decomposes a host-authored task into checked obligations. Local tools and
models propose results; the controller accepts only results that pass their
registered checks. A stronger model receives the remaining frontier, relevant
dependency values, and concrete failure feedback. It can request exact evidence
windows. Already accepted independent work stays outside that request.

Python 3.11+, **zero runtime dependencies**. Native **Ollama**, **OpenAI-compatible
HTTP endpoints**, and **custom Python/SDK providers**. Both tiers can run locally.

This is a research prototype with a runnable controller, real HTTP adapters, and
adversarial contract tests. The included benchmark is a **scripted simulation**;
it establishes controller behavior, not real LLM accuracy, token savings, or
publication-level novelty. See [the research claim](docs/research.md).

## Run immediately

From the repository root, without installation or credentials:

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
python3 -m unittest discover -s tests -v
```

Optional package installation:

```bash
python3 -m pip install -e .
residual demo
```

The demo produces a checked error count, connection diagnosis, policy action,
JSON usage report, and hash-linked trace. It labels its scripted workers as a
simulation. No network requests or API keys are used by the demo workers.

## Bring your models

Copy `examples/ollama-cloud.toml` to `config.local.toml`. Set the Ollama model to
one you have installed, and set the expert model and provider's base URL. The
compatible URL includes the API prefix, usually `/v1`; the adapter appends
`/chat/completions`.

```bash
ollama serve
# In another terminal, after editing config.local.toml:
export RESIDUAL_EXPERT_API_KEY='your-provider-key'
python3 -m residual run examples/incident/task.json --config config.local.toml
python3 -m residual run examples/maintenance/task.json --config config.local.toml --output runs/maintenance
```

For two local Ollama models, copy and edit `examples/ollama-only.toml`. Model names
are explicit placeholders: the harness never downloads a model or substitutes a
demo worker when a configured provider fails. `placement = "local"` is restricted
to loopback HTTP endpoints. A remote or LAN endpoint must use `placement = "remote"`
and HTTPS, so local-only evidence cannot be sent there accidentally.

Native Ollama uses `/api/chat`, non-streaming responses, structured JSON output,
and `options.num_predict`. Compatible providers use JSON mode by default; set
`json_mode = false` if unsupported, or `output_token_field = "max_tokens"` for
servers requiring that parameter. Local protocol and output verification still
apply. Native provider-specific APIs, including Anthropic Messages, require a
custom adapter or an OpenAI-compatible gateway. See [extension APIs](docs/extending.md).

## What the controller changes

| Mechanism | Implemented behavior |
| --- | --- |
| Residual frontier | Stronger models see only currently solvable, unaccepted obligations |
| Independent checks | Model confidence and self-declared success never accept a result |
| Counterexample feedback | A failed check supplies a code and bounded task-specific explanation |
| Evidence pull | Workers request exact, hashed, permitted line windows |
| Adaptive packet planning | Inline a small complete relevant artifact when cheaper than two framed seed requests |
| Frozen accepted values | A later response cannot overwrite an accepted obligation |
| Dependency receipts | Bind values to contracts, verifier revisions, evidence snapshots, and parent receipts |
| Revalidated cache | Every cache hit is checked again; changed inputs invalidate the appropriate keys |
| Explicit budgets | Reserve calls, request-body bytes, and per-call output caps before provider I/O |
| Honest accounting | Reported usage, simulation estimates, missing usage, and configured prices remain distinct |

See [architecture and invariants](docs/architecture.md) for the trust boundaries
and the limits of a passing check.

## Measured controller behavior

Eight synthetic incident cases, identical checks and budgets, caches disabled:

| Policy | Cases passed | Expert calls | Modeled remote request bytes |
| --- | ---: | ---: | ---: |
| Full cloud | 8/8 | 24 | 1,044,858 |
| Full-context cascade | 8/8 | 6 | 262,188 |
| Adaptive residual | 8/8 | 12 | 37,368 |
| Local only | 2/8 | 0 | 0 |
| Fixed windows with no evidence pull | 2/8 | 24 | 68,448 |

Residual used **85.7% fewer framed request bytes than the cascade**, with twice
as many expert calls on this workload. **These are not measured model tokens or
API bills.** The diagnosis fixture intentionally exercises escalation even
though a task-specific deterministic solver could solve it locally.

The [size study](docs/scale-study.md) includes a failure of the fixed-window design:
it used 29.5% more bytes than the cascade on tiny inputs. Adaptive packet planning
reduced bytes by 32.9% on those same inputs. Raw run data, limitations, and the
reproduction commands are in [evaluation](docs/evaluation.md).

## Your own tasks and evaluation

Tasks declare artifacts, obligations, dependencies, trusted checks, and optional
local solvers. Artifacts are **local-only by default**. The incident example
demonstrates bulk local work. The maintenance example checks a proposed action
sequence against a state-transition model; it does not execute that sequence.

```bash
# Live evaluation: each case, mode, and repeat can invoke your configured models.
python3 -m residual benchmark --config config.local.toml \
  --task-suite examples/suite.json --modes cascade residual --repeats 3 \
  --output runs/live-comparison.json
```

Live budgets apply **per run**, not to the entire benchmark. Price tables are
optional and supplied by you. Missing usage stays unknown. Local electricity,
hardware amortization, and operational effort are not included in cloud cost.

## Prototype scope

- Host-authored DAGs and trusted Python plugins; no automatic task decomposition.
- Checks establish their declared conditions, not universal correctness.
- Accepted values are immutable within a run. Problems requiring backtracking
  must be grouped into a single obligation or started as a new task snapshot.
- No arbitrary shell tool, autonomous deployment, learned router, streaming,
  distributed scheduler, model fine-tuning, or crash-resume service is included.
- API adapters are tested over loopback HTTP fixtures. No live model evaluation
  was performed in the development environment.
- Hash chains detect alterations against a retained root; they are not signatures
  and do not authenticate the machine that produced a result.

## Publishing this repository

The working tree is committed locally. The distributable ZIP includes a Git
bundle containing that history. GitHub remote creation was unavailable in the
development session. With Git and an authenticated GitHub CLI installed:

```bash
python3 scripts/publish.py --dry-run
python3 scripts/publish.py --owner ninja-ops-guy
```

The script restores the bundled history if needed and creates a **private**
`residual-agent-harness` repository. It refuses to reuse an existing origin or
publish tracked edits that are not committed. If you create the empty repository
through GitHub instead, the normal `git remote add origin ...` and `git push -u
origin main` flow works from the committed checkout.

No public license has been selected. The prototype remains private pending the
owner's publication decision.
