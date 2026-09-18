#!/usr/bin/env python3
"""Fail-closed validator for D0-D4 determinism qualification evidence bundles.

Additive tooling only. A determinism bundle (``residual.determinism.bundle.v1``)
wraps one PR #152 ``residual.qualification.evidence.v1`` EvidenceEnvelope and
adds the determinism-specific comparison surface (suite identity, per-run
canonical output hashes, canonicalization policy, equivalence result, optional
negative control). See ``docs/qualification/determinism-classes.md``.

Design rules (fail-closed):

- Wrong schema id, cross-revision evidence, missing required evidence, or any
  inconsistency between the bundle and its embedded envelope is rejected.
- ``UNKNOWN``/``SKIP``/``FAIL`` bundles validate as *retained observations* but
  can never satisfy class entry; only a fully evidenced ``PASS`` qualifies.
- This module assigns no class to any backend. It only decides whether one
  bundle is well-formed evidence for the class it attempted.
- The validator is stdlib-only so it runs on current main. When PR #152's
  ``residual.qualification.evidence`` module is importable, the embedded
  envelope is additionally round-tripped through ``EvidenceEnvelope.from_dict``
  and any rejection there is fatal.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BUNDLE_SCHEMA = "residual.determinism.bundle.v1"
ENVELOPE_SCHEMA = "residual.qualification.evidence.v1"

RESULTS = ("PASS", "FAIL", "UNKNOWN", "SKIP")
CLASSES = ("D0", "D1", "D2", "D3", "D4")
BACKEND_KINDS = (
    "llm_adapter", "browser_provider", "sandbox_executor",
    "fixture_harness", "in_process_executor", "other",
)
FLOAT_POLICIES = ("exact_ieee754_hex", "fixed_precision_decimal", "tolerance")
RELATIONS = ("canonical_bitwise", "canonical_with_float_tolerance", "semantic_declared")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID = re.compile(r"^[0-9a-f]{40}$")
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# ---------------------------------------------------------------------------
# JSON Schema (documentation/contract artifact; the validator below implements
# the same checks procedurally and fail-closed). The shipped JSON copy at
# docs/qualification/schemas/residual.determinism.bundle.v1.schema.json must be
# byte-identical to json.dumps(BUNDLE_JSON_SCHEMA, indent=2, sort_keys=True)+"\n".
# ---------------------------------------------------------------------------

BUNDLE_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "residual.determinism.bundle.v1",
    "title": "DeterminismQualificationBundle",
    "type": "object",
    "required": [
        "schema", "bundle_id", "predecessor_id", "backend", "class_attempted",
        "envelope", "suite", "runs", "canonicalization", "equivalence",
        "result", "non_claims",
    ],
    "additionalProperties": False,
    "properties": {
        "schema": {"const": BUNDLE_SCHEMA},
        "bundle_id": {"type": "string", "format": "uuid"},
        "predecessor_id": {
            "type": ["string", "null"],
            "description": "bundle_id this observation amends/supersedes; null starts a new observation line",
        },
        "backend": {
            "type": "object",
            "required": ["backend_id", "backend_version", "kind"],
            "additionalProperties": False,
            "properties": {
                "backend_id": {"type": "string", "minLength": 1},
                "backend_version": {"type": "string", "minLength": 1},
                "kind": {"enum": list(BACKEND_KINDS)},
            },
        },
        "class_attempted": {"enum": list(CLASSES)},
        "envelope": {
            "description": (
                "Embedded PR #152 EvidenceEnvelope (residual.qualification.evidence.v1). "
                "envelope.source.{commit,tree} is the commit/tree binding; "
                "envelope.gate_id MUST equal 'determinism-<class-lowercase>-<backend_id>'; "
                "envelope.result MUST equal this bundle's result; "
                "envelope.skip_count/unknown_count MUST be 0 for class-entry bundles."
            ),
            "type": "object",
            "required": [
                "schema", "gate_id", "result", "started_at", "finished_at",
                "source", "environment",
            ],
            "properties": {
                "schema": {"const": ENVELOPE_SCHEMA},
                "gate_id": {"type": "string", "minLength": 1},
                "result": {"enum": list(RESULTS)},
                "started_at": {"type": "string"},
                "finished_at": {"type": "string"},
                "source": {
                    "type": "object",
                    "required": ["commit", "tree", "tracked_source_dirty"],
                    "properties": {
                        "commit": {"type": "string", "minLength": 1},
                        "tree": {"type": "string", "minLength": 1},
                        "tracked_source_dirty": {"type": ["boolean", "null"]},
                    },
                },
                "environment": {"type": "object"},
                "command": {"type": "array", "items": {"type": "string"}},
                "evidence": {
                    "type": "object",
                    "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
                "skip_count": {"type": "integer", "minimum": 0},
                "unknown_count": {"type": "integer", "minimum": 0},
                "notes": {"type": "array", "items": {"type": "string"}},
                "non_claims": {"type": "array", "items": {"type": "string"}},
            },
        },
        "suite": {
            "type": "object",
            "required": ["suite_id", "suite_version", "input_hashes", "seed"],
            "additionalProperties": False,
            "properties": {
                "suite_id": {"type": "string", "minLength": 1},
                "suite_version": {"type": "string", "minLength": 1},
                "seed": {"type": ["integer", "null"]},
                "excluded_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "timestamps/UUIDs/other run-unique values excluded from the canonical comparison surface",
                },
                "input_hashes": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "description": "path -> sha256 of every canonical input",
                },
            },
        },
        "runs": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["run_index", "environment", "output_hashes", "canonical_output_sha256"],
                "additionalProperties": False,
                "properties": {
                    "run_index": {"type": "integer", "minimum": 0},
                    "started_at": {"type": "string"},
                    "finished_at": {"type": "string"},
                    "environment": {
                        "type": "object",
                        "required": ["platform", "machine", "python"],
                        "additionalProperties": False,
                        "properties": {
                            "platform": {"type": "string"},
                            "machine": {"type": "string"},
                            "python": {"type": "string"},
                            "container_image_digest": {"type": ["string", "null"]},
                        },
                    },
                    "restart_generation": {"type": "integer", "minimum": 0, "default": 0},
                    "network_disabled": {"type": "boolean", "default": False},
                    "output_hashes": {
                        "type": "object",
                        "minProperties": 1,
                        "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    },
                    "canonical_output_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            },
        },
        "canonicalization": {
            "type": "object",
            "required": ["float_policy", "key_ordering", "encoding", "newline"],
            "additionalProperties": False,
            "properties": {
                "float_policy": {"enum": list(FLOAT_POLICIES)},
                "float_tolerance": {"type": ["number", "null"]},
                "key_ordering": {"const": "sorted_utf8_codepoint"},
                "encoding": {"const": "utf-8"},
                "newline": {"const": "lf"},
            },
        },
        "equivalence": {
            "type": "object",
            "required": ["relation", "all_pairwise_equal"],
            "additionalProperties": False,
            "properties": {
                "relation": {"enum": list(RELATIONS)},
                "semantic_relation_ref": {"type": ["string", "null"]},
                "all_pairwise_equal": {"type": "boolean"},
                "divergences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["run_a", "run_b", "artifact", "hash_a", "hash_b"],
                        "additionalProperties": False,
                        "properties": {
                            "run_a": {"type": "integer"},
                            "run_b": {"type": "integer"},
                            "artifact": {"type": "string"},
                            "hash_a": {"type": "string"},
                            "hash_b": {"type": "string"},
                        },
                    },
                },
            },
        },
        "negative_control": {
            "type": ["object", "null"],
            "required": ["performed", "tamper_detected"],
            "additionalProperties": False,
            "properties": {
                "performed": {"type": "boolean"},
                "tamper_detected": {"type": "boolean"},
                "evidence_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
            },
            "description": "REQUIRED non-null with performed=tamper_detected=true for D4 PASS",
        },
        "result": {"enum": list(RESULTS)},
        "non_claims": {"type": "array", "items": {"type": "string"}},
    },
}


class BundleValidationError(ValueError):
    """Raised when a determinism bundle fails validation. Carries all reasons."""

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__("invalid determinism bundle: " + "; ".join(self.reasons))


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_envelope_structure(envelope: Any, errors: list[str]) -> None:
    if not isinstance(envelope, dict):
        errors.append("envelope must be an object")
        return
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        errors.append(f"envelope.schema must be {ENVELOPE_SCHEMA!r} (cross-revision evidence rejected)")
    for key in ("gate_id", "result", "started_at", "finished_at", "source", "environment"):
        if key not in envelope:
            errors.append(f"envelope.{key} is missing")
            return
    if not _is_str(envelope.get("gate_id")) or not envelope["gate_id"]:
        errors.append("envelope.gate_id must be a non-empty string")
    if envelope.get("result") not in RESULTS:
        errors.append(f"envelope.result must be one of {RESULTS}")
    source = envelope.get("source")
    if not isinstance(source, dict):
        errors.append("envelope.source must be an object")
    else:
        for key in ("commit", "tree"):
            if not _is_str(source.get(key)) or not source[key]:
                errors.append(f"envelope.source.{key} must be a non-empty string")
        if "tracked_source_dirty" not in source:
            errors.append("envelope.source.tracked_source_dirty is missing")
        elif source["tracked_source_dirty"] is not None and not isinstance(source["tracked_source_dirty"], bool):
            errors.append("envelope.source.tracked_source_dirty must be boolean or null")
    if not isinstance(envelope.get("environment"), dict):
        errors.append("envelope.environment must be an object")
    for key in ("skip_count", "unknown_count"):
        if key in envelope and (not _is_int(envelope[key]) or envelope[key] < 0):
            errors.append(f"envelope.{key} must be a non-negative integer")
    evidence = envelope.get("evidence", {})
    if not isinstance(evidence, dict) or any(
        not _is_str(v) or not _SHA256.match(v) for v in evidence.values()
    ):
        errors.append("envelope.evidence values must be sha256 hex strings")


def _cross_check_with_pr152(envelope: dict[str, Any], errors: list[str]) -> None:
    """If PR #152's envelope module is importable, defer to its authority too."""
    try:
        from residual.qualification.evidence import EvidenceEnvelope
    except ImportError:
        return  # pre-#152 checkout: structural checks above are authoritative
    try:
        EvidenceEnvelope.from_dict(envelope)
    except Exception as exc:
        errors.append(f"embedded envelope rejected by residual.qualification.evidence: {type(exc).__name__}: {exc}")


