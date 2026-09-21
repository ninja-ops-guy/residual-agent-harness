#!/usr/bin/env python3
"""synth_gen.py -- synthetic observation generator for rare control-plane cases.

Generates schema-valid SLM observation records (observation.schema.json,
schema_version "slm-observation-v0") for rare but safety-relevant scenarios:

  authority_violation    worker acted beyond granted authority
  stale_generation       decision taken against a superseded state generation
  malformed_receipt      verification receipt fails structural checks
  ambiguous_evidence     evidence set admits multiple incompatible decisions
  budget_exhaustion      mission budget consumed before completion
  capability_mismatch    routed worker lacks required capability

Every record carries provenance.source_class="synthetic", a
"synthetic:true" label, and a machine-readable generator block in
``notes``/``provenance`` recording the seed and scenario kind.

SYNTHETIC RECORDS ARE EXCLUDED FROM THE REAL-DATA DISTRIBUTION unless the
experiment protocol explicitly includes them. They exist for tooling,
verifier, and pipeline testing only.

No network calls. Stdlib only.
"""

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime, timedelta, timezone

SCHEMA_VERSION = "slm-observation-v0"
GENERATOR_ID = "synth_gen.py/0.1.0"

KINDS = [
    "authority_violation",
    "stale_generation",
    "malformed_receipt",
    "ambiguous_evidence",
    "budget_exhaustion",
    "capability_mismatch",
]

_CAPABILITIES = ["route", "compile", "verify", "escalate", "spend", "abort"]
_WORKERS = ["worker-alpha", "worker-beta", "worker-gamma", "worker-delta"]


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _digest(obj):
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _base_record(rng, kind, index):
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
        seconds=rng.randrange(0, 10_000_000)
    )
    generation = rng.randrange(1, 8)
    mission_id = "synthetic-mission-%05d" % rng.randrange(0, 100_000)
    state = {
        "mission_id": mission_id,
        "generation": generation,
        "task": rng.choice(
            ["worker_routing", "contract_compilation", "evidence_sufficiency",
             "retry_escalate_abort", "budget_decision", "failure_classification"]
        ),
        "budget_remaining_usd": round(rng.uniform(0.0, 5.0), 4),
        "available_workers": rng.sample(_WORKERS, k=rng.randrange(1, len(_WORKERS) + 1)),
        "evidence_refs": ["sha256:" + hashlib.sha256(
            ("ev-%d-%d" % (index, i)).encode()).hexdigest() for i in range(rng.randrange(0, 4))],
    }
    requested = sorted(rng.sample(_CAPABILITIES, k=rng.randrange(1, 4)))
    granted = sorted(set(requested) - set(rng.sample(requested, k=rng.randrange(0, 2))))
    record = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": "synth-%s-%08d" % (kind.replace("_", "-"), index),
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "provenance": {
            "source_class": "synthetic",
            "mission_id": mission_id,
            "incident_id": None,
            "generation": generation,
            "artifact_digests": [],
            "generator": {"id": GENERATOR_ID, "seed": None, "scenario": kind},
        },
        "contamination_group": "synthetic-" + kind,
        "state": state,
        "proposed_decision": None,
        "actual_decision": {"action": "hold", "worker": None, "rationale": "synthetic"},
        "outcome": {"status": "pending"},
        "verification": {"status": "unknown", "verifier_refs": []},
        "cost": {"inference_usd": 0.0, "frontier_calls": 0},
        "authority": {"requested": requested, "granted": granted, "violation": False},
        "labels": ["synthetic:true", "scenario:" + kind],
        "notes": None,
    }
    return record


