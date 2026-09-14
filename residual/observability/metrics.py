from __future__ import annotations
from collections import defaultdict
from threading import RLock
class Counter:
    def __init__(self): self._v=defaultdict(float); self._lock=RLock()
    def inc(self,labels=(),amount=1.0):
        if amount<0: raise ValueError("counter cannot decrease")
        with self._lock: self._v[tuple(labels)]+=float(amount)
    def samples(self):
        with self._lock: return dict(self._v)
class Gauge:
    def __init__(self): self._v=defaultdict(float); self._lock=RLock()
    def set(self,labels=(),value=0.0):
        with self._lock: self._v[tuple(labels)]=float(value)
    def inc(self,labels=(),amount=1.0):
        with self._lock: self._v[tuple(labels)]+=float(amount)
    def samples(self):
        with self._lock: return dict(self._v)
class Histogram:
    DEFAULT_BUCKETS=(.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10,float("inf"))
    def __init__(self,buckets=None): self.buckets=tuple(buckets or self.DEFAULT_BUCKETS); self._data={}; self._lock=RLock()
    def observe(self,labels=(),value=0.0):
        key=tuple(labels)
        with self._lock:
            d=self._data.setdefault(key,{"count":0,"sum":0.0,"buckets":[0]*len(self.buckets)}); d["count"]+=1; d["sum"]+=float(value)
            for i,b in enumerate(self.buckets):
                if value<=b: d["buckets"][i]+=1
    def samples(self):
        with self._lock: return {k:{"count":v["count"],"sum":v["sum"],"buckets":list(v["buckets"])} for k,v in self._data.items()}
class MetricsRegistry:
    def __init__(self):
        self.metrics={
            "residual_tokens_total":(Counter(),("provider",)),
            "residual_tokens_saved":(Counter(),("cache_hit",)),
            "residual_brake_trips_total":(Counter(),("brake_name","action")),
            "residual_verification_duration_seconds":(Histogram(),("check_name",)),
            "residual_quarantine_denials_total":(Counter(),("policy_name",)),
            "residual_hitl_challenges_pending":(Gauge(),()),
            "residual_receipts_issued_total":(Counter(),("verdict",)),
            "residual_engine_executions_total":(Counter(),("engine_name","outcome")),
            "residual_loop_iterations_total":(Counter(),("mode",)),
            "residual_loop_residual_mass":(Gauge(),("mode",)),
            "residual_loop_progress_delta":(Gauge(),("mode",)),
            "residual_loop_stagnation_total":(Counter(),("mode",)),
            "residual_loop_escalations_total":(Counter(),("mode",)),
            "residual_loop_completion_total":(Counter(),("mode","status")),
            "residual_loop_accepted_tree_changes_total":(Counter(),("mode",)),
            "residual_loop_repeated_failure_total":(Counter(),("mode",)),
            "residual_loop_churn_total":(Counter(),("mode",)),
        }
    def __getitem__(self,name): return self.metrics[name][0]
    def label_names(self,name): return self.metrics[name][1]
