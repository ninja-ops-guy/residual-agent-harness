"""Durable swarm project-state synchronization and capability registry.

This module is intentionally transport-agnostic. It gives Station a fail-closed,
rebuildable coordination contract without granting models, chat, or presence any
authority. Network/authentication wiring belongs to the worker identity lane.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from residual.core import ContractError, canonical, digest, identifier, strict_json


PROJECT_STATE_SCHEMA = "residual.project_state.v1"
STATE_DELTA_SCHEMA = "residual.state_delta.v1"
CAPABILITY_SCHEMA = "residual.runner_capabilities.v1"
SYNC_SCHEMA = "residual.runner_sync.v1"

_SHA = re.compile(r"^[a-f0-9]{40,64}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_CAPABILITY_STATES = {"advertised", "observed", "qualified"}
_PLACEMENTS = {"local", "remote"}

# These keys describe current coordination truth. Non-authoritative model
# synthesis may be retained as annotations, but it may never shadow them.
AUTHORITATIVE_FIELDS = {
    "main_sha",
    "release_sha",
    "release_phase",
    "active_missions",
    "blockers",
    "readiness_gates",
    "accepted_changes",
    "retained_failures",
    "experiments",
    "res_up_candidates",
    "claim_boundaries",
    "topology_generation",
    "operator_decisions",
    "evidence",
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _text(value: Any, name: str, maximum: int = 300, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise ContractError(f"{name} must be text of at most {maximum} characters")
    return value.strip()


def _bounded_json(value: Any, name: str, maximum: int = 250_000) -> Any:
    try:
        encoded = canonical(value)
    except (TypeError, ValueError):
        raise ContractError(f"{name} must be canonical JSON") from None
    if len(encoded.encode("utf-8")) > maximum:
        raise ContractError(f"{name} exceeds {maximum} bytes")
    return strict_json(encoded)


def _validate_sha(value: Any, name: str, empty: bool = False) -> str:
    if empty and value in {None, ""}:
        return ""
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ContractError(f"{name} must be a Git SHA")
    return value


def _validate_authoritative(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != AUTHORITATIVE_FIELDS:
        missing = sorted(AUTHORITATIVE_FIELDS - set(value or {}) if isinstance(value, dict) else AUTHORITATIVE_FIELDS)
        extra = sorted(set(value or {}) - AUTHORITATIVE_FIELDS if isinstance(value, dict) else [])
        raise ContractError(f"Project state fields mismatch; missing={missing}, extra={extra}")
    result = _bounded_json(value, "project state")
    result["main_sha"] = _validate_sha(result["main_sha"], "main_sha")
    result["release_sha"] = _validate_sha(result["release_sha"], "release_sha", empty=True)
    result["release_phase"] = _text(result["release_phase"], "release_phase", 80)
    if type(result["topology_generation"]) is not int or result["topology_generation"] < 0:
        raise ContractError("topology_generation must be a nonnegative integer")
    for key in AUTHORITATIVE_FIELDS - {"main_sha", "release_sha", "release_phase", "topology_generation"}:
        if not isinstance(result[key], list):
            raise ContractError(f"{key} must be a list")
    return result


def _validate_annotations(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContractError("annotations must be an object")
    if set(value) & AUTHORITATIVE_FIELDS:
        raise ContractError("Non-authoritative annotations cannot shadow project-state authority")
    return _bounded_json(value, "annotations", 100_000)


def _state_body(generation: int, authoritative: dict[str, Any], annotations: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROJECT_STATE_SCHEMA,
        "state_generation": generation,
        "authoritative": authoritative,
        "annotations": annotations,
    }


def _state_hash(body: dict[str, Any]) -> str:
    return digest({"domain": PROJECT_STATE_SCHEMA, "state": body})


def validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict) or set(state) != {"schema_version", "state_generation", "authoritative", "annotations", "state_hash"}:
        raise ContractError("Invalid project-state envelope")
    if state["schema_version"] != PROJECT_STATE_SCHEMA or type(state["state_generation"]) is not int or state["state_generation"] < 1:
        raise ContractError("Invalid project-state schema or generation")
    authoritative = _validate_authoritative(state["authoritative"])
    annotations = _validate_annotations(state["annotations"])
    body = _state_body(state["state_generation"], authoritative, annotations)
    expected = _state_hash(body)
    if not isinstance(state["state_hash"], str) or not _HEX64.fullmatch(state["state_hash"]) or state["state_hash"] != expected:
        raise ContractError("Project-state hash mismatch")
    return {**body, "state_hash": expected}


def apply_delta(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Apply a bounded top-level StateDelta and verify its exact target hash."""
    base = validate_state(base)
    if not isinstance(delta, dict) or set(delta) != {
        "schema_version", "from_generation", "from_hash", "to_generation", "to_hash",
        "authoritative_set", "authoritative_remove", "annotation_set", "annotation_remove",
    }:
        raise ContractError("Invalid state-delta envelope")
    if delta["schema_version"] != STATE_DELTA_SCHEMA:
        raise ContractError("Invalid state-delta schema")
    if delta["from_generation"] != base["state_generation"] or delta["from_hash"] != base["state_hash"]:
        raise ContractError("StateDelta does not apply to this base state")
    if type(delta["to_generation"]) is not int or delta["to_generation"] <= delta["from_generation"]:
        raise ContractError("StateDelta target generation must advance")
    if not isinstance(delta["authoritative_set"], dict) or not isinstance(delta["authoritative_remove"], list):
        raise ContractError("Invalid authoritative StateDelta changes")
    if not isinstance(delta["annotation_set"], dict) or not isinstance(delta["annotation_remove"], list):
        raise ContractError("Invalid annotation StateDelta changes")

    authoritative = strict_json(canonical(base["authoritative"]))
    annotations = strict_json(canonical(base["annotations"]))
    for key in delta["authoritative_remove"]:
        if key not in AUTHORITATIVE_FIELDS:
            raise ContractError("StateDelta removes an unknown authoritative field")
        authoritative.pop(key, None)
    for key, value in delta["authoritative_set"].items():
        if key not in AUTHORITATIVE_FIELDS:
            raise ContractError("StateDelta sets an unknown authoritative field")
        authoritative[key] = value
    for key in delta["annotation_remove"]:
        if not isinstance(key, str):
            raise ContractError("Annotation removal keys must be text")
        annotations.pop(key, None)
    for key, value in delta["annotation_set"].items():
        if key in AUTHORITATIVE_FIELDS:
            raise ContractError("StateDelta annotation cannot shadow authority")
        annotations[key] = value

    body = _state_body(delta["to_generation"], _validate_authoritative(authoritative), _validate_annotations(annotations))
    target = {**body, "state_hash": _state_hash(body)}
    if delta["to_hash"] != target["state_hash"]:
        raise ContractError("StateDelta target hash mismatch")
    return target


