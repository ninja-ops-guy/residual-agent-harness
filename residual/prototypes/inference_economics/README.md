# IE-001 inference-economics prototype

Development-only qualification candidate for the contract in PR #160. It also
models the prerequisite behavior later specified by IE-002 through IE-007
(PRs #161, #162, #163, #164, #166, #167) without wiring any of it into
production execution.

## Authority boundary

This package consumes deterministic frozen/replayed observations only. It does
not call a provider, spawn/terminate a worker, verify or accept a candidate,
issue a receipt, integrate an artifact, or mutate the production scheduler.
It changes no Factory/M4 trust-boundary source, protected test, ownership pin,
shared evidence schema, provider authorization, or release/research threshold.

## What is implemented

- canonical 11-stage lifecycle observations with commit + tree provenance;
- attempt, verifier-terminal, accepted, and integrated throughput classes;
- TTFW/TTE/TTA/TTI plus per-obligation and per-stage measurements;
- explicit UNKNOWN-preserving pressure/resource/usage accounting;
- OTX-compatible phase projection without zero-imputing missing timings;
- nine deterministic bottleneck outcomes used by IE-007;
- independent metric, queue, OTX, and bottleneck oracle;
- deterministic replay and tamper evidence;
- Q5 pressure/backpressure model;
- Q6 provenance-safe context-fragment cache model;
- Q7 evidence-gated sequential escalation model;
- Q8 hard-constraint-first uncertainty-aware advisory routing model;
- external hash-bound evidence-bundle builder retaining normative streams,
  oracle/prototype/policy/replay records, and test results.

## Qualification posture

Local prototype tests can establish candidate evidence for Q1-Q9. They cannot
self-certify Q10 or Q11:

- **Q10** requires all applicable repository CI on the exact PR head.
- **Q11** in PR #160 explicitly requires genuinely independent current-head
  technical review. The repository's solo-maintainer attestation mechanism does
  not manufacture independent review for a claim-specific gate that still asks
  for it.

Therefore this package must not be described as an IE-001 *qualified* prototype
until Q10 and Q11 are actually satisfied on the same exact head.

## Run the focused qualification suite

```bash
python -m pytest residual/prototypes/inference_economics/tests -q
```

## Evidence bundle

`evidence-bundle.json` is deliberately **not** committed. A bundle binds the
exact source commit and git tree; checking that same bundle into the tree would
make the identity self-referential. Generate and retain the bundle externally
after the candidate head is fixed, using `build_bundle(...)` with the exact
commit/tree and the actual test result record.

The artifact schema is development-only:

`residual.inference-economics.prototype.v1`

It is not a Factory/M4 evidence schema and proves no production performance,
provider-cost, model-quality, reliability, scheduling-safety, GPU-optimization,
or paper-facing research claim.
