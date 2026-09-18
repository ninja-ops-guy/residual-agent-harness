from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from residual.core import ContractError, canonical, digest
from residual.discovery_metrics import (
    MetricDefinition, MetricDefinitionProposal, ProposalDisposition,
    admission_binding, load_metric_registry,
)
from residual.receipts import StationReceipt
from residual.station.models import save_settings, model_call
from residual.station.service import Station
from residual.station import workspace as ws
from residual.verifier import CheckResult


TASK_ID = "m6-discover-007t"

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
                "type": {"const": "insufficient_evidence"},
                "observation": {
                    "type": "object",
                    "properties": {
                        "observed_metric": {"type": "string"},
                        "observed_value": {"type": "number"},
                    },
                    "required": ["observed_metric", "observed_value"],
                    "additionalProperties": False,
                },
                "reason": {"type": "string"},
                "preserve_invariants": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "evidence_snapshot_hash": {"type": "string"},
                "human_approval_required": {"const": True},
            },
            "required": ["type","observation","reason","preserve_invariants"],
            "additionalProperties": False,
        },
    ]
}

QUERY_SCHEMA = {
    "type":"object",
    "properties":{
        "metrics":{"type":"array","items":{"type":"string"},"minItems":2,"maxItems":5},
        "purpose":{"type":"string"},
    },
    "required":["metrics","purpose"],
    "additionalProperties":False,
}

QUERY_SYSTEM = """Select 2 to 5 metric IDs from the supplied trusted metric catalog that are most useful for deciding the next evidence-grounded improvement direction.
You are selecting evidence to inspect, not proposing an improvement yet.
Return only the typed selection. Do not invent metric IDs."""

PLANNER_SCHEMA = {
    "oneOf":[
        {"type":"object","properties":{
            "type":{"const":"existing_metric_request"},
            "observation":{"type":"object","properties":{"observed_metric":{"type":"string"},"observed_value":{"type":"number"}},"required":["observed_metric","observed_value"],"additionalProperties":False},
            "question":{"type":"string"},"requested_metric_id":{"type":"string"},"why_needed":{"type":"string"},
            "preserve_invariants":{"type":"array","items":{"type":"string"},"minItems":1},
            "evidence_snapshot_hash":{"type":"string"},"metric_registry_sha256":{"type":"string"},
            "human_approval_required":{"const":True}},
         "required":["type","observation","question","requested_metric_id","why_needed","preserve_invariants"],"additionalProperties":False},
        {"type":"object","properties":{
            "type":{"const":"new_metric_proposal"},
            "observation":{"type":"object","properties":{"observed_metric":{"type":"string"},"observed_value":{"type":"number"}},"required":["observed_metric","observed_value"],"additionalProperties":False},
            "definition":{"type":"object","properties":{
                "metric_id":{"type":"string"},"description":{"type":"string"},"unit":{"type":"string"},
                "aggregation":{"type":"string"},"population":{"type":"string"},"valid_domain":{"type":"string"},
                "directionality":{"type":"string","enum":["lower_is_better","higher_is_better","target","contextual"]},
                "collection_method":{"type":"string"},"implementation_ref":{"type":"string"},"revision":{"type":"string"}},
                "required":["metric_id","description","unit","aggregation","population","valid_domain","directionality","collection_method","implementation_ref","revision"],"additionalProperties":False},
            "reason_existing_registry_insufficient":{"type":"string"},
            "preserve_invariants":{"type":"array","items":{"type":"string"},"minItems":1},
            "evidence_snapshot_hash":{"type":"string"},"metric_registry_sha256":{"type":"string"},
            "human_approval_required":{"const":True}},
         "required":["type","observation","definition","reason_existing_registry_insufficient","preserve_invariants"],"additionalProperties":False}
    ]
}

