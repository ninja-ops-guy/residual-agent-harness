# Arena API and Agent Arena benchmarking integration

Date: 2026-09-19

## Boundary

RESIDUAL integrates Arena in two separate roles:

1. **Arena API provider transport** — `ai_providers.adapters.ArenaAdapter` uses Arena's OpenAI-compatible preview endpoint as a model gateway.
2. **Arena-aligned evaluation** — `residual.eval.arena` extracts local measurements corresponding to publicly described Agent Arena signals.

These roles are deliberately separated. The repository does not claim to submit RESIDUAL into the official Agent Arena leaderboard and does not label local results as official Arena scores.

## Provider safety

The Arena adapter submits a single model ID per request. Scientific runs keep fallback disabled. If an operator wants failover for non-experimental use, it should be expressed through RESIDUAL's existing `Router`, where every attempt is separately observed and receipted.

Environment variables:

- `ARENA_API_KEY`
- `ARENA_BASE_URL` (optional; defaults to `https://api.preview.arena.ai/v1`)

The provider remains a remote/cloud route. It is not accepted as a local provider.

## Workbench commands

Model discovery:

    python -m residual.workbench arena models

Freeze:

    python -m residual.workbench arena freeze --manifest <manifest.json> \
      --model arena:<model-id> [--model arena:<model-id> ...] --output <lock.json>

Score:

    python -m residual.workbench arena score --lock <lock.json> \
      --traces <traces.jsonl> --output <report.json>

The lock binds the workload, randomized schedule, model refs, conditions, source hashes, fallback policy, seed, and methodology before outcomes are inspected.

## Trace event vocabulary

The signal extractor consumes explicit event labels rather than inferring hidden semantics:

- `task_feedback`: `{"approved": true|false}`
- `feedback`: `{"sentiment": "praise"|"complaint"}`
- `correction`: `{"correction_id": "..."}`
- `correction_outcome`: `{"correction_id": "...", "status": "accepted"|"extended"|"redirected"|"rejected"|"gave_up"}`
- `tool_call`: `{"name": "..."}`
- `bash_result`: `{"ok": true|false}`

Tool hallucination is measured against the trace's frozen `available_tools` set. Bash recovery begins on a failed bash result and counts subsequent bash results through the first success.

## Experimental interpretation

AX-ARENA-01 is a paired harness-treatment experiment. The same task/model/repetition cell has one control observation and one RESIDUAL observation. The current report computes a descriptive success-rate delta and a task-cluster bootstrap interval.

That interval is not an automatic superiority verdict. Corpus selection, evaluator validity, provider stochasticity, environmental drift, multiple testing, and repeated inspection all remain relevant.

## Next experimental extensions

- AX-ARENA-02: component ablation across orchestration, contracts, observation, verification, deterministic integration, recovery, and memory.
- AX-ARENA-03: swarm scaling at 1/2/4/8/16/32 workers with coordination-cost accounting.
- Fault-injection variants: transport death, malformed tool output, unavailable verifier, conflicting worker results, budget exhaustion, and checkpoint recovery.
