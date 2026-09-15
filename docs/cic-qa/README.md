# CIC integration validation

These are public scripted controller fixtures, run on Python 3.12 with three
repeats of six cases per arm. Repeats reproduce scripted behavior; they are not
independent samples of model ability. Both infeasible cases remain unsuccessful
in the task-success denominator even when correctly blocked.

| Mode | Independently successful / scheduled | False acceptances | Calls |
| --- | ---: | ---: | ---: |
| residual | 3 / 18 | 12 | 30 |
| structural | 12 / 18 | 0 | 48 |
| cic | 12 / 18 | 0 | 36 |

Atomic grouping accounts for the success difference here. CIC preflight avoids
the 12 calls the grouping-only arm spends on the three UNSAT trials, with
additional host analysis overhead. The independent-domains case needs two calls
in each grouping mode versus one in baseline residual. The stronger-member-check
case stays blocked despite a SAT model. These outcomes establish fixture
behavior, not min-fill superiority, real model quality, or financial savings.
All cost-per-success estimates are unknown because the providers are scripted.

Validation:

- 32 CIC tests pass, including 150 finite models checked against an independent
  exhaustive oracle, privacy, atomicity, UNKNOWN, cache, receipt, and study tests.
- Full unittest discovery: 646 tests run, one skip, no failures or errors.
- Full pytest: 1,085 passed, 10 failed, 32 skipped. Unchanged baseline
  `800ea736308e3b0c091b81bf9cdb18c9786b9ac4` reproduces exactly those 10 failures
  (1,053 passed): nine bubblewrap namespace failures in this environment and
  one existing executable-bit assertion for `scripts/status_check.py`.
- A built wheel installed in a separate environment completed an 18-run study
  from outside the source checkout. Compilation and diff checks pass.
- No live provider was configured or tested.

[`validation.json`](validation.json) records hashes and exact failure IDs.
[`report.json`](report.json) retains outcomes, accounting, analysis overhead,
and the protocol binding. [`study-evidence.tar.gz`](study-evidence.tar.gz)
contains the complete 54-run journals, results, traces, schedule, environment,
protocol, and report. To regenerate the report without provider calls:

```bash
mkdir -p runs/cic-replay
tar -xzf docs/cic-qa/study-evidence.tar.gz -C runs/cic-replay
python -m residual study report runs/cic-replay/cic-study
```

The retained protocol pins runtime Python sources and tasks; it is a reproducible
fixture record, not signed execution attestation. Fresh executions require a
fresh lock whenever pinned code changes. See [the integration guide](../cic-integration.md)
for commands, architecture, source attribution, and limitations.
