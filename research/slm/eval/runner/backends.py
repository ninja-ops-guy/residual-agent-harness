"""Model backend protocol + reference baselines for the SLM eval runner.

Implements the frozen SLM-01 baseline roles (BASELINES.yaml):

* ``DeterministicPolicyBackend``  -> B0 deterministic/no-model floor
* ``RandomPolicyBackend``         -> B1 random-policy floor (seeded, uniform
  over the schema-valid decision space declared by ``output_schema`` and
  ``input_state`` -- NEVER ``expected_output``; G2-B1 remediation)
* ``TrivialMajorityBackend``      -> B2 trivial majority-class floor (fit on a
  provided TRAIN-split stats file only; holdout labels never read)
* ``OracleBackend``               -> B3 oracle ceiling (emits the declared
  expected_output projected to candidate shape via
  ``expected_output_to_candidate`` (X-M2); ceiling verification only,
  never a candidate policy)
* ``OllamaBackend``/``B5OllamaBackend`` -> B4/B5 real Ollama backends
  (localhost /api/generate; model pinned from BASELINES.yaml; fail-closed
  on unreachable endpoint) (X-M3)
* ``OpenAICompatibleBackend``     -> B6 vLLM OpenAI-compatible backend
  (/v1/chat/completions; fail-closed on unreachable endpoint) (X-M3)

Floors and the oracle exist to expose weak benchmarks (random-majority
exploits, trivially passable items); per protocol they are reported
prominently, never hidden.

All backends are pure functions of (item, per-call RNG) with no training, no
tuning, and no benchmark mutation. Stdlib-only. Backend names are the exact
baseline IDs of BASELINES.yaml (B0..B6, X-m1 unified casing).
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

    G2-B1 structural control: unless ``requires_gold`` is True, the runner
    passes backends ONLY the whitelisted candidate payload built by
    ``candidate_payload`` -- a fresh deep copy per call containing the fields
    a live model would see. Gold/label-derived keys (``expected_output``,
    ``expected_escalation``, gold rationale, contamination metadata, digest,
    verifier_ref, ...) are ABSENT, so reading them fails loudly with
    ``KeyError`` instead of silently leaking labels.
    """

    name: str = "abstract"

    #: False for every candidate-eligible backend. True ONLY for the B3
    #: oracle, which per BASELINES.yaml legitimately receives gold labels to
    #: define the ceiling (never a candidate policy).
    requires_gold: bool = False

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        raise NotImplementedError


# G2-B1: the ONLY item fields a non-oracle backend may observe -- exactly
# what a live deployed model would see at decision time.
CANDIDATE_PAYLOAD_FIELDS = (
    "item_id",
    "category",
    "input_state",
    "output_schema",
    "allowed_alternatives",
    "safety_critical",
    "difficulty",
)

#: Keys that must NEVER reach a non-oracle backend (gold labels, gold-derived
#: fields, contamination/integrity metadata). Used by tests to audit the
#: whitelist.
GOLD_OR_METADATA_FIELDS = (
    "expected_output",
    "expected_escalation",
    "gold_rationale",
    "rationale",
    "digest",
    "verifier_ref",
    "contamination_group",
    "source_provenance",
    "synthetic",
    "bench_version",
)


