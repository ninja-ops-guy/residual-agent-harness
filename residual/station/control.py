"""GoalSpec control plane for the station's real dependency-wave executor."""
from __future__ import annotations

import concurrent.futures
import json
from dataclasses import asdict

from residual import AmendmentRule, CheckResult, CheckType, GoalSpec, LoopController, SuccessCriterion, Verifier
from residual.core import ContractError, digest


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


class MissionPass:
    def __init__(self, station, pid, progress):
        self.station, self.pid, self.progress = station, pid, progress

    def run_pass(self, spec, pass_number):
        station, pid, progress = self.station, self.pid, self.progress
        store = station.store
        before = store.events(pid, 0, 100000)
        cursor = before[-1]["seq"] if before else 0
        p = store.project(pid)
        result = {"tokens_used": 0, "observations": []}
        if p["paused"]:
            return {**result, "candidate": p, "halt": "paused"}
        states = {t["id"]: t["state"] for t in p["tasks"]}
        ready = [t for t in p["tasks"] if t["state"] in {"ready", "repair_required"} and t["attempt"] < 3 and all(states[d] == "integrated" for d in t["depends_on"])]
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
            futures = [pool.submit(station.run_one, pid, t["id"], f"runner-{i % workers + 1}") for i, t in enumerate(ready)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        for task in store.project(pid)["tasks"]:
            if store.project(pid)["paused"]:
                break
            try:
                if task["state"] == "review_ready":
                    progress(f"Reviewing {task['id']}", None)
                    station.review(pid, task["id"])
                if store.task(pid, task["id"])["state"] == "approved":
                    station.integrate(pid, task["id"])
            except ContractError as exc:
                store.event(pid, "task.finding", {"message": str(exc)[:800]}, task["id"])
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


def run_controlled_batch(station, pid, progress):
    station.triage(pid, progress)
    store = station.store
    p, settings = store.project(pid), store.settings()
    spec = GoalSpec(goal_id=pid, objective=p["goal"], success_criteria=(
        SuccessCriterion("acceptance", CheckType.MECHANICAL, "Every task has passing local checks", "station:acceptance"),
        SuccessCriterion("integration", CheckType.STRUCTURAL, "Original specifications are integrated", "station:integration",
                         {"spec_hash": p["spec_hash"], "task_ids": sorted(t["id"] for t in p["tasks"])}),
        SuccessCriterion("review", CheckType.JUDGE, "Reviewer receipts match integrated commits", "station:review"),
    ), max_passes=min(settings["batch_max_passes"], max(1, len(p["tasks"]) * 3)),
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
    summary = {"outcome": run.outcome.value, "passes": run.total_passes, "tokens": run.total_tokens,
               "wall_clock_s": run.wall_clock_s, "spec_hash": run.spec_hash,
               "tripped_brakes": list(run.tripped_brakes), "trip_reasons": list(run.trip_reasons), "evidence": artifact["id"]}
    store.project_update(pid, last_run=summary)
    store.event(pid, "project.note", {"message": f"Batch {run.outcome.value} after {run.total_passes} pass(es). Run-control evidence is available.", "evidence": artifact["id"]})
    p = store.project(pid)
    return {"integrated": sum(t["state"] == "integrated" for t in p["tasks"]), "total": len(p["tasks"]),
            "message": f"Batch {run.outcome.value}; inspect run control for verification and brakes", "control": summary}
