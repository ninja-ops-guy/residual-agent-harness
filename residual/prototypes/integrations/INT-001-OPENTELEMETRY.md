# INT-001: OpenTelemetry Integration Spec

## Metadata
- **ID**: INT-001
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-002 (telemetry), IE-001 (lifecycle model)
- **Protected boundaries**: Receipt semantics, verifier authority, M4 evidence, integration authority, disclosure policy, provider boundaries, scheduling authority

## Problem

RESIDUAL's telemetry is proprietary. It cannot be observed with standard tools (Grafana, Jaeger, Datadog), alerted on with standard monitors, or debugged with standard tracers. This makes RESIDUAL a closed system that requires custom tooling for basic observability.

## Goal

Export RESIDUAL's 11-stage lifecycle and metrics through OpenTelemetry (OTel) without changing execution semantics. Make RESIDUAL a first-class citizen in the observability ecosystem.

## Non-Goals

- Making OTel spans/metrics canonical evidence or acceptance authority

- Replacing RESIDUAL's internal telemetry with OTel
- Changing receipt semantics or verifier authority
- Adding new acceptance logic to the OTel exporter
- Supporting every OTel backend (Grafana, Jaeger, etc. are out of scope for the spec)

## Design

### Span Mapping

Each of the 11 lifecycle stages maps to an OTel span:

| Stage | OTel Span Name | Span Kind |
|---|---|---|
| mission_submit | residual.mission.submit | INTERNAL |
| planning | residual.mission.planning | INTERNAL |
| scheduling | residual.mission.scheduling | INTERNAL |
| queue_wait | residual.mission.queue_wait | INTERNAL |
| context_packaging | residual.mission.context_packaging | INTERNAL |
| worker_execution | residual.worker.execution | SERVER |
| evidence_publication | residual.evidence.publication | INTERNAL |
| verification | residual.verifier.verification | SERVER |
| integration_queue | residual.integration.queue | INTERNAL |
| integration | residual.integration.execution | SERVER |
| terminal | residual.mission.terminal | INTERNAL |

### Span Attributes

Every span carries:
- `residual.run_id` — unique run identifier
- `residual.obligation_id` — obligation identifier
- `residual.task_class` — task classification
- `residual.topology` — execution topology
- `residual.engine_class` — engine class (if known)
- `residual.source_commit` — source commit hash
- `residual.outcome` — PASS / FAIL / UNKNOWN / SATURATED
- `residual.evidence_class` — simulated / replayed / live

### Metrics Mapping

| IE Metric | OTel Metric Name | Type |
|---|---|---|
| attempt_throughput | residual.throughput.attempt | Gauge |
| accepted_goodput | residual.throughput.accepted | Gauge |
| integrated_goodput | residual.throughput.integrated | Gauge |
| ttfw_ns | residual.latency.ttfw | Histogram |
| tte_ns | residual.latency.tte | Histogram |
| tta_ns | residual.latency.tta | Histogram |
| tti_ns | residual.latency.tti | Histogram |
| worker_utilization | residual.pressure.worker_utilization | Gauge |
| verifier_utilization | residual.pressure.verifier_utilization | Gauge |
| queue_depth | residual.pressure.queue_depth | Gauge |

### Context Propagation

OTel trace context (trace_id, span_id) propagates through the lifecycle:
- Parent span: mission_submit
- Child spans: all subsequent stages
- Baggage: run_id, obligation_id, mission_id

### Exporter Configuration

```yaml
otel:
  enabled: true
  endpoint: "localhost:4317"  # OTLP gRPC
  protocol: grpc
  headers:
    authorization: "Bearer ${OTEL_TOKEN}"
  resource:
    service.name: "residual"
    service.version: "${RESIDUAL_VERSION}"
    deployment.environment: "${ENV}"
```

## Interfaces

### TelemetryOTelExporter

```python
class TelemetryOTelExporter:
    """Exports TelemetryCollector events to OTel."""

    def __init__(self, collector: TelemetryCollector, config: OTelConfig):
        ...

    def export_spans(self) -> int:
        """Export all collected spans. Returns count exported."""
        ...

    def export_metrics(self) -> int:
        """Export all collected metrics. Returns count exported."""
        ...

    def flush(self) -> None:
        """Flush any buffered spans/metrics."""
        ...
```

### OTelConfig

```python
@dataclass(frozen=True)
class OTelConfig:
    enabled: bool
    endpoint: str
    protocol: str  # "grpc" | "http"
    headers: dict[str, str]
    resource: dict[str, str]
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Span mapping: 11 stages produce 11 spans with correct names |
| T2 | Span attributes: all required attributes present on every span |
| T3 | Parent-child: mission_submit is parent of all subsequent spans |
| T4 | Metrics: all IE metrics exported with correct names and types |
| T5 | Non-interference: OTel export does not change execution (T1 of IE-002) |
| T6 | Flush: buffered spans/metrics flushed on demand |
| T7 | Disabled: OTel disabled produces no spans/metrics |

## Failure Modes

| Failure | Behavior |
|---|---|
| OTel endpoint unreachable | Log warning, continue execution (telemetry is non-critical) |
| Span export fails | Buffer and retry with exponential backoff |
| Metric export fails | Drop/buffer according to configured telemetry policy; canonical RESIDUAL evidence is unaffected |
| Invalid config | Fail closed at startup (refuse to start with bad config) |

## Exit Criteria

- [ ] All 11 stages export as OTel spans
- [ ] All IE metrics export as OTel metrics
- [ ] Non-interference proven (T5)
- [ ] Tests T1-T7 pass
- [ ] Documentation updated
- [ ] Q11: Maintainer attestation per #168
