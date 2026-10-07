"""GoalSpec control plane for the station's real dependency-wave executor."""
from __future__ import annotations

import concurrent.futures
import json
import threading
import time
from dataclasses import asdict

from residual import AmendmentRule, CheckResult, CheckType, GoalSpec, LoopController, SuccessCriterion, Verifier
from residual.core import ContractError, digest
from . import workspace as ws
from .store import MAX_TASK_ATTEMPTS


def _checks(candidate, parameters):
    okay = bool(candidate["tasks"]) and all(t["checks_result"] and all(c.get("passed") is True for c in t["checks_result"]) for t in candidate["tasks"])
    return (CheckResult.PASS if okay else CheckResult.FAIL, "acceptance_receipts_verified" if okay else "acceptance_checks_incomplete")


def _structure(candidate, parameters):
    okay = candidate["spec_hash"] == parameters["spec_hash"] and sorted(t["id"] for t in candidate["tasks"]) == list(parameters["task_ids"]) and all(t["state"] == "integrated" for t in candidate["tasks"])
    return (CheckResult.PASS if okay else CheckResult.FAIL, "all_specs_integrated" if okay else "integration_incomplete")


def _review(candidate, parameters):
    # Reuse head-bound reviewer receipts; this verification adds no inference call.
    okay = all(t.get("review", {}).get("approved") is True and t["review"].get("head_commit") == t["head_commit"] for t in candidate["tasks"])
    return (CheckResult.PASS if okay else CheckResult.FAIL, "review_receipts_match" if okay else "review_receipt_missing_or_stale")


class BudgetAdmission:
    """Host-owned pre-dispatch admission gate for run budget/deadline authority.

    LoopController evaluates token/wall-clock budgets only after a pass returns,
    so Station effects inside a pass must not outrun that authoritative verdict.
    This gate mirrors the same run-level accounting from durable usage receipts:

    * a dispatch is admitted only while the run has sufficient admissible
      budget/deadline authority for it;
    * bounded cost is reserved before dispatch where knowable — the reservation
      unit is the worst per-call usage observed in this run (one token before
      any observation), held for the in-flight call and reconciled against the
      recorded usage receipt on completion;
    * unknown or invalid usage is conservative: no further dispatch is admitted
      and no review/integration effect is permitted, matching the controller's
      abort on unknown usage;
    * the deadline is re-checked at every admission and before every
      review/integration effect.
    """

    def __init__(self, station, pid, cursor):
        self.station, self.pid = station, pid
        self._seen = cursor
        self._started = time.monotonic()
        self._spec = None
        self._lock = threading.Lock()
        self._used = 0
        self._reserved = 0
        self._worst_call = 0
        self._unknown = False

    def bind(self, spec):
        self._spec = spec

    def _refresh(self):
        # Caller holds the lock. Usage receipts are durable host records.
        for ev in self.station.store.events(self.pid, self._seen, 100000):
            self._seen = ev["seq"]
            if ev["event_type"] != "usage.recorded":
                continue
            data = ev["data"]
            values = (data.get("input_tokens"), data.get("output_tokens"))
            if any(type(v) is not int or v < 0 for v in values):
                self._unknown = True
                continue
            used = sum(values)
            self._used += used
            self._worst_call = max(self._worst_call, used)

    def _denial(self):
        if self._unknown:
            return "usage_unknown_or_invalid"
        if time.monotonic() - self._started >= self._spec.wall_clock_budget_s:
            return "wall_clock_budget_exhausted"
        if self._used + self._reserved >= self._spec.token_budget:
            return "token_budget_exhausted"
        return None

    def admit(self):
        """Reserve bounded cost for one dispatch.

        Returns (denial_reason, None) when admission is refused, or
        (None, reservation) with the held reservation token on success.
        """
        with self._lock:
            self._refresh()
            reason = self._denial()
            if reason is not None:
                return reason, None
            reservation = max(1, self._worst_call)
            if self._used + self._reserved + reservation >= self._spec.token_budget:
                return "token_budget_exhausted", None
            self._reserved += reservation
            return None, reservation

    def release(self, reservation):
        with self._lock:
            self._refresh()
            self._reserved = max(0, self._reserved - reservation)

    def denial_reason(self):
        """Re-check run authority without reserving (for review/integration gates)."""
        with self._lock:
            self._refresh()
            return self._denial()


