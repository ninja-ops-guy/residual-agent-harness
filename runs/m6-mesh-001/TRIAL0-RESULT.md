# M6-MESH-001 Trial 0 — retained result

Workflow run: 35424274389
Artifact: m6-mesh-001-trial0 (ID 10578541714)
Exact experiment head: d3b6f24d7b2e9c2ac08f51c02764fda41042af76

## Observed
- Sequential verified success: 3/3 missions (6/6 obligations).
- Parallel verified success: 3/3 missions (6/6 obligations).
- Sequential mean wall clock: 2.1899 s.
- Parallel mean wall clock: 1.8300 s.
- Naive mean speedup: 1.1967x.
- Mean token usage was effectively equal: 179.67 sequential vs 180 parallel.

## Confound discovered
The very first measured condition was sequential and took 3.0233 s. The later two sequential measurements were 1.7669 s and 1.7796 s, indicating a material first-use warm-up effect.

Warm-only sequential mean (repeats 1 and 2): 1.7732 s.
Parallel mean: 1.8300 s.

Therefore Trial 0 does NOT establish a concurrency speedup. Once the obvious cold-start observation is excluded, two concurrent calls on the same Ollama host are approximately flat/slightly slower than sequential execution.

This is retained as evidence, not discarded.

## Decision
Run Trial 0B with an explicit discarded warm-up, more balanced repeats, and pre-declared summary statistics before moving to native RESIDUAL scheduling.
