#!/usr/bin/env python3
"""Offline MC-V1-001 evidence consistency and byte-integrity checks.

This does not authenticate native executions, grant Station authority, or scan
arbitrary values/files for secrets. Use a frozen, operator-owned evidence root.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "docs/v1/MC-V1-001-NATIVE-EVIDENCE.schema.json"
MAX_JSON = 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
HOOKS = {"hermes": {"pre_llm_call", "post_llm_call"},
         "openclaw": {"message_received", "message_sent", "before_prompt_build", "gateway_stop"}}
FACTS = ("project_id", "task_id", "attempt", "spec_hash")
PROVENANCE = ("runtime_version", "build_identity", "plugin_source_sha256",
              "conversation_id", "instance_id", "binding_id")
STATES = ("false_completion_before_state", "false_completion_after_state",
          "verified_transition_observed", "acceptance_authority")
FORBIDDEN_KEYS = {"token", "secret", "password", "api_key", "authorization", "credential"}


class NativeEvidenceError(ValueError):
    pass


def reject_secret_keys(value):
    """A key-name denylist only; never a secret-free-content assertion."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise NativeEvidenceError("forbidden secret-bearing key")
            reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_keys(item)


def load_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise NativeEvidenceError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise NativeEvidenceError("non-finite JSON number")

    if len(raw) > MAX_JSON:
        raise NativeEvidenceError("JSON byte limit exceeded")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise NativeEvidenceError("invalid UTF-8 JSON (duplicate/non-finite/deep input rejected)") from exc


def schema_check(value, rule, schema):
    """Enforce the closed subset used by the bundled schema; no remote refs.

    Deliberately not a general JSON Schema engine. Unsupported keywords fail
    closed, including those in unvisited definitions (checked on schema load).
    """
    if "$ref" in rule:
        schema_check(value, schema["$defs"][rule["$ref"].removeprefix("#/$defs/")], schema)
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if "type" in rule and type(value) is not types[rule["type"]]:
        raise NativeEvidenceError("schema type mismatch")
    if "const" in rule and (type(value) is not type(rule["const"]) or value != rule["const"]):
        raise NativeEvidenceError("schema constant mismatch")
    if "enum" in rule and not any(type(value) is type(v) and value == v for v in rule["enum"]):
        raise NativeEvidenceError("schema enum mismatch")
    if isinstance(value, dict):
        if not set(rule.get("required", ())) <= value.keys():
            raise NativeEvidenceError("missing required schema field")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False and value.keys() - properties.keys():
            raise NativeEvidenceError("unknown schema field")
        for key in value.keys() & properties.keys():
            schema_check(value[key], properties[key], schema)
    if isinstance(value, list):
        if not rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", len(value)):
            raise NativeEvidenceError("schema array length mismatch")
        if "items" in rule:
            for item in value:
                schema_check(item, rule["items"], schema)
    if isinstance(value, str):
        if not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", len(value)):
            raise NativeEvidenceError("schema string length mismatch")
        if "pattern" in rule and not re.search(rule["pattern"], value):
            raise NativeEvidenceError("schema pattern mismatch")
        if rule.get("format") == "date-time":
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-5][0-9])", value):
                    raise ValueError()
                datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
            except ValueError as exc:
                raise NativeEvidenceError("invalid date-time") from exc
    if type(value) is int and "minimum" in rule and value < rule["minimum"]:
        raise NativeEvidenceError("schema minimum mismatch")


def load_schema():
    schema = load_json(SCHEMA_PATH.read_bytes())
    allowed = {"$schema", "$id", "title", "description", "$defs", "$ref", "type", "const", "enum",
               "required", "properties", "additionalProperties", "minItems", "maxItems", "items",
               "minLength", "maxLength", "pattern", "format", "minimum"}

    def check(rule):
        if type(rule) is not dict or rule.keys() - allowed:
            raise NativeEvidenceError("unsupported schema keyword")
        if "type" in rule and rule["type"] not in {"object", "array", "string", "integer", "boolean"}:
            raise NativeEvidenceError("unsupported schema type")
        if "format" in rule and rule["format"] != "date-time":
            raise NativeEvidenceError("unsupported schema format")
        if "additionalProperties" in rule and rule["additionalProperties"] is not False:
            raise NativeEvidenceError("unsupported additionalProperties rule")
        if "$ref" in rule and rule["$ref"] not in {"#/$defs/" + k for k in schema["$defs"]}:
            raise NativeEvidenceError("unsupported schema reference")
        for keyword in ("properties", "$defs"):
            for child in rule.get(keyword, {}).values():
                check(child)
        if "items" in rule:
            check(rule["items"])

    check(schema)
    return schema


def evidence_name(name):
    # Portable relative archive names: excludes drives, UNC, ADS, traversal,
    # percent escapes, Windows device aliases, backslashes and trailing dots.
    if not isinstance(name, str) or not 1 <= len(name) <= 256:
        raise NativeEvidenceError("invalid evidence path")
    for part in name.split("/"):
        if (not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part) or part.endswith(".")
                or re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])", part.split(".")[0])):
            raise NativeEvidenceError("invalid evidence path")
    return name


def checked_path(path):
    if str(path).startswith(("//", "\\\\")):
        raise NativeEvidenceError("network/device evidence roots are not supported")
    path = Path(path).absolute()
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise NativeEvidenceError("symlink/reparse point in evidence path")
    return path


