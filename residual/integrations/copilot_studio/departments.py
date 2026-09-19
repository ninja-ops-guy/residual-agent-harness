"""Enterprise department templates and Entra-group RBAC profiles."""
from __future__ import annotations

from dataclasses import dataclass

from ...core import ContractError, identifier
from .policy import DepartmentProfile, MissionTemplate, firmware_profile, firmware_templates

GLOBAL_DENY = frozenset({
    "pr.merge","production.write","policy.modify","qualification.bypass",
    "verifier.bypass","secrets.read","shell.host","network.arbitrary",
})


@dataclass(frozen=True)
class DepartmentGroups:
    members: frozenset[str]
    reviewers: frozenset[str] = frozenset()
    leads: frozenset[str] = frozenset()
    auditors: frozenset[str] = frozenset()

    def __post_init__(self):
        if not self.members:
            raise ContractError("department requires member groups")
        for values in (self.members,self.reviewers,self.leads,self.auditors):
            if not isinstance(values,frozenset) or any(not isinstance(v,str) or not v.strip() for v in values):
                raise ContractError("department groups must be frozensets of Entra group ids")


def mechanical_templates()->dict[str,MissionTemplate]:
    return {
        "mechanical-design-review":MissionTemplate(
            "mechanical-design-review","low",
            frozenset({"document.analyze","requirements.trace","evidence.read_own"}),
            ("Review the approved design evidence.","Separate observations from hypotheses.","Do not change released design state."),
            required_inputs=frozenset({"knowledge_source_id"}),
        ),
        "mechanical-change-impact":MissionTemplate(
            "mechanical-change-impact","medium",
            frozenset({"document.analyze","requirements.trace","change.propose","evidence.read_own"}),
            ("Identify interfaces and requirements affected by the proposed change.","Return evidence-backed impact only; release is prohibited."),
            required_inputs=frozenset({"knowledge_source_id","change_set_id"}),
        ),
    }


def electromechanical_templates()->dict[str,MissionTemplate]:
    return {
        "electromechanical-interface-review":MissionTemplate(
            "electromechanical-interface-review","medium",
            frozenset({"document.analyze","requirements.trace","interface.analyze","evidence.read_own"}),
            ("Trace electrical/mechanical interface assumptions.","Identify conflicting requirements with evidence.","Do not alter released baselines."),
            required_inputs=frozenset({"knowledge_source_id","interface_set_id"}),
        ),
        "electromechanical-integration-review":MissionTemplate(
            "electromechanical-integration-review","medium",
            frozenset({"document.analyze","tests.review","requirements.trace","evidence.read_own"}),
            ("Review integration evidence against approved requirements.","Flag missing or contradictory evidence."),
            required_inputs=frozenset({"knowledge_source_id","test_evidence_id"}),
        ),
    }


def automated_testing_templates()->dict[str,MissionTemplate]:
    return {
        "automated-test-plan-review":MissionTemplate(
            "automated-test-plan-review","low",
            frozenset({"tests.review","requirements.trace","evidence.read_own"}),
            ("Check test coverage against approved requirements.","Do not modify test infrastructure."),
            required_inputs=frozenset({"knowledge_source_id","test_profile_id"}),
        ),
        "automated-test-isolated-run":MissionTemplate(
            "automated-test-isolated-run","medium",
            frozenset({"sandbox.build","tests.run_approved","evidence.read_own"}),
            ("Run only the administrator-approved isolated test profile.","Return deterministic pass/fail evidence."),
            required_inputs=frozenset({"repository_id","build_profile_id"}),
        ),
    }


def quality_assurance_templates()->dict[str,MissionTemplate]:
    return {
        "quality-evidence-review":MissionTemplate(
            "quality-evidence-review","low",
            frozenset({"evidence.review","qualification.verify","evidence.read_own"}),
            ("Independently review supplied evidence.","Do not modify implementation under review."),
            required_inputs=frozenset({"evidence_set_id"}),
        ),
        "quality-release-readiness":MissionTemplate(
            "quality-release-readiness","medium",
            frozenset({"evidence.review","qualification.verify","requirements.trace","evidence.read_own"}),
            ("Check traceability and qualification completeness.","Produce findings, not a deployment action."),
            required_inputs=frozenset({"evidence_set_id","release_candidate_id"}),
        ),
    }


def _profile(profile_id:str,groups:DepartmentGroups,templates:dict[str,MissionTemplate])->DepartmentProfile:
    identifier(profile_id)
    caps=frozenset(cap for t in templates.values() for cap in t.capabilities)
    return DepartmentProfile(
        profile_id=profile_id,
        allowed_groups=groups.members,
        approved_templates=frozenset(templates),
        allow_capabilities=caps,
        deny_capabilities=GLOBAL_DENY,
        reviewer_groups=groups.reviewers,
        lead_groups=groups.leads,
        auditor_groups=groups.auditors,
        risk_ceiling="medium",
    )


def mechanical_profile(groups:DepartmentGroups)->DepartmentProfile:
    return _profile("mechanical-engineering",groups,mechanical_templates())


def electromechanical_profile(groups:DepartmentGroups)->DepartmentProfile:
    return _profile("electromechanical-engineering",groups,electromechanical_templates())


def automated_testing_profile(groups:DepartmentGroups)->DepartmentProfile:
    return _profile("automated-testing",groups,automated_testing_templates())


def quality_assurance_profile(groups:DepartmentGroups)->DepartmentProfile:
    return _profile("quality-assurance",groups,quality_assurance_templates())


def firmware_enterprise_profile(groups:DepartmentGroups)->DepartmentProfile:
    return firmware_profile(
        allowed_groups=groups.members,
        reviewer_groups=groups.reviewers,
        lead_groups=groups.leads,
        auditor_groups=groups.auditors,
    )


def department_catalog(groups:dict[str,DepartmentGroups]):
    required={"firmware","mechanical","electromechanical","automated_testing","quality_assurance"}
    if set(groups)!=required:
        raise ContractError("department group catalog must define all five engineering departments")
    return {
        "firmware":(firmware_enterprise_profile(groups["firmware"]),firmware_templates()),
        "mechanical":(mechanical_profile(groups["mechanical"]),mechanical_templates()),
        "electromechanical":(electromechanical_profile(groups["electromechanical"]),electromechanical_templates()),
        "automated_testing":(automated_testing_profile(groups["automated_testing"]),automated_testing_templates()),
        "quality_assurance":(quality_assurance_profile(groups["quality_assurance"]),quality_assurance_templates()),
    }
