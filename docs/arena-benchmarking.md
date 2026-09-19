# Arena API and Agent Arena benchmarking integration

Date: 2026-09-19

## Boundary

RESIDUAL integrates Arena in two separate roles:

1. **Arena API provider transport** — `ai_providers.adapters.ArenaAdapter` uses Arena's OpenAI-compatible preview endpoint as a model gateway.
2. **Arena-aligned evaluation** — `residual.eval.arena` extracts local measurements corresponding to publicly described Agent Arena signals.

These roles are deliberately separated. The repository does not claim to submit RESIDUAL into the official Agent Arena leaderboard and does not label local results as official Arena scores.

## Setup from RESIDUAL

The easiest path is **Command Station → Model Workshop → Cloud provider → Arena API**.

When Arena is selected, RESIDUAL shows a guided setup card:

1. **Get Arena API key** opens the Arena dashboard Keys page directly: `https://portal.api.preview.arena.ai/dashboard/keys`.
2. Create a **virtual API key** in Arena and copy it.
3. Return to RESIDUAL, paste it in the API key field, and click **Save model routes**.
4. Click **Test cloud connection**.
5. Click **List cloud models** and copy/select the exact model ID you want to benchmark.

RESIDUAL does not fetch or create the Arena credential on your behalf. The key is entered directly into the Station credential field and is not returned by bootstrap/settings APIs.

Terminal users can open the same destination with:

    python -m residual.workbench arena setup

For headless systems:

    python -m residual.workbench arena setup --print-only

## Provider safety

The Arena adapter submits a single model ID per request and writes `allow_fallbacks: false` into every Arena request. Scientific runs therefore disable Arena gateway fallback at the transport boundary. If an operator wants failover for non-experimental use, it should be expressed through RESIDUAL's existing `Router`, where every attempt is separately observed and receipted.

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

Run a frozen live protocol:

    python -m residual.workbench arena run --lock <lock.json> --output <run-directory>

Score an externally produced complete trace set:

    python -m residual.workbench arena score --lock <lock.json> \
      --traces <traces.jsonl> --output <report.json>

The built-in live executor is intentionally narrow: exact-answer tasks, one raw single-call Arena control, and the same Arena model behind RESIDUAL's real obligation harness. It records transport/provider failures as `UNKNOWN` rather than task failures. More complex coding/tool benchmarks should implement a task/evaluator adapter against the same frozen schedule and trace contract.

The lock binds the workload, randomized schedule, model refs, conditions, complete RESIDUAL/provider/observation source hashes, fallback policy, seed, and methodology before outcomes are inspected. Live execution refuses a changed source tree.

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
