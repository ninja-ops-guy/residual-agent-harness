# Residual 10-minute quickstart

## 1. Install

```bash
pip install residual-agent-harness
```

## 2. Start a local model

Install Ollama, then:

```bash
ollama pull qwen2.5:7b
ollama serve
```

## 3. Run a bounded task

Start the station with `residual-station`, open the local station URL, configure the Ollama provider, and submit a GoalSpec with explicit pass, token, and wall-clock budgets. Residual keeps verification and brake decisions host-owned; model output is only a candidate.

## 4. View evidence

The run result exposes station receipts for verified obligations. A receipt binds the task, cache key, value hash, verifier identity/revision, parent receipts, and execution-engine identity. Receipt integrity does not replace re-verification.

## 5. Metrics

The async station periphery can expose `/metrics` in Prometheus text format. Slow telemetry refreshes are cached and never block verifier execution.
