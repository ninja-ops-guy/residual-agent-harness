# Offline reproduction preparation

`residual reproduce` rebuilds descriptive results from retained, hash-checked
artifacts without model calls, network requests, subprocesses, plugins, candidate
execution, or signing. It does not resume runs or reexecute verification.

```bash
python -m residual.reproduce synthetic-demo --runs-dir examples/reproduction
# Equivalent installed CLI after integration:
residual reproduce synthetic-demo --runs-dir examples/reproduction
# Save a new report; the parent directory must already exist:
residual reproduce synthetic-demo --runs-dir examples/reproduction --output /tmp/reproduced.json
```

The fixture contains six scheduled cells, five recorded outcomes, a fabricated
incorrect acceptance, an UNKNOWN outcome, a timeout, and a missing cell. All
identities, token counts, times, and prices are synthetic. It establishes replay
behavior, not model performance, system reliability, savings, or provenance.

`reproduce(run_id, *, runs_dir="runs", manifest_sha256=None)` returns a report
dictionary. `main(argv=None)` returns 0 on reconstruction or 2 for unusable input.
`canonical_bytes(report)` produces stable UTF-8 JSON with sorted keys, no generated
timestamp, and no nonfinite numbers. The CLI refuses to overwrite an output.

The versioned directory and field contract is [bundle-v1.md](bundle-v1.md).

## Integrity and authority

The manifest lists each retained artifact's SHA-256 and byte length. Reproduction
reads pinned file descriptors, checks every indexed artifact, and uses those
in-memory bytes. It rejects path traversal, noncanonical paths, symlink components,
hardlinks, nonregular files, oversized artifacts, duplicate JSON keys/records,
nonfinite values, torn JSONL records, unknown manifest/record fields, and rows for
unscheduled cells. Missing required files are errors; missing cell *rows* remain
visible in the scheduled denominator.

An attacker who rewrites both artifact and manifest can produce a consistent
bundle. `--manifest-sha256 <digest>` checks a separately retained content commitment;
it does not establish who authored that commitment, independent preregistration,
or a trustworthy Station key. Receipt, scheduler, and verifier envelopes are
hash-checked and retained as JSON objects; their signatures, native semantics,
causal ordering, and chain completeness are **not** authenticated by this command.
`source_refs` establish only that the named bytes were retained. They do not prove
that those bytes justify an assertion. The report always states these limitations
and sets `publication_ready: false`, including for `evidence_mode: measured` or a
protocol whose retained metadata says `frozen`.

Run against a quiescent local copy. Descriptor-based reads and hashes prevent
common path substitution attacks, but this tool is not a sandbox for a compromised
host. A hostile writer with host privileges or an adversary who controls an
unpinned manifest remains outside its guarantees. There is no generic archive
extractor. POSIX with `O_NOFOLLOW` is required; other platforms fail explicitly.

## Reconstructed estimands

The scheduled workload cell retains family, task, repetition, configuration, model
class, and topology for pairing. Ground truth is a separate retained assertion:
verifier PASS never implies independently correct. Reported acceptance also stays
separate from the verifier verdict. An accepted row with a non-PASS verdict or
non-COMPLETED execution is listed in `invariant_violations`; it is not silently
removed or relabeled.