PLANNER_SYSTEM = """Act only as the Measurement Planner after the Hypothesis Scientist has declared evidence insufficient.
You receive exact inspected evidence and versioned Metric Registry definitions.
If a registered metric already expresses the evidence you need, return existing_metric_request with that exact metric ID.
Only if no registered definition expresses the needed measurable axis may you return new_metric_proposal, and then define it completely with a deterministic population and collection method.
Do not use vague populations such as normal, typical, usual, or representative conditions. Do not invent a near-alias of an existing metric.
Do not claim nonredundancy; the host and independent reviewer decide it.
Snapshot/registry identity and human-gate provenance are host-owned and intentionally absent from your output schema.\nDo not propose code or an intervention. Return only the typed request."""

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "findings": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    },
    "required": ["approved", "findings"],
    "additionalProperties": False,
}

SCIENTIST_SYSTEM = """Analyze only the host-returned selected_evidence and trusted catalog metadata.
Return exactly one typed proposal matching the response schema.
Do not invent measurements or numeric baselines. Missing telemetry is not evidence of a defect.
Choose the single most defensible measured improvement opportunity.
Return improvement_spec when the inspected evidence supports a falsifiable intervention.
Otherwise return insufficient_evidence with the exact measured observation and a substantive reason the inspected evidence cannot yet support an intervention hypothesis.
Do not request a metric yourself; a separate Measurement Planner owns evidence requests.
When evidence_resolution_history is supplied, incorporate those exact resolved values.
An observation and any ImprovementSpec target/preserve metrics must come from selected_evidence.
Snapshot identity and human-gate provenance are host-owned and intentionally absent from your output schema.\nDo not implement code, change evidence, or claim promotion authority."""

IMPROVEMENT_REVIEW_SYSTEM = """Independently review a mechanically grounded ImprovementSpec against the supplied EvidenceSnapshot.
Reject causal overclaim, incoherent preservation criteria, non-falsifiable acceptance, or a proposal that does not follow from the evidence.
Do not rewrite the proposal. Return only the structured verdict."""

GAP_REVIEW_SYSTEM = """Independently review a mechanically grounded MeasurementGap against the supplied EvidenceSnapshot.
A MeasurementGap is not an intervention hypothesis and does not require causal proof or improvement acceptance thresholds.
Approve only if: the observed anomaly is meaningful and evidence-bound; the missing measurement is genuinely absent and nonredundant; the proposed measurement is mechanically collectible; collecting it could materially resolve the stated uncertainty; and the preserved authority/integrity invariants are appropriate.
Reject speculative causal claims presented as facts, redundant measurements, uncollectible measurements, or gaps that would not change what can be concluded.
Do not rewrite the proposal. Return only the structured verdict."""


METRIC_REVIEW_SYSTEM = """Independently review a proposed discovery MetricDefinition against the versioned registered definitions and originating inspected evidence.
Approve only if the definition is unambiguous, mechanically collectible, and genuinely new or an explicitly justified refinement with distinct aggregation/population semantics.
Reject aliases, likely misspellings, undefined or subjective populations, unit/aggregation ambiguity, uncollectible measurements, or proposals whose answer is already represented by a registered metric.
Approval does not register the metric, implement a collector, or authorize promotion.
Return only the structured verdict."""


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
    elif kind=="insufficient_evidence":
        obs=proposal.get("observation")
        if not isinstance(obs,dict):
            errors.append("insufficiency observation must be structured")
        else:
            observed=obs.get("observed_metric")
            if observed not in metrics:
                errors.append("insufficiency observed_metric is not measured")
            elif obs.get("observed_value") != metrics[observed]:
                errors.append("insufficiency observed_value does not match evidence")
        reason=proposal.get("reason")
        if not isinstance(reason,str) or len(reason.strip())<20:
            errors.append("insufficiency reason not substantive")
        inv=proposal.get("preserve_invariants")
        if not isinstance(inv,list) or not inv or any(x not in ALLOWED_INVARIANTS for x in inv):
            errors.append("invalid insufficiency invariants")
    else:
        errors.append("unknown proposal type")
    return errors

def verify_selected(proposal: dict, selected: dict) -> list[str]:
    errors=[]
    kind=proposal.get("type")
    obs=proposal.get("observation")
    if isinstance(obs,dict):
        metric=obs.get("metric") if kind=="improvement_spec" else obs.get("observed_metric")
        if metric not in selected:
            errors.append("observation metric was not actively inspected")
    if kind=="improvement_spec":
        for field in ("target_metrics","preserve_metrics"):
            values=proposal.get(field,[])
            if isinstance(values,list) and any(x not in selected for x in values):
                errors.append(f"{field} contains metric not actively inspected")
    return errors


