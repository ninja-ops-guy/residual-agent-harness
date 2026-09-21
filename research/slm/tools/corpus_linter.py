#!/usr/bin/env python3
"""corpus_linter.py -- quality checks for an SLM observation JSONL corpus.

Checks (fail-closed: any ERROR finding exits non-zero):
  schema        required fields / enums of observation.schema.json are
                satisfied (schema_version slm-observation-v0 or the
                ratified slm-observation-v0.1; see SCHEMA-ERRATUM-001)
  exact_dup     byte-identical canonical records
  near_dup      shingle-based near-duplicate records (Jaccard over
                word 5-shingles of the canonical record text)
  contamination lineage collisions: records sharing mission/incident
                lineage (retries, repairs, receipts, templates,
                paraphrases, counterfactuals) MUST share a
                contamination_group. Fallback when mission/incident ids
                are null (SLM-INFRA-QUAL MATERIAL-3):
                  * near-dup lineage inference -- a near-duplicate pair
                    with DIFFERENT contamination_groups is an ERROR
                    (related records straddling groups)
                  * a near-duplicate pair sharing one group is
                    consistent (WARN-only near_dup still reported)
                  * records whose lineage cannot be bound at all (no
                    mission_id, no incident_id, no contamination_group)
                    yield WARN -- the check never passes silently
                  * if NO record binds primary lineage ids, a WARN is
                    emitted that the check is running in degraded
                    (fallback) mode
  provenance    missing provenance.source_class or unreplayable records.
                Timestamp rule (X-B1, schema v0.1 semantics ratified from
                SCHEMA-ERRATUM-001): a null/absent timestamp PASSES only
                when provenance.timestamp_erratum == "SCHEMA-ERRATUM-001";
                a null timestamp WITHOUT the marker is an ERROR. The
                timestamp is never imputed.
  leakage       suspicious label-leakage patterns (outcome/verification/
                label text embedded in state, decision echoing labels)

Canonical serialization (single convention, X-m5): json.dumps(obj,
sort_keys=True, separators=(",", ":")) -- no spaces after separators.

Machine-readable JSON report on stdout (or --report). No network calls.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict

SCHEMA_VERSIONS = {"slm-observation-v0", "slm-observation-v0.1"}
TIMESTAMP_ERRATUM = "SCHEMA-ERRATUM-001"
REQUIRED = ["schema_version", "observation_id", "timestamp", "provenance",
            "state", "proposed_decision", "actual_decision", "outcome",
            "verification", "cost", "authority"]
SOURCE_CLASSES = {"ax21", "synthetic", "benchmark", "replay", "other"}
VERIF_STATUS = {"verified_success", "verified_failure", "provisional",
                "rejected", "unknown"}
LEAK_TOKENS = re.compile(
    r"(expected_output|verified_success|verified_failure|correct_escalation|"
    r"false_non_escalation|label|answer_key)", re.IGNORECASE)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def shingles(text, n=5):
    words = re.findall(r"[A-Za-z0-9_]+", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def lineage_key(rec):
    prov = rec.get("provenance", {}) or {}
    for k in ("mission_id", "incident_id"):
        v = prov.get(k)
        if v:
            return "%s:%s" % (k, v)
    return None


def check_schema(rec):
    errs = []
    for k in REQUIRED:
        if k not in rec:
            errs.append("missing required field '%s'" % k)
    if rec.get("schema_version") not in SCHEMA_VERSIONS:
        errs.append("schema_version not in %s" % sorted(SCHEMA_VERSIONS))
    prov = rec.get("provenance")
    if isinstance(prov, dict):
        if prov.get("source_class") not in SOURCE_CLASSES:
            errs.append("provenance.source_class missing or invalid")
    vs = rec.get("verification", {})
    if isinstance(vs, dict) and vs.get("status") not in VERIF_STATUS:
        errs.append("verification.status invalid")
    auth = rec.get("authority", {})
    if isinstance(auth, dict):
        for k in ("requested", "granted", "violation"):
            if k not in auth:
                errs.append("authority.%s missing" % k)
    return errs


def check_provenance(rec):
    errs = []
    prov = rec.get("provenance")
    if not isinstance(prov, dict) or not prov.get("source_class"):
        errs.append("missing provenance.source_class")
    if not rec.get("observation_id"):
        errs.append("missing observation_id (unreplayable)")
    # X-B1: SCHEMA-ERRATUM-001 ratified as schema v0.1 -- a null timestamp
    # is legal ONLY with the erratum marker; without it, ERROR (never
    # imputed, never silently accepted).
    if not rec.get("timestamp"):
        marker = prov.get("timestamp_erratum") if isinstance(prov, dict) else None
        if marker == TIMESTAMP_ERRATUM:
            pass  # null timestamp ratified by SCHEMA-ERRATUM-001 marker
        elif marker is not None:
            errs.append("provenance.timestamp_erratum is %r, expected %r"
                        % (marker, TIMESTAMP_ERRATUM))
        else:
            errs.append("missing timestamp (unreplayable); null timestamp "
                        "requires provenance.timestamp_erratum == %r "
                        "(SCHEMA-ERRATUM-001, schema v0.1)" % TIMESTAMP_ERRATUM)
    return errs


def check_leakage(rec):
    """Heuristic label-leakage patterns in fields shown to the model."""
    errs = []
    state_text = canonical(rec.get("state", {}))
    for m in set(t.lower() for t in LEAK_TOKENS.findall(state_text)):
        errs.append("state contains label-like token %r" % m)
    labels = rec.get("labels") or []
    decision_text = canonical(rec.get("actual_decision", {}))
    for lab in labels:
        if lab and not lab.startswith(("synthetic:", "scenario:")) and lab in decision_text:
            errs.append("label %r echoed in actual_decision" % lab)
    return errs


def lint(path, dup_threshold, max_records):
    report = {"corpus": path, "record_count": 0,
              "findings": [], "ok": True}

    def finding(severity, check, message, ids=None):
        report["findings"].append({"severity": severity, "check": check,
                                   "message": message,
                                   "observation_ids": ids or []})
        if severity == "ERROR":
            report["ok"] = False

    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            if len(records) >= max_records:
                finding("ERROR", "schema",
                        "corpus exceeds --max-records %d" % max_records)
                break
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                finding("ERROR", "schema",
                        "line %d: invalid JSON: %s" % (lineno, exc))
    report["record_count"] = len(records)

    for rec in records:
        rid = rec.get("observation_id", "?") if isinstance(rec, dict) else "?"
        if not isinstance(rec, dict):
            finding("ERROR", "schema", "record is not a JSON object", [rid])
            continue
        for e in check_schema(rec):
            finding("ERROR", "schema", e, [rid])
        for e in check_provenance(rec):
            finding("ERROR", "provenance", e, [rid])
        for e in check_leakage(rec):
            finding("WARN", "leakage", e, [rid])

    by_digest = defaultdict(list)
    for rec in records:
        if isinstance(rec, dict):
            by_digest[digest(rec)].append(rec.get("observation_id", "?"))
    for d, ids in by_digest.items():
        if len(ids) > 1:
            finding("ERROR", "exact_dup",
                    "exact duplicate records (sha256 %s)" % d[:12], ids)

    shingle_sets = [(rec.get("observation_id", "?"),
                     shingles(canonical(rec))) for rec in records
                    if isinstance(rec, dict)]
    # near-dup pairs are collected first so the contamination fallback can
    # reuse them for lineage inference (MATERIAL-3).
    near_dup_pairs = []
    for i in range(len(shingle_sets)):
        for j in range(i + 1, len(shingle_sets)):
            ida, sa = shingle_sets[i]
            idb, sb = shingle_sets[j]
            if jaccard(sa, sb) >= dup_threshold:
                near_dup_pairs.append((ida, idb))
                finding("WARN", "near_dup",
                        "near-duplicate (jaccard>=%.2f)" % dup_threshold,
                        [ida, idb])

    lineage_groups = defaultdict(set)
    lineage_ids = defaultdict(list)
    unbindable = []  # no mission/incident id AND no contamination_group
    for rec in records:
        if not isinstance(rec, dict):
            continue
        lk = lineage_key(rec)
        if lk:
            lineage_groups[lk].add(rec.get("contamination_group"))
            lineage_ids[lk].append(rec.get("observation_id", "?"))
        elif not rec.get("contamination_group"):
            unbindable.append(rec.get("observation_id", "?"))
    for lk, groups in lineage_groups.items():
        if len(groups) > 1:
            finding("ERROR", "contamination",
                    "lineage %s spans contamination groups %s"
                    % (lk, sorted(str(g) for g in groups)),
                    lineage_ids[lk])

    # ---- MATERIAL-3 fallback: mission/incident ids are null for the whole
    # converted corpus, so the primary check above can never fire on it.
    # Fall back to declared contamination_group + near-dup lineage
    # inference, and never pass silently.
    if records and not lineage_groups:
        finding("WARN", "contamination",
                "no mission_id/incident_id lineage bound for any record; "
                "contamination check running in degraded fallback mode "
                "(declared contamination_group + near-dup inference)")
    if unbindable:
        finding("WARN", "contamination",
                "cannot bind lineage for %d record(s): no mission_id, no "
                "incident_id, and no contamination_group; contamination "
                "check is vacuous for these records" % len(unbindable),
                unbindable[:50])
    # Near-dup lineage inference: near-identical records are lineage
    # relatives; they MUST share a contamination_group.
    group_of = {}
    for rec in records:
        if isinstance(rec, dict):
            group_of[rec.get("observation_id", "?")] = (
                rec.get("contamination_group"))
    for ida, idb in near_dup_pairs:
        ga, gb = group_of.get(ida), group_of.get(idb)
        if ga is not None and gb is not None and ga != gb:
            finding("ERROR", "contamination",
                    "near-duplicate lineage inference: near-identical "
                    "records %r and %r carry different contamination "
                    "groups (%r vs %r); related records MUST share one "
                    "group" % (ida, idb, ga, gb), [ida, idb])
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Lint an SLM observation JSONL corpus. Fail-closed: "
                    "exits 2 if any ERROR finding is produced.")
    ap.add_argument("corpus", help="path to JSONL corpus")
    ap.add_argument("--dup-threshold", type=float, default=0.8,
                    help="Jaccard threshold for near-duplicates (default: 0.8)")
    ap.add_argument("--max-records", type=int, default=1_000_000,
                    help="fail if corpus exceeds this many records")
    ap.add_argument("--report", default="-",
                    help="write JSON report here, or '-' for stdout")
    args = ap.parse_args(argv)

    try:
        report = lint(args.corpus, args.dup_threshold, args.max_records)
    except OSError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report == "-":
        sys.stdout.write(text)
    else:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("report written to %s (ok=%s)" % (args.report, report["ok"]),
              file=sys.stderr)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
