# CIC structural integration

RESIDUAL can now use a host-authored finite constraint model to decide which
obligations must be proposed and accepted together. This is an opt-in extension
to the original obligation harness (`residual run` and `residual study`). It does
not modify Factory M2–M5, Command Station execution, or the gateway control plane.

The motivating failure is small but consequential: `a ∈ {1,2}`, `b ∈ {1}`, and
`a != b`. A scalar domain check can accept `a=1`, freezing a choice that makes
`b` impossible. Grouping changes the acceptance unit to `{a,b}`; only a complete
candidate satisfying both member checks and the declared joint constraints can
receive a receipt. The accepted result is `{a:2,b:1}`. Nothing already accepted
is rolled back or silently revised.

## Modes and authority

| Mode | Proposal and acceptance unit | Host structural search |
| --- | --- | --- |
| `residual` | Original obligations and original checks | None; optional `structure` metadata is inactive |
| `structural` | Connected components of the declared constraint graph | None; complete proposals receive exact joint checks |
| `cic` | Same connected components and exact joint checks | Deterministic min-fill analysis, then bounded feasibility preflight |

Both new modes retain residual local/expert routing, evidence pull, and the
existing provider call and byte budgets. Each component gets its own packet,
which can increase calls for independent work. The CIC arm adds analysis to the
same grouping comparator, making the incremental preflight cost visible.

Preflight outcomes describe **only the declared finite model**:

- **SAT:** a complete model assignment was found. This does not accept any value
  or establish that the original member verifiers will pass. The witness is not
  injected into provider packets or installed as an answer.
- **UNSAT:** exhaustive bounded search finished without a model assignment.
  That component is blocked before cache access or provider calls. Other ready
  components can continue; dependents remain blocked.
- **UNKNOWN:** the search node budget ran out. Normal proposal and complete
  verification continue. UNKNOWN alone grants neither acceptance nor an UNSAT claim.

An accurate model can detect incompatible choices before freezing them. It
cannot discover missing natural-language requirements or repair an inaccurate
formalization. A SAT model can still fail the original verifiers; the included
`stronger-member-check` fixture demonstrates this boundary.

## Declare a model and run

Add `"structure": "requirements"` to a task. The value names an existing artifact
whose entire text is the following strict JSON model (inline text or an ordinary
task-relative artifact file). Domain keys are original obligation IDs, and each
modeled obligation must declare this artifact in its `evidence` list.

```json
{
  "domains": {"a": [1, 2], "b": [1]},
  "different": [["a", "b"]]
}
```

Supported constraints are `different` pairs, strict `less_than` pairs, and
`sums` such as `{"keys":["a","b"],"equals":3}`. Domains contain unique integers;
booleans are rejected. Limits are 32 variables, 64 values per domain, 128 total
constraints, 32 distinct variables per sum, integer magnitudes at most 1,000,000,
and a 128,000-byte model artifact. Arbitrary Python, SAT subprocesses, and
model-generated verifier code are not accepted by this interface.

```bash
python -m residual run examples/cic/frozen-dead-end/task.json \
  --config examples/study-fixture.toml --mode cic --output runs/cic-demo
python -m residual verify-trace runs/cic-demo/trace.jsonl \
  --result runs/cic-demo/result.json
```

`examples/study-fixture.toml` uses scripted providers and needs no credentials.
Use a normal configured provider TOML for a live run. Set the deterministic
search budget in that same file:

```toml
[limits]
max_structural_nodes = 10000
```

The limit counts attempted variable assignments across **all components in one
run**, defaults to 10,000, and permits 0 through 1,000,000. Zero disables search
progress while retaining grouping and exact candidate checking. Model size
limits also bound graph analysis. This is a work counter, not a wall-clock
deadline or a guarantee about trusted custom verifier execution time.

Tasks without `structure` follow ordinary residual behavior in either new mode
and record `structural.applicable=false`. Malformed or unsupported declarations
raise a contract error before any provider call. Existing modes and fixtures
keep their existing acceptance semantics; select a structural mode explicitly
to enforce the additional model.

## Graph, checks, privacy, and receipts

Edges represent actual shared formal constraints, not merely dependency-DAG
edges or shared documents. Each sum's scope forms a clique. Connected components
are exact for this declared graph. Min-fill uses deterministic ties by fill
count, degree, then identifier. The returned certificate records the complete
elimination order, remaining neighbors, and fill edges at each step; its replay
rejects omitted, duplicated, unknown, or tampered steps.

`width_upper_bound` is the maximum remaining-neighbor count during elimination.
A valid order gives an upper bound on this graph's treewidth. A large reported
value does **not** prove high treewidth, model difficulty, a lower bound, or a
security guarantee. There is no width-based hard/easy classifier or calibrated
model portfolio in this implementation. Feasibility is a bounded depth-first
finite-domain search using reverse min-fill order and sound partial pruning;
it is not a tree-decomposition dynamic program or a new SAT algorithm.

