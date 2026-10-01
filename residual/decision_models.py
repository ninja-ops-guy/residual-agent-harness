"""Experimental v2 decision evidence. No Station, receipt, or action authority.

Clef's System One wire format is NOT a chat-completions API. Only the bounded
text/JSON subset is supported. Live execution is explicitly opt-in.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

ADAPTER_VERSION = "clef-evidence-v0.1"
MAX_REQUEST_BYTES = 32_768
MAX_RESPONSE_BYTES = 262_144
MODELS = frozenset({"clef", "clef-flash"})
_ID = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
_ACCOUNT = re.compile(r"[a-fA-F0-9]{32}\Z")
_TOLERANCE = 1e-5


class DecisionError(ValueError):
    """Stable, non-sensitive failure code; never a passing decision."""


def _fail(code: str) -> None:
    raise DecisionError(code)


def _json_shape(value: Any, depth: int = 0) -> None:
    if depth > 32:
        _fail("JSON_DEPTH_EXCEEDED")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _json_shape(item, depth + 1)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for item in value.values():
            _json_shape(item, depth + 1)
        return
    _fail("INVALID_JSON_VALUE")


def _encode(value: Any) -> bytes:
    try:
        _json_shape(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DecisionError("INVALID_JSON_VALUE") from None


def _decode(raw: bytes, limit: int = MAX_RESPONSE_BYTES) -> Any:
    if type(raw) is not bytes or not raw or len(raw) > limit:
        _fail("INVALID_BODY_SIZE")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _fail("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _: _fail("NONFINITE_JSON"))
        _json_shape(value)
        return value
    except DecisionError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DecisionError("INVALID_JSON") from None


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(value: Any, limit: int = 4096) -> bool:
    return type(value) is str and 0 < len(value) <= limit and bool(value.strip())


def _probability(value: Any) -> float:
    if type(value) not in (int, float) or not 0 <= value <= 1:
        _fail("INVALID_PROBABILITY")
    return float(value)


def _validate_payload(payload: Any) -> None:
    if type(payload) is not dict or set(payload) != {"state", "questions"}:
        _fail("INVALID_REQUEST_FIELDS")
    if type(payload["state"]) not in (str, dict, list):
        _fail("INVALID_STATE")
    questions = payload["questions"]
    if type(questions) is not dict or not 1 <= len(questions) <= 64:
        _fail("INVALID_QUESTION_COUNT")
    for qid, question in questions.items():
        if not _ID.fullmatch(qid) or type(question) is not dict:
            _fail("INVALID_QUESTION")
        if set(question) - {"type", "instructions", "criteria"}:
            _fail("UNKNOWN_QUESTION_FIELDS")
        kind = question.get("type")
        if kind not in ("noul", "choice", "score"):
            _fail("UNSUPPORTED_QUESTION_TYPE")
        if "instructions" in question and not _text(question["instructions"]):
            _fail("INVALID_INSTRUCTIONS")
        criteria = question.get("criteria")
        if kind == "noul":
            if "criteria" in question and (
                type(criteria) is not dict or set(criteria) != {"true", "false"}
                or not all(_text(v) for v in criteria.values())
            ):
                _fail("INVALID_NOUL_CRITERIA")
        elif kind == "choice":
            if type(criteria) is not dict or not 2 <= len(criteria) <= 64:
                _fail("INVALID_CHOICE_CRITERIA")
            if not all(_ID.fullmatch(k) and _text(v) for k, v in criteria.items()):
                _fail("INVALID_CHOICE_CRITERIA")
        elif (type(criteria) is not list or not 2 <= len(criteria) <= 64
              or not all(_text(v) for v in criteria)):
            _fail("INVALID_SCORE_CRITERIA")


@dataclass(frozen=True)
class DecisionRequest:
    """Immutable snapshot; evidence references are local provenance, not instructions."""

    subject: str
    payload_json: bytes = field(repr=False)
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _text(self.subject, 256):
            _fail("INVALID_SUBJECT")
        if (type(self.evidence_refs) is not tuple or not 1 <= len(self.evidence_refs) <= 64
                or not all(_text(v, 512) for v in self.evidence_refs)
                or len(set(self.evidence_refs)) != len(self.evidence_refs)):
            _fail("INVALID_EVIDENCE_REFS")
        value = _decode(self.payload_json, MAX_REQUEST_BYTES)
        _validate_payload(value)
        if _encode(value) != self.payload_json:
            _fail("NONCANONICAL_REQUEST")

    @classmethod
    def build(cls, *, subject: str, state: Any, questions: dict[str, Any],
              evidence_refs: tuple[str, ...]) -> DecisionRequest:
        return cls(subject, _encode({"state": state, "questions": questions}), evidence_refs)

    def payload(self) -> dict[str, Any]:
        return _decode(self.payload_json, MAX_REQUEST_BYTES)

    def wire_bytes(self, model: str) -> bytes:
        if type(model) is not str or model not in MODELS:
            _fail("UNSUPPORTED_MODEL")
        raw = _encode({"model": model, **self.payload()})
        if len(raw) > MAX_REQUEST_BYTES:
            _fail("REQUEST_TOO_LARGE")
        return raw


@dataclass(frozen=True)
class DecisionEvidence:
    """Candidate artifact bytes only, deliberately not a WorkerReceipt."""

    document_json: bytes = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return _decode(self.document_json)

    def candidate_artifact(self) -> tuple[str, bytes]:
        return f"decision-claims/{_digest(self.document_json)}.json", self.document_json

    def review_hint(self, question_id: str, *, min_probability: float = 0.9,
                    min_margin: float = 0.1) -> str:
        threshold, margin = _probability(min_probability), _probability(min_margin)
        answer = self.to_dict()["answers"][question_id]
        probabilities = sorted(answer["probabilities"].values(), reverse=True)
        if (probabilities[0] < threshold or probabilities[0] - probabilities[1] < margin
                or probabilities[0] == probabilities[1]):
            return "REVIEW_REQUIRED"
        return "ADVISORY_ONLY"


class DecisionModelAdapter(Protocol):
    def evaluate(self, request: DecisionRequest) -> DecisionEvidence: ...


def _distribution(value: Any, labels: set[str]) -> dict[str, float]:
    if type(value) is not dict or set(value) != labels:
        _fail("PROBABILITY_LABEL_MISMATCH")
    result = {key: _probability(prob) for key, prob in value.items()}
    if abs(math.fsum(result.values()) - 1.0) > _TOLERANCE:
        _fail("PROBABILITIES_NOT_NORMALIZED")
    return result


def _answer(question: dict[str, Any], answer: Any) -> dict[str, Any]:
    kind = question["type"]
    if type(answer) is not dict or answer.get("type", kind) != kind:
        _fail("ANSWER_TYPE_MISMATCH")
    if kind == "noul":
        if set(answer) - {"type", "noul"} or "noul" not in answer:
            _fail("INVALID_NOUL_ANSWER")
        p = _probability(answer["noul"])
        return {"type": kind, "probabilities": {"true": p, "false": 1.0 - p},
                "probability_source": "provider_noul_and_complement",
                "provider_confidence": None, "value": p}
    allowed = ({"type", "choice", "confidence", "probabilities"} if kind == "choice"
               else {"type", "score", "confidence", "probabilities", "legend"})
    if set(answer) - allowed or not allowed - {"type"} <= set(answer):
        _fail("ANSWER_SCHEMA_MISMATCH")
    criteria = question["criteria"]
    labels = set(criteria) if kind == "choice" else {str(i) for i in range(len(criteria))}
    probabilities = _distribution(answer["probabilities"], labels)
    confidence = _probability(answer["confidence"])
    if kind == "choice":
        value = answer["choice"]
        if type(value) is not str or value not in probabilities:
            _fail("INVALID_CHOICE")
        if probabilities[value] < max(probabilities.values()) - _TOLERANCE:
            _fail("CHOICE_NOT_ARGMAX")
    else:
        value = answer["score"]
        if type(value) not in (int, float) or not 0 <= value <= len(criteria) - 1:
            _fail("INVALID_SCORE")
        expected = math.fsum(int(k) * p for k, p in probabilities.items())
        if not 0 <= value <= len(criteria) - 1 or abs(value - expected) > _TOLERANCE:
            _fail("SCORE_EXPECTATION_MISMATCH")
        if answer["legend"] != {str(i): text for i, text in enumerate(criteria)}:
            _fail("SCORE_LEGEND_MISMATCH")
    result = {"type": kind, "probabilities": probabilities, "value": value,
              "provider_confidence": confidence, "probability_source": "provider_distribution"}
    if kind == "score":
        result["legend"] = answer["legend"]
    return result


def _evidence(request: DecisionRequest, raw: bytes, model: str, source_kind: str,
              captured_at_ns: int) -> DecisionEvidence:
    wire = request.wire_bytes(model)
    body = _decode(raw)
    if type(body) is not dict:
        _fail("INVALID_RESPONSE")
    if "success" in body:
        if body["success"] is not True or body.get("errors"):
            _fail("PROVIDER_FAILURE")
        result = body.get("result")
    else:
        result = body
    if type(result) is not dict or set(result) - {"model", "answers", "usage"}:
        _fail("RESPONSE_SCHEMA_MISMATCH")
    if result.get("model") != model:
        _fail("MODEL_IDENTITY_MISMATCH")
    questions = request.payload()["questions"]
    answers = result.get("answers")
    if type(answers) is not dict or set(answers) != set(questions):
        _fail("ANSWER_SET_MISMATCH")
    usage = result.get("usage")
    if usage is not None and (type(usage) is not dict or any(
        type(v) is not int or v < 0 for v in usage.values()
    )):
        _fail("INVALID_USAGE")
    if type(captured_at_ns) is not int or captured_at_ns < 0:
        _fail("INVALID_CAPTURE_TIME")
    document = {
        "schema": "residual.decision-claim.v1", "adapter_version": ADAPTER_VERSION,
        "kind": "decision_claim", "authority": False, "status": "UNVERIFIED_CANDIDATE",
        "subject": request.subject, "evidence_refs": list(request.evidence_refs),
        "source_kind": source_kind, "captured_at_ns": captured_at_ns,
        "producer": {"provider": "cloudflare", "requested_model": model,
                     "reported_model": result["model"], "model_revision": None,
                     "model_identity_status": "UNPINNED_ALIAS"},
        "request_sha256": _digest(wire), "response_sha256": _digest(raw),
        "schema_sha256": _digest(_encode(questions)),
        "state_sha256": _digest(_encode(request.payload()["state"])),
        "answers": {qid: _answer(q, answers[qid]) for qid, q in questions.items()},
        "usage": usage, "usage_status": "REPORTED" if usage else "UNKNOWN",
        "calibration_status": "UNQUALIFIED", "input_completeness": "NOT_ATTESTED",
    }
    return DecisionEvidence(_encode(document))


def replay_clef(request: DecisionRequest, raw_response: bytes, *, model: str = "clef-flash",
                captured_at_ns: int = 0) -> DecisionEvidence:
    """Offline normalization, explicitly marked replay. Does not run a model."""
    return _evidence(request, raw_response, model, "OFFLINE_REPLAY", captured_at_ns)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        raise DecisionError("REDIRECT_REJECTED")


def _https_post(url: str, token: str, payload: bytes, timeout: float) -> bytes:
    # No ambient proxies, automatic redirects, retry loop, or provider fallback.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/json", "Accept-Encoding": "identity",
    })
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                _fail("HTTP_STATUS_REJECTED")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                _fail("RESPONSE_TOO_LARGE")
            return raw
    except DecisionError:
        raise
    except urllib.error.HTTPError as exc:
        code = ("AUTH_FAILURE" if exc.code in (401, 403) else
                "RATE_LIMITED" if exc.code == 429 else
                "REDIRECT_REJECTED" if 300 <= exc.code < 400 else "HTTP_FAILURE")
        exc.close()
        raise DecisionError(code) from None
    except TimeoutError:
        raise DecisionError("TRANSPORT_TIMEOUT") from None
    except (urllib.error.URLError, OSError):
        raise DecisionError("TRANSPORT_FAILURE") from None


@dataclass(frozen=True)
class ClefAdapter:
    account_id: str
    api_token: str = field(repr=False)
    model: str = "clef-flash"
    enabled: bool = False
    timeout_seconds: float = 15.0
    transport: Callable[[str, str, bytes, float], bytes] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.account_id) is not str or not _ACCOUNT.fullmatch(self.account_id):
            _fail("INVALID_ACCOUNT_ID")
        if (not _text(self.api_token, 4096)
                or any(ord(c) < 33 or ord(c) > 126 for c in self.api_token)):
            _fail("INVALID_API_TOKEN")
        if type(self.model) is not str or self.model not in MODELS:
            _fail("UNSUPPORTED_MODEL")
        if type(self.enabled) is not bool:
            _fail("INVALID_ENABLE_FLAG")
        if (type(self.timeout_seconds) not in (int, float)
                or not 0 < self.timeout_seconds <= 60):
            _fail("INVALID_TIMEOUT")
        if self.transport is not None and not callable(self.transport):
            _fail("INVALID_TRANSPORT")

    def evaluate(self, request: DecisionRequest) -> DecisionEvidence:
        if not self.enabled:
            _fail("ADAPTER_DISABLED")
        payload = request.wire_bytes(self.model)
        url = (f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}"
               f"/ai/run/@cf/cloudflare/{self.model}")
        transport = self.transport or _https_post
        try:
            raw = transport(url, self.api_token, payload, self.timeout_seconds)
        except DecisionError:
            if self.transport is not None:
                raise DecisionError("TRANSPORT_FAILURE") from None
            raise
        except Exception:
            # Custom transports may put credentials or state in their exceptions.
            raise DecisionError("TRANSPORT_FAILURE") from None
        return _evidence(request, raw, self.model,
                         "INJECTED_TRANSPORT" if self.transport else "CLOUDFLARE_HTTPS",
                         time.time_ns())
