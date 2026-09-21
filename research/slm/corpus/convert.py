#!/usr/bin/env python3
"""SLM-00 corpus converter: structured swarm evidence -> observation.schema.json records.

Deterministic, side-effect-free, per-source converters. Rules (per SLM-PREFLIGHT-REPORT
and SCHEMA-ERRATUM-001):
  - Unknown/unavailable fields are null/unknown; NOTHING is invented.
  - timestamp is null everywhere (SCHEMA-ERRATUM-001); provenance.timestamp_erratum set.
  - verification.status is a recorded verifier verdict or "unknown"/"provisional";
    success inference from result fields is NOT treated as verification.
  - authority defaults to requested=[], granted=[], violation=False ONLY where the
    source records no authority material; this default is a documented assumption
    (preflight SS2.1), flagged in authority.authority_default_assumed.
  - Every record carries provenance: source_file, source_blob_sha, source_class,
    plus contamination_group per the deterministic scheme below.
  - All outcome classes preserved (success, failure, retry, rejection, conflict,
    stale-state, authority) -- no filtering of failures. Sanitation: any record
    containing credential-like material is REJECTED and counted, never repaired.

Contamination groups:
  OTX  : otx:<task_class>-<granularity>   (task family; all replicates share config)
  VQ   : vq:case:<case_id>  (case_id LINEAGE-keyed, NOT blob-keyed. Rationale
         (SLM-INFRA-QUAL MATERIAL-2): the prior scheme vq:<prefix>:<blob-sha8>
         keyed groups by source-file blob SHA; outcomes-adequate.part2 and
         outcomes-degraded.part2 share the same 30 case_ids with 20/30
         content-identical records but DIFFERENT blob SHAs, so identical
         records were assigned different groups and could straddle a split
         undetected. Keying by case_id lineage guarantees every variant of a
         case (adequate/degraded, flipped verdicts included) shares exactly
         one group, so related records can never straddle a split.)
  OBS  : obs006-fixture-v1                (single fixture = single group)
  DSM  : dsm004:<schedule> for fault inbox journals; dsm004:outbox-shared for the
         hash-identical outbox journals (same event hashes in all 6 schedules);
         dsm004:recovery/<scenario> (journal events AND the scenario record share
         the lineage group: retries/duplicates/replays stay together)
  RUNTIME: runtime005:<scenario>          (scenario lineage)

Usage: python3 convert.py <repo_root> --out corpus.jsonl
Requires only the Python stdlib. Not executed in the authoring environment
(GitHub MCP only); logic is pure parsing + field mapping. A 13-record hand-converted
sample produced with this exact mapping is at
research/slm/corpus/sample/converted-sample.jsonl (locally validated against the
SCHEMA-ERRATUM-001-amended schema: 13/13 pass; 13/13 fail the strict schema on
timestamp alone).
"""

import argparse
import hashlib
import json
import re
import sys

SCHEMA_VERSION = "slm-observation-v0"
TIMESTAMP_ERRATUM = "SCHEMA-ERRATUM-001"

SOURCE_SHAS = {
    "evidence/otx/observations.jsonl": "9d24ececfe5e52a3732d6f5cc6c571d8af125ca2",
    "evidence/obs/obs006-evidence.json": "4f140a2266df0c6b6f66f6a88a519b52a1c58182",
    "evidence/dsm/dsm-004-evidence.json": "20c8e7e4d8ad99dc0b5b0b73085388ab14477620",
    "evidence/runtime/runtime005_evidence.json": "76358dd1a1054e596a5e04c167dd84792e809dd0",
    "evidence/vq/outcomes-adequate.part0.jsonl": "e79f2946fd30cc11994a2015f35668fb4e9ab808",
    "evidence/vq/outcomes-adequate.part1.jsonl": "2fdc9b28d8f0814b7e579bc03fddfa18e55148c9",
    "evidence/vq/outcomes-adequate.part2.jsonl": "e14239f88af6718b7423a065f887141f55167654",
    "evidence/vq/outcomes-degraded.part0.jsonl": "e79f2946fd30cc11994a2015f35668fb4e9ab808",
    "evidence/vq/outcomes-degraded.part1.jsonl": "2fdc9b28d8f0814b7e579bc03fddfa18e55148c9",
    "evidence/vq/outcomes-degraded.part2.jsonl": "8d7c4b0ce090d34f22b9896751d0832161816cab",
}

