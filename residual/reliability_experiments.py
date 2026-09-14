"""Controlled fault injection and orchestration timing for reliability experiments.

This module is deliberately additive: it does not change ``Harness.run`` receipts
or acceptance semantics. Fault trials return a separate experiment receipt and
orchestration timing is measured by wrapping existing execution boundaries.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from types import MethodType
from typing import Any, Callable

from .core import ContractError, digest
from .providers import Provider, ProviderError, Reply, Usage


FAULT_KINDS = {
    "malformed_reply": "schema/contract boundary",
    "truncated_reply": "schema/contract boundary",
    "worker_abstain": "worker/controller boundary",
    "provider_error": "provider/runtime boundary",
    "worker_termination": "worker/runtime boundary",
    "invalid_scope_update": "obligation-scope boundary",
    "undeclared_evidence_request": "evidence-scope boundary",
    "oversized_evidence_request": "evidence-window boundary",
    "resource_exhaustion": "resource-budget boundary",
}

# These preregistered classes require the newer isolated worker / evidence-bus
# runtime and are intentionally not simulated against the classic Harness path.
DEFERRED_FAULT_KINDS = {
    "forbidden_tool_invocation": "M2 worker tool boundary",
    "forbidden_filesystem_write": "M2 OS-enforced filesystem boundary",
    "stale_telemetry": "M3 evidence/telemetry boundary",
    "receipt_tamper": "M3 receipt graph boundary",
    "verifier_revision_change": "M3 verifier-revision binding boundary",
    "dependency_fault": "M4 dependency scheduler boundary",
    "integration_conflict": "M4 deterministic integrator boundary",
}


@dataclass(frozen=True)
class FaultSpec:
    fault_id: str
    kind: str
    role: str = "expert"

    def __post_init__(self):
        if not isinstance(self.fault_id, str) or not self.fault_id:
            raise ContractError("fault_id must be nonempty")
        if self.kind not in FAULT_KINDS:
            raise ContractError("unsupported fault kind")
        if self.role not in {"local", "expert"}:
            raise ContractError("fault role must be local or expert")

    @property
    def expected_layer(self) -> str:
        return FAULT_KINDS[self.kind]


class FaultInjectingProvider(Provider):
    """Inject one deterministic transport/worker/protocol fault into a provider lane."""

    def __init__(self, provider: Provider, spec: FaultSpec):
        self.provider = provider
        self.spec = spec
        self.name = provider.name + ":fault:" + spec.fault_id
        self.placement = provider.placement
        self.prices = provider.prices
        self.injected = False

    def wire_size(self, packet, max_output_tokens):
        if self.spec.kind == "resource_exhaustion" and not self.injected:
            # The classic Harness enforces max_request_bytes before provider I/O.
            # Returning an impossible framed size deterministically exercises that
            # real budget boundary without fabricating a provider response.
            self.injected = True
            return 1 << 60
        return self.provider.wire_size(packet, max_output_tokens)

    @staticmethod
    def _first_obligation(packet):
        obligations = packet.get("obligations") if isinstance(packet, dict) else None
        if not obligations or not isinstance(obligations[0], dict):
            raise ProviderError("fault_packet_missing_obligation")
        node_id = obligations[0].get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ProviderError("fault_packet_missing_obligation")
        return obligations[0], node_id

    def generate(self, packet, max_output_tokens):
        if self.injected:
            return self.provider.generate(packet, max_output_tokens)
        self.injected = True
        if self.spec.kind == "provider_error":
            raise ProviderError("injected_provider_error")
        if self.spec.kind == "worker_termination":
            raise ProviderError("worker_terminated")
        if self.spec.kind == "malformed_reply":
            return Reply("{not-json", Usage(source="simulation"), 0.0, "stop")
        if self.spec.kind == "truncated_reply":
            return Reply('{"updates":{},"requests":[]}', Usage(source="simulation"), 0.0, "length")
        if self.spec.kind == "worker_abstain":
            return Reply('{"updates":{},"requests":[]}', Usage(source="simulation"), 0.0, "stop")
        obligation, node_id = self._first_obligation(packet)
        if self.spec.kind == "invalid_scope_update":
            return Reply('{"updates":{"__outside_scope__":0},"requests":[]}',
                         Usage(source="simulation"), 0.0, "stop")
        if self.spec.kind == "undeclared_evidence_request":
            text = ('{"updates":{},"requests":[{"obligation_id":' + _json_string(node_id) +
                    ',"artifact_id":"__undeclared_fault_artifact__","start_line":1,"end_line":1}]}')
            return Reply(text, Usage(source="simulation"), 0.0, "stop")
        if self.spec.kind == "oversized_evidence_request":
            evidence_ids = obligation.get("evidence_ids")
            if not evidence_ids or not isinstance(evidence_ids[0], str):
                raise ProviderError("fault_packet_missing_evidence")
            text = ('{"updates":{},"requests":[{"obligation_id":' + _json_string(node_id) +
                    ',"artifact_id":' + _json_string(evidence_ids[0]) +
                    ',"start_line":1,"end_line":1000000000}]}')
            return Reply(text, Usage(source="simulation"), 0.0, "stop")
        raise ContractError("unsupported fault kind")


# Avoid importing a second serializer contract just for synthetic protocol text.
def _json_string(value: str) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


class OrchestrationTimingProbe:
    """Measure orchestration boundaries without mutating the run result.

    Directly measured components:
    - context packaging + packet-plan selection (combined, because both occur in
      ``Harness._packet`` today);
    - dispatch partition/scheduling overhead exclusive of ``_work``;
    - response integration: protocol parse, receipt/integration work exclusive of
      verifier time, and evidence-request application.

    Provider, verifier and solver time remain authoritative in the normal run
    metrics. The combined packet component is intentionally not split into two
    invented numbers.
    """

    def __init__(self, harness):
        self.harness = harness
        self.packet_ms = 0.0
        self.dispatch_total_ms = 0.0
        self.work_nested_ms = 0.0
        self.integration_ms = 0.0
        self._installed = False

    @staticmethod
    def _elapsed(start):
        return (time.monotonic() - start) * 1000

    def install(self):
        if self._installed:
            raise ContractError("timing probe already installed")
        h = self.harness
        original_packet = h._packet
        original_dispatch = h._dispatch
        original_work = h._work
        original_parse = h._parse
        original_accept = h._accept
        original_request = h._request_evidence
        probe = self

        def packet(this, *args, **kwargs):
            started = time.monotonic()
            try:
                return original_packet(*args, **kwargs)
            finally:
                probe.packet_ms += probe._elapsed(started)

        def work(this, *args, **kwargs):
            started = time.monotonic()
            try:
                return original_work(*args, **kwargs)
            finally:
                probe.work_nested_ms += probe._elapsed(started)

        def dispatch(this, *args, **kwargs):
            started = time.monotonic()
            before = probe.work_nested_ms
            try:
                return original_dispatch(*args, **kwargs)
            finally:
                total = probe._elapsed(started)
                nested = probe.work_nested_ms - before
                probe.dispatch_total_ms += max(0.0, total - nested)

        def parse(this, *args, **kwargs):
            started = time.monotonic()
            try:
                return original_parse(*args, **kwargs)
            finally:
                probe.integration_ms += probe._elapsed(started)

        def accept(this, *args, **kwargs):
            started = time.monotonic()
            before_verify = getattr(this, "verification_ms", 0.0)
            try:
                return original_accept(*args, **kwargs)
            finally:
                total = probe._elapsed(started)
                verifier = max(0.0, getattr(this, "verification_ms", 0.0) - before_verify)
                probe.integration_ms += max(0.0, total - verifier)

        def request(this, *args, **kwargs):
            started = time.monotonic()
            try:
                return original_request(*args, **kwargs)
            finally:
                probe.integration_ms += probe._elapsed(started)

        h._packet = MethodType(packet, h)
        h._work = MethodType(work, h)
        h._dispatch = MethodType(dispatch, h)
        h._parse = MethodType(parse, h)
        h._accept = MethodType(accept, h)
        h._request_evidence = MethodType(request, h)
        self._installed = True
        return self

    def snapshot(self) -> dict[str, Any]:
        if not self._installed:
            raise ContractError("timing probe not installed")
        measured = {
            "dispatch_scheduling_ms": self.dispatch_total_ms,
            "context_packaging_and_planning_ms": self.packet_ms,
            "integration_ms": self.integration_ms,
        }
        return {
            "schema_version": "residual.orchestration-timing.v1",
            **measured,
            "measured_orchestration_ms": sum(measured.values()),
            "planning_context_split_available": False,
            "note": "Packet planning and context packaging share one execution boundary in Harness._packet and are reported together rather than fabricated as separate timings.",
        }


def run_timed(harness, task) -> tuple[dict[str, Any], dict[str, Any]]:
    probe = OrchestrationTimingProbe(harness).install()
    result = harness.run(task)
    timing = probe.snapshot()
    timing["task_id"] = task.id
    timing["mode"] = harness.mode
    timing["sha256"] = digest(timing)
    return result, timing


def _fault_detected(harness, kind: str) -> bool:
    expected = {
        "malformed_reply": {("counterexample", "invalid_protocol")},
        "truncated_reply": {("counterexample", "invalid_protocol")},
        "worker_abstain": {("counterexample", "worker_abstained")},
        "provider_error": {("provider_failed", "injected_provider_error"),
                           ("counterexample", "injected_provider_error")},
        "worker_termination": {("provider_failed", "worker_terminated"),
                               ("counterexample", "worker_terminated")},
        "invalid_scope_update": {("counterexample", "invalid_protocol")},
        "undeclared_evidence_request": {("counterexample", "undeclared_evidence"),
                                        ("evidence_denied", "undeclared_evidence")},
        "oversized_evidence_request": {("counterexample", "evidence_window_limit"),
                                       ("evidence_denied", "evidence_window_limit")},
        "resource_exhaustion": {("counterexample", "budget_exhausted")},
    }[kind]
    for event in getattr(getattr(harness, "ledger", None), "events", []):
        pair = (event.get("kind"), (event.get("data") or {}).get("code"))
        if pair in expected:
            return True
    return False


def run_fault_trial(harness, task, spec: FaultSpec,
                    independent_grade: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    """Run one controlled fault trial and emit an explicit containment receipt.

    ``independent_grade`` receives the final accepted value mapping and must return
    whether the candidate state is independently correct. Containment is then a
    direct property of the injected trial: the injected fault did not produce an
    incorrect accepted state. Detection is reported separately and is never used
    as a substitute for containment.
    """
    if not callable(independent_grade):
        raise ContractError("independent_grade must be callable")
    target = getattr(harness, spec.role)
    if target is None:
        raise ContractError("fault target provider is disabled")
    injected = FaultInjectingProvider(target, spec)
    setattr(harness, spec.role, injected)
    result, timing = run_timed(harness, task)
    independently_correct = bool(independent_grade(result["values"]))
    accepted = bool(result["success"])
    incorrect_accepted_state = accepted and not independently_correct
    detected = _fault_detected(harness, spec.kind)

    receipt = {
        "schema_version": "residual.fault-trial.v1",
        "fault_injected": True,
        "fault_id": spec.fault_id,
        "fault_kind": spec.kind,
        "fault_role": spec.role,
        "expected_containment_layer": spec.expected_layer,
        "injection_observed": injected.injected,
        "fault_detected": detected,
        "independently_correct": independently_correct,
        "controller_accepted": accepted,
        "incorrect_fault_crossed_acceptance_boundary": incorrect_accepted_state,
        "fault_contained": bool(injected.injected and not incorrect_accepted_state),
        "result_sha256": digest(result),
        "timing": timing,
    }
    receipt["sha256"] = digest(receipt)
    return receipt
