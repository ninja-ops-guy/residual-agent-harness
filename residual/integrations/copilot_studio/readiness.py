"""Content-addressed enterprise-readiness evidence bundle for Copilot integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ...core import ContractError, canonical, digest
from .deployment import EnterpriseCopilotDeployment


@dataclass(frozen=True)
class QualificationRecord:
    name:str
    head_sha:str
    status:str
    evidence_ref:str=""

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name.strip(): raise ContractError("qualification name required")
        if not isinstance(self.head_sha,str) or len(self.head_sha)!=40 or any(c not in "0123456789abcdef" for c in self.head_sha):
            raise ContractError("qualification head_sha must be full lowercase Git SHA")
        if self.status not in {"pass","fail","unknown"}: raise ContractError("qualification status invalid")
        if not isinstance(self.evidence_ref,str): raise ContractError("qualification evidence_ref invalid")

    def to_dict(self):
        return {"name":self.name,"head_sha":self.head_sha,"status":self.status,"evidence_ref":self.evidence_ref}


def _profile_payload(profile,templates):
    return {
        "profile_id":profile.profile_id,
        "groups":{
            "members":sorted(profile.allowed_groups),"reviewers":sorted(profile.reviewer_groups),
            "leads":sorted(profile.lead_groups),"auditors":sorted(profile.auditor_groups),
        },
        "approved_templates":sorted(profile.approved_templates),
        "allow_capabilities":sorted(profile.allow_capabilities),
        "deny_capabilities":sorted(profile.deny_capabilities),
        "risk_ceiling":profile.risk_ceiling,
        "templates":{
            tid:{
                "risk":t.risk,"capabilities":sorted(t.capabilities),
                "acceptance":list(t.acceptance),"required_inputs":sorted(t.required_inputs),
                "optional_inputs":sorted(t.optional_inputs),
            } for tid,t in sorted(templates.items())
        },
    }


def build_readiness_bundle(*,head_sha:str,deployment:EnterpriseCopilotDeployment,
                           qualifications:tuple[QualificationRecord,...],
                           scenarios:tuple[Mapping[str,Any],...],
                           release_artifacts:Mapping[str,str]|None=None,
                           known_limitations:tuple[str,...]=()):
    if not isinstance(head_sha,str) or len(head_sha)!=40 or any(c not in "0123456789abcdef" for c in head_sha):
        raise ContractError("head_sha must be full lowercase Git SHA")
    if not isinstance(deployment,EnterpriseCopilotDeployment): raise ContractError("deployment required")
    if not isinstance(qualifications,tuple) or any(not isinstance(q,QualificationRecord) for q in qualifications):
        raise ContractError("qualifications must be QualificationRecord tuple")
    if any(q.head_sha!=head_sha for q in qualifications):
        raise ContractError("qualification evidence must bind the exact release head")
    if not isinstance(scenarios,tuple) or any(not isinstance(s,Mapping) for s in scenarios):
        raise ContractError("scenarios must be a tuple of mappings")
    if not isinstance(known_limitations,tuple) or any(not isinstance(x,str) or not x.strip() for x in known_limitations):
        raise ContractError("known_limitations invalid")
    artifacts=dict(release_artifacts or {})
    for name,value in artifacts.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(value,str) or len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ContractError("release artifact hashes must be named lowercase SHA-256 values")
    departments=deployment.departments()
    body={
        "schema_version":"residual.copilot.enterprise-readiness.v1",
        "head_sha":head_sha,
        "deployment_config_hash":deployment.config_hash,
        # IDs are security configuration, not secrets, but the bundle records
        # only their hash to avoid unnecessarily redistributing tenant metadata.
        "department_policy":{name:_profile_payload(profile,templates) for name,(profile,templates) in sorted(departments.items())},
        "qualifications":[q.to_dict() for q in sorted(qualifications,key=lambda q:q.name)],
        "scenarios":[dict(s) for s in scenarios],
        "release_artifacts":dict(sorted(artifacts.items())),
        "known_limitations":list(known_limitations),
    }
    body["release_eligible"]=(
        all(q.status=="pass" for q in qualifications)
        and all(bool(dict(s).get("passed")) for s in scenarios)
        and not known_limitations
        and bool(artifacts)
    )
    body["bundle_hash"]=digest(body)
    return body


def verify_readiness_bundle(bundle:Mapping[str,Any])->bool:
    if not isinstance(bundle,Mapping): return False
    expected=bundle.get("bundle_hash")
    if not isinstance(expected,str): return False
    unsigned=dict(bundle); unsigned.pop("bundle_hash",None)
    integrity=digest(unsigned)==expected
    exact=all(q.get("head_sha")==bundle.get("head_sha") for q in bundle.get("qualifications",[]))
    return integrity and exact


def release_eligible(bundle:Mapping[str,Any])->bool:
    return bool(verify_readiness_bundle(bundle) and bundle.get("release_eligible") is True)