def _check_runs(runs: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(runs, list) or not runs:
        errors.append("runs must be a non-empty array")
        return []
    good: list[dict[str, Any]] = []
    seen_index: set[int] = set()
    for i, run in enumerate(runs):
        where = f"runs[{i}]"
        if not isinstance(run, dict):
            errors.append(f"{where} must be an object")
            continue
        allowed = {"run_index", "started_at", "finished_at", "environment",
                   "restart_generation", "network_disabled", "output_hashes",
                   "canonical_output_sha256"}
        extra = set(run) - allowed
        if extra:
            errors.append(f"{where} has unexpected keys: {sorted(extra)}")
        idx = run.get("run_index")
        if not _is_int(idx) or idx < 0:
            errors.append(f"{where}.run_index must be a non-negative integer")
        elif idx in seen_index:
            errors.append(f"{where}.run_index {idx} is duplicated")
        else:
            seen_index.add(idx)
        env = run.get("environment")
        if not isinstance(env, dict):
            errors.append(f"{where}.environment must be an object")
        else:
            for key in ("platform", "machine", "python"):
                if not _is_str(env.get(key)) or not env[key]:
                    errors.append(f"{where}.environment.{key} must be a non-empty string")
            unknown_env = set(env) - {"platform", "machine", "python", "container_image_digest"}
            if unknown_env:
                errors.append(f"{where}.environment has unexpected keys: {sorted(unknown_env)}")
        rg = run.get("restart_generation", 0)
        if not _is_int(rg) or rg < 0:
            errors.append(f"{where}.restart_generation must be a non-negative integer")
        nd = run.get("network_disabled", False)
        if not isinstance(nd, bool):
            errors.append(f"{where}.network_disabled must be a boolean")
        out = run.get("output_hashes")
        if not isinstance(out, dict) or not out or any(
            not _is_str(v) or not _SHA256.match(v) for v in out.values()
        ):
            errors.append(f"{where}.output_hashes must map paths to sha256 hex")
        if not _is_str(run.get("canonical_output_sha256")) or not _SHA256.match(
            run.get("canonical_output_sha256", "")
        ):
            errors.append(f"{where}.canonical_output_sha256 must be a sha256 hex string")
        good.append(run)
    return good


def validate_bundle(raw: Any) -> dict[str, Any]:
    """Validate one decoded determinism bundle. Fail-closed: raises
    BundleValidationError listing every detected defect. Returns the bundle."""
    errors: list[str] = []
    if not isinstance(raw, dict):
        raise BundleValidationError(["bundle must be a JSON object"])

    # -- schema identity & closed shape --------------------------------------
    if raw.get("schema") != BUNDLE_SCHEMA:
        errors.append(f"schema must be {BUNDLE_SCHEMA!r} (got {raw.get('schema')!r}); unknown revisions are rejected")
    required = set(BUNDLE_JSON_SCHEMA["required"])
    missing = sorted(required - set(raw))
    if missing:
        errors.append(f"missing required keys: {missing}")
    extra = sorted(set(raw) - set(BUNDLE_JSON_SCHEMA["properties"]))
    if extra:
        errors.append(f"unexpected keys: {extra}")
    if missing or extra or errors:
        raise BundleValidationError(errors)

    if not _is_str(raw["bundle_id"]) or not _UUID.match(raw["bundle_id"]):
        errors.append("bundle_id must be a UUID string")
    pred = raw["predecessor_id"]
    if pred is not None and (not _is_str(pred) or not _UUID.match(pred)):
        errors.append("predecessor_id must be null or a UUID string")

    backend = raw["backend"]
    if not isinstance(backend, dict):
        errors.append("backend must be an object")
        backend = {}
    else:
        if set(backend) != {"backend_id", "backend_version", "kind"}:
            errors.append("backend must contain exactly backend_id, backend_version, kind")
        for key in ("backend_id", "backend_version"):
            if not _is_str(backend.get(key)) or not backend.get(key):
                errors.append(f"backend.{key} must be a non-empty string")
        if backend.get("kind") not in BACKEND_KINDS:
            errors.append(f"backend.kind must be one of {BACKEND_KINDS}")
    backend_id = backend.get("backend_id", "")

    cls = raw["class_attempted"]
    if cls not in CLASSES:
        errors.append(f"class_attempted must be one of {CLASSES}")

    # -- embedded envelope ----------------------------------------------------
    envelope = raw["envelope"]
    _check_envelope_structure(envelope, errors)
    if isinstance(envelope, dict):
        _cross_check_with_pr152(envelope, errors)
        # bundle <-> envelope cross-references
        if envelope.get("result") != raw.get("result"):
            errors.append("envelope.result must equal bundle result (cross-reference mismatch)")
        if isinstance(backend_id, str) and backend_id and cls in CLASSES:
            expected_gate = f"determinism-{cls.lower()}-{backend_id}"
            if envelope.get("gate_id") != expected_gate:
                errors.append(f"envelope.gate_id must be {expected_gate!r} for this bundle")

    result = raw["result"]
    if result not in RESULTS:
        errors.append(f"result must be one of {RESULTS}")

    # -- suite ----------------------------------------------------------------
    suite = raw["suite"]
    if not isinstance(suite, dict):
        errors.append("suite must be an object")
        suite = {}
    else:
        allowed = {"suite_id", "suite_version", "input_hashes", "seed", "excluded_fields"}
        if set(suite) - allowed:
            errors.append(f"suite has unexpected keys: {sorted(set(suite) - allowed)}")
        for key in ("suite_id", "suite_version"):
            if not _is_str(suite.get(key)) or not suite.get(key):
                errors.append(f"suite.{key} must be a non-empty string")
        if suite.get("seed") is not None and not _is_int(suite.get("seed")):
            errors.append("suite.seed must be an integer or null")
        ih = suite.get("input_hashes")
        if not isinstance(ih, dict) or not ih or any(
            not _is_str(v) or not _SHA256.match(v) for v in ih.values()
        ):
            errors.append("suite.input_hashes must map at least one path to a sha256 hex")

    # -- runs -----------------------------------------------------------------
    runs = _check_runs(raw["runs"], errors)

    # -- canonicalization -----------------------------------------------------
    canon = raw["canonicalization"]
    if not isinstance(canon, dict):
        errors.append("canonicalization must be an object")
        canon = {}
    else:
        if set(canon) - {"float_policy", "float_tolerance", "key_ordering", "encoding", "newline"}:
            errors.append("canonicalization has unexpected keys")
        if canon.get("float_policy") not in FLOAT_POLICIES:
            errors.append(f"canonicalization.float_policy must be one of {FLOAT_POLICIES}")
        ft = canon.get("float_tolerance")
        if ft is not None and not (isinstance(ft, (int, float)) and not isinstance(ft, bool)):
            errors.append("canonicalization.float_tolerance must be a number or null")
        if canon.get("float_policy") == "tolerance" and ft is None:
            errors.append("tolerance float_policy requires a declared float_tolerance")
        if canon.get("float_policy") != "tolerance" and ft is not None:
            errors.append("float_tolerance is only meaningful with tolerance float_policy")
        if canon.get("key_ordering") != "sorted_utf8_codepoint":
            errors.append("canonicalization.key_ordering must be 'sorted_utf8_codepoint'")
        if canon.get("encoding") != "utf-8":
            errors.append("canonicalization.encoding must be 'utf-8'")
        if canon.get("newline") != "lf":
            errors.append("canonicalization.newline must be 'lf'")

    # -- equivalence ----------------------------------------------------------
    equiv = raw["equivalence"]
    if not isinstance(equiv, dict):
        errors.append("equivalence must be an object")
        equiv = {}
    else:
        if set(equiv) - {"relation", "semantic_relation_ref", "all_pairwise_equal", "divergences"}:
            errors.append("equivalence has unexpected keys")
        if equiv.get("relation") not in RELATIONS:
            errors.append(f"equivalence.relation must be one of {RELATIONS}")
        if equiv.get("relation") == "semantic_declared" and not equiv.get("semantic_relation_ref"):
            errors.append("semantic_declared relation requires semantic_relation_ref")
        if not isinstance(equiv.get("all_pairwise_equal"), bool):
            errors.append("equivalence.all_pairwise_equal must be a boolean")

    # -- negative control -----------------------------------------------------
    nc = raw.get("negative_control")
    if nc is not None:
        if not isinstance(nc, dict):
            errors.append("negative_control must be an object or null")
            nc = None
        else:
            if set(nc) - {"performed", "tamper_detected", "evidence_sha256"}:
                errors.append("negative_control has unexpected keys")
            for key in ("performed", "tamper_detected"):
                if not isinstance(nc.get(key), bool):
                    errors.append(f"negative_control.{key} must be a boolean")
            ev = nc.get("evidence_sha256")
            if ev is not None and (not _is_str(ev) or not _SHA256.match(ev)):
                errors.append("negative_control.evidence_sha256 must be sha256 hex or null")

    if not isinstance(raw["non_claims"], list) or any(
        not _is_str(item) for item in raw["non_claims"]
    ):
        errors.append("non_claims must be an array of strings")

    # -- result-dependent class-entry rules (fail-closed) ----------------------
    if result == "PASS":
        if cls == "D0":
            errors.append("D0 is the default unqualified class; no bundle can PASS a D0 attempt")
        if isinstance(envelope, dict):
            if envelope.get("result") != "PASS":
                errors.append("PASS bundle requires envelope.result == PASS")
            if envelope.get("skip_count", 0) != 0:
                errors.append("PASS bundle requires envelope.skip_count == 0")
            if envelope.get("unknown_count", 0) != 0:
                errors.append("PASS bundle requires envelope.unknown_count == 0")
            src = envelope.get("source") or {}
            if src.get("tracked_source_dirty") is not False:
                errors.append("PASS bundle requires tracked_source_dirty == false")
            # Class-entry evidence binds an exact revision: stricter than the
            # envelope contract (non-empty), per compat-notes C2.
            for key in ("commit", "tree"):
                if not _is_str(src.get(key)) or not _GIT_OID.match(src[key]):
                    errors.append(f"PASS bundle requires envelope.source.{key} to be a full 40-hex git object id")
        if equiv.get("all_pairwise_equal") is not True:
            errors.append("PASS bundle requires equivalence.all_pairwise_equal == true")
        if equiv.get("divergences"):
            errors.append("PASS bundle must not record divergences")

        relation = equiv.get("relation")
        if cls in ("D2", "D3", "D4"):
            if relation != "canonical_bitwise":
                errors.append(f"{cls} PASS requires canonical_bitwise equivalence (float tolerance is a D1 property)")
            if canon.get("float_policy") == "tolerance":
                errors.append(f"{cls} PASS forbids tolerance float_policy")
            digests = {r.get("canonical_output_sha256") for r in runs}
            if len(digests) > 1:
                errors.append(f"{cls} PASS requires identical canonical_output_sha256 across all runs")
        if cls == "D1":
            if len(runs) < 3:
                errors.append("D1 PASS requires >= 3 repeat runs")
            if relation == "canonical_with_float_tolerance" and canon.get("float_policy") != "tolerance":
                errors.append("canonical_with_float_tolerance requires tolerance float_policy")
        if cls in ("D2", "D3", "D4"):
            if suite.get("seed") is None:
                errors.append(f"{cls} PASS requires an explicit recorded seed")
            if len(runs) < 2:
                errors.append(f"{cls} PASS requires >= 2 replay runs of the same seed")
        if cls in ("D3", "D4"):
            pairs = {
                (r.get("environment", {}).get("platform"), r.get("environment", {}).get("machine"))
                for r in runs
            }
            if len(pairs) < 2:
                errors.append(f"{cls} PASS requires >= 2 distinct (platform, machine) environments")
            if not any(_is_int(r.get("restart_generation")) and r["restart_generation"] >= 1 for r in runs):
                errors.append(f"{cls} PASS requires >= 1 run with restart_generation >= 1")
        if cls == "D4":
            if nc is None:
                errors.append("D4 PASS requires a non-null negative_control")
            else:
                if nc.get("performed") is not True or nc.get("tamper_detected") is not True:
                    errors.append("D4 PASS requires negative_control.performed and tamper_detected == true")
                if not nc.get("evidence_sha256"):
                    errors.append("D4 PASS requires negative_control.evidence_sha256")
            if not any(r.get("network_disabled") is True for r in runs):
                errors.append("D4 PASS requires >= 1 network-disabled (air-gapped) replay run")

    if errors:
        raise BundleValidationError(errors)
    return raw


def load_bundle(path: Path | str) -> dict[str, Any]:
    """Load and validate a bundle file. Any decode/validation defect raises."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleValidationError([f"unreadable bundle {path}: {type(exc).__name__}: {exc}"]) from exc
    return validate_bundle(raw)


def write_schema(path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BUNDLE_JSON_SCHEMA, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("bundle", nargs="*", type=Path, help="bundle JSON file(s) to validate")
    parser.add_argument("--write-schema", type=Path, help="write the JSON schema artifact and exit")
    args = parser.parse_args(argv)
    if args.write_schema:
        write_schema(args.write_schema)
        return 0
    if not args.bundle:
        parser.error("at least one bundle file is required (or --write-schema)")
    rc = 0
    for path in args.bundle:
        try:
            bundle = load_bundle(path)
        except BundleValidationError as exc:
            rc = 1
            print(f"REJECTED {path}", file=sys.stderr)
            for reason in exc.reasons:
                print(f"  - {reason}", file=sys.stderr)
            continue
        print(f"OK {path} backend={bundle['backend']['backend_id']} "
              f"class_attempted={bundle['class_attempted']} result={bundle['result']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
