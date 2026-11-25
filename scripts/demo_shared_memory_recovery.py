"""Offline stigmergic recovery example: real Station/Git/checks, no provider."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

# Support the documented direct-script invocation from an isolated checkout.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.core import ContractError
from residual.station.service import DEMO_FILES, Station, demo_spec


def run():
    with tempfile.TemporaryDirectory(prefix="residual-memory-demo-") as directory:
        original = Station(directory)
        pid = original.create(demo_spec(), demo=True)["project_id"]
        original.triage(pid)
        departed = original.prepare(pid, "worker-before-loss", "OPS-101")
        original.finish(departed, {"files": {"station/health.py": 'def status(services):\n    return "ready"\n'}})
        before = original.store.memory(pid, "OPS-101")
        failed = next(item for item in before["items"] if item["kind"] == "checks.completed")
        assert failed["negative"]

        # The fresh interpreter receives only the durable path and scoped IDs.
        cold = subprocess.run([sys.executable, "-m", "residual.station.memory", "--root", directory,
                               "--project", pid, "--task", "OPS-101"], cwd=ROOT,
                              check=True, capture_output=True, text=True)
        recovered = json.loads(cold.stdout)
        assert failed["id"] in {item["id"] for item in recovered["items"]}
        del original

        replacement = Station(directory)
        work = replacement.prepare(pid, "worker-after-loss", "OPS-101")
        inherited = work["packet"]["shared_memory"]
        assert failed["id"] in {item["id"] for item in inherited["items"]}
        try:
            replacement.finish(departed, {"files": {}})
        except ContractError:
            stale_lease_rejected = True
        else:
            raise AssertionError("departed worker retained execution authority")
        replacement.finish(work, {"files": DEMO_FILES["OPS-101"]})
        replacement.review(pid, "OPS-101")
        replacement.integrate(pid, "OPS-101")
        after = replacement.store.memory(pid, "OPS-101")
        assert any(item["id"] == failed["id"] and item["negative"] for item in after["items"])
        assert replacement.store.task(pid, "OPS-101")["state"] == "integrated"
        return {
            "schema": "residual.station.shared-memory-demo/1",
            "result": "PASS",
            "environment": {"os": platform.system(), "python": platform.python_version(),
                            "qualification_host": "scratch_only_not_DBOX_or_LEGION"},
            "scenario": "failed worker -> cold process -> replacement worker -> fresh checks/review/integration",
            "project_id": pid, "task_id": "OPS-101", "source_worker": "worker-before-loss",
            "replacement_worker": "worker-after-loss", "failed_evidence": failed,
            "cold_process_recovered_original_trace": True,
            "replacement_inherited_original_trace": True,
            "stale_lease_rejected": stale_lease_rejected,
            "negative_history_retained_after_success": True,
            "new_acceptance_state": "integrated",
            "provider_calls": 0,
            "limits": ["synthetic demonstration, not P5 operator-effort evidence",
                       "single local Station, not remote SC-MESH or multi-host qualification",
                       "retained bytes are required; complete storage loss is not recovered",
                       "no production host, activation, deployment or release"],
            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in [ROOT / "residual/station" / name for name in
                                           ("memory.py", "store.py", "service.py", "server.py")]},
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(run(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
