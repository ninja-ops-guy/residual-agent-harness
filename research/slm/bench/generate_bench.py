#!/usr/bin/env python3
"""Residual Control Bench v0 generator (Lane C, SLM-00) — CD-XVAL remediated.

Emits exactly 1,000 frozen bench items conforming to Lane D's verifier
contracts (research/slm/verifiers/*.py on branch slm00/verifiers; each module
docstring is the item contract):

  worker_routing 200, contract_compilation 150, evidence_sufficiency 150,
  retry_escalate_abort 100, budget_decisions 100, failure_classification 100,
  adversarial_malformed 100, stale_state_authority 100.

CD-XVAL resolution (see docs/research/EXP-M6-SLM/CD-XVAL-REPORT.md and
CONTROL-BENCH-V0-DESIGN.md):
  X1: verifier_ref is Lane D's registry ID (slm00.verifier.<category>).
  X2: category identifiers are Lane D's exact ids (snake_case, plural where
      Lane D uses plural: budget_decisions).
  X3: input_state/expected_output shapes are Lane D's contracts. Lane C's
      divergent task semantics (topology/utility selection, per-dimension
      approve/deny, free-form reason strings, ad-hoc adversarial outputs)
      were replaced. Authentic seeds that cannot be expressed in Lane D's
      contract shape are DEFERRED (documented in the design doc), not forced.
  MATERIAL: exact-dup rejection is enforced at generation time (canonical
      content key dedupe with salt escalation); every contamination group is
      guaranteed duplicate-free; expansion rules draw from enlarged seed
      dimensions per category.

Usage:
    python generate_bench.py --seed-dir research/slm/bench/seed \
        --out research/slm/bench/control-bench-v0.jsonl \
        --manifest research/slm/bench/control-bench-v0-manifest.json
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

BENCH_VERSION = "control-bench-v0"
RNG_SEED = 20260920

CATEGORIES = [
    # (code, Lane D category id, target_count)
    ("WR", "worker_routing", 200),
    ("CC", "contract_compilation", 150),
    ("ES", "evidence_sufficiency", 150),
    ("REA", "retry_escalate_abort", 100),
    ("BD", "budget_decisions", 100),
    ("FC", "failure_classification", 100),
    ("AM", "adversarial_malformed", 100),
    ("SA", "stale_state_authority", 100),
]

SEED_FILENAMES = {
    "WR": "worker-routing.json",
    "CC": "contract-compilation.json",
    "ES": "evidence-sufficiency.json",
    "REA": "retry-escalate-abort.json",
    "BD": "budget-decision.json",
    "FC": "failure-classification.json",
    "AM": "adversarial-malformed.json",
    "SA": "stale-state-authority.json",
}

# X1: Lane D registry IDs (research/slm/verifiers/MANIFEST.json).
VERIFIER_REFS = {code: "slm00.verifier.%s" % cat for code, cat, _ in CATEGORIES}

# Inline output-schema fragments describing the Lane D candidate-output shape.
OUTPUT_SCHEMAS = {
    "WR": {"type": "object", "required": ["action", "route"],
           "properties": {"action": {"enum": ["route", "hold", "escalate"]},
                          "route": {"type": ["string", "null"]}},
           "additionalProperties": True},
    "CC": {"type": "object", "required": ["contract"],
           "properties": {"contract": {"type": "object"}}, "additionalProperties": True},
    "ES": {"type": "object", "required": ["sufficient", "missing_requirements"],
           "properties": {"sufficient": {"type": "boolean"},
                          "missing_requirements": {"type": "array", "items": {"type": "string"}},
                          "verifier_outputs": {"type": "array", "items": {"type": "string"}}},
           "additionalProperties": True},
    "REA": {"type": "object", "required": ["action", "reason_code"],
            "properties": {"action": {"enum": ["retry", "escalate", "abort"]},
                           "reason_code": {"type": "string"}},
            "additionalProperties": True},
    "BD": {"type": "object", "required": ["decision"],
           "properties": {"decision": {"type": "string"}}, "additionalProperties": True},
    "FC": {"type": "object", "required": ["label"],
           "properties": {"label": {"type": "string"}}, "additionalProperties": True},
    "AM": {"type": "object", "required": ["reject", "reason_code"],
           "properties": {"reject": {"const": True}, "reason_code": {"type": "string"},
                          "action": {"type": "string"}}, "additionalProperties": True},
    "SA": {"type": "object", "required": ["legal", "violation"],
           "properties": {"legal": {"type": "boolean"},
                          "violation": {"enum": [None, "STALE_RECEIPT",
                                                 "AUTHORITY_SCOPE_EXCEEDED",
                                                 "ILLEGAL_TRANSITION",
                                                 "PROTECTED_BOUNDARY_TOUCHED"]}},
           "additionalProperties": True},
}

CAP_POOL = ["parse", "search", "synthesize", "code", "verify", "integrate",
            "plan", "translate", "classify", "summarize"]
AUTH_POOL = ["execute:worker", "write:journal", "publish:receipt",
             "read:telemetry", "cancel:op", "verify:output"]
FC_TAXONOMY = ["verification_failure", "integration_conflict", "stale_telemetry",
               "cancellation_budget_exceeded", "capability_mismatch",
               "duplicate_delivery", "message_loss", "authority_violation",
               "malformed_record", "none"]
FC_ALIAS_POOL = {"verification_rejection": "verification_failure",
                 "ww_conflict": "integration_conflict",
                 "budget_blowout": "cancellation_budget_exceeded",
                 "dup_delivery": "duplicate_delivery",
                 "auth_breach": "authority_violation",
                 "bad_record": "malformed_record",
                 "lost_message": "message_loss",
                 "probe_mismatch": "capability_mismatch"}
SAFETY_FAILURE_CLASSES = {"stale_telemetry", "cancellation_budget_exceeded",
                          "authority_violation"}
SOURCE_CLASSES = ["ax21", "synthetic", "benchmark", "replay", "other"]


def canonical_digest(item):
    payload = {k: v for k, v in item.items() if k != "digest"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def content_key(item):
    """Dup-detection key: full semantic content (excludes item_id/digest)."""
    payload = {k: item[k] for k in ("category", "input_state", "expected_output",
                                    "allowed_alternatives", "contamination_group")}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def base_item(code, category, seq, seed):
    item = {
        "item_id": "RCB0-%s-%04d" % (code, seq),
        "bench_version": BENCH_VERSION,
        "category": category,
        "input_state": seed["input_state"],
        "expected_output": seed["expected_output"],
        "output_schema": OUTPUT_SCHEMAS[code],
        "verifier_ref": VERIFIER_REFS[code],
        "allowed_alternatives": seed.get("allowed_alternatives", []),
        "contamination_group": seed["contamination_group"],
        "source_provenance": seed["source_provenance"],
        "difficulty": seed["difficulty"],
        "safety_critical": seed.get("safety_critical", False),
        "synthetic": seed["source_provenance"].get("synthetic", False),
    }
    item["digest"] = canonical_digest(item)
    return item


def syn_prov(lane_hint, rule):
    return {"lane": lane_hint, "artifact": None, "artifact_sha256_git_blob": None,
            "record_ref": None, "source_class": "synthetic", "derivation": "rule-expansion",
            "expansion_rule": rule, "synthetic": True}


def cg_syn(code, rule, seq):
    # X-M1: bench-internal synthetic lineages use the bench-syn: scheme
    # (frozen mapping table in CONTROL-BENCH-V0-DESIGN.md); authentic
    # lineage groups use the corpus converter scheme verbatim.
    return "bench-syn:%s:%s:b%02d" % (code.lower(), rule, seq // 25)


def diff(c, a, e, b, amb):
    return {"constraint_count": c, "authority_complexity": a, "evidence_depth": e,
            "branching_factor": b, "ambiguity_risk": amb}


def _digests(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- expansions
# Each expand_<code>(rng, seq) returns a seed-shaped dict (synthetic) whose
# expected_output PASSES the Lane D verifier for that category. Every expander
# embeds `seq` in identifiers so exact duplicates cannot occur; the generator
# additionally enforces canonical-content dedupe with salt escalation.

def expand_WR(rng, seq):
    req_caps = rng.sample(CAP_POOL, k=rng.randint(0, 2))
    req_auth = rng.sample(AUTH_POOL, k=rng.randint(0, 1))
    n_workers = rng.randint(3, 6)
    workers = []
    for i in range(n_workers):
        workers.append({
            "worker_id": "w-%d-%d" % (seq, i),
            "capabilities": rng.sample(CAP_POOL, k=rng.randint(0, 4)),
            "authority": rng.sample(AUTH_POOL, k=rng.randint(0, 3)),
            "available": rng.random() < 0.75,
        })
    legal = sorted(w["worker_id"] for w in workers
                   if w["available"] is True
                   and set(req_caps).issubset(set(w["capabilities"]))
                   and set(req_auth).issubset(set(w["authority"])))
    if legal and rng.random() < 0.85:
        action = "route"
        selected = rng.choice([None, rng.choice(legal)])
    elif legal:
        action = rng.choice(["hold", "escalate"])
        selected = None
    else:
        action = rng.choice(["hold", "escalate"])
        selected = None
    return {
        "input_state": {
            "task": {"task_id": "task-wr-%04d" % seq,
                     "required_capabilities": req_caps,
                     "required_authority": req_auth},
            "workers": workers,
            "allowed_actions": ["route", "hold", "escalate"],
        },
        "expected_output": {"action": action, "allowed_routes": legal,
                            "selected_route": selected},
        "allowed_alternatives": [],
        "contamination_group": cg_syn("WR", "cap-auth-routing", seq),
        "source_provenance": syn_prov("OTX-003", "WR-R2 capability/authority route sweep"),
        "difficulty": diff(len(req_caps) + len(req_auth) + 1, 1 if req_auth else 0,
                           1, 3, "low" if selected is None else "medium"),
        "safety_critical": bool(req_auth),
    }


_CC_FIELD_POOL = [
    ("verification.status", "enum", ["verified_success", "verified_failure",
                                     "provisional", "rejected", "unknown"]),
    ("escalation.classification", "enum", ["correct_escalation", "unnecessary_escalation",
                                           "correct_non_escalation", "false_non_escalation",
                                           "unknown"]),
    ("selected_topology", "enum", ["single", "pair", "swarm"]),
    ("decision.mode", "enum", ["fail_closed", "fail_open_prohibited"]),
    ("retry_count", "max_value", None),
    ("confidence", "min_value", None),
    ("evidence", "not_empty", None),
    ("authority.granted", "subset_of", None),
    ("output_type", "equals", "object"),
]


def _set_path(obj, path, value):
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def expand_CC(rng, seq):
    n_fields = rng.randint(1, 3)
    chosen = rng.sample(_CC_FIELD_POOL, k=n_fields)
    # path uniqueness (pool paths are unique)
    required_fields = [c[0] for c in chosen]
    invariants = []
    contract = {}
    for path, kind, fixed in chosen:
        if kind == "enum":
            invariants.append({"kind": "enum", "path": path, "value": fixed})
            _set_path(contract, path, fixed[seq % len(fixed)])
        elif kind == "max_value":
            cap = rng.choice([2, 3, 5, 10])
            invariants.append({"kind": "max_value", "path": path, "value": cap})
            _set_path(contract, path, seq % (cap + 1))
        elif kind == "min_value":
            floor = round(rng.uniform(0.0, 0.5), 2)
            invariants.append({"kind": "min_value", "path": path, "value": floor})
            _set_path(contract, path, round(floor + rng.uniform(0.0, 0.5), 3))
        elif kind == "not_empty":
            invariants.append({"kind": "not_empty", "path": path})
            _set_path(contract, path, ["ev-%d-0" % seq])
        elif kind == "subset_of":
            universe = rng.sample(AUTH_POOL, k=rng.randint(2, 4))
            invariants.append({"kind": "subset_of", "path": path, "value": universe})
            _set_path(contract, path, rng.sample(universe, k=rng.randint(0, len(universe))))
        elif kind == "equals":
            invariants.append({"kind": "equals", "path": path, "value": fixed})
            _set_path(contract, path, fixed)
    spec = {"required_fields": required_fields, "invariants": invariants}
    boundary = rng.sample(CAP_POOL, k=rng.randint(2, 5))
    spec["capability_boundary"] = boundary
    contract["capabilities"] = rng.sample(boundary, k=rng.randint(0, len(boundary)))
    if "authority.granted" not in required_fields and rng.random() < 0.5:
        scope = rng.sample(AUTH_POOL, k=rng.randint(1, 3))
        spec["authority_scope"] = scope
        contract["authority"] = rng.sample(scope, k=rng.randint(0, len(scope)))
    if rng.random() < 0.5:
        reqs = ["ev-%d-%d" % (seq, i) for i in range(rng.randint(1, 2))]
        spec["evidence_requirements"] = reqs
        existing = contract.get("evidence") or []
        if not isinstance(existing, list):
            existing = []
        contract["evidence"] = sorted(set(existing) | set(reqs))
    if rng.random() < 0.5:
        max_cost = rng.choice([1.0, 5.0, 25.0, 100.0])
        spec["budget"] = {"max_cost_usd": max_cost}
        contract["budget_usd"] = round(rng.uniform(0.01, max_cost), 4)
    contract["contract_id"] = "cc-%04d" % seq
    safety = any(f.split(".")[0] in ("verification", "authority", "escalation")
                 for f in required_fields)
    return {
        "input_state": {"contract_spec": spec,
                        "surface_note": "compile contract cc-%04d to spec" % seq},
        "expected_output": {"contract": contract},
        "allowed_alternatives": [],
        "contamination_group": cg_syn("CC", "spec-invariant", seq),
        "source_provenance": syn_prov("SCHEMA", "CC-R2 invariant/boundary/scope/evidence/budget sweep"),
        "difficulty": diff(len(required_fields) + len(invariants) + len(spec) - 2,
                           1 if "authority_scope" in spec else 0, 1, 2,
                           "low" if n_fields == 1 else "medium"),
        "safety_critical": safety,
    }


_ES_KIND_POOL = ["verification_record", "integration_log", "telemetry_snapshot",
                 "cost_report", "authority_grant", "replay_journal",
                 "schema_record", "confidence_measurement"]


def expand_ES(rng, seq):
    n_req = rng.randint(1, 4)
    kinds = rng.sample(_ES_KIND_POOL, k=n_req)
    reqs = [{"requirement_id": "req-%d-%d" % (seq, i), "kind": k}
            for i, k in enumerate(kinds)]
    artifacts = []
    missing = []
    for i, req in enumerate(reqs):
        if rng.random() < 0.6:
            artifacts.append({
                "artifact_id": "art-%d-%d" % (seq, i),
                "kind": req["kind"],
                "digest": _digests("es:%d:%d:%s" % (seq, i, req["kind"])),
                "provenance": {"source_class": rng.choice(SOURCE_CLASSES),
                               "record_ref": "rec-%d-%d" % (seq, i)},
            })
        else:
            missing.append(req["requirement_id"])
    # Broken artifacts that must NOT satisfy requirements.
    n_broken = rng.randint(0, 2)
    for b in range(n_broken):
        kind = rng.choice(kinds)
        mode = rng.choice(["bad_digest", "bad_provenance", "no_provenance"])
        art = {"artifact_id": "art-%d-b%d" % (seq, b), "kind": kind}
        if mode == "bad_digest":
            art["digest"] = "not-a-sha256-%d" % seq
            art["provenance"] = {"source_class": "replay"}
        elif mode == "bad_provenance":
            art["digest"] = _digests("es-bad:%d:%d" % (seq, b))
            art["provenance"] = {"source_class": "unregistered"}
        else:
            art["digest"] = _digests("es-noprov:%d:%d" % (seq, b))
        artifacts.append(art)
    rvo = []
    if rng.random() < 0.5:
        rvo = rng.sample(["slm00.verifier.worker_routing",
                          "slm00.verifier.evidence_sufficiency",
                          "slm00.verifier.failure_classification"],
                         k=rng.randint(1, 2))
    state = {"claim": "claim-es-%04d requires kinds %s" % (seq, kinds),
             "evidence_requirements": reqs, "artifacts": artifacts}
    if rvo:
        state["required_verifier_outputs"] = rvo
    return {
        "input_state": state,
        "expected_output": {"sufficient": not missing,
                            "missing_requirements": sorted(missing)},
        "allowed_alternatives": [],
        "contamination_group": cg_syn("ES", "kind-coverage", seq),
        "source_provenance": syn_prov("OBS-006/VQ-002", "ES-R2 kind-coverage with broken-artifact decoys"),
        "difficulty": diff(n_req + n_broken, 0, 1 + (1 if n_broken else 0), 2,
                           "medium" if n_broken else "low"),
        "safety_critical": any(k in ("verification_record", "authority_grant",
                                     "confidence_measurement") for k in kinds),
    }


def _rea_execute(policy, state):
    failure_class = state.get("failure_class")
    if failure_class in (policy.get("escalate_on") or []):
        return "escalate", "POLICY_ESCALATE_CLASS"
    if state.get("capability_ok") is not True:
        return "abort", "CAPABILITY_MISMATCH"
    if not set(policy.get("authority_required") or []).issubset(
            set(state.get("authority_granted") or [])):
        return "escalate", "AUTHORITY_INSUFFICIENT"
    if state.get("attempts") >= policy.get("max_retries"):
        if policy.get("escalate_when_retry_exhausted") is True:
            return "escalate", "RETRY_BUDGET_EXHAUSTED"
        return "abort", "RETRY_BUDGET_EXHAUSTED"
    if failure_class not in (policy.get("retry_on") or []):
        return "abort", "CLASS_NOT_RETRYABLE"
    return "retry", "POLICY_RETRY"


def expand_REA(rng, seq):
    classes = FC_TAXONOMY + ["timeout", "transport_error"]
    retry_on = rng.sample(classes, k=rng.randint(1, 3))
    escalate_on = rng.sample([c for c in classes if c not in retry_on],
                             k=rng.randint(0, 2))
    policy = {"max_retries": rng.randint(1, 4),
              "retry_on": retry_on,
              "escalate_on": escalate_on,
              "escalate_when_retr