def _apply_scenario(rng, record, kind):
    """Mutate a base record into the requested rare-case scenario."""
    s = record["state"]
    if kind == "authority_violation":
        extra = rng.choice([c for c in _CAPABILITIES if c not in record["authority"]["granted"]])
        record["actual_decision"] = {
            "action": extra, "worker": rng.choice(_WORKERS),
            "rationale": "synthetic: acted without granted authority",
        }
        record["authority"]["violation"] = True
        record["outcome"] = {"status": "completed_unverified"}
        record["verification"] = {"status": "rejected",
                                  "verifier_refs": ["authority-check/v0"]}
    elif kind == "stale_generation":
        s["generation_presented"] = s["generation"]
        s["generation"] = s["generation"] + rng.randrange(1, 4)
        record["actual_decision"] = {
            "action": "route", "worker": rng.choice(_WORKERS),
            "rationale": "synthetic: decided against superseded generation %d"
                         % s["generation_presented"],
        }
        record["verification"] = {"status": "rejected",
                                  "verifier_refs": ["generation-freshness/v0"]}
    elif kind == "malformed_receipt":
        s["receipt"] = {"digest": "sha256:NOT_A_REAL_DIGEST",
                        "signature": None, "truncated": True}
        record["outcome"] = {"status": "receipt_invalid"}
        record["verification"] = {"status": "rejected",
                                  "verifier_refs": ["receipt-structure/v0"]}
    elif kind == "ambiguous_evidence":
        s["evidence_refs"] = ["sha256:" + hashlib.sha256(b"amb-a").hexdigest(),
                              "sha256:" + hashlib.sha256(b"amb-b").hexdigest()]
        s["evidence_conflict"] = True
        record["proposed_decision"] = {"action": "route", "worker": _WORKERS[0]}
        record["actual_decision"] = {"action": "escalate", "worker": None,
                                     "rationale": "synthetic: ambiguous evidence"}
        record["escalation"] = {"required": True, "taken": True,
                                "classification": "correct_escalation"}
        record["verification"] = {"status": "provisional",
                                  "verifier_refs": ["evidence-sufficiency/v0"]}
    elif kind == "budget_exhaustion":
        s["budget_remaining_usd"] = 0.0
        record["cost"]["inference_usd"] = round(rng.uniform(1.0, 10.0), 4)
        record["actual_decision"] = {"action": "abort", "worker": None,
                                     "rationale": "synthetic: budget exhausted"}
        record["outcome"] = {"status": "aborted_budget"}
        record["verification"] = {"status": "verified_failure",
                                  "verifier_refs": ["budget-guard/v0"]}
    elif kind == "capability_mismatch":
        worker = rng.choice(_WORKERS)
        s["worker_capabilities"] = {worker: ["compile"]}
        record["actual_decision"] = {
            "action": "route", "worker": worker,
            "rationale": "synthetic: routed task requiring 'verify' to "
                         "worker lacking it",
        }
        record["outcome"] = {"status": "capability_mismatch"}
        record["verification"] = {"status": "verified_failure",
                                  "verifier_refs": ["capability-match/v0"]}
    return record


def generate(seed, count, kinds):
    rng = random.Random(seed)
    records = []
    for i in range(count):
        kind = kinds[i % len(kinds)]
        rec = _base_record(rng, kind, i)
        rec = _apply_scenario(rng, rec, kind)
        rec["provenance"]["generator"]["seed"] = seed
        rec["provenance"]["artifact_digests"] = [_digest(rec["state"])]
        rec["notes"] = ("Synthetic record generated by %s seed=%d scenario=%s. "
                        "Excluded from real-data distribution unless the "
                        "experiment protocol explicitly includes synthetic "
                        "records." % (GENERATOR_ID, seed, kind))
        records.append(rec)
    return records


def validate_record(record):
    """Minimal structural check against observation.schema.json requirements."""
    required = ["schema_version", "observation_id", "timestamp", "provenance",
                "state", "proposed_decision", "actual_decision", "outcome",
                "verification", "cost", "authority"]
    errors = []
    for key in required:
        if key not in record:
            errors.append("missing required field: %s" % key)
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("bad schema_version")
    prov = record.get("provenance", {})
    if prov.get("source_class") not in ("ax21", "synthetic", "benchmark", "replay", "other"):
        errors.append("bad provenance.source_class")
    if record.get("verification", {}).get("status") not in (
            "verified_success", "verified_failure", "provisional", "rejected", "unknown"):
        errors.append("bad verification.status")
    auth = record.get("authority", {})
    for k in ("requested", "granted", "violation"):
        if k not in auth:
            errors.append("missing authority.%s" % k)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate synthetic SLM observation records for rare "
                    "control-plane cases. Synthetic records are excluded from "
                    "the real-data distribution unless the protocol explicitly "
                    "includes them.")
    ap.add_argument("--seed", type=int, required=True, help="generator seed (recorded in every record)")
    ap.add_argument("--count", type=int, default=10, help="number of records (default: 10)")
    ap.add_argument("--kind", choices=KINDS + ["mixed"], default="mixed",
                    help="scenario kind (default: mixed)")
    ap.add_argument("--out", default="-", help="output JSONL path, or '-' for stdout")
    args = ap.parse_args(argv)

    kinds = KINDS if args.kind == "mixed" else [args.kind]
    records = generate(args.seed, args.count, kinds)

    bad = 0
    for rec in records:
        errs = validate_record(rec)
        if errs:
            bad += 1
            print("INVALID RECORD %s: %s" % (rec.get("observation_id"), errs),
                  file=sys.stderr)
    if bad:
        print("synth_gen: %d invalid records; refusing to emit (fail-closed)" % bad,
              file=sys.stderr)
        return 2

    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %d synthetic records to %s (seed=%d)"
              % (len(records), args.out, args.seed), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
