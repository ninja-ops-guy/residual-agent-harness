# SLM Telemetry Instrumentation (EXP-M6-SLM / SLM-06 pre-freeze)

Module: `residual.telemetry.slm` — schema: `residual/telemetry/slm/telemetry.schema.json`
(`schema_version: slm-telemetry-v0`). Governing: EVALUATION-PROTOCOL.md
(eval-protocol-v1.0.0), `slm-observation-v0`.

## What is captured
- **Per inference call** (`inference_call`): tokens in/out, `cost.latency_ms`,
  realized `cost.inference_usd` (measured tokens x pinned, versioned price
  table), `cost.energy_wh` and `power_w` only where measurable (NVML /
  nvidia-smi; otherwise null and flagged), `cost.frontier_calls`,
  `verification.status`, `schema_valid`, `confidence`.
- **Per routing decision** (`routing_decision`): selected model/worker AND
  the full alternative set available at decision time, each with a
  `counterfactual_cost_usd` labeled `estimate: true`.
- **Escalation** (`escalation_outcome`): required/taken/classification
  (slm-observation-v0 vocabulary) + correctness, feeding FNER/UER.
- **Operator time** (`operator_active`): `cost.operator_active_seconds`
  (frozen metric reports minutes).
- **Degradations** (`telemetry_degradation`): every fail-open degradation
  (unpriced model, power unavailable, sink failure) is logged; telemetry
  never blocks authoritative paths.

## Frozen rules honored
- Counterfactual costs are ALWAYS `estimate: true`; never reported as
  observed savings (§6). `Recorder.summary()` aggregates realized totals only.
- Unknown stays unknown: null `inference_usd` / `energy_wh` are never
  imputed (§8); unpriced models trigger a logged degradation.
- Energy is measured or reported "not measurable" — never estimated (§6).
- Price table is pinned and versioned (`price_table_version`,
  `price_source`, `price_date` on every event, per §6 cost procedure).

## Metric-name alignment
See `x-frozen-metric-alignment` in telemetry.schema.json: vmsr, fner, avr,
frontier_calls_avoided, uer, operator_active_minutes, latency,
schema_invalid_rate, ece, brier, throughput, vsms_per_dollar, vsms_per_watt.

## Integration
- `ai_providers.router.Router(slm_recorder=...)`: each attempt receipt
  (provider, model, usage, elapsed_ms) is recorded fail-open; receipts
  remain authoritative, telemetry is not.
- Station workers/services construct `Recorder(TelemetryConfig(enabled=...))`
  and `DecisionContextRecorder` and pass them into routers; config-gated off
  by default.

## Testing
`tests/test_slm_telemetry.py` uses fake clocks and fake power samplers; no
network or GPU required.