def candidate_payload(item: Mapping[str, Any]) -> Dict[str, Any]:
    """Whitelisted, freshly deep-copied view of an item for a backend (G2-B1).

    Contains ONLY ``CANDIDATE_PAYLOAD_FIELDS`` present on the item. Each call
    returns a fresh deep copy, so a backend mutating its payload can never
    affect the frozen item or other backends. Gold fields are absent, and
    because the payload is a plain ``dict`` (not a defaulting mapping), a
    backend attempting to read a non-whitelisted key fails loudly with
    ``KeyError`` -- the leak is structurally impossible, not merely
    discouraged.
    """
    return {k: copy.deepcopy(item[k])
            for k in CANDIDATE_PAYLOAD_FIELDS if k in item}


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

    name = "B0-deterministic-rules"

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

    G2-B1 remediation: the decision space is constructed ONLY from fields a
    live model could see -- never from ``expected_output`` or any
    label-derived field (the runner's whitelisted payload makes such reads
    impossible; see ``candidate_payload``). Sources, in priority order:

    1. the item's declared ``allowed_alternatives`` (top-level or under
       ``input_state``): candidate-shaped objects declared as part of the
       valid decision space -- sampled uniformly;
    2. schema-driven sampling over ``output_schema``: each ``enum`` property
       is sampled uniformly over its declared values, ``const`` properties
       take their constant, and string-valued properties declared legal in
       ``input_state`` (e.g. ``allowed_routes`` for ``route``, or the worker
       ids of ``input_state.workers``) are sampled uniformly over those
       declared legal values; everything else takes the schema-minimal
       default.

    Seeded via the runner-supplied RNG so streams are item-order stable and
    reproducible. The expected B1 score is the random floor, far below any
    qualification threshold; a B1 run approaching the ceiling indicates a
    label leak or a trivially passable benchmark.
    """

    name = "B1-random-policy"

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        choices = self._declared_alternatives(item)
        if choices:
            return copy.deepcopy(rng.choice(choices))
        schema = item.get("output_schema")
        if isinstance(schema, Mapping):
            return self._sample_from_schema(schema, item, rng)
        return MalformedOutput(raw=None)

    @staticmethod
    def _declared_alternatives(item: Mapping[str, Any]) -> list:
        """Declared candidate alternatives (decision-space, never labels)."""
        for source in (item.get("allowed_alternatives"),
                       (item.get("input_state") or {}).get("allowed_alternatives")
                       if isinstance(item.get("input_state"), Mapping) else None):
            if (isinstance(source, Sequence)
                    and not isinstance(source, str) and source):
                return [a for a in source if isinstance(a, Mapping)]
        return []

    @classmethod
    def _sample_from_schema(cls, schema: Mapping[str, Any],
                            item: Mapping[str, Any],
                            rng: random.Random) -> Any:
        props = schema.get("properties")
        if not isinstance(props, Mapping) or not props:
            return _schema_default(schema)
        state = item.get("input_state")
        if not isinstance(state, Mapping):
            state = {}
        return {name: cls._sample_property(name, props[name], state, rng)
                for name in sorted(props, key=str)}

    @classmethod
    def _sample_property(cls, name: str, sub: Any,
                         state: Mapping[str, Any], rng: random.Random) -> Any:
        if isinstance(sub, Mapping):
            enum = sub.get("enum")
            if (isinstance(enum, Sequence) and not isinstance(enum, str)
                    and enum):
                return rng.choice(list(enum))
            if "const" in sub:
                return sub["const"]
            typ = sub.get("type")
            types = typ if isinstance(typ, list) else [typ]
            if "string" in types:
                declared = cls._declared_legal_values(name, state)
                if declared:
                    return rng.choice(declared)
        return _schema_default(sub)

    @staticmethod
    def _declared_legal_values(prop: str, state: Mapping[str, Any]) -> list:
        """Legal values for a string property declared in ``input_state``.

        Looks for ``input_state.allowed_<prop>s`` (e.g. ``allowed_routes``
        for ``route``); for ``route`` additionally falls back to the worker
        ids declared in ``input_state.workers`` plus ``None`` (a route may
        legitimately be null). Only input_state-declared surfaces are used.
        """
        declared = state.get("allowed_" + prop + "s")
        if (isinstance(declared, Sequence) and not isinstance(declared, str)
                and declared):
            return list(declared)
        if prop == "route":
            workers = state.get("workers")
            if isinstance(workers, Sequence) and not isinstance(workers, str):
                ids = [w.get("worker_id") for w in workers
                       if isinstance(w, Mapping) and w.get("worker_id")]
                if ids:
                    return ids + [None]
        return []


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

    name = "B2-trivial-majority"

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


# --------------------------------------------------------------------- X-M2
# expected_output -> candidate-output converter. Lane D verifier contracts
# (research/slm/verifiers/*.py module docstrings) define the CANDIDATE shape
# per category; the bench's expected_output carries verifier-internal fields
# (allowed_routes, feasible_routes, ...) that are NOT candidate fields. The
# converter projects expected_output to the exact candidate shape so the
# B3 oracle and the positive battery produce candidate-shaped outputs.
def expected_output_to_candidate(item: Mapping[str, Any]) -> Any:
    """Project an item's expected_output into candidate-output shape (X-M2).

    Returns a Mapping conforming to the category's candidate contract, or a
    MalformedOutput sentinel when the item's category/expected_output is not
    convertible (the verifier then surfaces BENCHMARK_DEFECT). Never imputes
    fields absent from the item.
    """
    expected = item.get("expected_output")
    if not isinstance(expected, Mapping):
        return MalformedOutput(raw=expected)
    category = item.get("category")
    if category == "worker_routing":
        action = expected.get("action")
        if action == "route":
            route = expected.get("selected_route")
            if route is None:
                allowed = expected.get("allowed_routes") or []
                route = allowed[0] if allowed else None  # any legal route passes
            return {"action": "route", "route": route}
        return {"action": action, "route": None}
    if category == "contract_compilation":
        contract = expected.get("contract")
        if not isinstance(contract, Mapping):
            return MalformedOutput(raw=expected)
        return {"contract": copy.deepcopy(contract)}
    if category == "evidence_sufficiency":
        state = item.get("input_state") or {}
        return {
            "sufficient": expected.get("sufficient"),
            "missing_requirements": list(expected.get("missing_requirements") or []),
            "verifier_outputs": list(state.get("required_verifier_outputs") or []),
        }
    if category == "retry_escalate_abort":
        return {"action": expected.get("action"),
                "reason_code": expected.get("reason_code")}
    if category == "budget_decisions":
        return {"decision": expected.get("decision")}
    if category == "failure_classification":
        return {"label": expected.get("label")}
    if category == "adversarial_malformed":
        return {"reject": True, "reason_code": expected.get("reason_code")}
    if category == "stale_state_authority":
        return {"legal": expected.get("legal"),
                "violation": expected.get("violation")}
    return MalformedOutput(raw={"unconvertible_category": category})


class OracleBackend(ModelBackend):
    """B3: emit the candidate-shaped projection of expected_output (X-M2).

    Per BASELINES.yaml the oracle reads labels only to define the ceiling; it
    is never eligible as a candidate policy and its outputs are never used in
    training corpora. Items whose expected_output is not convertible yield
    MalformedOutput (the verifier will surface the item defect).

    G2-B1: this is the ONLY backend with ``requires_gold = True`` -- the
    runner passes it the full read-only item instead of the whitelisted
    candidate payload. This is the documented, spec-sanctioned gold-label
    path (ceiling verification); every other backend is structurally
    prevented from observing gold fields.
    """

    name = "B3-oracle"
    requires_gold = True

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        return expected_output_to_candidate(item)


# --------------------------------------------------------------------- X-M3
def render_prompt(item: Mapping[str, Any]) -> str:
    """Prompt for live backends (template id exp-m6-slm-control-decision-v0).

    Canonical serialization convention (X-m5, one true form):
    json.dumps(obj, sort_keys=True, separators=(",", ":")).
    """
    payload = {
        "instruction": (
            "You are a Residual control-decision component. Respond with ONE "
            "JSON object conforming to output_schema. No prose, no markdown."
        ),
        "input_state": item.get("input_state"),
        "output_schema": item.get("output_schema"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_json_object(text: Any) -> Any:
    if not isinstance(text, str):
        return MalformedOutput(raw=text)
    text = text.strip()
    try:
        obj = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return MalformedOutput(raw=text[:200])
        try:
            obj = json.loads(text[start:end + 1])
        except Exception:
            return MalformedOutput(raw=text[:200])
    return obj if isinstance(obj, Mapping) else MalformedOutput(raw=obj)


class OllamaBackend(ModelBackend):
    """B4/B5: real Ollama backend via localhost /api/generate.

    Model pinned from BASELINES.yaml (B4: qwen2.5:7b-instruct;
    B5: qwen2.5:1.5b-instruct). Decoding from the BASELINES shared block
    (temperature 0.0, seed 0). FAIL-CLOSED: any connection/parse failure
    yields MalformedOutput (attributed to the configuration, never hidden).
    Not exercised in unit tests (no live calls in CI).
    """

    name = "B4-local-7b"
    DEFAULT_MODEL = "qwen2.5:7b-instruct"

    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 *, model: Optional[str] = None, timeout_s: float = 120.0,
                 decoding: Optional[Mapping[str, Any]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.timeout_s = timeout_s
        dec = {"temperature": 0.0, "top_p": 1.0, "top_k": -1,
               "seed": 0, "num_predict": 1024}
        dec.update(decoding or {})
        self.decoding = dec

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        schema = item.get("output_schema")
        body = {
            "model": self.model,
            "prompt": render_prompt(item),
            "stream": False,
            "options": self.decoding,
        }
        if isinstance(schema, Mapping):
            body["format"] = schema
        req = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # fail-closed: unreachable/parse failure
            return MalformedOutput(raw="ollama: %s: %s" % (type(exc).__name__, exc))
        if not isinstance(payload, Mapping) or "response" not in payload:
            return MalformedOutput(raw=payload)
        return _parse_json_object(payload.get("response"))


class B5OllamaBackend(OllamaBackend):
    """B5: qwen2.5:1.5b-instruct via Ollama (same path, smaller pin)."""

    name = "B5-slm-1p5b"
    DEFAULT_MODEL = "qwen2.5:1.5b-instruct"


class OpenAICompatibleBackend(ModelBackend):
    """B6: OpenAI-compatible endpoint (vLLM), /v1/chat/completions.

    Model pinned from BASELINES.yaml: Qwen/Qwen2.5-32B-Instruct served via
    vLLM. FAIL-CLOSED: unreachable endpoint, HTTP error, or non-JSON output
    yields MalformedOutput. No live calls in tests (socket-level mocked).
    """

    name = "B6-reference-strong"
    DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct"

    def __init__(self, base_url: str, *, model: Optional[str] = None,
                 api_key: Optional[str] = None, timeout_s: float = 120.0,
                 decoding: Optional[Mapping[str, Any]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key
        self.timeout_s = timeout_s
        dec = {"temperature": 0.0, "top_p": 1.0, "seed": 0,
               "max_tokens": 1024}
        dec.update(decoding or {})
        self.decoding = dec

    def predict(self, item: Mapping[str, Any], rng: random.Random) -> Any:
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": render_prompt(item)}],
            "response_format": {"type": "json_object"},
            **self.decoding,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(
            self.base_url + "/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"), method="POST",
            headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
        except Exception as exc:  # fail-closed
            return MalformedOutput(raw="openai-compatible: %s: %s"
                                   % (type(exc).__name__, exc))
        return _parse_json_object(content)


BACKENDS = {
    DeterministicPolicyBackend.name: DeterministicPolicyBackend,
    RandomPolicyBackend.name: RandomPolicyBackend,
    TrivialMajorityBackend.name: TrivialMajorityBackend,
    OracleBackend.name: OracleBackend,
    OllamaBackend.name: OllamaBackend,
    B5OllamaBackend.name: B5OllamaBackend,
    OpenAICompatibleBackend.name: OpenAICompatibleBackend,
}
