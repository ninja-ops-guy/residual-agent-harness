# Assurance ↔ Factory Runtime Integration

`FactoryFixedSwarmExecutor` connects the adaptive assurance layer to the existing Linux `FactoryRuntime` without weakening either boundary.

## Execution flow

1. `AdaptiveAssuranceRuntime` chooses `FIXED_SWARM` and a VCM engine.
2. The caller supplies an already-approved `FactoryExecutionPlan`, `FrozenPlan`, and at least two `WorkerContract` templates through a `FactoryFixedSwarmJob`.
3. Every `WorkerContract.engine_hint` must equal the selected engine id (`name@version`).
4. The selected engine authors raw Python source for each worker on the trusted host. Unknown token usage or usage above that worker's contract budget fails before Factory dispatch.
5. The exact engine output is passed to `FactoryRuntime.run_many`; fenced prose is rejected rather than rewritten.
6. Factory executes each source under its existing worktree, broker, lease, watchdog, memory, syscall and tool boundaries.
7. The adapter returns a deterministic content-hash-only manifest of the quarantined `RuntimeResult` candidates. It does not merge candidates and does not issue Station receipts.
8. The normal assurance verifier evaluates the manifest. VCM reputation is updated only because the adapter explicitly binds `engine_attribution` to the engine that authored every worker.

## Attribution rule

Generic non-direct strategy executors no longer automatically update an engine's VCM profile. A non-direct `EngineResult` must include:

```python
raw_metadata={"engine_attribution": "<selected-name>@<selected-version>"}
```

and the value must exactly match the market decision. DIRECT execution remains inherently attributable.

This prevents a swarm, ensemble, external scheduler, or hand-written executor from accidentally crediting a model for work it did not perform.

## Security boundary

The adapter deliberately does **not**:

- give model-authored source ambient filesystem or network access;
- bypass `FrozenPlan` or `WorkerContract` checks;
- reinterpret Markdown-fenced model output as code;
- run workers when model token usage is unknown or over budget;
- merge candidate commits;
- manufacture M3/Station verification receipts;
- enable `DYNAMIC_SWARM` resizing.

`DYNAMIC_SWARM` remains a separate integration because `FactoryRuntime.run_many` currently accepts a fixed capacity for one invocation. Claiming dynamic resizing on top of that API would overstate the runtime semantics.

## Registration

```python
executor = FactoryFixedSwarmExecutor(factory_runtime, build_job)
assurance.register_strategy_executor(ExecutionStrategy.FIXED_SWARM, executor)
```

`build_job(engine, task, context)` is responsible for returning contracts already bound to the approved Factory plan and to the selected engine id. The adapter validates those bindings again before authoring or dispatch.