class MissionPass:
    def __init__(self, station, pid, progress):
        self.station, self.pid, self.progress = station, pid, progress
        before = station.store.events(pid, 0, 100000)
        self._gate = BudgetAdmission(station, pid, before[-1]["seq"] if before else 0)

    def _denied(self, reason, stage, tid=None):
        self.station.store.event(
            self.pid, "project.note",
            {"message": "Run budget/deadline admission denied an authority-bearing Station effect",
             "reason": reason, "stage": stage, **({"task_id": tid} if tid else {})},
            actor="coordinator",
        )

    def _run_admitted(self, task, owner):
        reason, reservation = self._gate.admit()
        if reason is not None:
            self._denied(reason, "pre-dispatch", task["id"])
            return {"task_id": task["id"], "state": "admission_denied", "reason": reason}
        try:
            return self.station.run_one(self.pid, task["id"], owner)
        finally:
            self._gate.release(reservation)

    def _stop_authority_effects(self, cursor, stage):
        reason = self._gate.denial_reason()
        if reason is None:
            return None
        self._denied(reason, stage)
        return self._result(cursor)

    def _result(self, cursor):
        store = self.station.store
        pid = self.pid
        used = 0
        for ev in store.events(pid, cursor, 100000):
            if ev["event_type"] != "usage.recorded":
                continue
            data = ev["data"]
            values = (data.get("input_tokens"), data.get("output_tokens"))
            if any(type(v) is not int or v < 0 for v in values):
                used = None
                break
            used += sum(values)
        p = store.project(pid)
        fingerprint = digest([{k: t[k] for k in ("id", "state", "head_commit")} for t in p["tasks"]])
        return {"candidate": p, "tokens_used": used,
                "observations": [{"kind": "tool.invoked", "payload": {"tool": "mission_wave", "fingerprint": fingerprint}}],
                **({"halt": "paused"} if p["paused"] else {})}

    def run_pass(self, spec, pass_number):
        station, pid, progress = self.station, self.pid, self.progress
        self._gate.bind(spec)
        store = station.store
        before = store.events(pid, 0, 100000)
        cursor = before[-1]["seq"] if before else 0
        p = store.project(pid)
        result = {"tokens_used": 0, "observations": []}
        if p["paused"]:
            return {**result, "candidate": p, "halt": "paused"}
        states = {t["id"]: t["state"] for t in p["tasks"]}
        ready = [t for t in p["tasks"] if t["state"] in {"ready", "repair_required"} and t["attempt"] < MAX_TASK_ATTEMPTS and all(states[d] == "integrated" for d in t["depends_on"])]
        if not ready and not any(t["state"] in {"review_ready", "approved"} for t in p["tasks"]):
            return {**result, "candidate": p, **({} if all(t["state"] == "integrated" for t in p["tasks"]) else {"halt": "no_runnable_tasks"})}
        settings = store.settings()
        for task in ready:
            if task["state"] == "repair_required" and task["attempt"] >= 2 and task["route"] == "local" and p["allow_cloud"] and settings.get("cloud", {}).get("model"):
                store.update_task(pid, task["id"], route="cloud")
                store.event(pid, "task.finding", {"message": "Two local attempts failed; escalating the unresolved specification to the configured cloud runner"}, task["id"])
        workers = settings.get("workers", 2)
        progress(f"Dispatching wave {pass_number} · {len(ready)} ready tasks", None)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(self._run_admitted, t, f"runner-{i % workers + 1}") for i, t in enumerate(ready)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        blocked = self._stop_authority_effects(cursor, "post-runner")
        if blocked is not None:
            return blocked
        for task in store.project(pid)["tasks"]:
            if store.project(pid)["paused"]:
                break
            try:
                if task["state"] == "review_ready":
                    blocked = self._stop_authority_effects(cursor, "pre-review")
                    if blocked is not None:
                        return blocked
                    reason, reservation = self._gate.admit()
                    if reason is not None:
                        self._denied(reason, "pre-review", task["id"])
                        return self._result(cursor)
                    try:
                        progress(f"Reviewing {task['id']}", None)
                        station.review(pid, task["id"])
                    finally:
                        self._gate.release(reservation)
                    blocked = self._stop_authority_effects(cursor, "post-review")
                    if blocked is not None:
                        return blocked
                if store.task(pid, task["id"])["state"] == "approved":
                    blocked = self._stop_authority_effects(cursor, "pre-integration")
                    if blocked is not None:
                        return blocked
                    station.integrate(pid, task["id"])
            except ContractError as exc:
                store.event(pid, "task.finding", {"message": str(exc)[:800]}, task["id"])
        return self._result(cursor)


