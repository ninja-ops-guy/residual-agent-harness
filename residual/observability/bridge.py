from __future__ import annotations
from .metrics import MetricsRegistry
class ObservationMetricsBridge:
    def __init__(self,registry:MetricsRegistry): self.registry=registry
    def __call__(self,kind,payload):
        event=payload.get("event")
        if kind=="llm.response": self.registry["residual_tokens_total"].inc((payload.get("provider","unknown"),),payload.get("usage",{}).get("total_tokens",0) or 0)
        elif kind=="custom" and event=="cache_hit": self.registry["residual_tokens_saved"].inc((str(payload.get("cache_hit",True)).lower(),),payload.get("tokens_saved",0) or 0)
        elif kind=="state.transition" and payload.get("to_state")=="brake_tripped": self.registry["residual_brake_trips_total"].inc((payload.get("brake_name","unknown"),payload.get("action","unknown")))
        elif kind=="custom" and event=="verification_report": self.registry["residual_verification_duration_seconds"].observe((payload.get("check_name","overall"),),(payload.get("duration_ms",0) or 0)/1000.0)
        elif kind=="tool.failed" and payload.get("reason")=="quarantine_denied": self.registry["residual_quarantine_denials_total"].inc((payload.get("policy_name","unknown"),))
        elif kind=="checkpoint" and event in {"hitl_challenge_created","hitl_challenge_resolved"}: self.registry["residual_hitl_challenges_pending"].inc((),1 if event.endswith("created") else -1)
        elif kind=="checkpoint" and event=="receipt_issued": self.registry["residual_receipts_issued_total"].inc((payload.get("verdict","unknown"),))
        elif kind=="custom" and event=="engine_result": self.registry["residual_engine_executions_total"].inc((payload.get("engine_name","unknown"),payload.get("outcome","unknown")))


class ReliabilityMetricsProjection:
    """Project retained reliability observations into bounded metrics."""

    def __init__(self, registry: MetricsRegistry, max_dynamic_values: int = 32):
        if type(max_dynamic_values) is not int or max_dynamic_values < 1:
            raise ValueError("max_dynamic_values must be positive")
        self.registry = registry
        self.max_dynamic_values = max_dynamic_values
        self._seen = {"task_class": set(), "verifier_family": set()}

    def _bounded(self, family: str, value: str) -> str:
        seen = self._seen[family]
        if value in seen:
            return value
        if len(seen) >= self.max_dynamic_values:
            return "__other__"
        seen.add(value)
        return value

    def observe(self, observation) -> None:
        task_class = self._bounded("task_class", observation.task_class)
        topology = observation.topology
        self.registry["residual_reliability_runs_total"].inc(
            (task_class, topology, observation.terminal_state))
        self.registry["residual_reliability_acceptance_total"].inc(
            (task_class, topology, str(observation.accepted).lower()))
        if observation.verifier_rejected:
            self.registry["residual_reliability_verifier_rejections_total"].inc(
                (self._bounded("verifier_family", observation.verifier_family), topology))
        self.registry["residual_reliability_integration_conflicts_total"].inc(
            (task_class, topology), observation.conflicts)
        self.registry["residual_reliability_retries_total"].inc(
            (task_class, topology), observation.cost.retries)
        for phase, milliseconds in observation.timing.payload().items():
            if phase in {"wall_clock_ms", "worker_resource_ms", "verifier_resource_ms"}:
                continue
            self.registry["residual_reliability_phase_seconds"].observe(
                (phase.removesuffix("_ms"), topology), milliseconds / 1000.0)
        if observation.cost.api_cost_usd is not None:
            self.registry["residual_reliability_cost_usd_total"].inc(
                (topology, "api"), observation.cost.api_cost_usd)
        if observation.cost.failed_call_cost_usd is not None:
            self.registry["residual_reliability_cost_usd_total"].inc(
                (topology, "failed_call"), observation.cost.failed_call_cost_usd)
        self.registry["residual_reliability_evidence_total"].inc(
            (task_class, str(observation.evidence_complete).lower()))
