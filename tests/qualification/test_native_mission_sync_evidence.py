import copy, importlib.util, json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"scripts"/"qualify_native_mission_sync.py"
S=importlib.util.spec_from_file_location("nativeq",P); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)
C="1"*40; T="2"*40; W="3"*64

def good():
    common=dict(runtime_version="test",build_identity="build",plugin_source_sha256="4"*64,
                conversation_id="conv",instance_id="inst",binding_id="bind",
                hook_registration_proven=True,context_delivery_proven=True,inbound_observation_proven=True,
                reconnect_proven=True,restart_proven=True,wrong_id_rejected=True,revoked_binding_rejected=True,
                stale_attempt_rejected=True,text_private_by_default=True,no_acceptance_authority=True,
                gateway_restart_proven=False,cancellation_stop_proven=False)
    h=dict(common,name="hermes")
    o=dict(common,name="openclaw",gateway_restart_proven=True,cancellation_stop_proven=True)
    return {"schema":"residual.mc-v1-native-evidence.v1","candidate":{"commit":C,"tree":T,"wheel_sha256":W},
      "station":{"project_id":"p","task_id":"t","attempt":1,"spec_hash":"5"*64,
        "false_completion_before_state":"review","false_completion_after_state":"review",
        "verified_transition_observed":True,"acceptance_authority":"station_only"},
      "harnesses":[h,o],
      "two_conversation_demo":{"same_station_task":True,"both_conversations_received_current_context":True,
        "bidirectional_observation_proven":True,"false_completion_did_not_accept":True,"station_verifier_completed_transition":True},
      "independent_review":{"reviewer":"other","reviewed_at":"2026-10-05T00:00:00Z","verdict":"PASS","reviewer_not_executor":True},
      "evidence_files":[{"name":"journal.json","sha256":"6"*64}],
      "non_claims":["No release authority."]}

def validate(d): return m.validate(d,expected_commit=C,expected_tree=T,expected_wheel_sha256=W)
def test_good(): assert validate(good())
def test_false_completion_fails():
    d=good(); d["station"]["false_completion_after_state"]="integrated"
    with pytest.raises(m.NativeEvidenceError): validate(d)
def test_openclaw_stop_proof_required():
    d=good(); d["harnesses"][1]["cancellation_stop_proven"]=False
    with pytest.raises(m.NativeEvidenceError): validate(d)
def test_candidate_self_selection_fails():
    d=good(); d["candidate"]["commit"]="9"*40
    with pytest.raises(m.NativeEvidenceError): validate(d)
def test_secret_key_rejected():
    d=good(); d["harnesses"][0]["token"]="leak"
    with pytest.raises(m.NativeEvidenceError): validate(d)
def test_exact_harness_set_required():
    d=good(); d["harnesses"][0]["name"]="openclaw"
    with pytest.raises(m.NativeEvidenceError): validate(d)