def run_controlled_batch(station, pid, progress):
    station.triage(pid, progress)
    store = station.store
    p, settings = store.project(pid), store.settings()
    spec = GoalSpec(goal_id=pid, objective=p["goal"], success_criteria=(
        SuccessCriterion("acceptance", CheckType.MECHANICAL, "Every task has passing local checks", "station:acceptance"),
        SuccessCriterion("integration", CheckType.STRUCTURAL, "Original specifications are integrated", "station:integration",
                         {"spec_hash": p["spec_hash"], "task_ids": sorted(t["id"] for t in p["tasks"])}),
        SuccessCriterion("review", CheckType.JUDGE, "Reviewer receipts match integrated commits", "station:review"),
    ), max_passes=min(settings["batch_max_passes"], max(1, len(p["tasks"]) * MAX_TASK_ATTEMPTS)),
       token_budget=settings["batch_token_budget"], wall_clock_budget_s=settings["batch_wall_clock_s"],
       amendment_rule=AmendmentRule(("operator",)))
    bus = store.observation_bus(pid, component="loop_controller")
    def emit(kind, payload):
        # Durable host control facts precede lifecycle hooks, even with telemetry off.
        if kind == "checkpoint" and payload.get("event") in {"run_opened", "run_closed"}:
            store.event(pid, "project.note", {"message": payload["event"], "control": payload})
        if bus:
            bus.emit(kind, payload, source="residual.loop")
    extensions = station.extensions(pid)
    run = LoopController(spec, Verifier({}), MissionPass(station, pid, progress), emit=emit, extensions=extensions).run()
    receipt = {"schema_version": 1, "goal_spec": spec.to_dict(), "run": asdict(run),
               "extensions": dict(extensions.modules), "extension_diagnostics": list(extensions.diagnostics)}
    body = "# Mission run control\n\nGoal contract and deterministic verification receipt. Token usage is null when unavailable.\n\n```json\n" + json.dumps(receipt, indent=2) + "\n```\n"
    artifact = store.add_artifact(pid, "RUN-CONTROL.md", body, "control")
    final_project = store.project(pid)
    project_head = ws.git(final_project["repo"], "rev-parse", "HEAD")
    summary = {"outcome": run.outcome.value, "passes": run.total_passes, "tokens": run.total_tokens,
               "wall_clock_s": run.wall_clock_s, "spec_hash": run.spec_hash,
               "project_spec_hash": final_project["spec_hash"], "project_head": project_head,
               "tripped_brakes": list(run.tripped_brakes), "trip_reasons": list(run.trip_reasons), "evidence": artifact["id"]}
    store.project_update(pid, last_run=summary)
    store.event(pid, "project.note", {"message": f"Batch {run.outcome.value} after {run.total_passes} pass(es). Run-control evidence is available.", "evidence": artifact["id"]})
    p = store.project(pid)
    return {"integrated": sum(t["state"] == "integrated" for t in p["tasks"]), "total": len(p["tasks"]),
            "message": f"Batch {run.outcome.value}; inspect run control for verification and brakes", "control": summary}
