"""Qualification for native Copilot Studio department templates and RBAC."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from residual.core import ContractError
from residual.integrations.copilot_studio import (
    DepartmentProfile,
    DepartmentRegistry,
    FirmwareFactoryAdapter,
    FirmwarePolicy,
)


ROOT = Path(__file__).resolve().parents[2]
DEPARTMENT_DIR = (
    ROOT / "residual/integrations/copilot_studio/departments"
)
EXPECTED_DEPARTMENTS = {
    "firmware-engineering",
    "mechanical-engineering",
    "electromechanical-engineering",
    "automated-testing",
    "quality-assurance",
}


def load_profiles():
    profiles = []
    for path in sorted(DEPARTMENT_DIR.glob("*.yaml")):
        if path.name == "rbac.yaml":
            continue
        profiles.append(DepartmentProfile.from_dict(
            yaml.safe_load(path.read_text())
        ))
    return tuple(profiles)


def profile_map():
    return {profile.department_id: profile for profile in load_profiles()}


def test_exact_department_catalog_and_unique_native_assets():
    profiles = load_profiles()
    assert {profile.department_id for profile in profiles} == EXPECTED_DEPARTMENTS
    registry = DepartmentRegistry(profiles)
    assert set(registry.profiles) == EXPECTED_DEPARTMENTS

    solutions = [profile.agent.solution_name for profile in profiles]
    chat_groups = [profile.agent.chat_security_group_id for profile in profiles]
    maker_groups = [profile.agent.maker_security_group_id for profile in profiles]
    assert len(solutions) == len(set(solutions))
    assert len(chat_groups) == len(set(chat_groups))
    assert len(maker_groups) == len(set(maker_groups))
    assert not set(chat_groups) & set(maker_groups)


def test_all_agents_use_native_generative_orchestration_and_shared_gateway():
    for profile in load_profiles():
        assert profile.agent.orchestration == "generative"
        assert profile.agent.publish_status == "inactive"
        assert profile.agent.connector_reference == "residual-gateway"
        assert set(profile.agent.connector_operations) == {
            "submitResidualMission",
            "getResidualMission",
            "getResidualMissionEvidence",
            "cancelResidualMission",
        }
        assert profile.agent.knowledge_slots


def test_only_real_factory_capability_is_advertised_executable():
    profiles = profile_map()
    firmware = profiles["firmware-engineering"]
    assert firmware.backend_status == "pilot"
    assert firmware.residual.executable_templates == (
        "firmware-repository-analysis",
    )
    assert set(firmware.residual.planned_templates) == {
        "firmware-sandbox-build",
        "firmware-test-triage",
    }
    assert FirmwareFactoryAdapter.template_id in firmware.residual.executable_templates

    for department_id, profile in profiles.items():
        if department_id == "firmware-engineering":
            continue
        assert profile.backend_status == "planned"
        assert profile.residual.executable_templates == ()


def test_firmware_department_does_not_overclaim_gateway_templates():
    p = FirmwarePolicy(
        allowed_tenants=("11111111-1111-4111-8111-111111111111",),
        allowed_groups=("33333333-3333-4333-8333-333333333333",),
        required_scopes=("access_as_user",),
        allowed_clients=("22222222-2222-4222-8222-222222222222",),
    )
    firmware = profile_map()["firmware-engineering"]
    declared = (
        set(firmware.residual.executable_templates)
        | set(firmware.residual.planned_templates)
    )
    assert declared == set(p.templates)
    assert set(firmware.residual.executable_templates) == {
        FirmwareFactoryAdapter.template_id
    }


def test_quality_profile_is_explicit_independent_review_not_implementation():
    qa = profile_map()["quality-assurance"]
    assert qa.residual.evidence_scope == "authorized-cross-department-review"
    assert qa.residual.executable_templates == ()
    assert set(qa.residual.assigned_agent_roles) == {
        "evidence-reviewer",
        "quality-analyst",
        "verifier",
    }


def test_planned_profile_cannot_be_made_active_or_executable_by_metadata():
    raw = yaml.safe_load(
        (
            DEPARTMENT_DIR / "mechanical-engineering.yaml"
        ).read_text()
    )
    raw["agent"]["publish_status"] = "active"
    with pytest.raises(ContractError):
        DepartmentProfile.from_dict(raw)

    raw = yaml.safe_load(
        (
            DEPARTMENT_DIR / "mechanical-engineering.yaml"
        ).read_text()
    )
    raw["residual"]["executable_templates"] = ["mechanical-design-analysis"]
    with pytest.raises(ContractError):
        DepartmentProfile.from_dict(raw)


def test_department_registry_is_immutable_and_rejects_duplicates():
    profiles = load_profiles()
    registry = DepartmentRegistry(profiles)
    with pytest.raises(TypeError):
        registry.profiles["evil"] = profiles[0]
    with pytest.raises(ContractError):
        DepartmentRegistry((profiles[0], profiles[0]))


def test_department_profile_has_no_direct_capability_grant_field():
    for path in DEPARTMENT_DIR.glob("*.yaml"):
        if path.name == "rbac.yaml":
            continue
        raw = yaml.safe_load(path.read_text())
        assert "capabilities" not in raw
        assert "permissions" not in raw["residual"]
        assert "allowed_tools" not in raw["residual"]


def test_rbac_matrix_preserves_separation_of_duties():
    rbac = yaml.safe_load((DEPARTMENT_DIR / "rbac.yaml").read_text())
    assert rbac["schema_version"] == "copilot-rbac-v1"

    roles = rbac["roles"]
    assert roles["copilot-agent-maker"]["residual"] == []
    assert "residual.authority.by-maker-role" in (
        roles["copilot-agent-maker"]["denied"]
    )
    assert "engineering-authority.by-platform-role" in (
        roles["platform-admin"]["denied"]
    )
    assert "candidate.modify.under-review" in (
        roles["qa-reviewer"]["denied"]
    )
    assert roles["auditor"]["copilot"] == []
    assert "mission.submit" in roles["auditor"]["denied"]

    positive = {
        permission
        for role in roles.values()
        for bucket in ("copilot", "residual")
        for permission in role[bucket]
    }
    assert "verifier.bypass" not in positive
    assert "qualification.bypass" not in positive
    assert "production.write" not in positive
    assert "pr.merge" not in positive

    sod = {
        item["id"] for item in rbac["separation_of_duties"]
    }
    assert sod == {
        "sod-policy-approval",
        "sod-qa-candidate",
        "sod-maker-runtime",
        "sod-platform-engineering",
    }


def test_all_department_chat_and_maker_groups_are_separate():
    for profile in load_profiles():
        assert (
            profile.agent.chat_security_group_id
            != profile.agent.maker_security_group_id
        )


def test_native_deployment_doc_refuses_fake_solution_zip():
    text = (
        ROOT / "docs/integrations/COPILOT_STUDIO_NATIVE_DEPLOYMENT.md"
    ).read_text()
    assert "Do not fabricate a Power Platform solution ZIP" in text
    assert "generative orchestration" in text
    assert "end-user Microsoft Entra/OBO" in text
    assert "Conditional Access/device-compliance" in text
