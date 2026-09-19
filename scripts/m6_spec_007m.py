from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from residual.core import canonical, digest
from residual.receipts import StationReceipt
from residual.station.models import save_settings, model_call
from residual.station.service import Station
from residual.station import workspace as ws
from residual.verifier import CheckResult


TASK_ID = "m6-discover-007m"

ALLOWED_INVARIANTS = {
    "M4", "evidence_integrity", "verification_integrity", "promotion_authority",
}
OPS = {"<=", ">=", "==", "<", ">"}

PROPOSAL_SCHEMA = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "improvement_spec"},
                "observation": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "value": {"type": "number"},
                        "comparison_metric": {"type": "string"},
                        "comparison_value": {"type": "number"},
                    },
                    "required": ["metric", "value"],
                    "additionalProperties": False,
                },
                "hypothesis": {"type": "string"},
                "target_metrics": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "preserve_metrics": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "protected_invariants": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "acceptance": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "metric": {"type": "string"},
                            "operator": {"type": "string", "enum": ["<=", ">=", "==", "<", ">"]},
                            "threshold": {"type": "number"},
                        },
                        "required": ["metric", "operator", "threshold"],
                        "additionalProperties": False,
                    },
                },
                "evidence_snapshot_hash": {"type": "string"},
                "human_approval_required": {"const": True},
            },
            "required": [
                "type", "observation", "hypothesis", "target_metrics", "preserve_metrics",
                "protected_invariants", "acceptance", "evidence_snapshot_hash",
                "human_approval_required",
            ],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "evidence_request"},
                "observation": {
                    "type": "object",
                    "properties": {
                        "observed_metric": {"type": "string"},
                        "observed_value": {"type": "number"},
                    },
                    "required": ["observed_metric", "observed_value"],
                    "additionalProperties": False,
                },
                "question": {"type": "string"},
                "requested_metric": {"type": "string"},
                "why_needed": {"type": "string"},
                "proposed_measurement": {"type": "string"},
                "preserve_invariants": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "evidence_snapshot_hash": {"type": "string"},
                "human_approval_required": {"const": True},
            },
            "required": [
                "type", "observation", "question", "requested_metric", "why_needed", "proposed_measurement",
                "preserve_invariants", "evidence_snapshot_hash", "human_approval_required",
            ],
            "additionalProperties": False,
        },
    ]
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "findings": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    },
    "required": ["approved", "findings"],
    "additionalProperties": False,
}

SCIENTIST_SYSTEM = """Analyze only the supplied measured EvidenceSnapshot.
Return exactly one typed proposal matching the response schema.
Do not invent measurements or numeric baselines. Missing telemetry is not evidence of a defect.
Choose the single most defensible measured improvement opportunity.
Use improvement_spec when the measured evidence supports a falsifiable intervention.
Otherwise emit evidence_request: identify the exact measured anomaly in observation, then request the specific metric you need to resolve the uncertainty.
Do NOT decide whether requested evidence is missing; the trusted host EvidenceResolver owns that fact and will return exact available evidence or classify a genuine MeasurementGap.
When evidence_resolution_history is supplied, incorporate those exact resolved values and do not request the same already-resolved metric again.
Do not implement code, change evidence, or claim promotion authority."""

IMPROVEMENT_REVIEW_SYSTEM = """Independently review a mechanically grounded ImprovementSpec against the supplied EvidenceSnapshot.
Reject causal overclaim, incoherent preservation criteria, non-falsifiable acceptance, or a proposal that does not follow from the evidence.
Do not rewrite the proposal. Return only the structured verdict."""

GAP_REVIEW_SYSTEM = """Independently review a mechanically grounded MeasurementGap against the supplied EvidenceSnapshot.
A MeasurementGap is not an intervention hypothesis and does not require causal proof or improvement acceptance thresholds.
Approve only if: the observed anomaly is meaningful and evidence-bound; the missing measurement is genuinely absent and nonredundant; the proposed measurement is mechanically collectible; collecting it could materially resolve the stated uncertainty; and the preserved authority/integrity invariants are appropriate.
Reject speculative causal claims presented as facts, redundant measurements, uncollectible measurements, or gaps that would not change what can be concluded.
Do not rewrite the proposal. Return only the structured verdict."""


