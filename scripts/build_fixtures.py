"""Reproduce the shipped incident files from the controller workload generator."""
import json
from dataclasses import asdict
from pathlib import Path

from residual.demo import make_case


def main():
    root = Path(__file__).resolve().parents[1] / "examples" / "incident"
    root.mkdir(parents=True, exist_ok=True)
    task = make_case()
    artifacts = []
    for a in task.artifacts.values():
        name = a.id + (".json" if a.id == "actions" else ".log")
        (root / name).write_text(a.text, encoding="utf-8")
        artifacts.append({"id": a.id, "path": name, "cloud": a.cloud})
    data = {"id": task.id, "goal": task.goal, "artifacts": artifacts,
            "obligations": [asdict(o) for o in task.obligations]}
    (root / "task.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
