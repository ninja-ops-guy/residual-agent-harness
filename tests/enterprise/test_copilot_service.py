"""Service composition qualification for all five Copilot departments."""
from __future__ import annotations

from residual.iam.crypto import jwt_encode,rsa_generate_keypair
from residual.integrations.copilot_studio.deployment import EnterpriseCopilotDeployment
from residual.integrations.copilot_studio.gateway import InMemoryMissionBackend
from residual.integrations.copilot_studio.service import DepartmentCopilotService
from residual.integrations.copilot_studio.store import InMemoryMissionStore


def _deployment():
    ids=[f"00000000-0000-0000-0000-{i:012d}" for i in range(1,16)]
    return EnterpriseCopilotDeployment("https://residual.example.com",*ids)


def _token(service,key,group):
    return jwt_encode({
        "iss":service.deployment.entra().issuer,"sub":"user","aud":service.deployment.entra().audience,
        "iat":1000,"exp":1200,"tid":service.deployment.tenant_id,"oid":"object-user",
        "scp":"access_as_user","groups":[group],"azp":service.deployment.connector_client_app_id,
    },key,alg="RS256",headers={"kid":"k1"})


def test_all_department_services_share_same_gateway_path():
    dep=_deployment(); key=rsa_generate_keypair(1024)
    departments=dep.departments()
    for name,(profile,templates) in departments.items():
        service=DepartmentCopilotService(
            name,dep,InMemoryMissionBackend(),InMemoryMissionStore(),
            jwks_provider=lambda kid:key.public_key if kid=="k1" else None,
        )
        token=_token(service,key,next(iter(profile.allowed_groups)))
        template=next(iter(templates.values()))
        inputs={k:(k.replace("_id","")+"_fixture") for k in template.required_inputs}
        response=service.api.handle(
            "POST","/v1/copilot/missions","Bearer "+token,
            {"request_id":"service-1","template_id":template.template_id,
             "objective":"Perform approved bounded engineering review.","inputs":inputs},
            now=1100,
        )
        assert response.status==202
        assert response.body["template_id"]==template.template_id


def test_cross_department_group_cannot_submit():
    dep=_deployment(); key=rsa_generate_keypair(1024)
    fw_profile,_=dep.departments()["firmware"]
    mechanical_group=next(iter(dep.departments()["mechanical"][0].allowed_groups))
    service=DepartmentCopilotService(
        "firmware",dep,InMemoryMissionBackend(),InMemoryMissionStore(),
        jwks_provider=lambda kid:key.public_key,
    )
    token=_token(service,key,mechanical_group)
    response=service.api.handle(
        "POST","/v1/copilot/missions","Bearer "+token,
        {"request_id":"cross-1","template_id":"firmware-repository-analysis",
         "objective":"Analyze firmware.","inputs":{"repository_id":"firmware_sample"}},
        now=1100,
    )
    assert response.status==403


def test_reviewer_auditor_and_lead_permissions_are_enforced_end_to_end():
    dep=_deployment(); key=rsa_generate_keypair(1024)
    backend=InMemoryMissionBackend(); store=InMemoryMissionStore()
    service=DepartmentCopilotService(
        "firmware",dep,backend,store,jwks_provider=lambda kid:key.public_key,
    )
    profile,_=dep.departments()["firmware"]
    owner_token=_token(service,key,next(iter(profile.allowed_groups)))
    created=service.api.handle(
        "POST","/v1/copilot/missions","Bearer "+owner_token,
        {"request_id":"rbac-owner","template_id":"firmware-repository-analysis",
         "objective":"Analyze firmware.","inputs":{"repository_id":"firmware_sample"}},now=1100,
    )
    mid=created.body["mission_id"]

    def token_for(oid,group):
        return jwt_encode({
            "iss":service.deployment.entra().issuer,"sub":oid,"aud":service.deployment.entra().audience,
            "iat":1000,"exp":1200,"tid":service.deployment.tenant_id,"oid":oid,
            "scp":"access_as_user","groups":[group],"azp":service.deployment.connector_client_app_id,
        },key,alg="RS256",headers={"kid":"k1"})

    reviewer=token_for("reviewer",next(iter(profile.reviewer_groups)))
    auditor=token_for("auditor",next(iter(profile.auditor_groups)))
    lead=token_for("lead",next(iter(profile.lead_groups)))

    assert service.api.handle("GET",f"/v1/copilot/missions/{mid}/evidence","Bearer "+reviewer,None,now=1100).status==200
    assert service.api.handle("POST",f"/v1/copilot/missions/{mid}/cancel","Bearer "+reviewer,{},now=1100).status==404
    assert service.api.handle("GET",f"/v1/copilot/missions/{mid}","Bearer "+auditor,None,now=1100).status==200
    assert service.api.handle("POST",f"/v1/copilot/missions/{mid}/cancel","Bearer "+auditor,{},now=1100).status==404
    assert service.api.handle("POST",f"/v1/copilot/missions/{mid}/cancel","Bearer "+lead,{},now=1100).status==202


def test_department_reviewer_does_not_cross_department_boundary():
    dep=_deployment(); key=rsa_generate_keypair(1024)
    fw_backend=InMemoryMissionBackend(); fw_store=InMemoryMissionStore()
    fw_service=DepartmentCopilotService(
        "firmware",dep,fw_backend,fw_store,jwks_provider=lambda kid:key.public_key,
    )
    fw_profile,_=dep.departments()["firmware"]
    owner_token=_token(fw_service,key,next(iter(fw_profile.allowed_groups)))
    created=fw_service.api.handle(
        "POST","/v1/copilot/missions","Bearer "+owner_token,
        {"request_id":"review-boundary","template_id":"firmware-repository-analysis",
         "objective":"Analyze firmware.","inputs":{"repository_id":"firmware_sample"}},now=1100,
    )
    mid=created.body["mission_id"]

    mechanical_reviewer=next(iter(dep.departments()["mechanical"][0].reviewer_groups))
    reviewer_token=jwt_encode({
        "iss":fw_service.deployment.entra().issuer,"sub":"mech-reviewer",
        "aud":fw_service.deployment.entra().audience,"iat":1000,"exp":1200,
        "tid":fw_service.deployment.tenant_id,"oid":"mech-reviewer",
        "scp":"access_as_user","groups":[mechanical_reviewer],
        "azp":fw_service.deployment.connector_client_app_id,
    },key,alg="RS256",headers={"kid":"k1"})
    denied=fw_service.api.handle(
        "GET",f"/v1/copilot/missions/{mid}/evidence",
        "Bearer "+reviewer_token,None,now=1100,
    )
    assert denied.status==404
    assert denied.body["code"]=="not_found"
