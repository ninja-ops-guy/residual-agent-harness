"""Exact-head HITL qualification for Copilot consequential writes."""
from __future__ import annotations

from residual.hitl.gateway import HITLEscalationGateway
from residual.integrations.copilot_studio.hitl import CopilotExternalWriteGate, ExternalWriteIntent


def _intent(evidence="e"*64):
    return ExternalWriteIntent(
        mission_id="m-"+"a"*32,
        binding_hash="b"*64,
        plan_hash="c"*64,
        evidence_hash=evidence,
        action="draft_pr.create",
        target="firmware_repo",
    )


def test_exact_head_approval_succeeds_once(tmp_path):
    def auth(record,response,role):
        return response=="approved:"+record["challenge_id"] and role=="engineering_lead"
    gateway=HITLEscalationGateway(b"k"*32,str(tmp_path),authenticate=auth)
    gate=CopilotExternalWriteGate(gateway,("engineering_lead",))
    intent=_intent()
    challenge=gate.request(intent)
    approval=gate.confirm(intent,challenge.challenge_id,"approved:"+challenge.challenge_id,"engineering_lead")
    assert approval.approved
    replay=gate.confirm(intent,challenge.challenge_id,"approved:"+challenge.challenge_id,"engineering_lead")
    assert not replay.approved


def test_changed_evidence_invalidates_pending_approval(tmp_path):
    gateway=HITLEscalationGateway(b"k"*32,str(tmp_path),authenticate=lambda *args:True)
    gate=CopilotExternalWriteGate(gateway,("engineering_lead",))
    old=_intent("1"*64); challenge=gate.request(old)
    new=_intent("2"*64)
    try:
        gate.confirm(new,challenge.challenge_id,"yes","engineering_lead")
    except Exception as exc:
        assert "stale" in str(exc) or "different" in str(exc)
    else:
        raise AssertionError("stale exact-head approval was accepted")


def test_wrong_role_cannot_approve(tmp_path):
    gateway=HITLEscalationGateway(b"k"*32,str(tmp_path),authenticate=lambda *args:True)
    gate=CopilotExternalWriteGate(gateway,("engineering_lead",))
    intent=_intent(); challenge=gate.request(intent)
    approval=gate.confirm(intent,challenge.challenge_id,"yes","firmware_engineer")
    assert not approval.approved


def test_missing_host_authenticator_fails_closed(tmp_path):
    gateway=HITLEscalationGateway(b"k"*32,str(tmp_path))
    gate=CopilotExternalWriteGate(gateway,("engineering_lead",))
    intent=_intent(); challenge=gate.request(intent)
    approval=gate.confirm(intent,challenge.challenge_id,"yes","engineering_lead")
    assert not approval.approved
