"""Measured execution adapters for EXP-NESTED-SWARM-001.

The collector consumes real runtime result/trace material. It does not fabricate
missing counters: unavailable measurements make a trial inconclusive unless the
caller supplies an explicitly measured override.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from residual.core import canonical, digest, strict_json
from .nested_swarm import ExperimentManifest, TrialRecord, verify_trial

Runner = Callable[[Mapping[str, Any]], Mapping[str, Any]]

@dataclass(frozen=True)
class ArmExecution:
    arm_id: str
    provider_snapshot: Mapping[str, Any]
    worker_contract_sha256: str
    runner: Runner

def _nonnegative_int(value,name):
    if type(value) is not int or value < 0: raise ValueError(f"missing or invalid measured {name}")
    return value

def _rate(num,den):
    return float(num)/float(den) if den else 0.0

def metrics_from_residual_result(result:Mapping[str,Any],*,overrides:Mapping[str,Any]|None=None):
    m=result.get("metrics") if isinstance(result,Mapping) else None
    calls=result.get("calls") if isinstance(result,Mapping) else None
    if not isinstance(m,Mapping) or not isinstance(calls,list): raise ValueError("real RESIDUAL result metrics/calls required")
    total=int(m.get("total_obligations",0)); accepted=int(m.get("accepted_obligations",0))
    inp=sum((c.get("usage") or {}).get("input_tokens") or 0 for c in calls)
    out=sum((c.get("usage") or {}).get("output_tokens") or 0 for c in calls)
    measured=dict(overrides or {})
    allowed_overrides={"evidence_requests","failed_tool_calls","human_interventions","integration_conflicts"}
    if set(measured)-allowed_overrides:
        raise ValueError("only unavailable measured counters may be supplied as overrides")
    def measured_count(name):
        value=measured.pop(name,m.get(name))
        return _nonnegative_int(value,name)

    values={
      "task_success":result.get("success") is True,
      "verifier_pass_rate":_rate(accepted,total),
      "elapsed_ms":float(m["elapsed_ms"]),
      "input_tokens":_nonnegative_int(inp,"input_tokens"),
      "output_tokens":_nonnegative_int(out,"output_tokens"),
      "api_cost_usd":float(m.get("remote_cost_usd") if m.get("remote_cost_usd") is not None else m.get("remote_cost_known_subtotal_usd",0.0)),
      "provider_calls":_nonnegative_int(len(calls),"provider_calls"),
      "retries":_nonnegative_int(m.get("repeated_dispatch_calls",0),"retries"),
      "evidence_requests":measured_count("evidence_requests"),
      "failed_tool_calls":measured_count("failed_tool_calls"),
      "human_interventions":measured_count("human_interventions"),
      "integration_conflicts":measured_count("integration_conflicts"),
      "duplicate_work_items":_nonnegative_int(m.get("repeated_dispatch_calls",0),"duplicate_work_items"),
      "convergence_iterations":_nonnegative_int(len(calls),"convergence_iterations"),
      "provenance_completeness":1.0 if result.get("trace_root") else 0.0,
    }
    return values

def metrics_from_external_measurement(measurement:Mapping[str,Any]):
    """Strict boundary for Moonshot/OpenClaw-native runners.

    External runtimes must report the complete frozen vector; absent counters are
    not silently converted to zero because that would bias cross-arm comparisons.
    """
    required={"metrics","trace_root"}
    if not isinstance(measurement,Mapping) or not required <= set(measurement): raise ValueError("external measured result requires metrics and trace_root")
    metrics=measurement["metrics"]
    from .nested_swarm import METRICS
    if not isinstance(metrics,Mapping) or set(metrics)!=set(METRICS): raise ValueError("external runtime must report complete frozen metric vector")
    return dict(metrics)

def execute_trial(*,manifest:ExperimentManifest,execution:ArmExecution,trial_index:int,task_id:str,
                  task_payload:Mapping[str,Any],measured_overrides:Mapping[str,Any]|None=None)->TrialRecord:
    raw=execution.runner(task_payload)
    if not isinstance(raw,Mapping): raise ValueError("runner must return measured mapping")
    task_hash=digest(task_payload)
    trace_root=raw.get("trace_root")
    if not isinstance(trace_root,str) or len(trace_root)!=64: raise ValueError("measured trace root required")
    if execution.arm_id in {"A","D"}:
        metrics=metrics_from_residual_result(raw,overrides=measured_overrides)
    else:
        metrics=metrics_from_external_measurement(raw)
    outcome="pass" if metrics["task_success"] else ("inconclusive" if raw.get("inconclusive") else "fail")
    record=TrialRecord(manifest.sha256,execution.arm_id,trial_index,task_id,task_hash,manifest.runtime_revision,
                       execution.provider_snapshot,execution.worker_contract_sha256,trace_root,metrics,outcome,
                       raw.get("failure_code"))
    verify_trial(record,manifest)
    return record

def load_measured_json(path:str|Path):
    data=strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data,dict): raise ValueError("measured evidence must be an object")
    return data
