# Reliability Metrics Extraction

This note defines how paper-facing metrics are derived from frozen study artifacts without changing historical `residual.study-report.v1` run semantics.

## Why a separate analysis layer exists

The existing study runner defines a successful system outcome as:

```text
controller_success AND independent_grader_pass
```

That is useful operationally, but the paper needs to distinguish two different random variables:

- `X`: the final worker candidate is independently correct;
- `A`: the controller accepts the candidate.

A correct candidate may be rejected. A wrong candidate may be accepted. Collapsing those cases into one `success` bit prevents a direct estimate of `P(X)`, `P(A)`, and `P(X|A)`.

`residual.reliability_metrics` therefore derives the paper metrics from independently graded run rows after the normal study report has validated hashes, traces, schedules, and call receipts.

## Metrics

For each mode:

| Metric | Definition |
| --- | --- |
| Candidate correctness | independent grader passes the completed final candidate |
| Coverage | `P(A) = accepted / scheduled` |
| Raw candidate correctness | independently correct / completed candidates |
| Accepted correctness | `P(X|A) = accepted & correct / accepted` |
| AER | accepted & incorrect / accepted |
| FAR | controller-accepted but independently incorrect / accepted |
| ISR | independently correct final candidates / scheduled |
| Accepted system success rate | accepted & correct / scheduled |

AER and FAR are deliberately both emitted because the paper uses both labels. Under the current binary acceptance model they are numerically identical. This should be stated explicitly rather than presenting them as independent measurements.

If no output is accepted, accepted correctness, AER, and FAR are `null`; zero coverage must never be reported as perfect reliability.

## Controlled Failure Containment Rate

FCR is **not** inferred from ordinary failures or rejections. Controlled fault trials are produced by `residual.reliability_experiments` and carry explicit trial metadata:

```json
{
  "schema_version": "residual.fault-trial.v1",
  "fault_injected": true,
  "fault_id": "case:malformed_reply",
  "fault_kind": "malformed_reply",
  "expected_containment_layer": "schema/contract boundary",
  "fault_detected": true,
  "fault_contained": true,
  "incorrect_fault_crossed_acceptance_boundary": false
}
```

Detection and containment are separate outcomes. Detection is derived from the execution ledger; containment is determined from whether the known injected fault resulted in independently incorrect accepted state. A retry may therefore recover successfully while preserving evidence that the initial fault was detected.

The first deterministic injection set covers:

- malformed worker replies;
- truncated replies;
- explicit worker abstention;
- provider/runtime errors.

These tests establish behavior only for the injected fault classes represented in the receipts. They do not imply coverage of the full fault matrix in the H1 protocol.

`residual.reliability_experiment_report` aggregates explicit receipts into overall and per-fault-kind detection rate and FCR. Ordinary run rows never enter this denominator automatically.

## Orchestration timing

The historical study report exposes `other_host_elapsed_ms`, calculated after subtracting provider, verifier, solver, and independent-grader timing. `residual.reliability_metrics` continues to expose that only as a broad host-overhead proxy for historical runs.

New controlled experiments can additionally install `OrchestrationTimingProbe`, which directly instruments existing harness execution boundaries without changing the normal run result or acceptance semantics. It measures:

- dispatch partition / scheduling overhead exclusive of worker execution;
- context packaging **plus packet-plan selection**;
- response integration, including protocol parsing, evidence-request application, and receipt/integration work exclusive of verifier time.

The result is schema-versioned as `residual.orchestration-timing.v1`.

Planning and context packaging currently occur inside the same `_packet` boundary, so they are intentionally reported together as `context_packaging_and_planning_ms`. The instrumentation does **not** invent a split that the implementation cannot directly observe. Provider, verifier, and solver timing remain separately reported by the existing harness.

This means the new measurements are stronger than residual wall-time subtraction, but a paper must still state that planning/context packaging are a combined boundary until the core harness separates those phases.

## Development fault matrix

The bundled fixture suite can be exercised reproducibly with:

```bash
python scripts/run_reliability_fault_matrix.py \
  --output runs/fault-matrix
```

The runner executes every supported fault kind against every selected suite case with a fresh harness and emits:

- `fault-trials.jsonl` — hash-bound `residual.fault-trial.v1` receipts;
- `fault-report.json` — aggregate detection, FCR, and timing statistics.

Bundled fixtures have `development_fixture` evidence status. The script preserves that label and must not be used to describe fixture behavior as confirmatory live-model evidence.

## Reliability metric usage

Given a validated study report:

```bash
python -m residual.reliability_metrics runs/experiment/report.json \
  --output runs/experiment/reliability-metrics.json
```

The output is schema-versioned as `residual.reliability-metrics.v1` and bound to the source report hash when available.

For controlled fault receipts:

```bash
python -m residual.reliability_experiment_report runs/fault-matrix/fault-trials.jsonl \
  --output runs/fault-matrix/experiment-report.json
```

## Interpretation for H1

The central comparison is not merely whether Residual has a higher final success rate. For a fixed worker model, evaluate the joint movement of:

- raw candidate correctness `P(X)`;
- coverage `P(A)`;
- accepted correctness `P(X|A)`;
- AER/FAR;
- independent and accepted system success;
- controlled FCR for preregistered fault classes;
- measured orchestration overhead;
- cost and latency.

Support for the reliability hypothesis requires a meaningful improvement in accepted correctness / reduction in accepted error while retaining nontrivial coverage and acceptable system utility. A system that achieves zero accepted errors by rejecting everything has not established the intended result.

## Evidence status

The metric extractor, controlled injection harness, and timing probe are analysis instrumentation. They do not themselves provide empirical support for H1. Fixture studies remain development evidence; confirmatory claims require the frozen live-model/held-out protocol described in [`reliability-h1-protocol.md`](reliability-h1-protocol.md).
