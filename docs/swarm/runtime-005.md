# SPEC-SWARM-RUNTIME-005 — Engine + Async Runtime Integration

Branch: `swarm/runtime-005-engine-async`

## Summary

Unifies heterogeneous execution engines behind the existing
`residual.engines.protocol.ExecutionEngine` contract and adds async-runtime
guarantees in the new `residual/runtime/` package. Existing engine adapters
(SDK, CrewAI, LangGraph, provider bridge) and async components
(`residual/async_io/`) are reused/wrapped, not duplicated.

## Modules

| Module | Purpose |
|---|---|
| `residual/runtime/adapters.py` | RUN-R1: `LocalDeterministicEngine` (local fixture engine) + `SDKFunctionEngine` (wraps existing `ClaudeSDKEngine`/`OpenAIAssistantsEngine` around a callable) |
| `residual/runtime/router.py` | RUN-R2/R3: `RuntimeCapabilityRouter` — fresh pre-dispatch capability probe, fail-closed `RoutingError`, local-preferred with name/version tie-break (delegates to `engines.CapabilityRouter`) |
| `residual/runtime/records.py` | RUN-R4: `EngineExecutionRecord` binds engine name/version/provider into receipts and evaluation records (hash-covered) |
| `residual/runtime/policy.py` | RUN-R5: `PolicyAuthority` — strips provider-native HITL/autonomy, treats provider approval claims as advisory-only, fails closed on authority-metadata leaks |
| `residual/runtime/telemetry.py` | RUN-R6: `FreshnessGuard` — clock-injectable staleness guard; stale/absent reads return `UNKNOWN` with the value suppressed |
| `residual/runtime/cancellation.py` | RUN-R7: `CancellationController` — abort propagates to tracked async tasks within a `CancellationBudget`; budget overrun is fail-closed with survivors listed |
| `residual/runtime/sinks.py` | RUN-R8: `BufferedObservationSink` — buffered async flush; `close()` performs a durable (fsync'd JSONL) terminal flush |
| `residual/runtime/conformance.py` | RUN-R9: shared adapter conformance checks run identically against every adapter |
| `residual/runtime/evidence.py` | Gates B/C: deterministic scenario runner + artifact builder + reproduction check |

## Requirements → tests traceability

| Req | Tests (tests/swarm/test_runtime005.py) |
|---|---|
| RUN-R1 | `test_r1_adapters_conform_to_execution_engine_protocol`, `test_r1_sdk_wrapper_delegates_to_existing_sdk_adapter`, `test_r1_local_engine_is_deterministic` |
| RUN-R2 | `test_r2_router_probes_declared_capability_before_routing`, `test_r2_router_fails_closed_on_capability_mismatch`, `test_r2_router_rejects_unhealthy_engine_at_registration`, `test_r2_router_fails_closed_when_engine_degrades_after_registration` |
| RUN-R3 | `test_r3_local_preferred_when_capability_equivalent`, `test_r3_deterministic_tie_break_for_equal_scores` |
| RUN-R4 | `test_r4_engine_metadata_enters_execution_record_and_receipt`, `test_r4_provider_engine_metadata_includes_provider_name` |
| RUN-R5 | `test_r5_sanitize_disables_provider_native_autonomy_and_hitl`, `test_r5_provider_authority_metadata_never_overrides_residual_policy`, `test_r5_residual_deny_and_escalate_are_authoritative`, `test_r5_apply_fails_closed_on_provider_authority_leak` |
| RUN-R6 | `test_r6_fresh_read_returns_current_with_age`, `test_r6_stale_read_returns_unknown_and_suppresses_value`, `test_r6_absent_telemetry_is_unknown`, `test_r6_async_telemetry_client_stale_read_is_unknown` |
| RUN-R7 | `test_r7_abort_propagates_within_budget`, `test_r7_budget_exceeded_is_fail_closed_with_survivors`, `test_r7_abort_with_no_active_operations_is_clean` |
| RUN-R8 | `test_r8_buffered_async_flush_delivers_events`, `test_r8_terminal_flush_is_durable`, `test_r8_emit_after_close_is_rejected`, `test_r8_sink_satisfies_run_coordinator_cancel_contract` |
| RUN-R9 | `test_r9_adapter_conformance_suite_passes[local-deterministic]`, `test_r9_adapter_conformance_suite_passes[claude-sdk]`, `test_r9_same_conformance_checks_for_all_adapters`, `test_r9_conformance_detects_contract_violation` |
| Faults/Gates B–C | `test_fault_scenarios_deterministic_fail_closed`, `test_gate_c_reproduction_matches_evidence_hash` |

## Acceptance

- Two adapters (`local-deterministic`, `claude-sdk` via `SDKFunctionEngine`)
  pass the SAME 12-check conformance suite (RUN-R9 parametrized test).
- Stale telemetry reads deterministically return `UNKNOWN` with the value
  suppressed; cancellation beyond budget deterministically reports
  `cancelled=False` + survivor list (fail closed).
- Evidence artifact: `evidence/runtime/runtime005_evidence.json`
  (schema `residual.swarm.runtime005.evidence.v1`) contains commit/tree
  identity, conformance results, fault-scenario raw observations, and a
  `scenario_hash` reproduced by `runtime.evidence.reproduce` (Gate C).

## Regeneration

```bash
python3 -m pytest tests/swarm/ -q
python3 -c "import json; from residual.runtime import evidence; \
print(json.dumps(evidence.build_artifact(), indent=2, sort_keys=True))" \
  > evidence/runtime/runtime005_evidence.json
```
