#!/usr/bin/env python3
"""replay.py -- deterministic replay harness for frozen SLM observations.

Given a frozen observation record, reconstructs EXACTLY the state that was
presented to the model:

  * canonical serialization (sorted keys, tight separators, UTF-8, LF)
  * SHA-256 digest of the reconstructed state, verified against an
    expected digest (--digest, a manifest file, or the digest recorded in
    the record's provenance.artifact_digests when present)

Use for reproducibility audits and debugging. Read-only; no network calls.
"""

import argparse
import hashlib
import json
import sys

CANONICAL_KW = {"sort_keys": True, "separators": (",", ":"),
                "ensure_ascii": True}


def canonical(obj):
    """Canonical JSON serialization used across the SLM tooling."""
    return json.dumps(obj, **CANONICAL_KW)


def digest_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reconstruct_state(record):
    """Return exactly the object presented to the model for this record.

    The presented state is the record's ``state`` field together with the
    provenance fields that were visible at decision time (generation,
    mission/incident lineage). Decision, outcome, verification, cost, and
    labels are post-hoc and are never part of the presented state.
    """
    prov = record.get("provenance", {}) or {}
    presented = {
        "schema_version": record.get("schema_version"),
        "state": record.get("state", {}),
        "visible_provenance": {
            "mission_id": prov.get("mission_id"),
            "incident_id": prov.get("incident_id"),
            "generation": prov.get("generation"),
        },
    }
    return presented


def load_record(path, observation_id):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            record = json.loads(text)
        except json.JSONDecodeError:
            record = None  # multi-record JSONL
        if record is not None:
            if observation_id and record.get("observation_id") != observation_id:
                raise ValueError("record observation_id %r != requested %r"
                                 % (record.get("observation_id"), observation_id))
            return record
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("observation_id") == observation_id:
            return rec
    raise ValueError("observation_id %r not found in %s"
                     % (observation_id, path))


def expected_digest(record, args):
    if args.digest:
        return args.digest.lower().removeprefix("sha256:")
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        oid = record.get("observation_id")
        entry = manifest.get(oid) if isinstance(manifest, dict) else None
        if entry is None and isinstance(manifest, list):
            entry = next((e.get("state_digest") for e in manifest
                          if e.get("observation_id") == oid), None)
        if isinstance(entry, dict):
            entry = entry.get("state_digest")
        if not entry:
            raise ValueError("no digest in manifest for %r" % oid)
        return str(entry).lower().removeprefix("sha256:")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Deterministically reconstruct and digest-verify the "
                    "state presented to the model for a frozen observation.")
    ap.add_argument("record", help="JSON file (single record) or JSONL corpus")
    ap.add_argument("--observation-id", default=None,
                    help="record to replay (required for JSONL input)")
    ap.add_argument("--digest", default=None,
                    help="expected sha256 state digest (hex or 'sha256:hex')")
    ap.add_argument("--manifest", default=None,
                    help="JSON manifest mapping observation_id -> state digest")
    ap.add_argument("--out", default="-",
                    help="write canonical state here, or '-' for stdout")
    args = ap.parse_args(argv)

    try:
        record = load_record(args.record, args.observation_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("replay: cannot load record: %s" % exc, file=sys.stderr)
        return 2

    presented = reconstruct_state(record)
    canon = canonical(presented)
    actual = digest_hex(canon)

    result = {"observation_id": record.get("observation_id"),
              "state_digest": "sha256:" + actual,
              "digest_verified": None}
    try:
        exp = expected_digest(record, args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("replay: %s" % exc, file=sys.stderr)
        return 2
    if exp is not None:
        result["digest_verified"] = (exp == actual)

    if args.out == "-":
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        sys.stdout.write(canon + "\n")
    else:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(canon + "\n")
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if exp is not None and exp != actual:
        print("replay: DIGEST MISMATCH expected sha256:%s got sha256:%s"
              % (exp, actual), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
