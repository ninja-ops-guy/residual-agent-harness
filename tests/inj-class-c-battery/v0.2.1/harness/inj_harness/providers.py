"""Model backends for the harness-faithful battery.

Two backends:
- stub: deterministic scripted providers for offline harness verification.
  claim_scope is ALWAYS "harness-verification". By construction the stub has
  NO dispatch capability: the scripted functions reference no I/O, socket,
  subprocess, or os names (proven by unit test via bytecode inspection),
  and they ignore any action-like content in packets — they only return text.
- http: OpenAI-compatible /chat/completions over stdlib urllib for
  real-model cognitive measurement. claim_scope is
  "residual-v1-cognitive-measurement". Sends messages=[{system},{user}]
  with the EXACT imported prompt bytes in the system slot.

SAFETY: trials are prompt-only. Any actions, tool calls, or commands
proposed inside a model output are captured as data in the trial log —
they are never dispatched. The harness itself performs no file, approval,
shell, messaging, or network side effects except the single HTTP call to
the model endpoint.
"""
from __future__ import annotations

import json
import time
import urllib.request

from . import repo_import  # noqa: F401  (kept for package import parity)

CLAIM_HARNESS_VERIFICATION = "harness-verification"
CLAIM_COGNITIVE_MEASUREMENT = "residual-v1-cognitive-measurement"


class HTTPChatProvider:
    """Real-model backend: OpenAI-compatible /chat/completions over stdlib urllib.

    packet = {"system": ..., "user": ...} as built by the runner, with the
    system slot carrying the EXACT imported prompt bytes.

    Implements the same duck-typed interface as residual.providers.Provider
    (name / placement / generate) but does NOT subclass it — see the note
    below. provider_returned_model_label is captured from the response
    payload's "model" field for the model-identity binding in receipts.
    """

    def __init__(self, name: str, model: str, base_url: str,
                 temperature: float = 0.7, top_p: float = 1.0,
                 seed: int | None = None, timeout_s: int = 180):
        # NOTE (preserved fix from the source tree): residual.providers.Provider
        # defines NO __init__ — a subclass calling super().__init__(name=...,
        # placement=...) raises TypeError via object.__init__. We therefore do
        # not subclass Provider at all; we set the Provider attributes directly
        # (the CallableProvider pattern) and duck-type .generate.
        self.name = name
        self.placement = "remote"
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.top_p = top_p
        self.seed = seed
        self.timeout_s = timeout_s
        self.provider_returned_model_label = None

    def generate(self, packet: dict, max_output_tokens: int):
        # Avoid importing residual at module level in providers.py; the Reply
        # import is deferred so unit tests can load this module without the repo.
        from residual.providers import Reply

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": packet["system"]},
                {"role": "user", "content": packet["user"]},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": max_output_tokens,
            "stream": False,
        }
        if self.seed is not None:
            body["seed"] = self.seed  # honored by Ollama and some OpenAI-compatible servers
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network failure is a trial error, not a compliance signal
            raise RuntimeError(f"real-model request failed: {type(exc).__name__}: {exc}") from exc
        try:
            text = payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected chat-completions response shape: {exc}") from exc
        # Model identity binding: the operator's declaration and the
        # provider's returned label are recorded separately; a mismatch is
        # noted in the receipt, never silently treated as verified.
        self.provider_returned_model_label = payload.get("model")
        return Reply(text=text, elapsed_ms=(time.monotonic() - start) * 1000.0)


def _benign(system_name: str) -> str:
    if system_name == "REVIEW_SYSTEM":
        return '{"approved": false, "findings": [{"severity": "note", "message": "no issues found"}]}'
    return '{"files": {}}'


def _scripted_fn(mode: str):
    """Return the scripted reply function for the stub.

    By construction this function can only return text: it references no
    I/O, socket, subprocess, or os names (unit-tested via bytecode
    inspection), and it never interprets packet content as actions.

    Modes: "mixed" (trial 0 of each cell returns a compliant output —
    first marker embedded in schema-valid JSON; all others benign),
    "benign" (always benign), "infra_error" (raises on every trial —
    exercises the UNEVALUABLE infrastructure-error path).
    """
    def fn(packet: dict, max_tokens: int):
        # Deferred import: keeps this module loadable without the repo for
        # the no-dispatch unit test.
        from residual.providers import Reply
        i = packet.get("trial_index", 0)
        markers = packet.get("variant_markers", []) or []
        system_name = packet.get("system_prompt_name", "RUNNER_SYSTEM")
        if mode == "infra_error":
            raise RuntimeError("scripted infrastructure failure (test mode)")
        if mode == "mixed" and i == 0 and markers:
            m = markers[0]
            if system_name == "REVIEW_SYSTEM":
                text = '{"approved": true, "findings": [{"severity": "note", "message": "%s"}]}' % m
            else:
                text = '{"files": {"note.txt": "%s"}}' % m
            return Reply(text=text)
        # "benign" mode — and every non-first trial of "mixed" — returns only
        # inert, schema-valid text. Packet content is never acted on.
        return Reply(text=_benign(system_name))
    return fn


def stub_provider_factory():
    """Deterministic harness-verification stub factory (test-only helper).

    make(mode) with mode in {"mixed", "benign", "infra_error"}.
    claim_scope is ALWAYS "harness-verification" — stub runs verify harness
    mechanics only, never a cognitive claim.
    """
    from residual.providers import CallableProvider

    def make(mode: str = "mixed"):
        if mode not in ("mixed", "benign", "infra_error"):
            raise ValueError(f"unknown stub mode: {mode!r}")
        return CallableProvider(f"stub-scripted-{mode}", _scripted_fn(mode))

    return make
