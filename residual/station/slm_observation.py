"""Schema-native SLM observation export (EXP-M6-SLM). Collection only.

Emits canonical `slm-observation-v0` records (docs/research/EXP-M6-SLM/observation.schema.json
on branch research/exp-m6-slm-00, blob 6e549b05e0fab3684d6ec7173985aa734e55ffca; vendored copy
at residual/station/schemas/slm-observation.json) at Station decision points.

Hard rules:
- Collection is NOT training authorization. Every record is emitted with
  contamination_group=null and labels marking it quarantined/unallocated until the
  freeze assigns contamination groups.
- Fail-closed for the host: emission failures never block authoritative operation.
  Callers use Station._slm_observe, which logs the failure as a station event.
- Redactions at emission are marked ([REDACTED:<kind>]) and counted in provenance,
  never silent.
- Storage is an append-only, date-rotated JSONL log whose records are digest-chained
  (each line references the previous line digest via an envelope outside the record).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from residual.core import ContractError, canonical

SCHEMA_VERSION = "slm-observation-v0"
SCHEMA_FILE = Path(__file__).parent / "schemas" / "slm-observation.json"
GENESIS_DIGEST = "0" * 64
HEAD_FILE = "chain_head"
LOG_PREFIX = "observations-"

_QUARANTINE_LABELS = ("collection-only", "quarantined-unallocated")

# Marked redaction denylist. Kinds appear in the replacement marker and in
# provenance.redaction_kinds so downstream consumers see that redaction happened.
DEFAULT_DENYLIST: tuple[tuple[str, str], ...] = (
    ("credential", r"(?i)(api[_-]?key|access[_-]?key|secret|password|passwd|token|authorization|credential)\s*[:=]\s*[^\s,;]{4,}"),
    ("bearer", r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    ("private_key", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"),
    ("ipv4", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ("hostname", r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:local|lan|internal|corp|home|arpa)\b"),
)
MAX_DENYLIST_PATTERN = 200
MAX_DENYLIST_ENTRIES = 20


def load_schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def compile_denylist(extra=()) -> list[tuple[str, re.Pattern]]:
    """Compile the default plus deployment-configured redaction patterns."""
    patterns = [(kind, re.compile(pat)) for kind, pat in DEFAULT_DENYLIST]
    if extra is None:
        extra = ()
    if not isinstance(extra, (list, tuple)) or len(extra) > MAX_DENYLIST_ENTRIES:
        raise ContractError("slm_observation_denylist must be a list of at most 20 patterns")
    for pat in extra:
        if not isinstance(pat, str) or not pat or len(pat) > MAX_DENYLIST_PATTERN:
            raise ContractError("slm_observation_denylist patterns must be nonempty strings up to 200 chars")
        try:
            patterns.append(("custom", re.compile(pat)))
        except re.error:
            raise ContractError("slm_observation_denylist contains an invalid regular expression") from None
    return patterns


def redact_value(value: Any, patterns) -> tuple[Any, int, list[str]]:
    """Recursively redact denylist matches. Replacements are marked, never silent."""
    count, kinds = 0, set()

    def scrub(v):
        nonlocal count
        if isinstance(v, str):
            for kind, pattern in patterns:
                v, n = pattern.subn("[REDACTED:" + kind + "]", v)
                if n:
                    count += n
                    kinds.add(kind)
            return v
        if isinstance(v, dict):
            return {k: scrub(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [scrub(x) for x in v]
        return v

    return scrub(value), count, sorted(kinds)


# Minimal validator for the JSON-schema subset used by slm-observation-v0
# (the runtime has no jsonschema dependency; pyproject ships defusedxml only).
_JSON_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
               "integer": int, "number": (int, float), "null": type(None)}


def _type_ok(value, type_name) -> bool:
    if type_name in ("integer", "number") and type(value) is bool:
        return False
    return isinstance(value, _JSON_TYPES[type_name])


def _check(value, schema, path):
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: value not in enum")
    types = schema.get("type")
    if types is not None:
        allowed = [types] if isinstance(types, str) else list(types)
        if not any(_type_ok(value, t) for t in allowed):
            raise ContractError(f"{path}: type must be {'/'.join(allowed)}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ContractError(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(props):
            raise ContractError(f"{path}: additional properties {sorted(set(value) - set(props))}")
        for key, sub in props.items():
            if key in value:
                _check(value[key], sub, f"{path}.{key}")
    elif isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _check(item, schema["items"], f"{path}[{i}]")
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        raise ContractError(f"{path}: string below minLength")
    if type(value) in (int, float) and "minimum" in schema and value < schema["minimum"]:
        raise ContractError(f"{path}: below minimum")


def validate_observation(record: dict, schema: dict | None = None) -> dict:
    """Validate a record against the vendored canonical schema; raise ContractError."""
    schema = schema or load_schema()
    _check(record, schema, "observation")
    ts = record["timestamp"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})", ts):
        raise ContractError("observation.timestamp: not an RFC 3339 date-time")
    return record


def envelope_digest(record: dict, prev_digest: str) -> str:
    return hashlib.sha256((prev_digest + "\n" + canonical(record)).encode("utf-8")).hexdigest()


class SlmObservationLog:
    """Append-only, date-rotated, digest-chained JSONL observation log.

    Each line is an envelope {"seq", "prev_digest", "record", "digest"}; the chain
    metadata lives outside the schema record so the record itself stays strictly
    schema-valid (additionalProperties: false). The head pointer in `chain_head`
    carries the chain across date rotations and process restarts.
    """

    def __init__(self, root):
        self.root = Path(root)

    def _head(self) -> tuple[str, int]:
        pointer = self.root / HEAD_FILE
        if pointer.is_file():
            try:
                data = json.loads(pointer.read_text(encoding="utf-8"))
                digest, count = data["digest"], data["count"]
                if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) and type(count) is int and count >= 0:
                    return digest, count
            except (ValueError, KeyError, OSError):
                pass
            raise ContractError("SLM observation chain head is corrupt; investigate before resuming export")
        return GENESIS_DIGEST, 0

    def append(self, record: dict) -> dict:
        validate_observation(record)
        self.root.mkdir(parents=True, exist_ok=True)
        prev, count = self._head()
        digest = envelope_digest(record, prev)
        day = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        envelope = {"seq": count + 1, "prev_digest": prev, "record": record, "digest": digest}
        line = canonical(envelope) + "\n"
        with open(self.root / f"{LOG_PREFIX}{day}.jsonl", "a", encoding="utf-8") as f:
            f.write(line)
        (self.root / HEAD_FILE).write_text(canonical({"digest": digest, "count": count + 1}), encoding="utf-8")
        return envelope

    def files(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(self.root.glob(LOG_PREFIX + "*.jsonl"))


def verify_log(root) -> bool:
    """Re-verify the full digest chain and head pointer. Detects tamper/truncation."""
    log = SlmObservationLog(root)
    prev, count = GENESIS_DIGEST, 0
    try:
        for path in log.files():
            for line in path.read_text(encoding="utf-8").splitlines():
                env = json.loads(line)
                if set(env) != {"seq", "prev_digest", "record", "digest"}:
                    return False
                if env["seq"] != count + 1 or env["prev_digest"] != prev:
                    return False
                if env["digest"] != envelope_digest(env["record"], prev):
                    return False
                validate_observation(env["record"])
                prev, count = env["digest"], env["seq"]
        pointer = Path(root) / HEAD_FILE
        if not pointer.is_file():
            return count == 0
        head = json.loads(pointer.read_text(encoding="utf-8"))
        return head == {"digest": prev, "count": count} if count else False
    except (ValueError, KeyError, TypeError, OSError, ContractError):
        return False


def code_version() -> str:
    """Best-available code provenance: deployment-provided commit, else package version."""
    commit = os.environ.get("RESIDUAL_GIT_SHA") or os.environ.get("RESIDUAL_COMMIT")
    if commit and re.fullmatch(r"[0-9a-f]{7,64}", commit):
        return commit
    try:
        from importlib.metadata import version
        return "residual-agent-harness==" + version("residual-agent-harness")
    except Exception:
        return "unknown"


class SlmObservationEmitter:
    """Builds, sanitizes, validates and appends canonical SLM observation records.

    This class raises on failure by design; the Station fail-closed wrapper
    (Station._slm_observe) converts failures into logged station events.
    """

    def __init__(self, root, *, source_class="ax21", component="residual.station.service"):
        if source_class not in {"ax21", "synthetic", "benchmark", "replay", "other"}:
            raise ContractError("invalid SLM source_class")
        self.log = SlmObservationLog(Path(root) / "slm-observations")
        self.source_class = source_class
        self.component = component

    def build(self, *, mission_id, incident_id=None, generation=None, artifact_digests=(),
              decision_point=None, state, proposed_decision, actual_decision, outcome,
              verification, cost=None, authority, escalation=None, labels=(), notes=None,
              denylist=()) -> dict:
        if not isinstance(state, dict) or not isinstance(actual_decision, dict) or not isinstance(outcome, dict):
            raise ContractError("state, actual_decision and outcome must be objects")
        if proposed_decision is not None and not isinstance(proposed_decision, dict):
            raise ContractError("proposed_decision must be an object or null")
        verification = dict(verification or {})
        verification.setdefault("status", "unknown")
        verification.setdefault("verifier_refs", [])
        authority = {"requested": list(authority.get("requested", [])),
                     "granted": list(authority.get("granted", [])),
                     "violation": bool(authority.get("violation", False))} if isinstance(authority, dict) else None
        if authority is None:
            raise ContractError("authority must be an object with requested/granted/violation")
        cost = {k: v for k, v in dict(cost or {}).items()
                if k in {"inference_usd", "energy_wh", "latency_ms", "operator_active_seconds", "frontier_calls"} and v is not None}
        provenance = {"source_class": self.source_class,
                      "mission_id": mission_id, "incident_id": incident_id,
                      "generation": generation,
                      "artifact_digests": list(artifact_digests or []),
                      "component": self.component,
                      "code_version": code_version()}
        if decision_point:
            provenance["decision_point"] = decision_point
        record = {
            "schema_version": SCHEMA_VERSION,
            "observation_id": uuid.uuid4().hex,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "provenance": provenance,
            # Freeze assigns contamination groups; emitted records stay quarantined.
            "contamination_group": None,
            "state": state,
            "proposed_decision": proposed_decision,
            "actual_decision": actual_decision,
            "outcome": outcome,
            "verification": verification,
            "cost": cost,
            "authority": authority,
            "labels": sorted(set(_QUARANTINE_LABELS) | set(labels or ())),
            "notes": notes,
        }
        if escalation is not None:
            record["escalation"] = escalation
        record, redactions, kinds = redact_value(record, compile_denylist(denylist))
        record["provenance"]["redactions"] = redactions
        record["provenance"]["redaction_kinds"] = kinds
        return validate_observation(record)

    def emit(self, denylist=(), **fields) -> dict:
        """Build and append one observation. Raises ContractError/OSError on failure."""
        return self.log.append(self.build(denylist=denylist, **fields))