class SwarmStateStore:
    """Durable project state, synchronization acknowledgements and capabilities.

    The caller is responsible for deriving the authoritative payload from Git,
    Station receipts, qualification artifacts and operator decisions. This
    class deliberately has no model-call API.
    """

    def __init__(self, store):
        self.store = store
        with self.store.lock, self.store.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS swarm_states(
                generation INTEGER PRIMARY KEY,
                state_hash TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS swarm_runners(
                runner_id TEXT PRIMARY KEY,
                identity_digest TEXT NOT NULL,
                capability_revision TEXT NOT NULL,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS swarm_sync(
                runner_id TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

    def current(self) -> dict[str, Any] | None:
        with self.store.connect() as c:
            row = c.execute("SELECT value FROM swarm_states ORDER BY generation DESC LIMIT 1").fetchone()
        return validate_state(strict_json(row[0])) if row else None

    def state(self, generation: int) -> dict[str, Any]:
        if type(generation) is not int or generation < 1:
            raise ContractError("generation must be a positive integer")
        with self.store.connect() as c:
            row = c.execute("SELECT value FROM swarm_states WHERE generation=?", (generation,)).fetchone()
        if not row:
            raise ContractError("Project-state generation was not found")
        return validate_state(strict_json(row[0]))

    def publish(self, authoritative: dict[str, Any], annotations: dict[str, Any] | None = None) -> dict[str, Any]:
        authoritative = _validate_authoritative(authoritative)
        annotations = _validate_annotations(annotations)
        with self.store.transaction() as c:
            row = c.execute("SELECT generation,value FROM swarm_states ORDER BY generation DESC LIMIT 1").fetchone()
            if row:
                current = validate_state(strict_json(row["value"]))
                if current["authoritative"] == authoritative and current["annotations"] == annotations:
                    return current
                generation = row["generation"] + 1
            else:
                generation = 1
            body = _state_body(generation, authoritative, annotations)
            state = {**body, "state_hash": _state_hash(body)}
            c.execute("INSERT INTO swarm_states(generation,state_hash,value) VALUES(?,?,?)",
                      (generation, state["state_hash"], canonical(state)))
            return state

    def delta(self, from_generation: int) -> dict[str, Any]:
        base = self.state(from_generation)
        target = self.current()
        if target is None or target["state_generation"] <= from_generation:
            raise ContractError("No newer project state is available")
        a_set = {k: v for k, v in target["authoritative"].items() if base["authoritative"].get(k) != v}
        a_remove = sorted(set(base["authoritative"]) - set(target["authoritative"]))
        n_set = {k: v for k, v in target["annotations"].items() if base["annotations"].get(k) != v}
        n_remove = sorted(set(base["annotations"]) - set(target["annotations"]))
        return {
            "schema_version": STATE_DELTA_SCHEMA,
            "from_generation": base["state_generation"],
            "from_hash": base["state_hash"],
            "to_generation": target["state_generation"],
            "to_hash": target["state_hash"],
            "authoritative_set": a_set,
            "authoritative_remove": a_remove,
            "annotation_set": n_set,
            "annotation_remove": n_remove,
        }

    def register_runner(
        self,
        runner_id: str,
        *,
        identity_digest: str,
        host_id: str,
        display_name: str,
        placement: str,
        provider: str = "",
        model: str = "",
        adapter_version: str = "",
        capabilities: dict[str, str] | None = None,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        runner_id = identifier(runner_id)
        if not isinstance(identity_digest, str) or not _HEX64.fullmatch(identity_digest):
            raise ContractError("identity_digest must be a SHA-256 digest")
        host_id = _text(host_id, "host_id", 120)
        display_name = _text(display_name, "display_name", 120)
        if placement not in _PLACEMENTS:
            raise ContractError("placement must be local or remote")
        provider = _text(provider, "provider", 120, empty=True)
        model = _text(model, "model", 200, empty=True)
        adapter_version = _text(adapter_version, "adapter_version", 120, empty=True)
        capabilities = capabilities or {}
        if not isinstance(capabilities, dict) or len(capabilities) > 100:
            raise ContractError("capabilities must be an object with at most 100 entries")
        clean_caps = {}
        for capability, status in capabilities.items():
            clean_caps[identifier(capability)] = status
            if status not in _CAPABILITY_STATES:
                raise ContractError("capability state must be advertised, observed, or qualified")
        constraints = constraints or []
        if not isinstance(constraints, list) or len(constraints) > 100:
            raise ContractError("constraints must be a list with at most 100 entries")
        clean_constraints = sorted({_text(v, "constraint", 300) for v in constraints})

        revision_input = {
            "schema_version": CAPABILITY_SCHEMA,
            "runner_id": runner_id,
            "identity_digest": identity_digest,
            "host_id": host_id,
            "placement": placement,
            "provider": provider,
            "model": model,
            "adapter_version": adapter_version,
            "capabilities": dict(sorted(clean_caps.items())),
            "constraints": clean_constraints,
        }
        revision = digest({"domain": CAPABILITY_SCHEMA, "profile": revision_input})
        with self.store.transaction() as c:
            row = c.execute("SELECT identity_digest,value FROM swarm_runners WHERE runner_id=?", (runner_id,)).fetchone()
            if row and row["identity_digest"] != identity_digest:
                raise ContractError("Runner identity cannot be rebound to a different credential")
            enrolled_at = strict_json(row["value"]).get("enrolled_at") if row else _now()
            profile = {
                **revision_input,
                "display_name": display_name,
                "capability_revision": revision,
                "enrolled_at": enrolled_at,
                "updated_at": _now(),
            }
            c.execute(
                "INSERT OR REPLACE INTO swarm_runners(runner_id,identity_digest,capability_revision,value) VALUES(?,?,?,?)",
                (runner_id, identity_digest, revision, canonical(profile)),
            )
        return profile

    def runner(self, runner_id: str) -> dict[str, Any]:
        runner_id = identifier(runner_id)
        with self.store.connect() as c:
            row = c.execute("SELECT value FROM swarm_runners WHERE runner_id=?", (runner_id,)).fetchone()
        if not row:
            raise ContractError("Runner is not enrolled")
        return strict_json(row[0])

    def runners(self) -> list[dict[str, Any]]:
        with self.store.connect() as c:
            rows = c.execute("SELECT value FROM swarm_runners ORDER BY runner_id").fetchall()
        return [strict_json(r[0]) for r in rows]

    def acknowledge(self, runner_id: str, state_generation: int, state_hash: str, capability_revision: str) -> dict[str, Any]:
        runner = self.runner(runner_id)
        state = self.state(state_generation)
        if state["state_hash"] != state_hash:
            raise ContractError("Runner acknowledged the wrong project-state hash")
        if capability_revision != runner["capability_revision"]:
            raise ContractError("Runner capability revision is stale")
        value = {
            "schema_version": SYNC_SCHEMA,
            "runner_id": runner["runner_id"],
            "identity_digest": runner["identity_digest"],
            "state_generation": state_generation,
            "state_hash": state_hash,
            "capability_revision": capability_revision,
            "acknowledged_at": _now(),
        }
        with self.store.transaction() as c:
            c.execute("INSERT OR REPLACE INTO swarm_sync(runner_id,value) VALUES(?,?)",
                      (runner["runner_id"], canonical(value)))
        return value

    def acknowledgement(self, runner_id: str) -> dict[str, Any] | None:
        runner_id = identifier(runner_id)
        with self.store.connect() as c:
            row = c.execute("SELECT value FROM swarm_sync WHERE runner_id=?", (runner_id,)).fetchone()
        return strict_json(row[0]) if row else None

    def eligible(self, runner_id: str) -> bool:
        try:
            runner = self.runner(runner_id)
        except ContractError:
            return False
        current = self.current()
        ack = self.acknowledgement(runner_id)
        if current is None or ack is None or ack.get("schema_version") != SYNC_SCHEMA:
            return False
        return (
            ack.get("identity_digest") == runner["identity_digest"]
            and ack.get("capability_revision") == runner["capability_revision"]
            and ack.get("state_generation") == current["state_generation"]
            and ack.get("state_hash") == current["state_hash"]
        )

    def require_current(self, runner_id: str) -> dict[str, Any]:
        if not self.eligible(runner_id):
            raise ContractError("Runner must synchronize the current project state before claiming new work")
        return self.acknowledgement(runner_id)

    def work_binding(self, runner_id: str, *, mission_spec_hash: str, worker_contract_hash: str) -> dict[str, Any]:
        """Return the exact synchronization/capability binding for a new work packet."""
        ack = self.require_current(runner_id)
        current = self.current()
        if current is None:
            raise ContractError("Project state is not initialized")
        if not isinstance(mission_spec_hash, str) or not _HEX64.fullmatch(mission_spec_hash):
            raise ContractError("mission_spec_hash must be a SHA-256 digest")
        if not isinstance(worker_contract_hash, str) or not _HEX64.fullmatch(worker_contract_hash):
            raise ContractError("worker_contract_hash must be a SHA-256 digest")
        return {
            "schema_version": "residual.work_state_binding.v1",
            "runner_id": ack["runner_id"],
            "identity_digest": ack["identity_digest"],
            "state_generation": current["state_generation"],
            "state_hash": current["state_hash"],
            "main_sha": current["authoritative"]["main_sha"],
            "topology_generation": current["authoritative"]["topology_generation"],
            "capability_revision": ack["capability_revision"],
            "mission_spec_hash": mission_spec_hash,
            "worker_contract_hash": worker_contract_hash,
        }

    def capability_is(self, runner_id: str, capability: str, minimum: str = "qualified") -> bool:
        capability = identifier(capability)
        if minimum not in _CAPABILITY_STATES:
            raise ContractError("Invalid minimum capability state")
        order = {"advertised": 0, "observed": 1, "qualified": 2}
        actual = self.runner(runner_id)["capabilities"].get(capability)
        return actual in order and order[actual] >= order[minimum]