| Output | Definition |
| --- | --- |
| `verified_goodput` | Known independently correct acceptances / all scheduled cells. Missing and UNKNOWN outcomes demonstrate no success; they are not relabeled incorrect. |
| `acceptance_rate` | Recorded acceptances / scheduled cells, only when acceptance is known for every cell; otherwise null with lower/upper bounds. |
| `accepted_error_rate` | Known independently incorrect acceptances / recorded acceptances, only when acceptance and accepted grading are complete; otherwise null. No acceptances gives null. |
| `accepted_error_rate_bounds` | With `B` known bad, `A` recorded acceptances, `U` ungraded acceptances, `M` cells with unknown acceptance: `[B/(A+M), (B+U+M)/(A+M)]`. When `M=0`, this is the science plan's `[B/A,(B+U)/A]`. A zero denominator gives `[null,null]`. |
| `known_cost_usd_subtotal` | All retained known call fees, including errors/retries, plus declared local occupancy cost. Not a complete total when coverage is missing. |
| `total_cost_usd` | Known subtotal only if every cell has an outcome and timing/usage coverage, every call is terminal, and all fee/local cost fields are known; otherwise null. |
| `cost_per_correct_acceptance_usd` | Complete all-call-plus-local cost / independently correct acceptances; null for incomplete cost or zero good acceptances. |
| `token_cost_total` | Historical SPEC-EVAL-001 name: token count, **not dollars**. Null if incomplete, with a separate known subtotal. |

Missing completion for a RESERVED or UNKNOWN call prevents complete cost/token
claims even if supplied numerical fields happen to be zero. `usage_complete` is a
retained collector assertion, not independently provable from an unsigned bundle.
Invoice reconciliation, hidden provider retries, cached/reasoning token categories,
shared cross-cell calls, and reservation-event completeness require a future
version or source-ledger adapter. A call belongs to exactly one cell in v1; do not
copy shared calls into multiple cells. Local occupancy must exclude separately
priced inference fees to avoid double counting.

`system_metrics_by_cell` reproduces the nine existing SPEC-EVAL-001 formulas for
complete cell data. Tests compare against `SystemMetrics.from_counters` directly.
Unlike the older complete-run counter type, missing data and zero denominators
remain null, including verifier rejection rate when no conclusive verdict exists.
The file contains a single terminal verifier disposition per cell; ensemble/candidate
level quality requires a different unit. Execution/sandbox ERROR/UNKNOWN does not
count as a verifier false positive or false negative. Per-cell elapsed times are
not summed into experiment wall time: that would misrepresent concurrent runs.

The `pareto` report minimizes accepted error rate and complete total cost while
maximizing verified goodput, matching the frozen dimensions in
`docs/program/science/analysis-plan.md`. Dominance requires no worse on every
dimension and strictly better on at least one. Equal points remain on the frontier;
no weights or substitute dimensions are selected. Acceptance coverage, missingness,
and unknown accepted grading accompany every point.

An arm with unknown cost, ambiguous acceptance, zero acceptances, or unknown grading
of accepted outputs has indeterminate frontier membership. If any arm is
indeterminate, the global `frontier` is null; `frontier_among_complete_points` is
reported only as a conditional descriptive set. Known complete points may still
provably dominate each other. Unknown grading on rejected candidates does not alter
these three objectives and is not invented as ground truth. No bootstrap stability,
confidence statement, or probability of truth is implied. Latency remains in
per-cell metrics; this increment does not render the separate latency panel.

## Remaining science and product gates

The preparation plan lives at
`experiments/preflight/science/protocol.v1.json`. Retain its exact bytes as an
attachment when assembling a bundle. Pin the protocol and expected schedule
outside the mutable bundle before obtaining confirmatory results. The manifest
and workload schedule are cross-checked against each other; independent prior
retention is what prevents rewriting both to hide a failed scheduled cell.

This command implements **descriptive reconstruction and Pareto dominance**. Clustered
confidence intervals, paired tests, effect sizes, multiplicity correction,
figure generation, and the complete paper are deferred to the frozen
science analysis engine. Do not describe this increment as reproducing every
paper-facing result. The expected cell/pair fields provide its required inputs.
No comparison, model invocation, confirmatory R0–R5 study, degradation study, or
soak was run here.

A native Station/Factory bundle exporter, independently authenticated receipt-chain
auditor, immutable/external preregistration record, complete accounting adapter,
and larger streaming artifact format remain integration gates. Existing
`residual.eval.replay.signed_report_from_observations` remains a separate native
SPEC-EVAL replay path; this command does not silently convert its signed reports
or treat its existing cached metrics as raw observations.
