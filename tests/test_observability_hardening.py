"""Track N tests: metrics completeness, SLOs, alert rules, trace<->receipt correlation."""
import pytest

from residual.core import ContractError
from residual.observability import (
    CorrelationContext,
    DEFAULT_ALERT_RULES,
    DEFAULT_SLOS,
    MetricsRegistry,
    SLODefinition,
    TraceReceiptIndex,
    check_registry_completeness,
    evaluate_alerts,
    evaluate_slos,
    new_span_id,
    new_trace_id,
)


def _registry():
    return MetricsRegistry()


# -- N-R1: completeness --------------------------------------------------------

def test_default_registry_is_complete():
    report = check_registry_completeness()  # DEFAULT_METRICS
    assert report.complete, [f.detail for f in report.failures]


def test_completeness_fresh_registry_roundtrips_through_exporter():
    reg = _registry()
    reg["residual_engine_executions_total"].inc(("engine", "success"))
    reg["residual_verification_duration_seconds"].observe(("overall",), 0.5)
    report = check_registry_completeness(reg)
    assert report.complete, [f.to_dict() for f in report.failures]


def test_completeness_detects_unregistered_metric():
    reg = _registry()
    del reg.metrics["residual_tokens_total"]  # bridge still references it
    report = check_registry_completeness(reg)
    assert not report.complete
    assert any(f.subject == "residual_tokens_total" for f in report.failures)


def test_completeness_detects_bad_histogram_buckets():
    reg = _registry()
    from residual.observability.metrics import Histogram
    reg.metrics["residual_bad_histogram"] = (Histogram(buckets=(1.0, 0.5)), ())
    report = check_registry_completeness(reg)
    assert any(f.check == "histogram_buckets" and not f.ok for f in report.findings)


# -- N-R2: SLOs -----------------------------------------------------------------

def test_default_slos_cover_required_kinds():
    kinds = {s.kind for s in DEFAULT_SLOS}
    assert kinds == {"latency", "error_rate", "receipt_integrity"}


def test_slo_definition_validation():
    with pytest.raises(ContractError):
        SLODefinition("x", "bogus", 0.9, "bad kind")
    with pytest.raises(ContractError):
        SLODefinition("x", "latency", 1.5, "bad target")


def test_evaluate_slos_vacuously_compliant_on_empty_registry():
    statuses = evaluate_slos(_registry())
    assert all(s.compliant for s in statuses)


def test_evaluate_slos_latency_breach():
    reg = _registry()
    for _ in range(10):
        reg["residual_verification_duration_seconds"].observe(("overall",), 30.0)
    statuses = evaluate_slos(reg)
    latency = next(s for s in statuses if s.kind == "latency")
    assert not latency.compliant and latency.observed == 0.0


def test_evaluate_slos_error_rate_breach_and_healthy():
    reg = _registry()
    reg["residual_engine_executions_total"].inc(("e", "failure"), 5)
    reg["residual_engine_executions_total"].inc(("e", "success"), 5)
    statuses = evaluate_slos(reg)
    err = next(s for s in statuses if s.kind == "error_rate")
    assert not err.compliant
    reg2 = _registry()
    reg2["residual_engine_executions_total"].inc(("e", "success"), 1000)
    assert next(s for s in evaluate_slos(reg2) if s.kind == "error_rate").compliant


def test_evaluate_slos_receipt_integrity():
    reg = _registry()
    reg["residual_receipts_issued_total"].inc(("valid",))
    statuses = evaluate_slos(reg)
    assert next(s for s in statuses if s.kind == "receipt_integrity").compliant
    reg["residual_receipts_issued_total"].inc(("invalid",))
    statuses = evaluate_slos(reg)
    integrity = next(s for s in statuses if s.kind == "receipt_integrity")
    assert not integrity.compliant and integrity.observed == 0.5


def test_slo_definitions_serializable():
    for slo in DEFAULT_SLOS:
        doc = slo.to_dict()
        assert doc["slo_id"] and doc["kind"]


# -- N-R3: alert rules ----------------------------------------------------------

def test_alert_rule_validation():
    from residual.observability import AlertRule
    with pytest.raises(ContractError):
        AlertRule("a", "scream", "m", ">", 1, "e", "s")
    with pytest.raises(ContractError):
        AlertRule("a", "page", "m", "!=", 1, "e", "s")


