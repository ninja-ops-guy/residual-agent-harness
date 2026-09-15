# Engineering and evidence audit lane

This lane covers preparation tasks 5, 13, 14, 15, 16 and 18. It does not qualify
M4, modify the runtime, run a provider, or execute R0–R5. The base reviewed is
`dec571992a97b4ae80f0310aa32ffd8f542aef8c`. Read-only branch reviews are pinned to
PR40 `0063e6400fa945acf2db393f7e9d30db02cb1139`, PR43
`058e25b3ca73de4528648b72b1901b2c319fe643`, and PR81
`30d1d020469d958d90969bc02946145c248e0adb`. These are source snapshots, not claims
about later branch heads or merge status.

| Deliverable | Executable status | Remaining boundary |
|---|---|---|
| [Backward evidence audit](evidence-chain.md) | Schema probes and pinned source inventory | A complete retained run and the missing revision/output/workload links are required for a full backward proof |
| [Controller and metrics review](controller-observability-review.md) | Pinned-code synthetic counterexamples; no source edits | Runtime wiring and post-fix review are separate gates |
| [Cost accounting audit](cost-accounting.md) | Native pricing and actual Router with fake transports | Not every adapter has a durable per-attempt accounting join |
| Engineering microbenchmarks | Receipt roundtrip/signature, scheduler selection, plan DAG validation/hashing, observation chain serialization/validation, optional M2 candidate capture | No sandbox or accepted-integration timing before qualified #81 |
| Scale preparation | Explicit bounded node/observation/DAG/artifact sizes | Synthetic node records do not demonstrate 1,000 concurrent workers |

Run the mandatory local checks:

```bash
python -m unittest discover -s tests -p test_engineering_envelope.py -v
python scripts/engineering_envelope.py --output /tmp/residual-engineering-new.json
```

The 13 tests include 8 main-source tests and 5 tests of pinned review snapshots.
The latter explicitly skip if those Git objects are absent in a shallow clone;
this is not a review pass. No network fetch is performed by the script. Local
`cryptography` is required, as for the Factory optional dependency.

An explicit scale run (a fresh output filename is required):

```bash
python scripts/engineering_envelope.py \
  --workers 10 100 1000 --observations 1000 10000 100000 \
  --dag-nodes 100 1000 10000 --artifacts 10 1000 \
  --capture-files 10 100 --repeats 1 --timeout-s 10 --review-refs \
  --output /tmp/residual-engineering-scale-new.json
```

`--review-refs` requires the exact PR40/43/81 commits already present locally.
Each case has a POSIX timer and records `measured`, `timeout`, or `error`. Partial
timings do not acquire a success median. Exit code 1 means at least one case was
not measured successfully; its result is still retained. Repeats are bounded to
10, each case deadline to 60 seconds, and matrix dimensions have explicit limits.

The report records SHA/tree, dirty-worktree status, hashes of reviewed code files,
Python/platform, dimensions, individual elapsed nanoseconds, and a canonical
report hash. It deliberately does not dump environment variables. One warm
process and a shared host cannot establish throughput, tail latency, production
capacity, or a paper confidence interval. Temporary setup is included in
observation/DAG operations; scheduler object setup is outside the timer. Receipt
creation/signing is outside its roundtrip/verification timer. M2 capture excludes
Git initialization, worktree creation, broker writes and cleanup, and uses one
sample because capture owns a unique quarantine directory.

Unavailable cases are explicit in every report: #81 sandbox/output caps/M4
snapshot/integration latency, real concurrent workers/candidates, long
EvidenceBus receipt ancestry, and durable 100k-observation ingestion. M2 capture
is an existing mechanism, not a measurement of the new M4 secure snapshot.
These remain follow-up engineering cases after boundary qualification. No
successful small case establishes a maximum supported scale.

Retained run and source inventory live in
`experiments/preflight/engineering/`. These are engineering evidence and must
remain excluded from confirmatory, model degradation, heterogeneous-routing,
and paper reliability datasets. Controller fixture seconds are hand-authored
inputs; only `cases[*].samples_ns` are real elapsed measurements.
