# Reliability Metrics Extraction

This note defines how paper-facing metrics are derived from the frozen study artifacts without changing historical `residual.study-report.v1` run semantics.

## Why a separate analysis layer exists

The existing study runner defines a successful system outcome as:

```text
controller_success AND independent_grader_pass
```

That is useful operationally, but the paper needs to distinguish two different random variables:

- `X`: the final worker candidate is independently correct;
- `A`: the controller accepts the candidate.

A correct candidate may be rejected. A wrong candidate may be accepted. Collapsing those cases into one `success` bit prevents a direct estimate of `P(X)`, `P(A)`, and `P(X|A)`.

`residual.reliability_metrics` therefore derives the paper metrics from the independently graded run rows after the normal study report has validated hashes, traces, schedules, and call receipts.

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

## Failure Containment Rate

FCR is **not** inferred from ordinary failures or rejections. A fault-injection run must explicitly record:

```json
{
  "fault_injected": true,
  "fault_contained": true
}
```

Only explicitly labelled fault trials enter the FCR denominator. Until such trials exist, FCR is reported as undefined. This prevents ordinary model mistakes from being retrospectively reclassified as controlled fault injections.

## Orchestration tax

The existing study report exposes `other_host_elapsed_ms`, calculated after subtracting provider, verifier, solver, and independent-grader timing. The reliability analysis exposes this only as `host_overhead_proxy_ms`.

It is **not** the exact orchestration tax because planning, scheduling, context packaging, and deterministic integration are not yet separately timed. Publication claims must retain this distinction until dedicated timing hooks exist.

## Usage

Given a validated study report:

```bash
python -m residual.reliability_metrics runs/experiment/report.json \
  --output runs/experiment/reliability-metrics.json
```

The output is schema-versioned as `residual.reliability-metrics.v1` and bound to the source report hash when available.

## Interpretation for H1

The central comparison is not merely whether Residual has a higher final success rate. For a fixed worker model, evaluate the joint movement of:

- raw candidate correctness `P(X)`;
- coverage `P(A)`;
- accepted correctness `P(X|A)`;
- AER/FAR;
- independent and accepted system success;
- cost and latency.

Support for the reliability hypothesis requires a meaningful improvement in accepted correctness / reduction in accepted error while retaining nontrivial coverage and acceptable system utility. A system that achieves zero accepted errors by rejecting everything has not established the intended result.

## Evidence status

The metric extractor is analysis instrumentation. It does not itself provide empirical support for H1. Fixture studies remain development evidence; confirmatory claims require the frozen live-model/held-out protocol described in [`reliability-h1-protocol.md`](reliability-h1-protocol.md).
