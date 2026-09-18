"""Acceptance tests for the deterministic hybrid-Entra walkthrough."""
from __future__ import annotations

from examples.copilot_studio.hybrid_entra_demo import run_demo


def test_hybrid_demo_positive_negative_and_revocation_paths():
    result = run_demo()

    assert result["demo_mode"] == (
        "cryptographic-oidc-fixture-not-live-microsoft-tenant"
    )
    assert result["device_trust"] == {
        "assumed_for_walkthrough": "hybrid-entra-joined-and-compliant",
        "enforced_by": "microsoft-conditional-access-upstream",
        "residual_device_attestation": False,
    }

    positive = result["positive_firmware"]
    assert positive["submit_status"] == 202
    assert positive["state"] == "prepared"
    assert positive["template_id"] == "firmware-repository-analysis"
    assert positive["principal_oid"] == (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )

    handoff = result["factory_handoff"]
    assert handoff["prepared"] is True
    assert handoff["factory_execution_started"] is False
    assert handoff["station_receipt_issued"] is False
    assert set(handoff["allowed_tools"]) == {"read_file", "write_file"}
    assert set(handoff["forbidden_tools"]) == {"network", "shell"}
    assert handoff["allowed_outputs"] == [
        "reports/firmware-analysis.json"
    ]

    assert result["negative_mechanical"] == {
        "status": 403,
        "code": "department_denied",
    }
    assert result["membership_revocation"] == {
        "status": 403,
        "code": "department_denied",
    }

    assert result["claims"] == {
        "production_write": False,
        "merge_authority": False,
        "arbitrary_shell": False,
        "arbitrary_network": False,
    }


def test_hybrid_demo_is_deterministic_at_authority_boundary():
    first = run_demo()
    second = run_demo()

    assert (
        first["positive_firmware"]["mission_id"]
        == second["positive_firmware"]["mission_id"]
    )
    assert (
        first["factory_handoff"]["catalog_hash"]
        == second["factory_handoff"]["catalog_hash"]
    )
    assert (
        first["factory_handoff"]["binding_hash"]
        == second["factory_handoff"]["binding_hash"]
    )
    assert (
        first["factory_handoff"]["factory_plan_hash"]
        == second["factory_handoff"]["factory_plan_hash"]
    )
    assert (
        first["factory_handoff"]["worker_contract_hash"]
        == second["factory_handoff"]["worker_contract_hash"]
    )
