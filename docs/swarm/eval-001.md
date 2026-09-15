# SPEC-SWARM-EVAL-001 — Frozen Reliability Evaluation (Swarm A)

Status: implemented (Gates A–C green on the scripted development fixture).

## What this adds

`residual/eval_frozen/` implements the critical-path experiment comparing raw
unconstrained execution (R0) against progressively stronger Residual control
layers (R1–R5) while holding worker/model capability constant.

| Module | Role |
| --- | --- |
| `residual/eval_frozen/workload.py` | EVAL-R1: versioned `FrozenWorkload` (`residual.frozen-workload.v1`) with immutable sha256 over every task field; fault labels for FCR; JSON round-trip with hash verification. |
| `residual/eval_frozen/configs.py` | EVAL-R2/R3: configurations R0–R5 with cumulative control layers; `CONTROLLED_CONSTANTS` pins model/provider/version, prompting policy, inference settings, tool environment, and grader across all ablations. |
| `residual/eval_frozen/runner.py` | EVAL-R4/R5/R7/R8: deterministic scripted engine; paired `RunRecord` per (task, config, repeat); distinct `PASS`/`FAIL`/`REJECTED`/`UNKNOWN` states; aborted runs retained; `recompute_from_records` (Gate C). |
| `residual/eval_frozen/metrics.py` | EVAL-R6: AER/FAR, ISR, ASSR, acceptance coverage, false rejection, FCR (when fault labels exist), throughput, latency (mean/p50/p95), rework, conflicts, verifier rejection, token/compute cost. |
| `residual/eval_frozen/report.py` | EVAL-R8/R9: hash-bound aggregate report (`residual.eval-report.v1`), paper-ready CSV, reproducible plotting inputs (reliability-vs-cost, reliability-vs-latency, state distributions). |
| `residual/eval_frozen/evidence.py` | Gate B: evidence artifact (`residual.eval-evidence.v1`) with exact commit/tree identity (git or file-digest fallback), runtime versions, frozen inputs, raw observations, results. |
| `residual/eval_frozen/__main__.py` | EVAL-R10: `python3 -m residual.eval_frozen --out evidence/eval` runs the CI fixture end-to-end; `--live` produces separately labeled `live_model` evidence. |

## Metric definitions

X = independent grader correctness, A = pipeline acceptance. UNKNOWN/aborted
runs remain in every denominator (shared rule 5). Undefined rates (zero
denominator) are reported as `null`, never `0.0`.

- AER (acceptance error rate) = P(¬X | A) = FAR (false acceptance rate)
- ISR (incorrect suppression rate) = P(¬A | ¬X)
- ASSR (accepted-and-sound rate) = P(X ∧ A)
- acceptance coverage = P(A); false rejection = P(¬A | X)
- FCR (fault capture rate) = P(caught | fault-labeled), only when labels exist

## Scripted engine semantics (development fixture only)

Worker correctness is a pure function of (workload hash, task id, repeat) and
is *identical across configurations* (capability held constant, EVAL-R3); only
the acceptance boundary varies. Fault-labeled tasks are scripted incorrect.
R0/R1 accept everything; R2 contracts reject some malformed artifacts; R3 adds
a verifier (recall 0.90, false-reject 0.05); R4 deterministic integration
raises recall to 0.97 and removes integration conflicts; R5 dynamic swarm
lowers false rejection to 0.02. Fixture results measure controller behavior,
not live LLM capability.

## Requirements → tests traceability (shared rule 9)

