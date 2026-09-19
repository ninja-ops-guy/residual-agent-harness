# M6-MESH-001 Trial 0B — retained result

Exact experiment head: `96f27701519802ab36745862c4f9e23776f0fd46`  
Workflow run: `35424941934`  
Job: `105849142750`  
Artifact: `m6-mesh-001-trial0b`, ID `10578283879`  
Artifact archive SHA-256: `f23ceebfeedb4ecc6ad1b8bfda2916c2aeb5f715979c1b151a0fb91afb4c4d3f`

## Frozen question

After explicit warm-up, does issuing two independent, behaviorally verified obligations concurrently to one Ollama/Qwen2.5-Coder 1.5B host reduce wall-clock completion time without reducing verified success?

## Result

All 8 paired repeats were valid. Both conditions completed 8/8 verified missions (16/16 obligations each). Mean token usage was exactly 209 tokens per mission in both conditions.

| Metric | Sequential | Parallel |
|---|---:|---:|
| verified missions | 8/8 | 8/8 |
| mean wall time | 3.1692 s | 3.0604 s |
| median wall time | 3.0916 s | 3.1000 s |
| mean tokens | 209 | 209 |
| mean overlap factor | 1.0000 | 1.5330 |

Pre-registered primary statistic:
- median paired speedup (sequential / parallel): **1.0322x**
- mean paired speedup: **1.0532x**

Individual paired ratios alternated strongly with condition order:
`1.4386, 0.8396, 1.2073, 0.8570, 1.2120, 0.8225, 1.2086, 0.8398`.

## Interpretation

Trial 0B does **not** establish a meaningful same-host concurrency advantage. Verified quality and token use were equal, and the pre-registered median speedup was only ~3.2%. Median raw wall times were essentially identical. The strong alternating paired ratios show a material order/thermal/scheduling effect: the condition run first in a pair was generally disadvantaged.

The parallel condition did achieve real overlap (mean overlap factor 1.533), proving that Ollama serviced work concurrently, but this overlap did not translate into a robust wall-clock gain on one inference host.

This narrows the research hypothesis:

> The likely value of multi-instance RESIDUAL coordination is not merely concurrent requests to one saturated inference resource. The next test must introduce genuinely independent compute capacity and then measure whether bounded scheduling, verification, and evidence handoff convert that capacity into verified mission throughput.

## Decision

Trial 0 and 0B are retained, including the negative/ambiguous result. Do not optimize the scheduler around a same-host speedup claim.

Next experiment: **Trial 1 — independent-host capacity crossover**, followed by native WorkerContract/evidence-bus instrumentation. A2A federation is introduced only after the independent-capacity baseline is established.

Scope remains experimental. No production or general swarm/A2A qualification is implied.