# Credential/secret patterns. Matches -> record is rejected and counted, never repaired.
SANITATION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"\b(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"]?\S+",
        r"\bBearer\s+[A-Za-z0-9._-]+",
        r"\b(10|172\.(1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b",  # RFC1918 LAN IPs
    ]
]

MANIFEST = {
    "total_records": 0,
    "verified_successes": 0,
    "verified_failures": 0,
    "provisional_outcomes": 0,
    "unknown_verification": 0,
    "rejected_actions": 0,
    "interventions": 0,
    "retry_repair_events": 0,
    "escalation_events": 0,
    "false_non_escalation_candidates": 0,
    "authority_violations": 0,
    "schema_failures": 0,
    "sanitation_rejects": 0,
    "contamination_groups": {},
    "per_source": {},
    "null_field_rates": {},
}


def sanitize_or_none(record_dict):
    """Return the dict, or None if credential-like content is found (reject, don't repair)."""
    blob = json.dumps(record_dict, sort_keys=True)
    for pat in SANITATION_PATTERNS:
        if pat.search(blob):
            return None
    return record_dict


def base_record(obs_id, source_file, source_class, contamination_group,
                state, proposed, actual, outcome, verification_status,
                verifier_refs, cost, authority, labels=None, notes=None,
                extra_provenance=None):
    prov = {
        "source_class": source_class,
        "mission_id": None,
        "incident_id": None,
        "generation": None,
        "artifact_digests": ["git_blob_sha1:" + SOURCE_SHAS[source_file]] if source_file in SOURCE_SHAS else [],
        "source_file": source_file,
        "source_blob_sha": SOURCE_SHAS.get(source_file),
        "timestamp_erratum": TIMESTAMP_ERRATUM,
    }
    if extra_provenance:
        prov.update(extra_provenance)
    rec = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": obs_id,
        "timestamp": None,  # SCHEMA-ERRATUM-001: absent wall-clock stays null, never fabricated
        "provenance": prov,
        "contamination_group": contamination_group,
        "state": state,
        "proposed_decision": proposed,
        "actual_decision": actual,
        "outcome": outcome,
        "verification": {"status": verification_status, "verifier_refs": verifier_refs},
        "cost": cost,
        "authority": authority,
    }
    if labels is not None:
        rec["labels"] = labels
    if notes is not None:
        rec["notes"] = notes
    return rec


def default_authority(assumed=True):
    return {"requested": [], "granted": [], "violation": False,
            "authority_default_assumed": assumed}


NULL_COST = {"inference_usd": None, "energy_wh": None, "latency_ms": None,
             "operator_active_seconds": None, "frontier_calls": None}


