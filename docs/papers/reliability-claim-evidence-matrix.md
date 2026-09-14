# Reliability Paper — Claim/Evidence Matrix

**Branch:** `research/reliability-paper-evidence`  
**Purpose:** prevent architecture, implementation, and empirical claims from being conflated in the paper.

## Claim classes

- **A — architectural:** supported by source/specification showing that a mechanism exists.
- **I — implementation-validation:** supported by tests or controlled fixtures showing that the mechanism behaves as intended on those cases.
- **E — empirical:** requires frozen experiments with independent grading and reported uncertainty.
- **H — hypothesis:** intentionally unproven until E evidence exists.

| ID | Claim | Class | Current evidence | Paper status |
| --- | --- | --- | --- | --- |
| C1 | Generator authority is separated from acceptance authority. | A | `residual/receipts.py`, verifier layer, study independent grader | Safe to state as architecture. |
| C2 | Receipts preserve content-bound provenance across task dependencies. | A/I | `StationReceipt`, `ReceiptReference`, SHA-256 envelope, parent receipt graph validation | Safe to state narrowly; a valid hash is explicitly not verification authority. |
| C3 | Receipt reuse is bound to value, cache key, verifier identity/revision, parent receipts and engine metadata. | A/I | `StationReceipt.matches`, `cache_key()` | Safe to state as implemented binding. |
| C4 | Missing/skipped verification is not silently equivalent to PASS. | A | `CheckResult` semantics; skipped checks cannot issue receipts | Safe to state. |
| C5 | Controlled evaluation preserves failures and missing evidence in denominators. | A/I | `docs/controlled-evaluation.md`; `runs.jsonl`, `calls.jsonl`, lifecycle accounting | Safe to state for study runner. |
| C6 | The existing study can detect false acceptance using grading independent of controller checks. | A/I | Separate final grader and controller-success vs independent-success outcomes | Safe to state for supported grader families. |
| C7 | Residual reduces accepted error rate relative to raw/conventional execution. | H/E | No frozen live-model result yet | **Do not claim yet.** Primary H1 outcome. |
| C8 | Residual increases failure containment under injected worker faults. | H/E | Explicit fault-trial instrumentation now exists for malformed replies, truncation, worker abstention and provider/runtime errors; no complete confirmatory matrix yet | **Do not claim yet.** The measurement path exists; the empirical result does not. |
| C9 | Heterogeneous lower-cost workers can preserve accepted-system quality at lower cost. | H/E | Routing and accounting exist; fixture studies are insufficient | **Do not claim yet.** |
| C10 | Dynamic swarms improve verified throughput after orchestration tax. | H/E | Direct timing instrumentation now measures dispatch/scheduling, response integration and a combined context-packaging/packet-planning boundary; confirmatory swarm study still required | **Do not claim yet.** |
| C11 | Deterministic acceptance/integration can make accepted state more reproducible than worker execution. | H/E | Deterministic control mechanisms exist; comparative reproducibility study required | Phrase as design goal until measured. |
| C12 | Residual is state of the art or first in literature. | E | No exhaustive literature or matched external baseline | **Do not claim.** |
| C13 | Reliability can emerge from unreliable computation without improving the underlying model. | H | Formal model + proposed ablation + metric instrumentation separating `P(X)`, `P(A)` and `P(X|A)` | Central hypothesis, not a result. |

## Evidence anchors already present in the repository

### Receipt integrity and provenance

`residual/receipts.py` defines a frozen `StationReceipt` containing task ID, cache key, value hash, verifier name/revision, verdict, parent receipt references, and engine name/version. Receipt hashes use canonical domain-separated SHA-256 serialization. Parsing rejects altered envelopes, noncanonical parent order, cycles/self-dependencies, and integrity mismatches.

Critically, the module states that a valid hash is **never verification authority**, and `matches()` documents that callers must still run the host verifier. This is an important boundary for the paper: provenance integrity and semantic correctness are different claims.

### Independent study grading

`docs/controlled-evaluation.md` separates controller success from independent final grading. False acceptance is explicitly defined as controller success followed by independent grading failure. Missing/error/not-run outcomes remain in the scheduled denominator.

`residual/reliability_metrics.py` preserves independent candidate correctness separately from acceptance, allowing direct estimation of raw candidate correctness `P(X)`, coverage `P(A)`, accepted correctness `P(X|A)`, AER/FAR, ISR and accepted system success.

The current graders support exact structured values, bounded integer-expression tests, and finite-assignment constraints. They are not a general solution for arbitrary code repair; arbitrary-code experiments require a separately isolated hidden grader.

### Controlled fault evidence

`residual/reliability_experiments.py` provides deterministic injected faults with explicit trial IDs and expected containment layers. Detection is read from the hash-linked execution ledger; containment is recorded separately based on whether the known injected fault produced incorrect accepted state. Retry recovery therefore does not erase the detection event.

`residual/reliability_experiment_report.py` aggregates explicit `residual.fault-trial.v1` receipts into detection rates and FCR overall and by fault kind. Ordinary model failures are never silently added to the FCR denominator.

The implemented fault kinds are a subset of the preregistered matrix, so this is implementation-validation infrastructure, not a general containment result.

### Direct orchestration timing

`OrchestrationTimingProbe` measures dispatch/scheduling overhead exclusive of worker execution, response integration exclusive of verifier time, and the existing combined context-packaging/packet-planning boundary. These are direct instrumented measurements rather than residual wall-time estimates.

Planning and context packaging are not yet separate core phases and therefore must remain one combined reported value. The paper must not manufacture two values from one execution boundary.

### Accounting and reproducibility

The study runner freezes source/task/config inputs in a lock, refuses silent overwrite, records call reservations before transport invocation, records completed/skipped runs, checks result/trace binding, and rejects mismatched or missing evidence rather than treating it as free work. This makes it suitable as the base of the reliability study, but live models, external task authorship, and matched external baselines remain outstanding.

## Required evidence to promote H claims

### H1 / C7 — accepted-system reliability

Run identical frozen task/model pairs through configurations that progressively add controls. Report:

- raw worker correctness `P(X)`;
- coverage `P(A)`;
- accepted correctness `P(X|A)`;
- Accepted Error Rate (AER);
- false acceptance rate;
- independent success rate;
- accepted system success rate;
- confidence intervals and paired effect sizes.

### C8 — fault containment

Run the controlled matrix at known locations and report:

- injected faults by explicit fault ID and kind;
- detected faults;
- contained faults;
- faults incorrectly crossing the acceptance boundary;
- UNKNOWN/abstention outcomes;
- FCR overall and by fault family.

The development runner `scripts/run_reliability_fault_matrix.py` can exercise the currently implemented deterministic subset. It remains development evidence until independently authored confirmatory workloads and the broader fault matrix are used.

### C9 — verified cost efficiency

Hold task quality targets constant and report actual provider usage when available, local occupancy cost, latency, and cost per independent success. Never infer dollar savings from scripted providers.

### C10 — swarm value

Compare single-worker, fixed-swarm, and dynamic-swarm execution over multi-granularity tasks. Include directly measured dispatch/scheduling, context-packaging/packet-planning, verification and integration overhead in the denominator. A swarm is beneficial only if its verified throughput/cost frontier improves after orchestration tax.

## Rule for manuscript edits

Every quantitative sentence in Results must point to a frozen run artifact. Every architecture sentence should point to source/specification. Every novelty sentence should point to literature comparison. Any sentence without one of those anchors must be labeled as hypothesis, motivation, limitation, or future work.
