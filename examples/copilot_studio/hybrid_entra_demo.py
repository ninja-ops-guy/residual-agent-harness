"""Deterministic application-layer demo for the Copilot Studio pilot.

This exercises the actual RESIDUAL Copilot gateway, a cryptographically signed
OIDC fixture, department authorization, and the read-only Firmware Factory
handoff. It does not contact Microsoft, attest a Windows device, execute a
Factory worker, or manufacture a Station receipt.

Run from the repository root:
    python examples/copilot_studio/hybrid_entra_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from residual.iam.crypto import jwt_encode, rsa_generate_keypair
from residual.iam.oidc import OIDCClient, OIDCSettings
from residual.integrations.copilot_studio import (
    ApprovedRepository,
    CopilotHTTPAdapter,
    CopilotMissionStore,
    CopilotStudioService,
    FirmwareFactoryAdapter,
    FirmwarePolicy,
    OIDCBearerAuthenticator,
    ResourceCatalog,
)


NOW = 1_789_750_000
TENANT = "11111111-1111-4111-8111-111111111111"
CLIENT = "22222222-2222-4222-8222-222222222222"
FIRMWARE_GROUP = "33333333-3333-4333-8333-333333333333"
MECHANICAL_GROUP = "33333333-3333-4333-8333-333333333334"
FIRMWARE_OID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
MECHANICAL_OID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
AUDIENCE = "residual-api-demo"


def _token(key, *, oid: str, group: str, subject: str) -> str:
    return jwt_encode(
        {
            "iss": ISSUER,
            "sub": subject,
            "aud": AUDIENCE,
            "iat": NOW,
            "exp": NOW + 300,
            "tid": TENANT,
            "oid": oid,
            "groups": [group],
            "roles": [],
            "scp": "access_as_user",
            "azp": CLIENT,
            "amr": ["pwd", "mfa"],
        },
        key,
        alg="RS256",
        headers={"kid": "demo-key"},
    )


def _dispatch(http, method: str, path: str, token: str, body=None):
    return http.dispatch(
        method,
        path,
        headers={"Authorization": f"Bearer {token}"},
        body=None if body is None else json.dumps(body),
        now=NOW,
    )


def run_demo() -> dict:
    key = rsa_generate_keypair(1024)
    oidc = OIDCClient(
        OIDCSettings(issuer=ISSUER, client_id=AUDIENCE),
        {"demo-key": key.public_key},
    )
    store = CopilotMissionStore()
    policy = FirmwarePolicy(
        allowed_tenants=(TENANT,),
        allowed_groups=(FIRMWARE_GROUP,),
        required_scopes=("access_as_user",),
        allowed_clients=(CLIENT,),
        max_active_missions=4,
    )
    service = CopilotStudioService(
        OIDCBearerAuthenticator(oidc),
        policy=policy,
        store=store,
    )
    http = CopilotHTTPAdapter(service)

    firmware_token = _token(
        key,
        oid=FIRMWARE_OID,
        group=FIRMWARE_GROUP,
        subject="firmware-user-fixture",
    )
    mechanical_token = _token(
        key,
        oid=MECHANICAL_OID,
        group=MECHANICAL_GROUP,
        subject="mechanical-user-fixture",
    )
    firmware_after_group_removal = _token(
        key,
        oid=FIRMWARE_OID,
        group=MECHANICAL_GROUP,
        subject="firmware-user-fixture",
    )

    submission = _dispatch(
        http,
        "POST",
        "/v1/copilot/missions",
        firmware_token,
        {
            "request_id": "hybrid-demo-1",
            "template_id": "firmware-repository-analysis",
            "objective": (
                "Analyze the approved firmware snapshot for the reported defect "
                "and produce evidence without modifying source files."
            ),
            "inputs": {
                "repository_id": "firmware-demo",
                "analysis_profile_id": "default-analysis",
            },
        },
    )
    if submission.status != 202:
        raise RuntimeError(f"demo submission failed: {submission.body}")

    mission_id = submission.body["mission_id"]
    record = store.visible(
        mission_id,
        service._principal(firmware_token, NOW),
    )
    catalog = ResourceCatalog((
        ApprovedRepository(
            repository_id="firmware-demo",
            repository_root="/srv/residual/demo-firmware",
            input_commit="a" * 40,
            read_selectors=("README.md", "include/", "src/"),
            forbidden_selectors=("secrets/",),
            analysis_profiles=frozenset({"default-analysis"}),
        ),
    ))
    handoff = FirmwareFactoryAdapter(catalog).prepare(record)

    mechanical_attempt = _dispatch(
        http,
        "POST",
        "/v1/copilot/missions",
        mechanical_token,
        {
            "request_id": "hybrid-demo-mechanical-1",
            "template_id": "firmware-repository-analysis",
            "objective": "Attempt the Firmware-only mission.",
            "inputs": {
                "repository_id": "firmware-demo",
                "analysis_profile_id": "default-analysis",
            },
        },
    )
    membership_revocation = _dispatch(
        http,
        "GET",
        f"/v1/copilot/missions/{mission_id}",
        firmware_after_group_removal,
    )

    return {
        "demo_mode": "cryptographic-oidc-fixture-not-live-microsoft-tenant",
        "device_trust": {
            "assumed_for_walkthrough": "hybrid-entra-joined-and-compliant",
            "enforced_by": "microsoft-conditional-access-upstream",
            "residual_device_attestation": False,
        },
        "positive_firmware": {
            "submit_status": submission.status,
            "mission_id": mission_id,
            "state": submission.body["state"],
            "principal_oid": record.mission.principal_id,
            "tenant_id": record.mission.tenant_id,
            "template_id": record.template_id,
            "risk": record.risk,
        },
        "factory_handoff": {
            "prepared": True,
            "catalog_hash": handoff.catalog_hash,
            "binding_hash": handoff.binding_hash,
            "factory_plan_hash": handoff.plan.graph_hash,
            "worker_contract_hash": handoff.contract.contract_hash,
            "input_commit": handoff.contract.input_commit,
            "read_selectors": list(handoff.contract.inputs),
            "allowed_outputs": list(handoff.contract.allowed_outputs),
            "allowed_tools": list(handoff.contract.allowed_tools),
            "forbidden_tools": list(handoff.contract.forbidden_tools),
            "factory_execution_started": False,
            "station_receipt_issued": False,
        },
        "negative_mechanical": {
            "status": mechanical_attempt.status,
            "code": mechanical_attempt.body["code"],
        },
        "membership_revocation": {
            "status": membership_revocation.status,
            "code": membership_revocation.body["code"],
        },
        "claims": {
            "production_write": False,
            "merge_authority": False,
            "arbitrary_shell": False,
            "arbitrary_network": False,
        },
    }


def main() -> int:
    result = run_demo()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