| Requirement | Tests in `tests/swarm/test_eval_frozen.py` |
| --- | --- |
| EVAL-R1 versioned FrozenWorkload + immutable hash | `test_r1_schema_version_and_hash_stable`, `test_r1_hash_covers_every_task_field`, `test_r1_hash_mismatch_rejected`, `test_r1_duplicate_task_ids_rejected`, `test_r1_workload_is_frozen_dataclass` |
| EVAL-R2 configurations R0–R5 | `test_r2_six_configurations_r0_to_r5`, `test_r2_control_layers_cumulative` |
| EVAL-R3 constants held across ablations | `test_r3_constants_identical_across_configs`, `test_r3_config_hash_changes_with_layers_only`, `test_r5_worker_correctness_invariant_to_control_layers` |
| EVAL-R4 ≥3 runs per config per slice | `test_r4_at_least_three_runs_per_config_per_slice`, `test_r4_fewer_than_three_repeats_rejected` |
| EVAL-R5 X independent of A | `test_r5_correctness_and_acceptance_independent`, `test_r5_worker_correctness_invariant_to_control_layers` |
| EVAL-R6 metric families | `test_r6_all_metric_families_present`, `test_r6_metric_definitions`, `test_r6_fcr_none_without_fault_labels`, `test_r6_control_layers_change_outcomes` |
| EVAL-R7 paired run records | `test_r7_paired_records_enable_task_level_comparison` |
| EVAL-R8 failed/aborted retained | `test_r8_failures_and_aborts_stay_in_aggregates`, `test_r8_states_distinct_and_typed` |
| EVAL-R9 CSV/JSON + plotting inputs | `test_r9_csv_rows_parseable`, `test_r9_plotting_inputs_bound_to_report`, `test_r9_report_hash_bound_and_deterministic`, `test_r9_report_hash_pinned`, `test_r9_report_hash_reproducible_across_processes` |
| EVAL-R10 CI fixture vs live labeling | `test_r10_fixture_labeled_development`, `test_r10_live_runs_separately_labeled`, `test_r10_invalid_evidence_level_rejected` |
| Gate B evidence artifact | `test_gate_b_evidence_artifact_identity_and_contents` |
| Gate C reproduction (P(X), P(A), P(X\|A)) | `test_gate_c_recompute_probabilities_from_raw_records`, `test_gate_c_aggregate_metrics_match_recomputed`, `test_gate_c_unknowns_stay_in_recompute_denominators` |
| Acceptance (end-to-end R0–R5) | `test_acceptance_end_to_end_fixture_study`, `test_acceptance_cli_runs_end_to_end` |

Gate A: `python3 -m pytest tests/swarm/ -q` → 34 passed.

## Reproduction

```bash
python3 -m pytest tests/swarm/ -q          # Gate A + Gate C tests
python3 -m residual.eval_frozen --out evidence/eval   # regenerate fixture artifacts
```

Retained evidence (regenerated on `swarm/eval-001-frozen-reliability-v2`
from inside a clean git checkout at commit
`33778d24a7d4388cc05d67b79eca1190fb8cc125`, so the artifact's `source` block
carries the real `commit`/`tree`; the artifact file itself is committed in a
follow-up commit on the same branch):

- `evidence/eval/fixture-study.json` — full hash-bound report (`residual.eval-report.v1`);
  regenerated on demand by `python3 -m residual.eval_frozen` (deterministic; aggregate floats normalized to 9 decimal places before hashing) and pinned
  by `results.report_sha256` inside the evidence artifact
  (`1bce348dd69c4a0471fbf8b90c69d0603ce396cd75845e86c1c5ec76e53b2416`).
- `evidence/eval/fixture-study.csv` — paper-ready per-config/slice metrics
- `evidence/eval/fixture-study-plot-inputs.json` — plotting inputs bound to the report hash
- `evidence/eval/fixture-study-evidence.json` — Gate B artifact (`residual.eval-evidence.v1`), evidence sha256 `acb405f5a1a70534b23292f7d605a8762702b1e11dbc2cbe7a02301f9ca66211`

`recompute_from_records` recomputes P(X), P(A), P(X|A) per configuration from
the retained raw run records alone and is asserted equal to the aggregate
report in Gate C tests.

## Limitations

- Fixture outcomes are scripted; no live-model performance claim is made.
  Live runs must use `--live` and are labeled `live_model` separately.
- The frozen workload declares two slices ("development" and "evaluation"),
  but only the "evaluation" slice is exercised: all 108 retained observations
  (6 configurations × 6 tasks × 3 repeats) have `slice="evaluation"`. No
  per-slice comparison is possible from this fixture.
- The evidence artifact records the commit/tree of the generating code; the
  artifact file itself is committed in a follow-up commit on the same branch.