The compiler creates ordinary obligations with generated `cicgroup.*` IDs.
Within a group it evaluates every original checker in dependency order, with
the original obligation, original parameters, scoped evidence, and projected
dependencies. All must return PASS. A partial object, extra member, invalid
joint assignment, exception, or UNKNOWN cannot produce a receipt. Original
verifier feedback remains subject to the group's privacy rules.

External prerequisite references become references to prerequisite groups.
Ungrouped obligations are wrapped as singleton groups so their checkers can
consume original dependency values. The resulting DAG is validated. A grouping
that produces a dependency cycle is currently rejected; the compiler does not
guess how to merge additional components or revise the original DAG.

Evidence is the union of declared member evidence. One private member, artifact,
or transitive prerequisite makes the whole group local-only. Provider packets
include member IDs, instructions, declared evidence IDs and dependency IDs;
checker parameters, grader data, search witnesses, and elimination certificates
are not added to packets. Normal evidence windows may contain the explicitly
declared model. Because that model can cover several components, its artifact
may expose other variables to an authorized worker: grouping narrows obligation
and artifact scope, not fields inside an artifact. Split sensitive material into
appropriately classified artifacts before enabling this feature.

Acceptance and cache entries bind the complete group value, member contracts,
model/evidence hashes, external parent receipts, compiler source hash, and member
verifier labels and available identities. Modern station receipts are issued
only when all member verifier identities and external modern parents support
them. Legacy verifiers retain the legacy receipt path; grouping does not confer
a missing implementation identity. Group cache hits are rechecked in full.
Changing any bound constraint, member contract, or verifier identity invalidates
reuse. The source registry is retained separately, so repeated runs do not
accumulate generated verifier registrations.

Member deterministic solvers are retained when **every member** of a group has
one; their combined result still passes the joint and member checks. If only
some members have solvers, that group uses normal proposals. Solving a subset
would prematurely freeze the very choices grouping is meant to protect.

## Results and controlled comparison

Ordinary `values`, `receipts`, `station_receipts`, and `unresolved` are keyed by
compiled group ID. The receipt certifies the entire group; it is not duplicated
or relabeled as individual member receipts. `original_values` projects accepted
groups back to original obligation IDs, and the study runner grades that
projection after the run. `structural.groups` provides the explicit mapping.
The trace's terminal result hash binds both the projection and analysis.

The existing accepted/total obligation metrics count compiled units. Additional
`original_accepted_obligations` and `original_total_obligations` count members.
Study reports now include analysis time, search nodes, UNSAT groups, blocked
original obligations, candidate rejections, and repeated dispatch calls. A
candidate rejection counts a failed/unknown verification unit (scalar in the
baseline, group in compiled modes). A repeated dispatch call contains at least
one ID dispatched earlier, including evidence pulls or a local-to-expert handoff;
it is not a count of model reasoning retries. Analysis time is separated from
remaining host overhead and stays included in overall latency/local occupancy.
Failed runs remain in the cost numerator and success denominator.

```bash
python scripts/build_cic_suite.py
python -m residual study freeze --suite examples/cic/suite.json \
  --config examples/study-fixture.toml --modes residual structural cic \
  --repeats 3 --seed 42 --output runs/cic.lock.json
python -m residual study run --lock runs/cic.lock.json --output runs/cic-study
python -m residual study report runs/cic-study
```

All arms use identical task files, provider implementations/configuration,
per-run call and byte budgets, independent post-run graders, and paired study
scheduling. The treatments deliberately change grouping and preflight. They
do not establish a budget for hidden gateway attempts or a live dollar cap.
The suite covers weak composition, frozen prerequisites, UNSAT, sums, independent
domains, and a model weaker than a member verifier. The original study suite is
unchanged. These are public scripted development fixtures; the evaluation split
does not make them externally held-out evidence. Retained results are in
[`cic-qa/`](cic-qa/), and CI uploads complete raw run directories.

No live quality, cost savings, or superiority claim follows from these fixtures.
In particular, compare `structural` against `cic` before attributing an improvement
to min-fill rather than to the stronger joint acceptance contract. Live model
routing thresholds and learned portfolio selection remain future experiments.

## Research provenance

The structural direction comes from Mike Olivares's CIC research, pinned to
[`cic-p-vs-np-research` at `005c7ad4`](https://github.com/ninja-ops-guy/cic-p-vs-np-research/tree/005c7ad4ef44eaadeae2c0c7e9d686e78429322d),
particularly [`width_utils.py`](https://github.com/ninja-ops-guy/cic-p-vs-np-research/blob/005c7ad4ef44eaadeae2c0c7e9d686e78429322d/redteam_harness/utils/width_utils.py).
RESIDUAL contains a small independent implementation of the graph and finite
constraint mechanics with stricter validation, deterministic ties, replayable
certificates, explicit budgets, and oracle-tested status semantics. It adds no
third-party dependency and copies no research solver into the trusted path.

The integration does not adopt the research portfolio's substring SAT parser
(where UNSAT can match SAT), heuristic difficulty thresholds, unverified
security estimates, or P-vs-NP proof claims. The contribution here is applied
controller engineering: make coupled choices explicit, keep acceptance atomic,
and measure the cost and limits of structural analysis.
