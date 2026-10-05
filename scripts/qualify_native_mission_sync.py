#!/usr/bin/env python3
"""Fail-closed validator for MC-V1-001 installed-native evidence.

Structural validation is intentionally dependency-free. Candidate identity is
supplied externally so a self-consistent evidence file cannot select its own
release candidate. Tokens/secrets are forbidden anywhere in the evidence JSON.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_KEYS={"token","secret","password","api_key","authorization","credential"}

class NativeEvidenceError(ValueError): pass

def req(obj,key,typ=None):
    if key not in obj: raise NativeEvidenceError(f"missing {key}")
    v=obj[key]
    if typ is not None and type(v) is not typ: raise NativeEvidenceError(f"{key} has wrong type")
    return v

def no_secrets(value,path="$"):
    if isinstance(value,dict):
        for k,v in value.items():
            if str(k).lower() in FORBIDDEN_KEYS:
                raise NativeEvidenceError(f"secret-bearing key forbidden at {path}.{k}")
            no_secrets(v,f"{path}.{k}")
    elif isinstance(value,list):
        for i,v in enumerate(value): no_secrets(v,f"{path}[{i}]")

def validate(doc, *, expected_commit, expected_tree, expected_wheel_sha256):
    if not isinstance(doc,dict) or doc.get("schema")!="residual.mc-v1-native-evidence.v1":
        raise NativeEvidenceError("wrong schema")
    no_secrets(doc)
    candidate=req(doc,"candidate",dict)
    if candidate.get("commit")!=expected_commit or candidate.get("tree")!=expected_tree or candidate.get("wheel_sha256")!=expected_wheel_sha256:
        raise NativeEvidenceError("candidate identity does not equal externally selected identity")
    station=req(doc,"station",dict)
    if station.get("false_completion_before_state")!=station.get("false_completion_after_state"):
        raise NativeEvidenceError("false completion changed Station task state")
    if station.get("verified_transition_observed") is not True or station.get("acceptance_authority")!="station_only":
        raise NativeEvidenceError("Station authority proof incomplete")
    harnesses=req(doc,"harnesses",list)
    if len(harnesses)!=2 or {h.get("name") for h in harnesses}!={"hermes","openclaw"}:
        raise NativeEvidenceError("exact Hermes and OpenClaw evidence required")
    common=("hook_registration_proven","context_delivery_proven","inbound_observation_proven","reconnect_proven","restart_proven",
            "wrong_id_rejected","revoked_binding_rejected","stale_attempt_rejected","text_private_by_default","no_acceptance_authority")
    for h in harnesses:
        for field in ("runtime_version","build_identity","conversation_id","instance_id","binding_id"):
            if not isinstance(h.get(field),str) or not h[field].strip(): raise NativeEvidenceError(f"{h.get('name')} missing {field}")
        if not HEX64.fullmatch(str(h.get("plugin_source_sha256",""))): raise NativeEvidenceError(f"{h.get('name')} plugin hash invalid")
        for field in common:
            if h.get(field) is not True: raise NativeEvidenceError(f"{h['name']} missing proof: {field}")
        if h["name"]=="openclaw":
            if h.get("gateway_restart_proven") is not True or h.get("cancellation_stop_proven") is not True:
                raise NativeEvidenceError("OpenClaw restart/cancellation stop proof incomplete")
    demo=req(doc,"two_conversation_demo",dict)
    for field in ("same_station_task","both_conversations_received_current_context","bidirectional_observation_proven",
                  "false_completion_did_not_accept","station_verifier_completed_transition"):
        if demo.get(field) is not True: raise NativeEvidenceError(f"two-conversation demo incomplete: {field}")
    review=req(doc,"independent_review",dict)
    if review.get("verdict")!="PASS" or review.get("reviewer_not_executor") is not True:
        raise NativeEvidenceError("independent review incomplete")
    if not isinstance(review.get("reviewer"),str) or not review["reviewer"].strip(): raise NativeEvidenceError("reviewer missing")
    files=req(doc,"evidence_files",list)
    if not files: raise NativeEvidenceError("no evidence files")
    names=set()
    for f in files:
        if not isinstance(f,dict) or not isinstance(f.get("name"),str) or not HEX64.fullmatch(str(f.get("sha256",""))):
            raise NativeEvidenceError("invalid evidence file record")
        if f["name"] in names: raise NativeEvidenceError("duplicate evidence file name")
        names.add(f["name"])
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("evidence",type=Path)
    p.add_argument("--expected-commit",required=True)
    p.add_argument("--expected-tree",required=True)
    p.add_argument("--expected-wheel-sha256",required=True)
    a=p.parse_args()
    try:
        if not HEX40.fullmatch(a.expected_commit) or not HEX40.fullmatch(a.expected_tree) or not HEX64.fullmatch(a.expected_wheel_sha256):
            raise NativeEvidenceError("invalid externally selected identity")
        doc=json.loads(a.evidence.read_text(encoding="utf-8"))
        validate(doc,expected_commit=a.expected_commit,expected_tree=a.expected_tree,expected_wheel_sha256=a.expected_wheel_sha256)
    except (OSError,json.JSONDecodeError,NativeEvidenceError) as e:
        print(f"FAIL: {e}"); return 1
    print("PASS: MC-V1-001 installed-native evidence contract satisfied")
    return 0

if __name__=="__main__": raise SystemExit(main())
