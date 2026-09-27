# M6-MESH-001 — Trial 0B warm-controlled crossover

Status: pre-registered before execution.

Purpose: resolve the cold-start confound observed in Trial 0 before attributing any wall-clock advantage to concurrency.

Design:
- model: qwen2.5-coder:1.5b on one Ollama host;
- two independent behaviorally verified coding obligations;
- one explicit discarded model warm-up before measurement;
- 8 paired repeats;
- each pair runs sequential and two-concurrent conditions with alternating order;
- both conditions in a pair receive the same replicate-tagged prompts;
- temperature 0;
- a pair contributes to the efficiency estimate only if both conditions pass all deterministic checks.

Primary statistic: median of paired wall-clock ratios (sequential / parallel) among fully verified pairs.
Secondary: mean wall time, median wall time, tokens, and overlap factor = summed worker elapsed / wall clock.

Interpretation:
- >1 ratio favors parallel wall-clock performance;
- <=1 does not support a concurrency speedup;
- any loss of verified success invalidates an efficiency claim;
- result is scoped to one model on one host and is not evidence for A2A or heterogeneous mesh superiority.