# ---------------------------------------------------------------- OTX-003
def convert_otx(root):
    src = "evidence/otx/observations.jsonl"
    out = []
    with open(f"{root}/{src}", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            task = r["inputs"]["task"]
            group = f"otx:{task['task_class']}-{task['granularity']}"
            tb = r.get("result", {}).get("timing_breakdown") or {}
            latency_ms = round(sum(tb.values()) * 1000.0, 3) if tb else None
            candidates = [
                {"topology": c["topology"], "predicted_utility": c["predicted_utility"],
                 "predicted_reliability": c["predicted_reliability"],
                 "predicted_tax": c["predicted_tax"],
                 "predicted_total_s": c["predicted_total_s"]}
                for c in r.get("candidates", [])
            ]
            res = r.get("result", {})
            rec = base_record(
                obs_id=r["observation_id"],
                source_file=src,
                source_class="replay",
                contamination_group=group,
                state={
                    "task": task,
                    "config": r["inputs"]["config"],
                    "sequence": r.get("sequence"),
                },
                proposed={"candidates": candidates},
                actual={
                    "selected_topology": r.get("selected_topology"),
                    "selection_reason": r.get("selection_reason"),
                },
                outcome={
                    "success": res.get("success"),
                    "quality_score": res.get("quality_score"),
                    "observed_tax": res.get("observed_tax"),
                    "observed_total_s": res.get("observed_total_s"),
                    "timing_breakdown": tb or None,
                    "comparison": r.get("comparison"),
                },
                # success+quality==1.0 is NOT a recorded verifier verdict -> provisional
                verification_status="provisional",
                verifier_refs=[],
                cost={**NULL_COST, "latency_ms": latency_ms},
                authority=default_authority(),
                labels=["otx-003", f"task-family:{group}"],
                notes="verification.status=provisional: outcome is model-run result, not a recorded verifier verdict",
                extra_provenance={
                    "model_snapshot_sha256": (r.get("model_snapshot") or {}).get("sha256"),
                },
            )
            out.append(rec)
    return out


# ---------------------------------------------------------------- OBS-006
# Canonical-unit kinds become records; resource/timing kinds are attributes,
# not standalone observations (preflight SS2.2) and are NOT emitted as records.
OBS_CANONICAL_KINDS = {"execution", "acceptance", "rejection", "verification",
                       "integration", "conflict", "retry"}


def convert_obs006(root):
    src = "evidence/obs/obs006-evidence.json"
    with open(f"{root}/{src}", encoding="utf-8") as fh:
        doc = json.load(fh)
    fixture = doc["fixture_id"]
    identity = doc.get("identity", {})
    out = []
    for i, ev in enumerate(doc["raw_observations"]):
        kind = ev["kind"]
        if kind not in OBS_CANONICAL_KINDS:
            continue  # folded into sibling records as attributes; not standalone
        obs_id = f"obs006-{i:03d}-{kind}"
        verdict = ev.get("verdict")
        outcome_val = ev.get("outcome")
        if kind == "verification":
            vstatus = {"pass": "verified_success", "fail": "verified_failure"}.get(verdict, "unknown")
            vrefs = [ev["verifier_identity"]] if ev.get("verifier_identity") else []
        elif kind == "rejection":
            vstatus, vrefs = "rejected", []
        else:
            vstatus, vrefs = "unknown", []  # no recorded verifier verdict
        cost = dict(NULL_COST)
        if kind == "execution" and ev.get("worker_seconds") is not None:
            cost["latency_ms"] = round(ev["worker_seconds"] * 1000.0, 3)
        rec = base_record(
            obs_id=obs_id,
            source_file=src,
            source_class="synthetic",
            contamination_group=fixture,
            state={"task_class": ev.get("task_class"), "fixture_id": fixture,
                   "event_kind": kind},
            proposed=None,
            actual={"event_kind": kind, **{k: v for k, v in ev.items()
                                          if k not in ("kind", "schema_version", "task_class")}},
            outcome={"kind": kind, "outcome": outcome_val, "correct": ev.get("correct"),
                     "verdict": verdict, "result": ev.get("result"),
                     "resolution": ev.get("resolution"), "reason": ev.get("reason"),
                     "attempt": ev.get("attempt")},
            verification_status=vstatus,
            verifier_refs=vrefs,
            cost=cost,
            authority=default_authority(),
            labels=["obs006", f"kind:{kind}"],
            extra_provenance={
                "fixture_id": fixture,
                "source_commit": identity.get("commit"),
                "source_tree": identity.get("tree"),
                "observation_hash": doc.get("observation_hash"),
            },
        )
        out.append(rec)
    return out


# ---------------------------------------------------------------- DSM-004
def dsm_group(journal_path):
    """Deterministic contamination group for a journal path.

    All six fault-schedule outbox journals are hash-identical -> one shared group so
    identical records cannot straddle a split. Inbox journals and recovery journals
    group by their schedule/scenario lineage (retries, duplicates, retransmissions,
    and the recovery scenario record share the lineage group).
    """
    parent = journal_path.rsplit("/", 1)[0]
    if journal_path.endswith("/outbox.journal"):
        return "dsm004:outbox-shared"
    return f"dsm004:{parent}"


def convert_dsm004(root):
    src = "evidence/dsm/dsm-004-evidence.json"
    with open(f"{root}/{src}", encoding="utf-8") as fh:
        doc = json.load(fh)
    ident = doc.get("source_identity", {})
    out = []
    for journal_path, lines in sorted(doc["raw_event_logs"].items()):
        group = dsm_group(journal_path)
        for line in lines:
            ev = json.loads(line)
            payload = ev.get("payload", {})
            inner = payload.get("event", {})
            rec = base_record(
                obs_id=f"dsm004:{journal_path}#{ev['seq']}",
                source_file=src,
                source_class="replay",
                contamination_group=group,
                state={
                    "journal": journal_path,
                    "seq": ev.get("seq"),
                    "prev_hash": ev.get("prev_hash"),
                    "synthetic_time_ns": ev.get("time_ns"),  # kept in state, NOT timestamp
                },
                proposed=None,
                actual={"kind": ev.get("kind"), "event": inner,
                        "disposition": payload.get("disposition")},
                outcome={"disposition": payload.get("disposition"),
                         "hash": ev.get("hash"),
                         "value": inner.get("value")},  # failed/succeeded/running preserved
                verification_status="unknown",  # hash-chain integrity, no verifier verdict
                verifier_refs=[],
                cost=dict(NULL_COST),
                authority={"requested": [], "granted": [], "violation": False,
                           "authority_default_assumed": True,
                           "writer": inner.get("writer")},
                labels=["dsm-004", f"journal:{journal_path}"],
                notes="replay-class lineage record; reduced-scope use per preflight SS2.3",
                extra_provenance={
                    "source_commit": ident.get("commit"),
                    "source_tree": ident.get("tree"),
                    "journal_path": journal_path,
                },
            )
            out.append(rec)
    # Recovery scenarios: crash/retry lineage (duplicate dispositions preserved);
    # scenario record SHARES the contamination group of its journal lineage.
    for sc in doc.get("recovery_suite", {}).get("scenarios", []):
        group = f"dsm004:recovery/{sc['scenario']}"
        rec = base_record(
            obs_id=f"dsm004:recovery/{sc['scenario']}",
            source_file=src,
            source_class="replay",
            contamination_group=group,
            state={"scenario": sc["scenario"],
                   "crash_injected": sc.get("crash_injected")},
            proposed=None,
            actual={"scenario": sc["scenario"],
                    "duplicate_dispositions": sc.get("duplicate_dispositions")},
            outcome={"ok": sc.get("ok"),
                     "accepted_count": sc.get("accepted_count"),
                     "unique_count": sc.get("unique_count"),
                     "no_duplicate_accepted": sc.get("no_duplicate_accepted"),
                     "projection_after_recovery": sc.get("projection_after_recovery"),
                     "terminal_absorbing_rejected": sc.get("terminal_absorbing_rejected")},
            verification_status="verified_success" if sc.get("ok") is True else "unknown",
            verifier_refs=["dsm-004-recovery-suite"],
            cost=dict(NULL_COST),
            authority=default_authority(),
            labels=["dsm-004", "recovery"],
            extra_provenance={"provenance_intact": sc.get("provenance_intact"),
                              "source_commit": ident.get("commit"),
                              "source_tree": ident.get("tree")},
        )
        out.append(rec)
    return out


# ---------------------------------------------------------------- RUNTIME-005
def convert_runtime005(root):
    src = "evidence/runtime/runtime005_evidence.json"
    with open(f"{root}/{src}", encoding="utf-8") as fh:
        doc = json.load(fh)
    ident = doc.get("identity", {})
    out = []
    for fs in doc["scenarios"]["fault_scenarios"]:
        name = fs["scenario"]
        group = f"runtime005:{name}"
        obs = fs.get("observations", [])
        authority = default_authority()
        extra_labels = ["runtime005"]
        if name == "provider_native_authority_never_overrides_residual":
            san = (obs[0] if obs else {}).get("sanitized", {})
            authority = {
                "requested": [], "granted": [],
                "violation": any(bool(v) for k, v in san.items()
                                 if k != "residual_policy_authoritative"),
                "authority_default_assumed": False,
                "sanitized_authority_map": san,
                "residual_policy_authoritative": san.get("residual_policy_authoritative"),
            }
            extra_labels.append("authority")
        if name == "stale_telemetry_returns_unknown":
            extra_labels.append("stale-state")
        vstatus = "verified_success" if fs.get("pass") is True else "unknown"
        rec = base_record(
            obs_id=f"runtime005:{name}",
            source_file=src,
            source_class="synthetic",
            contamination_group=group,
            state={"scenario": name, "expected": fs.get("expected")},
            proposed=None,
            actual={"scenario": name},
            outcome={"pass": fs.get("pass"), "observations": obs},
            verification_status=vstatus,
            verifier_refs=["runtime005-fault-scenarios"],
            cost=dict(NULL_COST),
            authority=authority,
            labels=extra_labels,
            extra_provenance={"source_commit": ident.get("commit"),
                              "source_tree": ident.get("tree"),
                              "scenario_hash": doc.get("scenario_hash")},
        )
        out.append(rec)
    # Conformance checks (2 engines x 12) are suite-level booleans, not canonical
    # state->decision->outcome units -> NOT emitted as observations (rejected),
    # retained in the source artifact as provenance/verifier_refs evidence.
    return out


# ---------------------------------------------------------------- VQ-002
def convert_vq(root):
    out = []
    for src in sorted(p for p in SOURCE_SHAS if p.startswith("evidence/vq/outcomes-")):
        part = src.rsplit("/", 1)[-1].replace(".jsonl", "")
        with open(f"{root}/{src}", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                case_id = r["case_id"]
                m = re.match(r"^([A-Za-z]+)", case_id)
                prefix = m.group(1) if m else case_id
                # Case_id LINEAGE-keyed group (MATERIAL-2 fix): every variant of a
                # case -- adequate/degraded files, byte-identical parts, and the
                # part2 records whose verdicts differ -- shares ONE group, so
                # related records can never straddle a split. The prior
                # blob-sha8 keying gave adequate.part2/degraded.part2 different
                # groups despite 20/30 content-identical records.
                group = f"vq:case:{case_id}"
                gt, verdict = r.get("ground_truth"), r.get("verdict")
                if gt is None or verdict is None:
                    vstatus = "unknown"
                elif bool(gt) == bool(verdict):
                    vstatus = "verified_success"
                else:
                    vstatus = "verified_failure"
                rec = base_record(
                    obs_id=f"vq:{part}:{case_id}",
                    source_file=src,
                    source_class="benchmark",
                    contamination_group=group,
                    state={"case_id": case_id,
                           "safety_critical": r.get("safety_critical"),
                           "label_source": r.get("label_source")},
                    proposed=None,
                    actual={"verdict": verdict, "verifier_id": r.get("verifier_id")},
                    outcome={"verdict": verdict, "ground_truth": gt,
                             "agreement": (bool(gt) == bool(verdict))
                             if gt is not None and verdict is not None else None,
                             "confidence": r.get("confidence")},  # null stays null
                    verification_status=vstatus,
                    verifier_refs=[r["verifier_id"]] if r.get("verifier_id") else [],
                    cost=dict(NULL_COST),
                    authority=default_authority(),
                    labels=["vq-002", f"case-prefix:{prefix}"],
                    notes="thin training unit; verification-outcome record per preflight SS2.5",
                )
                out.append(rec)
    return out


# ---------------------------------------------------------------- manifest
NULL_TRACKED_FIELDS = [
    "timestamp",
    "cost.inference_usd",
    "cost.energy_wh",
    "cost.latency_ms",
    "cost.operator_active_seconds",
    "cost.frontier_calls",
    "provenance.mission_id",
    "provenance.incident_id",
]


def field_get(rec, dotted):
    cur = rec
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def update_manifest(records, rejects_by_source):
    groups = {}
    per_source = {}
    null_counts = {f: 0 for f in NULL_TRACKED_FIELDS}
    for rec in records:
        MANIFEST["total_records"] += 1
        src = rec["provenance"]["source_file"]
        per_source[src] = per_source.get(src, 0) + 1
        groups[rec["contamination_group"]] = groups.get(rec["contamination_group"], 0) + 1
        vs = rec["verification"]["status"]
        if vs == "verified_success":
            MANIFEST["verified_successes"] += 1
        elif vs == "verified_failure":
            MANIFEST["verified_failures"] += 1
        elif vs == "provisional":
            MANIFEST["provisional_outcomes"] += 1
        elif vs == "rejected":
            MANIFEST["rejected_actions"] += 1
        else:
            MANIFEST["unknown_verification"] += 1
        if rec["authority"].get("violation"):
            MANIFEST["authority_violations"] += 1
        out = rec.get("outcome", {})
        # MINOR-6 fix: retry/repair events are counted separately from
        # OPERATOR interventions. No source records operator interventions,
        # so `interventions` stays 0 (matching CORPUS-MANIFEST); retries and
        # re-attempts accumulate in `retry_repair_events`.
        if out.get("kind") in ("retry",) or out.get("attempt"):
            MANIFEST["retry_repair_events"] += 1
        esc = rec.get("escalation")
        if esc and esc.get("required") is not None:
            MANIFEST["escalation_events"] += 1
            if esc.get("classification") == "false_non_escalation":
                MANIFEST["false_non_escalation_candidates"] += 1
        for f in NULL_TRACKED_FIELDS:
            if field_get(rec, f) is None:
                null_counts[f] += 1
    MANIFEST["contamination_groups"] = groups
    MANIFEST["per_source"] = per_source
    MANIFEST["sanitation_rejects"] = sum(rejects_by_source.values())
    MANIFEST["sanitation_rejects_by_source"] = rejects_by_source
    n = max(MANIFEST["total_records"], 1)
    MANIFEST["null_field_rates"] = {f: round(c / n, 6) for f, c in null_counts.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="repo checkout root")
    ap.add_argument("--out", default="corpus.jsonl")
    ap.add_argument("--manifest", default="corpus-manifest-computed.json")
    args = ap.parse_args()

    records, rejects = [], {}
    for fn in (convert_otx, convert_obs006, convert_dsm004, convert_runtime005,
               convert_vq):
        for rec in fn(args.root):
            clean = sanitize_or_none(rec)
            if clean is None:
                key = rec["provenance"]["source_file"]
                rejects[key] = rejects.get(key, 0) + 1
                continue  # rejected, counted, never repaired
            records.append(clean)

    with open(args.out, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    update_manifest(records, rejects)
    with open(args.out, "rb") as fh:
        MANIFEST["corpus_sha256"] = hashlib.sha256(fh.read()).hexdigest()
    with open(args.manifest, "w", encoding="utf-8") as fh:
        json.dump(MANIFEST, fh, indent=2, sort_keys=True)
    print(f"wrote {MANIFEST['total_records']} records -> {args.out}; "
          f"sanitation rejects: {MANIFEST['sanitation_rejects']}", file=sys.stderr)


if __name__ == "__main__":
    main()
