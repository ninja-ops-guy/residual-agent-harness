# M5 independent audit — 2026-09-15

Historical review (not a fresh audit of the current merged M4 tree). Reviewed `main` at `800ea73` containing PR #80 (`e6385f7f11adf67455155461606bda367a08d107`).
Inspected the M4 integration interface at PR #81 head
`7ea194df0ecb76722610015491f4668b69619c05`; no M4 implementation was changed,
no branches were merged, and no live evaluations were run.

## Reproduced defects corrected here

1. `GoalEvaluator.evaluate` returned `complete=True` for a required result with
   status `"error"`, `"skipped"`, or `None`, provided its tree/root strings
   matched the enclosing result. An annotation did not enforce the enum.
   Results now normalize supported serialized enum values, reject unsupported
   states, and completion explicitly requires PASS. Adapters must map upstream
   non-PASS states deliberately; they cannot pass arbitrary status values through.
   The former controller could also crash on `.value` for such malformed states;
   the direct evaluator's false completion was reproduced independently.
2. Two results for the same required ID, first FAIL and then PASS, produced
   completion because the evaluator's dictionary silently selected the last.
   Factory result construction now rejects duplicate verification IDs.
3. An operator abort raised during synchronous `FactoryAdapter.run` was ignored
   if the returned result passed. Crossing the wall deadline had the same effect.
   Both are checked before completion, retaining the completed evidence record.

Validation: the original nine runtime tests passed before changes. After changes,
`python -m unittest discover -s tests -p 'test_loop_*.py' -v` passed 48 tests,
including five new regression tests. `git diff --check` passed.

## Remaining qualification blockers

| Requested guarantee | Evidence and limitation |
| --- | --- |
| Real Factory equivalence at one iteration | M5 defines a `FactoryAdapter` Protocol; no production implementation constructs `FactoryResultSet` from M4. The runtime tests use `FakeFactory`. There is no real Factory/M5 equivalence test. |
| Prefix consistency across iterations | The existing test compares the first synthetic iteration record for limits one and two. It does not exercise repeated real integrations, accepted-state mutation, evidence-head changes, or receipt duplication. |
| Residual deduplication | Residual IDs are unique within a result and equivalent attempts receive identical keys. Keys are advisory inputs to the adapter. The existing test confirms two dispatches with the same key, not reuse of a receipt-bound execution. |
| Accepted evidence provenance | Completion compares tree/root strings supplied by the adapter. It does not load or authenticate receipt references. M4 exposes `IntegrationOutcome.output_tree` and a signed integration receipt; the missing adapter must validate and project that authority before a production claim is supportable. |
| Abort prevents further integration | The new post-return check prevents late COMPLETE. A blocking Factory call still cannot observe the controller's abort callback or deadline during execution through the current Protocol. Cancellation/integration exclusion requires a cooperative production adapter boundary and a race test. |
| Host-owned versus adaptive evaluation | `LoopMode` names exist, but the controller has no mode selector and calls `next_intent` for escalation. Fixed host-owned and adaptive variants are not wired into the measured runner. |

Treat M5 as an implementation preview, with production integration unverified.
The local fixes close concrete controller defects; they do not qualify the M4
boundary or supply the missing real Factory adapter. PR #81 is now merged at
`de9c9fa`; after its exact merged-tree qualification is retained, build the adapter against that accepted interface and test exact
tree/root/receipt provenance, multi-iteration replay, deduplication, and abort
races before enabling M5 measured execution.
