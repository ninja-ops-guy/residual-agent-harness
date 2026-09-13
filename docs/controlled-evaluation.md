# Controlled evaluation and contract stress tests

RESIDUAL now has a frozen experiment runner for its original obligation harness.
It measures independently graded outcomes across the existing routing policies
and two new ablations. It does not establish a live-model efficiency result or
extend the station's software-task verifier to the obligation algorithm.

## Run the reproducible fixture study

From the repository root, with Python 3.11+ and no additional dependencies:

```bash
python -m residual study freeze \
  --suite examples/study/suite.json \
  --config examples/study-fixture.toml \
  --repeats 3 --seed 42 \
  --max-total-calls 2000 --max-total-remote-bytes 20000000 \
  --output runs/contract-study.lock.json
python -m residual study run \
  --lock runs/contract-study.lock.json --output runs/contract-study
python -m residual study report runs/contract-study
```

The runner refuses to overwrite the lock or run directory. Use a fresh name for
each experiment. Changing source, task contents, grader inputs, provider config,
or limits requires a new lock. A lock is a content commitment, not a signature
or independent preregistration.

The default experiment schedules **144 trials**: six evaluation cases, eight
policies, three repeats. A seventh case belongs exclusively to the development
split. This partition exercises family separation; every bundled case is public,
author-known development material. These are not independent held-out results.

## Independent acceptance and grading

The harness checks proposals using its normal host verifiers. Once a run ends,
the study grader examines the final accepted values using a separate grader file.
It never adds hidden grading answers to retry feedback or model packets.

| Outcome | Meaning |
| --- | --- |
| Controller success | Every declared obligation passed its registered check |
| Independent success | Controller success and the separate final grader passed |
| False acceptance | Controller reported success but independent grading failed |
| Partial/blocked | The controller could not establish all obligations |
| Error / not recorded / not run | Remains in the scheduled denominator; comparison is incomplete |

Supported graders are exact structured values, bounded integer-expression test
pairs, and joint finite-assignment constraints. Expression candidates use an AST
interpreter restricted to integers, `x`, unary signs, `+`, `-`, `*`, `//`, `%`, and
parentheses. Calls, attributes, exponentiation, arbitrary execution and unbounded
expressions are rejected. This is expression synthesis, not arbitrary code repair.

The grader path cannot also be a task artifact. No process sandbox is claimed:
trusted Python plugins or a worker with repository filesystem access could read
grader files. The current locked runner accepts only bundled plugins, whose code
is pinned. A future arbitrary-code suite needs a separately isolated grading
environment and independently authored hidden tests.

## What the contract stress cases demonstrate

| Case | Deliberate condition | Expected diagnostic value |
| --- | --- | --- |
| Quadratic expression | Visible examples allow an incorrect generalization | Hidden examples detect overfitting despite controller acceptance |
| Weak composition | Per-variable domain checks omit a cross-variable constraint | Independent joint grading detects an incorrect accepted combination |
| Frozen dead end | A prerequisite admits a choice that prevents a dependent solution | Controller reports partial progress; it cannot overwrite the accepted prerequisite |
| Joint choice | Coupled decisions share one obligation and joint verifier | A valid proposal can be checked and accepted atomically |

The tests also demonstrate explicit host revision: narrowing the prerequisite's
domain changes its binding, invalidates dependent reuse, and preserves an
unrelated checked cache entry. This uses the existing snapshot/cache protocol.
It is not automatic semantic dependency discovery or model-authorized rollback.

For tasks needing backtracking, author a joint obligation for the coupled search,
or create a new host-authorized task snapshot with revised constraints. Include
all relevant evidence and prerequisites in the contract. Freezing an incomplete
contract does not make it complete; a terminating loop does not prove convergence.

## Policies and comparability

| Policy | Controlled difference |
| --- | --- |
| `full_cloud` | Expert tier with full eligible context; no local solver/model stage |
| `cascade` | Local work followed by expert repair with full eligible context |
| `residual` | Adaptive scoped context and evidence pull |
| `residual_fixed` | Fixed seed windows with evidence pull |
| `no_pull` | Fixed seed windows without evidence pull; compare directly to `residual_fixed` to isolate pull |
| `no_feedback` | Adaptive residual with verifier feedback removed; checks still run |
| `no_solvers` | Adaptive residual with deterministic solvers disabled; checks still run |
| `local_only` | No expert tier |

