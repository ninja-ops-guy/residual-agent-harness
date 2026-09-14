from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from common import EXPECTED_OUTPUT_COMMIT, INPUT_COMMIT, create_fixture  # noqa: E402
from residual.factory.evidence_bus import StationIdentity  # noqa: E402


def model_digest(base_url: str, model: str) -> str:
    req = urllib.request.Request(base_url.rstrip("/") + "/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=10) as response:
        payload = json.load(response)
    for entry in payload.get("models", []):
        if entry.get("name") == model or entry.get("model") == model:
            digest = entry.get("digest")
            if isinstance(digest, str) and digest:
                return digest
    raise SystemExit(f"model not found in Ollama: {model}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze FB001 against one installed Ollama model revision")
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--output", default=str(HERE / "workload.local.json"))
    parser.add_argument("--station-key", default=str(HERE / "station.local.pem"))
    args = parser.parse_args()

    import tempfile
    with tempfile.TemporaryDirectory(prefix="residual-fb001-check-") as td:
        input_commit, expected_commit = create_fixture(Path(td) / "repo", known_good=True)
    if (input_commit, expected_commit) != (INPUT_COMMIT, EXPECTED_OUTPUT_COMMIT):
        raise SystemExit("FB001 deterministic fixture check failed")

    digest = model_digest(args.base_url, args.model)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    runner = HERE / "run_live.py"
    requirements = [
        "REQ-NORMALIZE", "REQ-RETRY", "REQ-BACKOFF",
        "REQ-HEALTH", "REQ-LABELS", "REQ-TIMEOUT",
    ]
    task_ids = [
        "normalize_rule", "retry_statuses", "backoff_seconds",
        "health_thresholds", "label_order", "timeout_budget_seconds",
    ]
    workload = {
        "schema_version": "factory-evaluation-v1",
        "workload_id": "fb001-service-policy-parallelism",
        "requirements": requirements,
        "tasks": [
            {
                "task_id": task_id,
                "requirement_ids": [requirement],
                "depends_on": [],
                "acceptance": [f"exact:{task_id}"],
            }
            for task_id, requirement in zip(task_ids, requirements)
        ],
        "input_commit": INPUT_COMMIT,
        "expected_output_commit": EXPECTED_OUTPUT_COMMIT,
        "engine": {
            "name": f"ollama:{args.model}",
            "version": digest,
            "temperature": 0,
            "seed": 7,
        },
        "driver_argv": [
            sys.executable,
            str(runner),
            "--config", "{config}",
            "--run", "{run}",
            "--workload", "{workload}",
            "--output", "{output}",
            "--model", args.model,
            "--model-version", digest,
            "--base-url", args.base_url,
        ],
    }
    output.write_text(json.dumps(workload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    key_path = Path(args.station_key).resolve()
    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        StationIdentity.generate().save_private(key_path)

    print(json.dumps({
        "status": "frozen",
        "workload": str(output),
        "station_key": str(key_path),
        "engine_name": workload["engine"]["name"],
        "engine_version": digest,
        "input_commit": INPUT_COMMIT,
        "expected_output_commit": EXPECTED_OUTPUT_COMMIT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