def test_no_alerts_on_healthy_registry():
    assert evaluate_alerts(_registry()) == []


def test_integrity_alert_pages_on_invalid_receipt():
    reg = _registry()
    reg["residual_receipts_issued_total"].inc(("forged",))
    events = evaluate_alerts(reg)
    page = next(e for e in events if e.alert_id == "alert.receipt.integrity")
    assert page.severity == "page"


def test_hitl_backlog_alert():
    reg = _registry()
    reg["residual_hitl_challenges_pending"].set((), 51)
    events = evaluate_alerts(reg)
    assert any(e.alert_id == "alert.hitl.backlog" for e in events)


def test_slo_breach_raises_ticket_event():
    reg = _registry()
    reg["residual_verification_duration_seconds"].observe(("overall",), 99.0)
    statuses = evaluate_slos(reg)
    events = evaluate_alerts(reg, slo_statuses=statuses)
    assert any(e.alert_id.startswith("alert.slo.") and e.severity == "ticket" for e in events)


def test_alert_rules_exportable():
    for rule in DEFAULT_ALERT_RULES:
        assert rule.expr and rule.summary and rule.to_dict()["alert_id"]


# -- N-R4: trace <-> receipt correlation ---------------------------------------

HASH = "a" * 64


def test_context_start_and_child_span():
    ctx = CorrelationContext.start(task_id="t1")
    assert len(ctx.trace_id) == 32 and len(ctx.span_id) == 16
    child = ctx.child_span()
    assert child.trace_id == ctx.trace_id and child.span_id != ctx.span_id


def test_traceparent_roundtrip():
    ctx = CorrelationContext.start().bind_receipt(HASH)
    parsed = CorrelationContext.from_traceparent(ctx.traceparent)
    assert parsed.trace_id == ctx.trace_id and parsed.span_id == ctx.span_id
    with pytest.raises(ContractError):
        CorrelationContext.from_traceparent("garbage")


def test_context_validation():
    with pytest.raises(ContractError):
        CorrelationContext(trace_id="bad", span_id=new_span_id())
    with pytest.raises(ContractError):
        CorrelationContext(trace_id=new_trace_id(), span_id="bad")
    with pytest.raises(ContractError):
        CorrelationContext(trace_id=new_trace_id(), span_id=new_span_id(),
                           receipt_hash="not-a-hash")


def test_bind_receipt_immutable_and_conflict_checked():
    ctx = CorrelationContext.start()
    bound = ctx.bind_receipt(HASH)
    assert ctx.receipt_hash is None and bound.receipt_hash == HASH
    assert bound.bind_receipt(HASH).receipt_hash == HASH  # idempotent
    with pytest.raises(ContractError):
        bound.bind_receipt("b" * 64)


def test_log_fields_joinable():
    ctx = CorrelationContext.start(task_id="t7").bind_receipt(HASH)
    fields = ctx.log_fields()
    assert fields == {"trace_id": ctx.trace_id, "span_id": ctx.span_id,
                      "receipt_hash": HASH, "task_id": "t7"}


def test_index_bidirectional_lookup():
    index = TraceReceiptIndex()
    ctx = CorrelationContext.start().bind_receipt(HASH)
    child = ctx.child_span()
    index.record(ctx)
    index.record(child)
    assert index.receipt_for_trace(ctx.trace_id) == HASH
    assert index.traces_for_receipt(HASH) == [ctx.trace_id]
    assert index.spans_for_trace(ctx.trace_id) == [ctx.span_id, child.span_id]
    assert index.receipt_for_trace(new_trace_id()) is None
    assert index.traces_for_receipt("f" * 64) == []


def test_index_rejects_unbound_and_conflicting():
    index = TraceReceiptIndex()
    with pytest.raises(ContractError):
        index.record(CorrelationContext.start())
    ctx = CorrelationContext.start().bind_receipt(HASH)
    index.record(ctx)
    with pytest.raises(ContractError):
        index.record(CorrelationContext(trace_id=ctx.trace_id, span_id=new_span_id(),
                                        receipt_hash="c" * 64))
