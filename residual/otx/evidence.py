"""Evidence artifact generator for SPEC-SWARM-OTX-003 (Gate B).

Runs the frozen development fixture through the controller, captures raw
observations, verifies exact replay (Gate C), and writes a
machine-readable artifact under ``evidence/otx/`` containing commit/tree
identity, runtime versions, configuration, frozen input hash, raw
observations, and results.

Usage: ``python3 -m residual.otx.evidence [--out evidence/otx]``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from typing import Dict, List

from .controller import ControllerConfig, OrchestrationTaxController, simulate_execution
from .replay import verify_replay
from .workload import default_fixture


def _git(args, cwd):
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except Exception:  # pragma: no cover - evidence must tolerate missing git
        return "UNKNOWN"


def run_study(config: ControllerConfig | None = None) -> Dict[str, object]:
    config = config or ControllerConfig()
    fixture = default_fixture()
    controller = OrchestrationTaxController(config=config)
    evaluation = controller.evaluate_fixture(fixture, simulate=simulate_execution, seed=fixture.seed)

    # Acceptance: learned task classes -> preferred topology (post-study
    # cold decisions on fresh probe tasks, using the learned model only).
    learned: Dict[str, Dict[str, object]] = {}
    for task_class in fixture.task_classes():
        probe = next(t for t in fixture.tasks if t.task_class == task_class)
        obs = controller.select_topology(probe)
        controller.log._observations.pop()  # probe is a query, not an experiment
        controller._seq -= 1
        learned[task_class] = {
            "preferred_topology": obs.selected_topology,
            "predicted_tax": {c.topology: c.predicted_tax for c in obs.candidates},
            "predicted_reliability": {c.topology: c.predicted_reliability for c in obs.candidates},
            "samples": {
                topo: controller.model.sample_count(task_class, topo) for topo in config.topologies
            },
        }

    replay = verify_replay(config, list(controller.log))

    observations_jsonl = controller.log.to_jsonl()
    return {
        "spec": "SPEC-SWARM-OTX-003",
        "config": config.to_dict(),
        "workload": {
            "name": fixture.name,
            "version": fixture.version,
            "workload_hash": fixture.workload_hash,
            "seed": fixture.seed,
            "granularities": list(fixture.granularities()),
            "task_classes": list(fixture.task_classes()),
            "task_count": len(fixture.tasks),
        },
        "evaluation": evaluation,
        "learned_preferences": learned,
        "replay": replay,
        "observations_sha256": hashlib.sha256(observations_jsonl.encode("utf-8")).hexdigest(),
        "observations": [o.to_dict() for o in controller.log],
    }


def build_artifact(study: Dict[str, object], repo_root: str) -> Dict[str, object]:
    return {
        "artifact": "otx-003-evidence",
        "artifact_version": "1.0.0",
        "identity": {
            "git_commit": _git(["rev-parse", "HEAD"], repo_root),
            "git_tree": _git(["rev-parse", "HEAD^{tree}"], repo_root),
            "git_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "study": study,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate OTX-003 evidence artifact")
    parser.add_argument("--out", default=os.path.join("evidence", "otx"))
    args = parser.parse_args(argv)

    repo_root = _git(["rev-parse", "--show-toplevel"], os.getcwd())
    if repo_root == "UNKNOWN":
        repo_root = os.getcwd()

    study = run_study()
    artifact = build_artifact(study, repo_root)

    os.makedirs(args.out, exist_ok=True)
    artifact_path = os.path.join(args.out, "results.json")
    obs_path = os.path.join(args.out, "observations.jsonl")
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(obs_path, "w", encoding="utf-8") as fh:
        jsonl = "\n".join(json.dumps(o, sort_keys=True) for o in study["observations"]) + "\n"
        fh.write(jsonl)

    digest = hashlib.sha256(open(artifact_path, "rb").read()).hexdigest()
    print(f"artifact: {artifact_path}")
    print(f"artifact_sha256: {digest}")
    print(f"observations: {obs_path} ({study['observations_sha256']})")
    print(f"replay_exact: {study['replay']['exact']} ({study['replay']['matched']}/{study['replay']['total']})")
    print("learned:", json.dumps({k: v["preferred_topology"] for k, v in study["learned_preferences"].items()}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