RUNS = [
    {"id":"M6-SPEC-006","outcome":"success","runner_attempts":3,"first_request_bytes":5614,"first_call_elapsed_ms":213211,"model_calls":4,"reported_tokens":9217,"wall_clock_s":759.722,"provider_timeouts":0,"identical_failure_repeats":0,"evidence_sha256":"ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61"},
    {"id":"M6-ROADMAP-001B","outcome":"success","runner_attempts":1,"first_request_bytes":5535,"first_call_elapsed_ms":231142,"model_calls":2,"reported_tokens":4384,"wall_clock_s":435.182,"provider_timeouts":0,"identical_failure_repeats":0,"evidence_sha256":"908b3b748b7d4841bdf92330e2cee5708bc65547663788dd5d0de29a4477effc"},
    {"id":"M6-SHIP-001","outcome":"failed","runner_attempts":5,"first_request_bytes":30606,"first_call_elapsed_ms":269391,"model_calls":5,"reported_tokens":12825,"wall_clock_s":823.616,"provider_timeouts":0,"identical_failure_repeats":4,"evidence_sha256":"69480331425268d01d08dd41c9778f94b347d2668328f4400fbe08d462cc7ffd"},
    {"id":"M6-SHIP-003","outcome":"aborted","runner_attempts":1,"first_request_bytes":32652,"first_call_elapsed_ms":300097,"model_calls":1,"reported_tokens":0,"wall_clock_s":300.205,"provider_timeouts":1,"identical_failure_repeats":0,"evidence_sha256":"bc62f566fbacb23600bab3348a7071b40ea0844fe8d8a45486bc8458617f2702"},
    {"id":"M6-SHIP-004","outcome":"success","runner_attempts":5,"first_request_bytes":7663,"first_call_elapsed_ms":275152,"model_calls":6,"reported_tokens":16558,"wall_clock_s":1163.466,"provider_timeouts":0,"identical_failure_repeats":0,"evidence_sha256":"7a6b9b31c9ca7116a73ea49ea9ba85c71a7ecd24097942e86af9b0aaf70ced69"},
]

def aggregate_metrics():
    success=[r for r in RUNS if r["outcome"]=="success"]
    non=[r for r in RUNS if r["outcome"]!="success"]
    n=len(RUNS)
    return {
        "shipping_task_success_rate": round(len(success)/n,6),
        "provider_timeout_rate": round(sum(r["provider_timeouts"] for r in RUNS)/n,6),
        "mean_runner_attempts": round(sum(r["runner_attempts"] for r in RUNS)/n,6),
        "mean_first_request_bytes": round(sum(r["first_request_bytes"] for r in RUNS)/n,6),
        "context_bytes_success_mean": round(sum(r["first_request_bytes"] for r in success)/len(success),6),
        "context_bytes_non_success_mean": round(sum(r["first_request_bytes"] for r in non)/len(non),6),
        "mean_wall_clock_s": round(sum(r["wall_clock_s"] for r in RUNS)/n,6),
        "successful_mean_wall_clock_s": round(sum(r["wall_clock_s"] for r in success)/len(success),6),
        "identical_failure_repeats_total": sum(r["identical_failure_repeats"] for r in RUNS),
        "mean_reported_tokens_per_run": round(sum(r["reported_tokens"] for r in RUNS)/n,6),
        "context_bytes_non_success_max": max(r["first_request_bytes"] for r in non),
    }

