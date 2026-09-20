# Capacity staircase: Residual-Nano → StationLM (EXP-M6-SLM)

Architecture configs for the from-scratch control-plane models. **All configs
are untrained**; training is gated on the SLM-00 benchmark freeze
(see `../SECURITY-BOUNDARY.md`).

## Staircase

| Config                | d_model | n_layers | n_heads | ~Params  |
|-----------------------|---------|----------|---------|----------|
| `nano-30m.yaml`       | 448     | 7        | 7       | 32.1M    |
| `nano-80m.yaml`       | 704     | 9        | 11      | 77.5M    |
| `stationlm-150m.yaml` | 896     | 12       | 14      | 146.2M   |
| `stationlm-250m.yaml` | 1024    | 16       | 16      | 236.3M   |
| `stationlm-400m.yaml` | 1280    | 18       | 20      | 397.6M   |

Shared: vocab_size 32000, max_seq 2048, head_dim 64, ffn_mult 4, tied
embeddings. Exact parameter arithmetic is shown in a comment inside each
YAML file.

Rationale: Residual-Nano (30M/80M) sizes are cheap smoke-test and
scaling-signal points; StationLM (150M–400M) is the candidate control-plane
family. Each step roughly multiplies non-embedding parameters by ~1.8–2.2×.

## Training protocol (after SLM-00 freeze)

1. Train each size in ascending order on the identical frozen corpus with the
   identical recipe (same tokens/step schedule per size, seed 1337) using
   `research/slm/scaffold` inside the `research/slm/training` container.
2. Evaluate each checkpoint on the frozen SLM-00 benchmark harness only.
   Holdout access remains forbidden.

## Saturation decision rule

Before training size N+1, ask: **did performance saturate enough that the
next size is unnecessary?**

Proceed to the next size only if the current size does **not** saturate,
where saturation is defined as:

- the relative benchmark-score improvement of size N over size N−1 is
  < 2% (relative), **and**
- validation loss is still decreasing at the end of the token budget
  (undertrained, not capacity-limited) — i.e. the bottleneck is data/steps,
  not parameters.

If size N saturates (gain < 2% relative AND loss has plateaued), the
staircase stops: larger sizes are unnecessary and the saturating size
becomes the StationLM candidate. Record the decision, with the score deltas
and loss curves, in the experiment log before any size is skipped or added.
