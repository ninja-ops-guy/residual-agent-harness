"""Deployment, hybrid-Entra demo, and readiness evidence qualification."""
from __future__ import annotations

import copy

from residual.integrations.copilot_studio.demo import DemoExpectation, HybridEntraDemoHarness
from residual.integrations.copilot_studio.deployment import EnterpriseCopilotDeployment
from residual.integrations.copilot_studio.readiness import QualificationRecord,build_readiness_bundle,verify_readiness_bundle,release_eligible
from tests.enterprise.test_copilot_studio import auth,make_api,make_token,payload


def _deployment():
    vals=[f"00000000-0000-0000-0000-{i:012d}" for i in range(1,16)]
    return EnterpriseCopilotDeployment(
        "https://residual.example.com",*vals
    )


def test_deployment_config_builds_all_departments_and_content_hash():
    d=_deployment()
    assert d.api_base_url=="https://residual.example.com"
    assert set(d.departments())=={"firmware","mechanical","electromechanical","automated_testing","quality_assurance"}
    assert len(d.config_hash)==64
    assert d.entra().tenant_id==d.tenant_id


def test_hybrid_demo_harness_redacts_tokens_and_records_expected_failures():
    api,_,_=make_api()
    owner=auth(make_token())
    outsider=auth(make_token(oid="other",sub="other"))
    h=HybridEntraDemoHarness(api,now=1_800_000_000,upstream_controls={
        "hybrid_entra_joined":True,"conditional_access":True,"mfa":True,"device_compliant":True,
    })
    created=h.step(DemoExpectation(
        "firmware-submit","POST","/v1/copilot/missions",owner,202,
        payload("demo-1"),
    ))
    mid=created.body["mission_id"]
    h.step(DemoExpectation("owner-status","GET",f"/v1/copilot/missions/{mid}",owner,200))
    h.step(DemoExpectation("cross-user-denied","GET",f"/v1/copilot/missions/{mid}/evidence",outsider,404,expected_code="not_found"))
    report=h.report()
    assert report["all_passed"]
    assert report["upstream_controls_authoritative_for_residual"] is False
    assert "Bearer " not in repr(report)


def test_readiness_bundle_requires_exact_head_passes():
    d=_deployment(); sha="a"*40
    qs=(QualificationRecord("copilot-matrix",sha,"pass","actions:1"),QualificationRecord("security-review",sha,"pass","doc:1"))
    bundle=build_readiness_bundle(
        head_sha=sha,deployment=d,qualifications=qs,
        scenarios=({"name":"hybrid-demo","passed":True},),
        release_artifacts={"managed_solution_zip":"c"*64},
        known_limitations=("Live tenant import still requires environment-owned solution export.",),
    )
    assert verify_readiness_bundle(bundle)
    assert not release_eligible(bundle)
    tampered=copy.deepcopy(bundle); tampered["scenarios"][0]["passed"]=False
    assert not verify_readiness_bundle(tampered)


def test_failed_qualification_does_not_verify_ready_bundle():
    d=_deployment(); sha="b"*40
    bundle=build_readiness_bundle(
        head_sha=sha,deployment=d,
        qualifications=(QualificationRecord("copilot-matrix",sha,"fail"),),
        scenarios=({"name":"x","passed":False},),
        release_artifacts={"managed_solution_zip":"d"*64},
    )
    assert verify_readiness_bundle(bundle)
    assert not release_eligible(bundle)


def test_release_eligible_requires_artifact_passed_scenarios_and_no_limitations():
    d=_deployment(); sha="e"*40
    bundle=build_readiness_bundle(
        head_sha=sha,deployment=d,
        qualifications=(QualificationRecord("copilot-matrix",sha,"pass"),),
        scenarios=({"name":"hybrid-demo","passed":True},),
        release_artifacts={"managed_solution_zip":"f"*64},
    )
    assert verify_readiness_bundle(bundle)
    assert release_eligible(bundle)