def verify_planner(request: dict, snapshot: dict, selected: dict, registry) -> list[str]:
    errors=[]
    if request.get("evidence_snapshot_hash") != snapshot["snapshot_hash"]:
        errors.append("planner evidence hash mismatch")
    if request.get("metric_registry_sha256") != registry.registry_sha256:
        errors.append("planner registry hash mismatch")
    if request.get("human_approval_required") is not True:
        errors.append("planner human approval not retained")
    obs=request.get("observation")
    if not isinstance(obs,dict) or obs.get("observed_metric") not in selected:
        errors.append("planner observation was not actively inspected")
    elif obs.get("observed_value") != selected[obs["observed_metric"]]:
        errors.append("planner observation value mismatch")
    inv=request.get("preserve_invariants")
    if not isinstance(inv,list) or not inv or any(x not in ALLOWED_INVARIANTS for x in inv):
        errors.append("invalid planner invariants")
    if request.get("type")=="existing_metric_request":
        for name in ("question","why_needed"):
            value=request.get(name)
            if not isinstance(value,str) or len(value.strip())<20:
                errors.append(f"planner {name} not substantive")
        requested=request.get("requested_metric_id")
        if not isinstance(requested,str) or not requested.strip():
            errors.append("requested_metric_id missing")
    elif request.get("type")=="new_metric_proposal":
        reason=request.get("reason_existing_registry_insufficient")
        if not isinstance(reason,str) or len(reason.strip())<30:
            errors.append("new metric insufficiency reason not substantive")
        if not isinstance(request.get("definition"),dict):
            errors.append("new metric definition missing")
    else:
        errors.append("unknown planner request type")
    return errors


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="qwen2.5:7b")
    ap.add_argument("--base-url",default="http://127.0.0.1:11446")
    ap.add_argument("--output",default="runs/m6-spec-007t/evidence.json")
    ap.add_argument("--registry",default="residual/discovery_metric_registry.json")
    a=ap.parse_args()
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    registry=load_metric_registry(a.registry)

    raw={
        "schema_version":1,
        "baseline_commit":"60d0c5a8fc2044a22619248292ce89c9b43edd37",
        "source_evidence":[r["evidence_sha256"] for r in RUNS],
        "sample_count":len(RUNS),
        "metric_catalog":[d.metric_id for d in registry.definitions],
        "metric_registry_revision":registry.revision,
        "metric_registry_sha256":registry.registry_sha256,
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
    registry.validate_snapshot_binding(snapshot)

    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        src=root/"repo"
        ws.init_repo(src,{"README.md":"# M6-SPEC-007T branch-aware review fixture\n"})
        station=Station(root/"station")
        save_settings(station.store,{
            "local":{"kind":"ollama","model":a.model,"base_url":a.base_url,"output_token_field":"max_tokens"},
            "review_placement":"local","workers":1,"max_output_tokens":900,
            "batch_max_passes":5,"batch_token_budget":30000,"batch_wall_clock_s":1500,
        })
        manifest={"name":"M6-SPEC-007T Branch-Aware Review","goal":"Originate and admit one evidence-grounded improvement proposal.","tasks":[{
            "id":TASK_ID,"title":"Typed discovery","instruction":"typed structured proposal",
            "files":[],"context":[],"depends_on":[],"route":"local","checks":[]
        }]}
        pid=station.store.create_project(manifest,"",src)

        query=model_call(
            station.store,pid,"scientist",
            {"metric_catalog":[{"metric_id":d.metric_id,"description":d.description,
                                "unit":d.unit,"aggregation":d.aggregation,
                                "population":d.population,"directionality":d.directionality}
                               for d in registry.definitions],
             "scope":snapshot["scope"],
             "metric_registry_sha256":registry.registry_sha256,
             "protected_invariant_catalog":snapshot["protected_invariant_catalog"]},
            QUERY_SYSTEM,QUERY_SCHEMA,"local",TASK_ID,
            extensions=station.extensions(pid),
        )
        chosen=query.get("metrics",[])
        if len(chosen)!=len(set(chosen)) or any(m not in snapshot["metrics"] for m in chosen):
            raise ValueError("Scientist evidence query returned invalid or duplicate metric IDs")
        selected_evidence={m:snapshot["metrics"][m] for m in chosen}

        scientist_outputs=[]
        planner_outputs=[]
        metric_assessments=[]
        resolution_history=[{"status":"actively_selected","metrics":dict(selected_evidence)}]
        proposal=None
        admitted_proposal=None
        errors=[]
        review={"approved":False,"findings":["no admissible proposal"]}
        admitted=False

        for cycle in range(1,3):
            packet={
                "evidence_snapshot_hash":snapshot["snapshot_hash"],
                "selected_evidence":selected_evidence,
                "protected_invariant_catalog":snapshot["protected_invariant_catalog"],
            }
            if resolution_history:
                packet["evidence_resolution_history"]=resolution_history
            proposal=model_call(
                station.store,pid,"scientist",packet,
                SCIENTIST_SYSTEM,PROPOSAL_SCHEMA,"local",TASK_ID,
                extensions=station.extensions(pid),
            )
            errors=verify(proposal,snapshot) + verify_selected(proposal,selected_evidence)
            scientist_outputs.append({"cycle":cycle,"proposal":proposal,"mechanical_errors":errors})
            if errors:
                break

            if proposal.get("type")=="improvement_spec":
                admitted_proposal=proposal
                review=model_call(
                    station.store,pid,"reviewer",
                    {"evidence_snapshot":snapshot,"proposal":admitted_proposal,
                     "registered_metric_definitions":[d.to_dict() for d in registry.definitions]},
                    IMPROVEMENT_REVIEW_SYSTEM,REVIEW_SCHEMA,"local",TASK_ID,
                    extensions=station.extensions(pid),
                )
                admitted=review.get("approved") is True
                break

            request=model_call(
                station.store,pid,"measurement_planner",
                {"selected_evidence":selected_evidence,"insufficiency":proposal,
                 "metric_registry":[d.to_dict() for d in registry.definitions],
                 "evidence_snapshot_hash":snapshot["snapshot_hash"],
                 "metric_registry_sha256":registry.registry_sha256},
                PLANNER_SYSTEM,PLANNER_SCHEMA,"local",TASK_ID,
                extensions=station.extensions(pid),
            )
            request_errors=verify_planner(request,snapshot,selected_evidence,registry)
            planner_outputs.append({"cycle":cycle,"request":request,"mechanical_errors":request_errors})
            if request_errors:
                errors=request_errors
                break

            if request["type"]=="existing_metric_request":
                requested=request["requested_metric_id"]
                try:
                    registered=registry.resolve(requested)
                except ContractError as exc:
                    errors=[str(exc)]
                    break
                if requested not in snapshot["metrics"]:
                    admitted_proposal={
                        "type":"measurement_gap",
                        "metric_definition":registered.to_dict(),
                        "observation":request["observation"],
                        "reason":"Registered metric is absent from the bound EvidenceSnapshot.",
                        "evidence_snapshot_hash":request["evidence_snapshot_hash"],
                        "metric_registry_revision":registry.revision,
                        "metric_registry_sha256":registry.registry_sha256,
                        "human_approval_required":True,
                        "classified_by":"host_evidence_resolver",
                    }
                    review=model_call(
                        station.store,pid,"reviewer",
                        {"evidence_snapshot":snapshot,"proposal":admitted_proposal,
                         "registered_definition":registered.to_dict()},
                        GAP_REVIEW_SYSTEM,REVIEW_SCHEMA,"local",TASK_ID,
                        extensions=station.extensions(pid),
                    )
                    admitted=review.get("approved") is True
                    break
                if requested in selected_evidence:
                    errors=[f"Measurement Planner requested already-inspected evidence {requested!r}"]
                    resolution_history.append({"status":"repeated","metric":requested,"value":snapshot["metrics"][requested]})
                    break
                selected_evidence[requested]=snapshot["metrics"][requested]
                resolution_history.append({
                    "status":"present","metric":requested,"value":snapshot["metrics"][requested],
                    "message":"Host EvidenceResolver added exact registered evidence for the next hypothesis cycle.",
                })
                continue

            try:
                definition=MetricDefinition(**request["definition"])
                metric_proposal=MetricDefinitionProposal(
                    definition=definition,
                    evidence_snapshot_hash=request["evidence_snapshot_hash"],
                    observed_metric=request["observation"]["observed_metric"],
                    observed_value=request["observation"]["observed_value"],
                    reason_existing_registry_insufficient=request["reason_existing_registry_insufficient"],
                    preserve_invariants=tuple(request["preserve_invariants"]),
                    human_approval_required=request["human_approval_required"],
                )
                assessment=registry.assess_proposal(metric_proposal)
            except ContractError as exc:
                errors=[f"metric definition rejected: {exc}"]
                break

            metric_assessments.append({
                "cycle":cycle,
                "proposal":metric_proposal.to_dict(),
                "disposition":assessment.disposition.value,
                "findings":list(assessment.findings),
                "similar_metric_ids":list(assessment.similar_metric_ids),
            })
            if assessment.disposition == ProposalDisposition.REJECT:
                errors=["metric definition mechanically rejected: "+("; ".join(assessment.findings))]
                break
            if assessment.disposition == ProposalDisposition.UNKNOWN and any(
                "ambiguous" in finding for finding in assessment.findings
            ):
                errors=["metric definition semantics UNKNOWN: "+("; ".join(assessment.findings))]
                break

            similar=[registry.resolve(mid).to_dict() for mid in assessment.similar_metric_ids]
            metric_review=model_call(
                station.store,pid,"metric_reviewer",
                {"proposed_definition":definition.to_dict(),
                 "similar_registered_definitions":similar,
                 "registered_metric_definitions":[d.to_dict() for d in registry.definitions],
                 "originating_observation":request["observation"],
                 "reason_existing_registry_insufficient":request["reason_existing_registry_insufficient"]},
                METRIC_REVIEW_SYSTEM,REVIEW_SCHEMA,"local",TASK_ID,
                extensions=station.extensions(pid),
            )
            metric_assessments[-1]["semantic_review"]=metric_review
            review=metric_review
            if metric_review.get("approved") is not True:
                break

            admitted_proposal={
                "type":"measurement_gap",
                "metric_definition_proposal":metric_proposal.to_dict(),
                "registry_assessment":{
                    "disposition":assessment.disposition.value,
                    "findings":list(assessment.findings),
                    "similar_metric_ids":list(assessment.similar_metric_ids),
                },
                "metric_semantic_review":metric_review,
                "evidence_snapshot_hash":snapshot["snapshot_hash"],
                "metric_registry_revision":registry.revision,
                "metric_registry_sha256":registry.registry_sha256,
                "human_approval_required":True,
                "classified_by":"host_metric_registry",
            }
            admitted=True
            break

        proposal_json=canonical(admitted_proposal or proposal)
        binding=admission_binding(
            evidence_snapshot_hash=sh,
            registry=registry,
            verifier_rules={"experiment":"M6-SPEC-007T","rules":"registry-aware-discovery-v1"},
        )
        receipt=None
        if admitted:
            receipt=StationReceipt(
                task_id=TASK_ID,
                cache_key=binding["cache_key"],
                value_hash=digest(admitted_proposal),
                verifier_name="m6:admission",
                verifier_revision=binding["verifier_revision"],
                verdict=CheckResult.PASS,
                engine_name="residual-m6",
                engine_version="007t",
            ).to_dict()

        evidence={
            "schema_version":1,
            "experiment":"M6-SPEC-007T",
            "snapshot":snapshot,
            "evidence_query":query,
            "selected_evidence_final":selected_evidence,
            "scientist_outputs":scientist_outputs,
            "measurement_planner_outputs":planner_outputs,
            "metric_assessments":metric_assessments,
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
        print("M6_SPEC_007T_EVIDENCE="+json.dumps(evidence,sort_keys=True,separators=(",",":")))
        return 0 if admitted else 1

if __name__=="__main__":
    raise SystemExit(main())
