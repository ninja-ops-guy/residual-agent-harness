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
