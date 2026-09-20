"""Model backend protocol + reference baselines for the SLM eval runner.

Implements the frozen SLM-01 baseline roles (BASELINES.yaml):

* ``DeterministicPolicyBackend``  -> B0 deterministic/no-model floor
* ``RandomPolicyBackend``         -> B1 random-policy floor (seeded, uniform
  over the schema-valid decision space incl. allowed_alternatives)
* ``TrivialMajorityBackend``      -> B2 trivial majority-class floor (fit on a
  provided TRAIN-split stats file only; holdout labels never read)
* ``OracleBackend``               -> B3 oracle ceiling (emits the declared
  expected_output; ceiling verification only, never a candidate policy)
* ``HttpBackend``                 -> stub for external models (B4/B5/B6 class)
  over an OpenAI-compatible/JSON HTTP endpoint

Floors and the oracle exist to expose weak benchmarks (random-majority
exploits, trivially passable items); per protocol they are reported
prominently, never hidden.

All backends are pure functions of (item, per-call RNG) with no training, no
tuning, and no benchmark mutation. Stdlib-only.
"""
from __future__ import annotations

import copy
import json
import random
import urllib.request
from typing import Any, Dict, Mapping, Optional, Sequence

try:  # verifier suite lives on slm00/verifiers; importable when merged
    from research.slm.verifiers.base import MalformedOutput
except Exception:  # pragma: no cover - standalone fallback
    class MalformedOutput:  # type: ignore[no-redef]
        """Sentinel wrapper for syntactically invalid candidate output."""

        def __init__(self, raw: Any = None) -> None:
            self.raw = raw


class ModelBackend:
    """Backend protocol: map a frozen benchmark item to a candidate output.

    Implementations MUST:
    * never mutate ``item``;
    * return a Mapping (parseable JSON-object-shaped candidate output) or a
      ``MalformedOutput`` sentinel when their own output is unparseable;
    * make no network calls unless explicitly an HTTP backend;
    * never train or tune on benchmark items.
    """

    name: str = "abstract"

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        raise NotImplementedError


def _schema_default(schema: Mapping[str, Any]) -> Any:
    """Schema-minimal default value for a JSON-schema fragment."""
    if not isinstance(schema, Mapping):
        return None
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "default" in schema:
        return schema["default"]
    typ = schema.get("type")
    if typ == "object" or "properties" in schema:
        return {k: _schema_default(v)
                for k, v in schema.get("properties", {}).items()}
    if typ == "array":
        return []
    if typ == "string":
        return ""
    if typ in ("integer", "number"):
        return 0
    if typ == "boolean":
        return False
    return None


class DeterministicPolicyBackend(ModelBackend):
    """B0: rule-based stub reading allowed_routes / expected structure.

    Capability-neutral rules only (no benchmark feedback):
    * if input_state declares ``allowed_routes``, route to the first allowed
      route (stable, deterministic order as declared);
    * safety-critical items escalate (protocol asymmetry: false
      non-escalation is costlier than unnecessary escalation);
    * otherwise emit the schema-minimal default for output_schema.
    """

    name = "b0-deterministic-rules"

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        input_state = item.get("input_state") or {}
        output: Dict[str, Any] = {}
        routes = input_state.get("allowed_routes")
        if isinstance(routes, Sequence) and not isinstance(routes, str) and routes:
            output["route"] = routes[0]
            output["action"] = "route"
        elif item.get("safety_critical"):
            output["action"] = "escalate"
        else:
            schema = item.get("output_schema")
            if isinstance(schema, Mapping):
                return _schema_default(schema)
            output["action"] = "escalate"  # fail-closed default
        return output


