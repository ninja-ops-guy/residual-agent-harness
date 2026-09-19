from __future__ import annotations

import argparse
import io
import json
import tempfile
import zipfile
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station


SPEC = """# Real-model simple mission

Implement a tiny calculator module from this behavioral specification. The implementation is not prescribed.

```json
{
  "schema_version": 1,
  "name": "Real Model Calculator Mission",
  "goal": "Create a small Python calculator module that correctly implements addition.",
  "tasks": [
    {
      "id": "CALC-REAL-001",
      "title": "Implement addition",
      "instruction": "Create calculator.py. It must expose add(a, b) and return the arithmetic sum of its two inputs. Keep the implementation small and readable. Do not add unrelated files.",
      "files": ["calculator.py"],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {"kind": "python_compile", "path": "calculator.py"},
        {
          "kind": "command",
          "argv": [
            "{python}",
            "-c",
            "from calculator import add; assert add(2, 3) == 5; assert add(-7, 2) == -5; assert add(0, 0) == 0; assert add(2.5, 0.5) == 3.0"
          ],
          "timeout": 30
        }
      ]
    }
  ]
}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-coder:1.5b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--output", default="runs/real-model-mission/evidence.json")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as root:
        station = Station(root)
        save_settings(station.store, {
            "local": {
                "kind": "ollama",
                "model": args.model,
                "base_url": args.base_url,
                "output_token_field": "max_tokens"
            },
            "review_placement": "local",
            "workers": 1,
            "max_output_tokens": 768,
            "batch_max_passes": 3,
            "batch_token_budget": 20000,
            "batch_wall_clock_s": 600
        })

        pid = station.create(SPEC, commands=True)["project_id"]
        result = station.batch(pid)
        project = station.store.project(pid)
        task = project["tasks"][0]
        metrics = station.metrics(pid)

        release_files = []
        generated_source = None
        export_error = None
        if task["state"] == "integrated":
            try:
                artifact = station.export(pid)
                _, release = station.store.artifact(artifact["id"])
                with zipfile.ZipFile(io.BytesIO(release)) as bundle:
                    release_files = sorted(bundle.namelist())
                    if "calculator.py" in release_files:
                        generated_source = bundle.read("calculator.py").decode("utf-8")
            except Exception as exc:
                export_error = f"{type(exc).__name__}: {exc}"

        evidence = {
            "schema_version": 1,
            "mission": project["name"],
            "goal": project["goal"],
            "provider": {"kind": "ollama", "model": args.model, "base_url": args.base_url},
            "project_id": pid,
            "batch": result,
            "task": {
                "id": task["id"],
                "state": task["state"],
                "attempt": task["attempt"],
                "findings": task["findings"],
                "checks_result": task["checks_result"],
                "review": task.get("review"),
                "head_commit": task.get("head_commit"),
                "verification_receipt": task.get("verification_receipt")
            },
            "metrics": metrics,
            "release_files": release_files,
            "generated_source": generated_source,
            "export_error": export_error,
            "events": [
                {
                    "seq": event["seq"],
                    "type": event["event_type"],
                    "task_id": event["task_id"],
                    "actor": event["actor"],
                    "data": event["data"]
                }
                for event in station.store.events(pid, 0, 1000)
                if event["event_type"] in {
                    "task.transition", "task.finding", "usage.recorded",
                    "checks.completed", "review.completed", "integration.completed",
                    "project.note", "release.exported"
                }
            ],
        }

        out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("REAL_MODEL_MISSION_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))

        success = (
            result["integrated"] == 1
            and task["state"] == "integrated"
            and all(check.get("passed") is True for check in task["checks_result"])
            and task.get("review", {}).get("approved") is True
            and bool(task.get("verification_receipt"))
            and generated_source is not None
            and export_error is None
        )
        return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
