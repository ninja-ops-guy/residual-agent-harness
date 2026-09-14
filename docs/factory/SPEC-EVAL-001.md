# SPEC-EVAL-001 comparative evidence

This layer evaluates the completed M4 Factory control path under one frozen workload and three configurations: `single`, `fixed`, and `dynamic`.

## Evidence boundary

The repository contains two evaluation contracts and they are intentionally separate.

- The older T10 benchmark requires at least 10 seeded simulator repeats and remains unchanged.
- SPEC-EVAL-001 requires at least 3 controlled runs per configuration and produces system-level publication evidence.

The built-in `residual evaluate` driver uses the repository's deterministic simulator backends and marks every resulting run `simulated`. It validates the evaluation machinery but MUST NOT be cited as measured production performance. Production orchestration can record real Factory counters through `SpecEvaluationEvidence.record_run(..., evidence_mode="measured")`.

## Frozen workload

`--workload` accepts the existing hash-locked `FrozenWorkload` JSON format. All runs in one comparison report must bind the same manifest hash.

Example:

```bash
residual evaluate \
  --workload spec.json \
  --configs single,fixed,dynamic \
  --runs 3 \
  --output runs/spec-eval/report.json \
  --observations runs/spec-eval/observations.jsonl
```

The configuration set must contain `single`, `fixed`, and `dynamic` exactly once.

## Metrics

Every run records the nine metrics required by SPEC-EVAL-001:

1. elapsed time in minutes;
2. accepted tasks per hour;
3. total LLM token count;
4. GPU time in minutes;
5. coordination overhead percentage;
6. rework rate;
7. integration conflict count;
8. verifier rejection rate;
9. final project test pass rate.

The report gives mean, median, sample standard deviation, minimum, and maximum for every metric and pairwise Mann-Whitney U or Welch t-test comparisons.

## Controls

`ExecutionControls` binds engine IDs, model/engine revisions, temperatures, and seed. `ExecutionControls.from_receipts()` can derive engine attribution from signed M3 `WorkerReceipt` values. Report generation fails closed when controls differ across runs.

For adapters whose provider exposes a model revision separately from the engine package revision, encode that revision into the receipt's engine version until the receipt schema gains a dedicated model-revision field.

## Cost analysis

Each run records:

- API cost = tokens / 1,000 × configured API rate;
- GPU cost = GPU hours × configured GPU rate;
- infrastructure cost = configured per-run infrastructure cost;
- total cost;
- cost per accepted task.

Each configuration also reports aggregate total cost divided by aggregate accepted tasks.

## Observation derivability

Every run is emitted through the hash-chained observation layer with its complete counters, controls, metric values, cost values, and run hash. The final observation contains only the report hash, signature metadata, significance settings, and source run hashes.

The full report is intentionally not copied into the terminal event because the observation schema has a 24 KB per-event ceiling. `signed_report_from_observations()` reconstructs the complete payload from run observations and reattaches the original Station key ID and signature from the terminal event. The original private key is not required for replay; an externally trusted public key is only needed to verify the recovered signature.

## Signature

`ComparisonReport` is signed by the same Ed25519 `StationIdentity` primitive used by Factory evidence. A persistent Station private key can be provided with `--station-key`. If it is omitted, the CLI uses an ephemeral evaluation-only identity and labels that fact in the output. The public key is written into the report wrapper so reviewers can verify the cryptographic signature; trust in the identity itself still requires an externally pinned Station public key.

## Claim discipline

A green SPEC-EVAL run demonstrates that the comparative evidence pipeline is reproducible, statistically summarized, observation-backed, and signed. Simulator results do not demonstrate that dynamic swarms are faster or cheaper in production. Those claims require `measured` runs from the real Factory runtime under the same frozen workload and execution controls.