All runs use identical task/grader snapshots, configured model identities and
per-run limits, with application caches disabled. The two new ablations preserve
the default behavior of existing modes. A fixture suite may be insensitive to an
ablation: for example, its tasks may have no declared solvers. Equal fixture
results are not evidence that the mechanism has no value on real workloads.

A seeded schedule shuffles case/repeat blocks and policy order inside each block.
The seed does not control provider sampling. Repeats are paired by case ID and
repeat index. Descriptive success-difference intervals resample whole families,
keeping repeated trials together. Small family counts and repeated analysis limit
interpretation; the report never automatically declares equivalence or superiority.

The `full_cloud` policy is an internal expert-only controller baseline, not a
reimplementation of a leading standalone coding agent. RouteLLM/DeLM or other
external baselines still need matched task/tool/budget adapters before making a
state-of-the-art claim.

## Accounting and failure evidence

`calls.jsonl` records a reservation before each transport invocation and a
completion afterward. Failed calls keep their reservation. Study-wide call and
remote-request-byte caps persist across cases, modes and repeats. They bound
top-level adapter calls, not hidden gateway work, dollar spend, or hung code.
Existing per-run reservations remain in force.

`runs.jsonl` records every finished or skipped run; `lifecycle.jsonl` records start
and finish events. Each completed run keeps its hash-bound result and normal
trace. `report` checks their binding, checks call counts against run receipts, and
rejects missing/duplicated/mismatched evidence rather than treating it as free work.
Missing call completions remain unknown; missing run records remain in the
denominator. A torn JSONL record requires diagnosis rather than silent truncation.
Report recovery does not rerun models or side effects, and does not resume jobs.

The report includes local/remote usage separately, cache-token subtotals, unknown
usage counts, all-call costs, verification/solver/grading/provider elapsed times,
remaining host overhead, and median/p95 run latency. Reported token subtotals can
be zero with incomplete coverage; inspect `usage_complete`. Per-call billed
reasoning tokens are not independently exposed by the existing usage contract.

Costs use supplied provider prices and an optional local host occupancy rate:

```text
total modeled cost = all known inference fees
                   + all run elapsed hours × supplied local hourly rate
cost per success = total modeled cost / independent successes
```

Failures contribute to the numerator. Zero successes yield an undefined ratio.
Missing prices, missing remote receipts, incomplete runs or a missing local rate
keep total cost unknown. Scripted runs never produce a real-dollar total.
For local placements without provider prices, the separate API fee is zero; the
local resource estimate still requires a rate. Configure that rate to exclude
any separately priced inference fees to avoid double counting. It includes host
occupancy while waiting for remote calls and is not measured energy consumption.
Engineering effort, provider invoice reconciliation, hidden upstream attempts,
and unsupported pricing tiers remain outside the measured cost scope.

## Run with actual models

1. Copy `examples/ollama-cloud.toml` to ignored `config.local.toml` and configure
   the installed local model, expert endpoint/model, environment key reference,
   and actual provider prices. Add this top-level entry **before** TOML tables:
   `plugins = ["residual.study_tasks:register"]`.
2. First freeze a small infrastructure smoke test with `--modes cascade residual
   --repeats 1 --max-total-calls 100`. Running it invokes the configured models.
3. Inspect transport/usage coverage and independent outcomes. A successful smoke
   test establishes interoperability on those inputs, not efficiency superiority.
4. Have a separate task author supply new task families and private grader files,
   with no family appearing in both splits. Label provenance honestly in the suite.
5. Freeze the confirmatory suite, models, budgets and pricing before evaluation.
   Repeat across model pairs; report failed runs, intervals and limitations. Record
   authoring effort separately. A lower cost with worse quality does not establish
   the proposed benefit.

Example live freeze after configuration (choose an appropriate local hourly rate):

```bash
python -m residual study freeze \
  --suite examples/study/suite.json --config config.local.toml \
  --modes cascade residual --repeats 1 --max-total-calls 100 \
  --output runs/live-smoke.lock.json
python -m residual study run \
  --lock runs/live-smoke.lock.json --output runs/live-smoke
```

No endpoint, key, model download, live interoperability, or real savings is implied
by the fixture study. Full source validation remains `python -m unittest discover
-s tests -v`. The included CI also runs the installed `study` command without keys.