def read_regular(path, limit):
    path = checked_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
        raise NativeEvidenceError("evidence must be a bounded regular file with one link")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    def identity(info):
        # Windows path stat and handle fstat can expose different ctime values.
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if identity(before) != identity(opened):
            raise NativeEvidenceError("evidence changed before reading")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    final = checked_path(path).stat()
    if (len(raw) > limit or len(raw) != before.st_size
            or not identity(before) == identity(after) == identity(final)
            or before.st_ctime_ns != final.st_ctime_ns or opened.st_ctime_ns != after.st_ctime_ns):
        raise NativeEvidenceError("evidence changed while reading")
    return raw


def validate(doc, *, expected_commit, expected_tree, expected_wheel_sha256,
             expected_project_id, expected_task_id, expected_attempt, expected_spec_hash,
             evidence_root):
    schema = load_schema()
    candidate = dict(commit=expected_commit, tree=expected_tree, wheel_sha256=expected_wheel_sha256)
    facts = dict(project_id=expected_project_id, task_id=expected_task_id,
                 attempt=expected_attempt, spec_hash=expected_spec_hash)
    schema_check(candidate, schema["$defs"]["candidate"], schema)
    schema_check(facts, schema["$defs"]["facts"], schema)
    reject_secret_keys(doc)
    schema_check(doc, schema, schema)
    if doc["candidate"] != candidate or {k: doc["station"][k] for k in FACTS} != facts:
        raise NativeEvidenceError("candidate/Station facts differ from external selection")
    station = doc["station"]
    if station["false_completion_before_state"] != station["false_completion_after_state"]:
        raise NativeEvidenceError("false completion changed Station task state")
    harnesses = doc["harnesses"]
    if {h["name"] for h in harnesses} != set(HOOKS):
        raise NativeEvidenceError("exact Hermes and OpenClaw evidence required")
    if len({h["binding_id"] for h in harnesses}) != 2:
        raise NativeEvidenceError("distinct native bindings required")
    root = checked_path(evidence_root)
    if not root.is_dir():
        raise NativeEvidenceError("evidence root must be a directory")
    files = {}
    names = set()
    total = 0
    for entry in doc["evidence_files"]:
        name = evidence_name(entry["name"])
        if name.casefold() in names:
            raise NativeEvidenceError("duplicate/aliased evidence path")
        names.add(name.casefold())
        raw = read_regular(root / name, min(MAX_FILE, MAX_TOTAL - total))
        total += len(raw)
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise NativeEvidenceError("evidence file digest mismatch")
        files[name] = raw

    structured = [station["evidence_file"]] + [e["evidence_file"] for h in harnesses for e in h["hook_executions"]]
    if len(set(structured)) != len(structured):
        raise NativeEvidenceError("each capture requires a distinct evidence file")

    def record(name, definition):
        if name not in files:
            raise NativeEvidenceError("capture is absent from evidence_files")
        value = load_json(files[name])
        reject_secret_keys(value)
        schema_check(value, schema["$defs"][definition], schema)
        if value["candidate"] != candidate or value["station"] != facts:
            raise NativeEvidenceError("capture candidate/Station facts mismatch")
        refs = value["raw_evidence_files"]
        if len(refs) != len(set(refs)) or any(ref not in files or ref in structured for ref in refs):
            raise NativeEvidenceError("raw evidence reference missing, repeated, or points to a capture")
        return value

    observed = record(station["evidence_file"], "station_capture")
    if any(observed[k] != station[k] for k in STATES):
        raise NativeEvidenceError("Station capture differs from manifest")
    events = set()
    for harness in harnesses:
        executions = harness["hook_executions"]
        if len(executions) != len(HOOKS[harness["name"]]) or {e["hook"] for e in executions} != HOOKS[harness["name"]]:
            raise NativeEvidenceError("individual native hook execution missing or duplicated")
        if harness["name"] == "openclaw" and not (harness["gateway_restart_proven"] and harness["cancellation_stop_proven"]):
            raise NativeEvidenceError("OpenClaw restart/cancellation stop proof incomplete")
        for execution in executions:
            observed = record(execution["evidence_file"], "hook_capture")
            if (observed["harness"] != harness["name"] or observed["hook"] != execution["hook"]
                    or any(observed[k] != harness[k] for k in PROVENANCE)):
                raise NativeEvidenceError("hook capture native identity/provenance mismatch")
            event = (harness["name"], observed["event_id"])
            if event in events:
                raise NativeEvidenceError("reused hook execution event")
            events.add(event)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--evidence-root", type=Path, required=True)
    for field in ("commit", "tree", "wheel-sha256", "project-id", "task-id", "spec-hash"):
        parser.add_argument("--expected-" + field, required=True)
    parser.add_argument("--expected-attempt", type=int, required=True)
    args = vars(parser.parse_args(argv))
    try:
        doc = load_json(read_regular(args.pop("evidence"), MAX_JSON))
        validate(doc, **args)
    except (OSError, ValueError, RecursionError) as exc:
        # Do not echo untrusted values, JSON, filesystem paths or file contents.
        print("FAIL: " + (str(exc) if isinstance(exc, NativeEvidenceError) else "unreadable or malformed evidence"))
        return 1
    print("PASS: MC-V1-001 evidence consistency and file digests checked; native authenticity and secret review remain external")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
