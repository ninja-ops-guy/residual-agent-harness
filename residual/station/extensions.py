"""Default station extensions and exact-revision task receipt issuance."""
from __future__ import annotations

import hashlib
from pathlib import Path

from residual.core import ContractError, canonical, digest
from residual.extensions import StationExtensionRegistry, VerifierDescriptor, VerifierRevision
from residual.goalspec import CheckType
from residual.modules.adapters import DashboardModule, LifecycleModule, MemoryModule, TrajectoryModule
from residual.modules.secops import SecOpsModule
from residual.receipts import ReceiptReference, StationReceipt, cache_key
from residual.verifier import CheckResult
from residual.trajectory import TrajectoryRecorder
from residual.memory import EpistemicMemoryStore
from residual.tui import ObservationCollector


def default_registry(station, pid):
    from . import control
    import residual.modules.secops as secops
    registry = StationExtensionRegistry()
    patterns = [r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
    module = SecOpsModule(patterns, ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC"])
    identity = VerifierRevision.from_artifact(secops.__file__,
        configuration={"patterns": patterns, "allowed_licenses": sorted(module._allowed)},
        policy={"stage": "before_git_staging", "scope": "declared_candidate_files"})
    registry.register_module(module, revisions={name: identity for name in module.verifiers()})

    class MissionModule(LifecycleModule):
        name = "station"
        def verifiers(self):
            identity = VerifierRevision.from_artifact(__file__,
                configuration={"control_hash": hashlib.sha256(Path(control.__file__).read_bytes()).hexdigest()},
                policy={"acceptance": "exact_revision_local_checks_and_review"})
            def structure(candidate, params):
                result, reason = control._structure(candidate, params)
                if result == CheckResult.PASS:
                    try:
                        for task in candidate["tasks"]:
                            validate_task_receipt(station, candidate, task)
                    except (ValueError, KeyError, TypeError):
                        return CheckResult.FAIL, "station_receipt_missing_or_stale"
                return result, reason
            return {name: VerifierDescriptor(kind, fn, identity) for name, kind, fn in (
                ("acceptance", CheckType.MECHANICAL, control._checks),
                ("integration", CheckType.STRUCTURAL, structure),
                ("review", CheckType.JUDGE, control._review))}
    registry.register_module(MissionModule())
    registry.register_module(DashboardModule(ObservationCollector()))
    directory = station.store.root / "extensions" / pid
    recorder = TrajectoryRecorder(str(directory / "trajectories"))
    def publish(trajectory):
        artifact = station.store.add_artifact(pid, "TRAJECTORY.json",
            canonical(recorder.load(trajectory.trajectory_hash)), "trajectory")
        station.store.event(pid, "project.note", {"message": "Structural trajectory recorded", "evidence": artifact["id"]})
    registry.register_module(TrajectoryModule(recorder, publish))
    def receipts(result):
        project = station.store.project(pid)
        for task in project["tasks"]:
            receipt, value = validate_task_receipt(station, project, task)
            yield task["instruction"], receipt, value
    registry.register_module(MemoryModule(EpistemicMemoryStore(str(directory / "memory")), receipts))
    return registry


def _revision(registry):
    here = Path(__file__).parent
    implementation = {name: hashlib.sha256((here / name).read_bytes()).hexdigest()
                      for name in ("extensions.py", "service.py", "workspace.py", "contracts.py")}
    return digest({"implementation": implementation,
        "verifiers": {name: desc.effective_revision for name, desc in registry.verifiers().items()},
        "modules": registry.modules})


def _binding(project, task, revision, parents):
    contract = {k: task[k] for k in ("id", "instruction", "files", "context", "depends_on", "checks")}
    return cache_key(project_id=project["id"], task_id=task["id"], goal_hash=project["spec_hash"],
        contract_hash=digest(contract), verifier_name="station:integration", verifier_revision=revision,
        check_type="structural", artifacts={"candidate": digest(task["head_commit"])}, parents=parents)


def validate_task_receipt(station, project, task):
    stored = task.get("verification_receipt")
    if not isinstance(stored, dict) or set(stored) != {"receipt", "value"}:
        raise ContractError("Task requires a current station receipt; re-run its verification")
    receipt = StationReceipt.from_dict(stored["receipt"])
    value = stored["value"]
    by_id = {t["id"]: t for t in project["tasks"]}
    parents = tuple(sorted(ReceiptReference(d, StationReceipt.from_dict(by_id[d]["verification_receipt"]["receipt"]).receipt_hash)
                           for d in task["depends_on"]))
    revision = _revision(station.extensions(project["id"]))
    if (task["state"] != "integrated" or receipt.task_id != task["id"]
            or value.get("head_commit") != task["head_commit"] or value.get("checks_hash") != task["checks_hash"]
            or value.get("review_hash") != digest(task["review"])
            or not receipt.matches(value=value, cache_key=_binding(project, task, revision, parents),
                verifier_name="station:integration", verifier_revision=revision, parents=parents)):
        raise ContractError("Station receipt is stale or does not match the task evidence")
    return receipt, value


def issue_task_receipt(station, project, task, integration_checks):
    by_id = {t["id"]: t for t in project["tasks"]}
    parents = tuple(sorted(ReceiptReference(d, validate_task_receipt(station, project, by_id[d])[0].receipt_hash)
                           for d in task["depends_on"]))
    revision = _revision(station.extensions(project["id"]))
    value = {"head_commit": task["head_commit"], "checks_hash": task["checks_hash"],
             "review_hash": digest(task["review"]), "integration_checks_hash": digest(integration_checks)}
    receipt = StationReceipt(task["id"], _binding(project, task, revision, parents), digest(value),
        "station:integration", revision, CheckResult.PASS, parents,
        engine_name="residual-station", engine_version="0.5.0")
    return {"receipt": receipt.to_dict(), "value": value}
