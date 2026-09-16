"""Exact-head repair of the self-maintenance study harness.

This wrapper preserves the original study design while correcting the artifact
path lookup used by the tamper-detection arm. The Store.artifact() API returns
database metadata that does not contain a sha256 field; the content digest is
encoded in the artifact id itself (project_id:digest).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("self_maintenance_study.py")
spec = importlib.util.spec_from_file_location("self_maintenance_study_base", MODULE_PATH)
base = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(base)


def documentation_experiment(repeats: int = 5) -> dict:
    successes = 0
    receipt_bindings = 0
    markdown_bindings = 0
    integrity_reports = 0
    tamper_detections = 0
    wall_clock = []
    integrated = []
    for i in range(repeats):
        with base.tempfile.TemporaryDirectory() as directory:
            station = base.Station(directory)
            project_id = station.create(base.demo_spec(), demo=True)["project_id"]
            result = station.batch(project_id)
            successes += int(result["control"]["outcome"] == "success")
            integrated.append(result["integrated"])
            wall_clock.append(result["control"]["wall_clock_s"])
            meta, body = station.store.artifact(result["control"]["evidence"])
            text = body.decode("utf-8")
            receipt_bindings += int(result["control"]["spec_hash"] in text)
            markdown_bindings += int("## Run control" in station.store.markdown(project_id))
            integrity_reports += int(
                station.store.observation_summary(project_id)["integrity"] == "verified"
            )
            if i == 0:
                artifact_id = result["control"]["evidence"]
                digest = artifact_id.split(":", 1)[1]
                artifact_path = station.store.root / "artifacts" / project_id / digest
                artifact_path.write_text("tampered", encoding="utf-8")
                try:
                    station.store.artifact(artifact_id)
                except base.ContractError:
                    tamper_detections += 1

    original = base.make_goal(2)
    amended = original.amend(
        max_passes=3,
        amendment_reason="additional bounded repair attempt",
        amended_by="operator",
    )
    return {
        "repeats": repeats,
        "successful_batches": successes,
        "integrated_counts": integrated,
        "receipt_spec_hash_bindings": receipt_bindings,
        "project_markdown_bindings": markdown_bindings,
        "verified_integrity_summaries": integrity_reports,
        "tamper_detection_trials": 1,
        "tamper_detections": tamper_detections,
        "mean_reported_wall_clock_s": base.statistics.fmean(wall_clock),
        "max_reported_wall_clock_s": max(wall_clock),
        "authorized_revision_changes_identity": original.content_hash != amended.content_hash,
        "authorized_revision_parent_bound": amended.parent_hash == original.content_hash,
        "artifact_metadata_name": meta["name"],
    }


base.documentation_experiment = documentation_experiment

if __name__ == "__main__":
    raise SystemExit(base.main())