class RandomPolicyBackend(ModelBackend):
    """B1: uniform random over the schema-valid decision space.

    Prefers the item's declared ``allowed_alternatives`` (plus the declared
    expected action class, which is part of the valid decision space); falls
    back to a uniform draw over the first ``enum`` found in output_schema,
    then to a random schema-default. Seeded via the runner-supplied RNG so
    streams are item-order stable and reproducible.
    """

    name = "b1-random-policy"

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        alternatives = item.get("allowed_alternatives")
        choices = []
        if isinstance(alternatives, Sequence) and not isinstance(alternatives, str):
            choices = [a for a in alternatives if isinstance(a, Mapping)]
        expected = item.get("expected_output")
        if isinstance(expected, Mapping):
            choices.append(expected)
        if choices:
            return copy.deepcopy(rng.choice(choices))
        schema = item.get("output_schema")
        enum_vals = self._first_enum(schema)
        if enum_vals:
            return {self._first_property_name(schema) or "action":
                    rng.choice(list(enum_vals))}
        if isinstance(schema, Mapping):
            return _schema_default(schema)
        return MalformedOutput(raw=None)

    @classmethod
    def _first_enum(cls, schema: Any) -> Optional[Sequence[Any]]:
        if isinstance(schema, Mapping):
            if isinstance(schema.get("enum"), Sequence) and schema["enum"]:
                return schema["enum"]
            for sub in schema.get("properties", {}).values():
                found = cls._first_enum(sub)
                if found:
                    return found
        return None

    @staticmethod
    def _first_property_name(schema: Any) -> Optional[str]:
        if isinstance(schema, Mapping):
            props = schema.get("properties")
            if isinstance(props, Mapping) and props:
                return sorted(props, key=str)[0]
        return None


class TrivialMajorityBackend(ModelBackend):
    """B2: always emit the train-split majority class per category.

    ``train_stats_path`` is a JSON file computed from the frozen TRAIN split
    ONLY, shaped::

        {"by_category": {"<category>": <majority expected_output object>},
         "global": <majority expected_output object>}

    The runner never computes these statistics; this backend only reads the
    provided file. Where no stats exist for the category, emits the
    schema-minimal default, escalating on safety-critical items.
    """

    name = "b2-trivial-majority"

    def __init__(self, train_stats_path: str) -> None:
        with open(train_stats_path, "r", encoding="utf-8") as fh:
            stats = json.load(fh)
        self._by_category = stats.get("by_category", {})
        self._global = stats.get("global")

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        majority = self._by_category.get(item.get("category"), self._global)
        if isinstance(majority, Mapping):
            return copy.deepcopy(majority)
        if item.get("safety_critical"):
            return {"action": "escalate"}
        schema = item.get("output_schema")
        if isinstance(schema, Mapping):
            return _schema_default(schema)
        return MalformedOutput(raw=None)


class OracleBackend(ModelBackend):
    """B3: emit the declared expected_output (ceiling verification only).

    Per BASELINES.yaml the oracle reads labels only to define the ceiling; it
    is never eligible as a candidate policy and its outputs are never used in
    training corpora. Items whose expected_output is not an object yield
    MalformedOutput (the verifier will surface the item defect).
    """

    name = "b3-oracle"

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        expected = item.get("expected_output")
        if isinstance(expected, Mapping):
            return copy.deepcopy(expected)
        return MalformedOutput(raw=expected)


class HttpBackend(ModelBackend):
    """Stub backend for external models (B4/B5/B6 class).

    POSTs a JSON body {"item_id", "input_state", "output_schema",
    "decoding"} to ``endpoint`` and expects a JSON object response. Network
    failures or non-object responses yield MalformedOutput (fail-closed;
    attributed to the configuration per protocol section 8). Not used in
    unit tests (no network in CI).
    """

    name = "http-external"

    def __init__(self, endpoint: str, *, timeout_s: float = 60.0,
                 headers: Optional[Mapping[str, str]] = None,
                 decoding: Optional[Mapping[str, Any]] = None) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.headers = dict(headers or {})
        self.decoding = dict(decoding or {"temperature": 0.0, "seed": 0})

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        body = json.dumps({
            "item_id": item.get("item_id"),
            "input_state": item.get("input_state"),
            "output_schema": item.get("output_schema"),
            "decoding": self.decoding,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint, data=body, method="POST",
            headers={"Content-Type": "application/json", **self.headers},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # fail-closed: infrastructure/parse failure
            return MalformedOutput(raw="%s: %s" % (type(exc).__name__, exc))
        if isinstance(payload, Mapping):
            return payload
        return MalformedOutput(raw=payload)


BACKENDS = {
    DeterministicPolicyBackend.name: DeterministicPolicyBackend,
    RandomPolicyBackend.name: RandomPolicyBackend,
    TrivialMajorityBackend.name: TrivialMajorityBackend,
    OracleBackend.name: OracleBackend,
    HttpBackend.name: HttpBackend,
}
