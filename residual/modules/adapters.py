"""Lifecycle adapters for the delivered components. Network effects are opt-in."""
from __future__ import annotations

from ..core import ContractError, digest
from ..loop import RunOutcome
from ..receipts import StationReceipt
from ..trajectory import TrajectoryStep


class LifecycleModule:
    version = "1.0.0"
    def quarantine_policies(self): return ()
    def verifiers(self): return {}
    def brakes(self): return ()
    def on_run_opened(self, spec): self.spec = spec
    def on_run_closed(self, result): pass


class DashboardModule(LifecycleModule):
    name = "dashboard"
    def __init__(self, collector): self.collector = collector
    def on_event(self, kind, payload): self.collector.on_event(kind, payload)


class TrajectoryModule(LifecycleModule):
    name = "trajectory"
    def __init__(self, recorder, publish=None):
        self.recorder, self.publish, self.last = recorder, publish, None
        self.steps = []
    def on_run_opened(self, spec):
        self.spec, self.steps = spec, []
    def on_event(self, kind, payload):
        # Only host-generated criterion events, never worker claimed verdicts.
        if kind == "custom" and payload.get("event") == "check_evaluated":
            verdict = payload["result"]
            self.steps.append(TrajectoryStep(len(self.steps) + 1, payload["check_name"],
                digest({"check": payload["check_name"], "type": payload["check_type"]}), verdict))
    def on_run_closed(self, result):
        self.last = self.recorder.record(result.spec_hash, self.steps, list(result.tripped_brakes), result.outcome.value)
        if self.publish: self.publish(self.last)


class MemoryModule(LifecycleModule):
    name = "memory"
    def __init__(self, store, receipts):
        """receipts(result) supplies host-validated (description, receipt, value)."""
        self.store, self.receipts = store, receipts
    def on_run_closed(self, result):
        if result.outcome != RunOutcome.SUCCESS:
            return
        for description, receipt, value in self.receipts(result):
            if not isinstance(receipt, StationReceipt) or receipt.verdict.value != "pass" or receipt.value_hash != digest(value):
                raise ContractError("memory requires a bound passing host receipt")
            self.store.index(description, receipt.receipt_hash,
                {"receipt": receipt.to_dict(), "value": value}, receipt.verifier_revision)


class HITLModule(LifecycleModule):
    name = "hitl"
    def __init__(self, gateway, publish=None):
        self.gateway, self.publish, self.last = gateway, publish, None
    def on_run_opened(self, spec):
        self.spec, self.last = spec, None
    def on_run_closed(self, result):
        # An abort never becomes an approval prompt; no hook resumes execution.
        if result.outcome == RunOutcome.ESCALATED:
            self.last = self.gateway.generate_challenge(result.goal_id,
                {"run_id": result.run_id, "tripped_brakes": list(result.tripped_brakes)},
                "; ".join(result.trip_reasons) or "operator_review_required", self.spec)
            if self.publish: self.publish(self.last)


class MeshModule(LifecycleModule):
    name = "mesh"
    def __init__(self, node, receipts):
        self.node, self.receipts = node, receipts
    def on_run_closed(self, result):
        if result.outcome != RunOutcome.SUCCESS:
            return
        for receipt in self.receipts(result):
            if not isinstance(receipt, StationReceipt) or receipt.verdict.value != "pass":
                raise ContractError("mesh export requires host receipts")
            # Compact references only. Delivery/admission and local re-verification
            # belong to the host; receiving a message never executes a task.
            self.node.broadcast_result(receipt.task_id, "", receipt.receipt_hash,
                                       receipt.verifier_revision, result.outcome.value)
