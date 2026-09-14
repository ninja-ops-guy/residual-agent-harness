# Assurance ↔ Factory Runtime Integration

Residual assurance can now execute both `FIXED_SWARM` and genuinely adaptive, multi-wave `DYNAMIC_SWARM` strategies against the bounded Linux `FactoryRuntime`, while keeping Station verification and M3 evidence authoritative.

## Fixed swarm flow

1. `AdaptiveAssuranceRuntime` chooses `FIXED_SWARM` and a VCM engine.
2. The caller supplies an approved `FactoryExecutionPlan`, `FrozenPlan`, and at least two `WorkerContract` templates through a `FactoryFixedSwarmJob`.
3. Every `WorkerContract.engine_hint` must equal the selected engine id (`name@version`).
4. The selected engine authors raw Python source for each worker on the trusted host. Unknown token usage or usage above that worker's contract budget fails before Factory dispatch.
5. The exact engine output is passed to `FactoryRuntime.run_many`; fenced prose is rejected rather than rewritten.
6. Factory executes each source under its existing worktree, broker, lease, watchdog, memory, syscall and tool boundaries.
7. The adapter returns a deterministic content-hash-only manifest of quarantined `RuntimeResult` candidates. It does not merge candidates.
8. The normal assurance verifier evaluates the manifest. VCM reputation is updated only because the adapter explicitly binds `engine_attribution` to the engine that authored every worker.

## Dynamic swarm flow

`FactoryDynamicSwarmExecutor` uses the same frozen plan, contracts, engine attribution, authoring-budget checks and sandbox boundary. The difference is scheduling.

All worker contracts and model-authored sources are frozen before the first worker is dispatched. A host-owned `DynamicSwarmPolicy` is then called between completed waves with:

- the remaining approved worker templates; and
- the completed `RuntimeResult` values from earlier waves.

The policy returns `DynamicWaveDecision(batch_size, capacity)`. The executor can therefore increase or decrease both the next wave size and its concurrency based on observed prior results. It cannot mutate contracts, invent workers, raise a worker's resource limits, or change a running wave.

This is real adaptive orchestration rather than a renamed fixed `run_many` invocation. Adaptation happens only at a deterministic host-controlled boundary between terminal waves.

```python
def policy(remaining, completed):
    if not completed:
        return DynamicWaveDecision(batch_size=1, capacity=1)
    return DynamicWaveDecision(
        batch_size=len(remaining),
        capacity=min(4, len(remaining)),
    )

job = FactoryDynamicSwarmJob(base=fixed_job, policy=policy)
executor = FactoryDynamicSwarmExecutor(factory_runtime, build_dynamic_job)
assurance.register_strategy_executor(ExecutionStrategy.DYNAMIC_SWARM, executor)
```

The `EngineResult.raw_metadata["factory_waves"]` record binds the observed wave number, batch size, capacity, attempt ids and terminal statuses.

## M3 admission

Quarantined runtime success is still not authoritative evidence. `FactoryM3Admission` provides the explicit bridge to the existing trusted Station path.

For every worker it requires a real `VerificationDecision` from a caller-supplied trusted decision provider. It then calls `FactoryStationIssuer.issue`, which verifies the exact contract/result identity, acceptance criteria and artifact hashes before creating a Station-signed `WorkerReceipt` and atomically appending that worker's artifact bytes to the Evidence Bus.

M3 admission is intentionally append-only per worker, not batch-transactional. If a later worker is rejected, any earlier valid signed receipts remain authoritative and are not rolled back. Worktree purge is stricter: no requested candidate is purged until the entire admission call succeeds, so a partially admitted run remains inspectable and retryable.

When a dynamic executor is configured with M3 admission, its result metadata changes from:

```text
candidate_state = quarantined
station_receipt_issued = false
```

to:

```text
candidate_state = m3-admitted
station_receipt_issued = true
station_receipt_hashes = (...)
```

The aggregate assurance verifier is **not** silently converted into a Station decision. Per-worker Station verification remains a distinct trusted boundary.

## Attribution rule

Generic non-direct strategy executors do not automatically update an engine's VCM profile. A non-direct `EngineResult` must include:

```python
raw_metadata={"engine_attribution": "<selected-name>@<selected-version>"}
```

and the value must exactly match the market decision. DIRECT execution remains inherently attributable.

This prevents a swarm, ensemble, external scheduler, or hand-written executor from accidentally crediting a model for work it did not perform.

M3 receipts continue to identify the actual Factory execution backend (`brokered-python`). Model authoring provenance stays in assurance metadata instead of overloading or silently changing the signed WorkerReceipt schema.

## Security boundary

These adapters deliberately do **not**:

- give model-authored source ambient filesystem or network access;
- bypass `FrozenPlan` or `WorkerContract` checks;
- reinterpret Markdown-fenced model output as code;
- run workers when model token usage is unknown or over budget;
- let a dynamic policy mutate a running attempt or create unapproved workers;
- infer Station acceptance from a runtime `CANDIDATE` state;
- infer Station acceptance from the aggregate assurance verifier;
- merge candidate commits as part of assurance execution; or
- rewrite the existing M3 receipt schema to make the authoring model look like the sandbox execution engine.

## Registration

```python
fixed = FactoryFixedSwarmExecutor(factory_runtime, build_fixed_job)
assurance.register_strategy_executor(ExecutionStrategy.FIXED_SWARM, fixed)

dynamic = FactoryDynamicSwarmExecutor(
    factory_runtime,
    build_dynamic_job,
    admission=FactoryM3Admission(factory_runtime, station_issuer, station_decision_for),
)
assurance.register_strategy_executor(ExecutionStrategy.DYNAMIC_SWARM, dynamic)
```

Job builders remain responsible for supplying contracts already bound to the approved Factory plan and selected engine id. Every adapter validates those bindings again before authoring, dispatch or admission.