def verify(proposal: dict, snapshot: dict) -> list[str]:
    errors=[]
    metrics=snapshot["metrics"]
    catalog=set(snapshot["metric_catalog"])
    if proposal.get("evidence_snapshot_hash") != snapshot["snapshot_hash"]:
        errors.append("evidence_snapshot_hash mismatch")
    if proposal.get("human_approval_required") is not True:
        errors.append("human approval not retained")
    kind=proposal.get("type")
    if kind=="improvement_spec":
        obs=proposal.get("observation")
        if not isinstance(obs,dict):
            errors.append("observation must be structured")
        else:
            metric=obs.get("metric")
            if metric not in metrics: errors.append("observation metric unmeasured")
            elif obs.get("value") != metrics[metric]: errors.append("observation baseline changed")
            if "comparison_metric" in obs:
                cm=obs["comparison_metric"]
                if cm not in metrics: errors.append("comparison metric unmeasured")
                elif obs.get("comparison_value") != metrics[cm]: errors.append("comparison baseline changed")
        hyp=proposal.get("hypothesis")
        if not isinstance(hyp,str) or len(hyp.strip())<30: errors.append("hypothesis not substantive")
        targets=proposal.get("target_metrics")
        preserves=proposal.get("preserve_metrics")
        if not isinstance(targets,list) or not targets or any(x not in catalog for x in targets): errors.append("invalid target metrics")
        if not isinstance(preserves,list) or not preserves or any(x not in catalog for x in preserves): errors.append("invalid preserve metrics")
        if isinstance(targets,list) and isinstance(preserves,list) and set(targets)&set(preserves): errors.append("target/preserve overlap")
        invariants=proposal.get("protected_invariants")
        if not isinstance(invariants,list) or not invariants or any(x not in ALLOWED_INVARIANTS for x in invariants): errors.append("invalid protected invariants")
        acceptance=proposal.get("acceptance")
        covered=set()
        if not isinstance(acceptance,list) or not acceptance:
            errors.append("acceptance missing")
        else:
            for c in acceptance:
                if not isinstance(c,dict) or set(c)!={"metric","operator","threshold"}:
                    errors.append("invalid acceptance criterion")
                    continue
                if c["operator"] not in OPS: errors.append("unsupported acceptance operator")
                if type(c["threshold"]) not in (int,float) or isinstance(c["threshold"],bool): errors.append("invalid threshold")
                covered.add(c["metric"])
            if isinstance(targets,list) and not set(targets).issubset(covered): errors.append("target acceptance missing")
            if isinstance(preserves,list) and not set(preserves).issubset(covered): errors.append("preserve acceptance missing")
    elif kind=="evidence_request":
        obs=proposal.get("observation")
        if not isinstance(obs,dict):
            errors.append("request observation must be structured")
        else:
            observed=obs.get("observed_metric")
            if observed not in metrics:
                errors.append("request observed_metric is not measured")
            elif obs.get("observed_value") != metrics[observed]:
                errors.append("request observed_value does not match evidence")
        requested=proposal.get("requested_metric")
        if not isinstance(requested,str) or not requested.strip():
            errors.append("requested_metric is required")
        for name in ("question","why_needed","proposed_measurement"):
            v=proposal.get(name)
            if not isinstance(v,str) or len(v.strip())<20: errors.append(f"{name} not substantive")
        inv=proposal.get("preserve_invariants")
        if not isinstance(inv,list) or not inv or any(x not in ALLOWED_INVARIANTS for x in inv): errors.append("invalid request invariants")
    else:
        errors.append("unknown proposal type")
    return errors

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="qwen2.5:7b")
    ap.add_argument("--base-url",default="http://127.0.0.1:11446")
    ap.add_argument("--output",default="runs/m6-spec-007m/evidence.json")
    a=ap.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)

    raw={
        "schema_version":1,
        "baseline_commit":"60d0c5a8fc2044a22619248292ce89c9b43edd37",
        "source_evidence":[r["evidence_sha256"] for r in RUNS],
        "sample_count":len(RUNS),
        "metric_catalog":[
            "shipping_task_success_rate","provider_timeout_rate","mean_runner_attempts",
            "mean_first_request_bytes","context_bytes_success_mean","context_bytes_non_success_mean",
            "mean_wall_clock_s","successful_mean_wall_clock_s","identical_failure_repeats_total",
            "mean_reported_tokens_per_run","context_bytes_non_success_max",
        ],
        "metrics":aggregate_metrics(),
        "protected_invariant_catalog":sorted(ALLOWED_INVARIANTS),
        "scope":"Aggregate M6 self-development/shipping measurements enriched by closing admitted MeasurementGap 007J",
        "measurement_records":[{
            "metric":"context_bytes_non_success_max",
            "method":"max(first_request_bytes) over retained runs where outcome != success",
            "source_run_ids":[r["id"] for r in RUNS if r["outcome"]!="success"],
            "source_evidence":[r["evidence_sha256"] for r in RUNS if r["outcome"]!="success"],
            "value":max(r["first_request_bytes"] for r in RUNS if r["outcome"]!="success"),
            "origin_admission_receipt":"09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9",
        }],
    }
    sh=hashlib.sha256(canonical(raw).encode()).hexdigest()
    snapshot={**raw,"snapshot_hash":sh}

    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        src=root/"repo"
        ws.init_repo(src,{"README.md":"# M6-SPEC-007M branch-aware review fixture\n"})
        station=Station(root/"station")
        save_settings(station.store,{
            "local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},
            "review_placement":"local","workers":1,"max_output_tokens":900,
            "batch_max_passes":5,"batch_token_budget":30000,"batch_wall_clock_s":1500,
        })
        manifest={"name":"M6-SPEC-007M Branch-Aware Review","goal":"Originate and admit one evidence-grounded improvement proposal.","tasks":[{
            "id":TASK_ID,"title":"Typed discovery","instruction":"typed structured proposal",
            "files":[],"context":[],"depends_on":[],"route":"local","checks":[]
        }]}
        pid=station.store.create_project(manifest,"",src)

        scientist_outputs=[]
        resolution_history=[]
        proposal=None
        admitted_proposal=None
        errors=[]
        review={"approved":False,"findings":["no admissible proposal"]}
        admitted=False

        for attempt in range(1,4):
            packet={"evidence_snapshot":snapshot}
            if resolution_history:
                packet["evidence_resolution_history"]=resolution_history
            proposal=model_call(
                station.store,pid,"scientist",packet,
                SCIENTIST_SYSTEM,PROPOSAL_SCHEMA,"local",TASK_ID,
                extensions=station.extensions(pid),
            )
            errors=verify(proposal,snapshot)
            scientist_outputs.append({"attempt":attempt,"proposal":proposal,"mechanical_errors":errors})
            if errors:
                break

            if proposal.get("type")=="evidence_request":
                requested=proposal["requested_metric"]
                if requested in snapshot["metrics"]:
                    resolution={
                        "status":"present",
                        "metric":requested,
                        "value":snapshot["metrics"][requested],
                        "message":"EvidenceResolver found this metric in the trusted EvidenceSnapshot; incorporate the exact value and reassess.",
                    }
                    if any(x.get("metric")==requested and x.get("status")=="present" for x in resolution_history):
                        errors=[f"Scientist repeated already-resolved evidence request {requested!r}"]
                        resolution_history.append({**resolution,"repeated":True})
                        break
                    resolution_history.append(resolution)
                    continue

                admitted_proposal={
                    "type":"measurement_gap",
                    "observation":proposal["observation"],
                    "question":proposal["question"],
                    "missing_metric":requested,
                    "why_needed":proposal["why_needed"],
                    "proposed_measurement":proposal["proposed_measurement"],
                    "preserve_invariants":proposal["preserve_invariants"],
                    "evidence_snapshot_hash":proposal["evidence_snapshot_hash"],
                    "human_approval_required":proposal["human_approval_required"],
                    "classified_by":"host_evidence_resolver",
                }
                review=model_call(
                    station.store,pid,"reviewer",
                    {"evidence_snapshot":snapshot,"proposal":admitted_proposal},
                    GAP_REVIEW_SYSTEM,REVIEW_SCHEMA,"local",TASK_ID,
                    extensions=station.extensions(pid),
                )
                admitted=review.get("approved") is True
                break

            admitted_proposal=proposal
            review=model_call(
                station.store,pid,"reviewer",
                {"evidence_snapshot":snapshot,"proposal":admitted_proposal},
                IMPROVEMENT_REVIEW_SYSTEM,REVIEW_SCHEMA,"local",TASK_ID,
                extensions=station.extensions(pid),
            )
            admitted=review.get("approved") is True
            break

        proposal_json=canonical(admitted_proposal or proposal)
        verifier_revision=digest({"experiment":"M6-SPEC-007M","rules":"evidence-resolver-admission-v1"})
        receipt=None
        if admitted:
            receipt=StationReceipt(
                task_id=TASK_ID,
                cache_key=digest({"snapshot_hash":sh,"proposal":admitted_proposal}),
                value_hash=digest(admitted_proposal),
                verifier_name="m6:admission",
                verifier_revision=verifier_revision,
                verdict=CheckResult.PASS,
                engine_name="residual-m6",
                engine_version="007m",
            ).to_dict()

        evidence={
            "schema_version":1,
            "experiment":"M6-SPEC-007M",
            "snapshot":snapshot,
            "scientist_outputs":scientist_outputs,
            "evidence_resolution_history":resolution_history,
            "proposal":admitted_proposal or proposal,
            "proposal_canonical_json":proposal_json,
            "proposal_sha256":hashlib.sha256(proposal_json.encode()).hexdigest(),
            "mechanical_errors":errors,
            "review":review,
            "admitted":admitted,
            "admission_receipt":receipt,
            "metrics":station.metrics(pid),
            "events":[
                {"seq":e["seq"],"type":e["event_type"],"task_id":e["task_id"],"actor":e["actor"],"data":e["data"]}
                for e in station.store.events(pid,0,5000)
                if e["event_type"] in {"usage.recorded","task.finding","project.note"}
            ],
        }
        out.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print("M6_SPEC_007M_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        return 0 if admitted else 1

if __name__=="__main__":
    raise SystemExit(main())
