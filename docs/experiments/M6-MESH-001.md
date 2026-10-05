# M6-MESH-001 — Cooperative Mission Efficiency, Trial 0

Status: experimental / no production authority.

Hypothesis: for independent, behaviorally verifiable obligations, two concurrent real-model workers can reduce mission wall clock without reducing verified task success relative to sequential execution.

Frozen Trial-0 design: same model and same two obligations in both conditions; sequential single worker versus two concurrent calls; temperature 0; three repeats with alternating condition order; deterministic behavioral checks define acceptance; record wall time, worker time, tokens, success, and response hashes.

Primary outcome: wall-clock speedup conditional on both obligations passing. A faster run with lower verified success is not an efficiency win.

This trial does not claim A2A, Command Station scheduling, multi-host scaling, or heterogeneous-model superiority. It measures the smallest real coordination crossover before adding those variables.
