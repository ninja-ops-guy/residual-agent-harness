from __future__ import annotations

import argparse
import io
import json
import threading
import time
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station


MANIFEST = {
    "schema_version": 1,
    "name": "Deterministic Control Ordering Probe",
    "goal": "Implement a tiny calculator through the normal RESIDUAL Station pipeline.",
    "tasks": [{
        "id": "CTRL-001",
        "title": "Implement addition",
        "instruction": "Create calculator.py with add(a, b) returning a + b. Modify only calculator.py.",
        "files": ["calculator.py"],
        "context": [],
        "depends_on": [],
        "route": "local",
        "checks": [
            {"kind": "python_compile", "path": "calculator.py"},
            {"kind": "command", "argv": ["{python}", "-c",
                "from calculator import add; assert add(2,3)==5; assert add(-2,5)==3; assert add(2.5,.5)==3.0"], "timeout": 30},
        ],
    }],
}


class DeterministicState:
    def __init__(self, *, delay_s: float = 0.0, contradictory_review: bool = False):
        self.delay_s = delay_s
        self.contradictory_review = contradictory_review
        self.calls = []
        self.lock = threading.Lock()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, state: DeterministicState):
        self.state = state
        super().__init__(("127.0.0.1", 0), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, status: int, payload: dict):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/tags":
            return self._send(200, {"models": [{"name": "deterministic:test"}]})
        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/chat":
            return self._send(404, {"error": "not_found"})
        n = int(self.headers.get("Content-Length", "0"))
        packet = json.loads(self.rfile.read(n))
        messages = packet.get("messages") or []
        system = messages[0].get("content", "") if messages else ""
        role = "reviewer" if "Review a candidate implementation" in system else "runner"
        if self.server.state.delay_s:
            time.sleep(self.server.state.delay_s)
        if role == "runner":
            content = json.dumps({"files": {"calculator.py": "def add(a, b):\n    return a + b\n"}}, separators=(",", ":"))
        else:
            findings = ["candidate has a serious semantic defect"] if self.server.state.contradictory_review else []
            content = json.dumps({"approved": True, "findings": findings}, separators=(",", ":"))
        with self.server.state.lock:
            self.server.state.calls.append({
                "role": role,
                "model": packet.get("model"),
                "format_supplied": "format" in packet,
                "delay_s": self.server.state.delay_s,
                "response": json.loads(content),
            })
        self._send(200, {
            "model": packet.get("model") or "deterministic:test",
            "created_at": "2026-09-18T00:00:00Z",
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 100,
            "eval_count": 20,
        })


def task_view(task):
    return {k: task.get(k) for k in (
        "id","state","attempt","findings","checks_result","review",
        "head_commit","base_commit","checks_hash","verification_receipt"
    )}


def run_case(name: str, *, token_budget: int, wall_budget: int, delay_s: float = 0.0, contradictory_review: bool = False):
    state = DeterministicState(delay_s=delay_s, contradictory_review=contradictory_review)
    server = Server(state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="residual-deterministic-control-") as root:
            station = Station(root)
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            save_settings(station.store, {
                "local": {"kind": "ollama", "model": "deterministic:test", "base_url": base_url, "output_token_field": "max_tokens"},
                "review_placement": "local",
                "workers": 1,
                "max_output_tokens": 768,
                "batch_max_passes": 3,
                "batch_token_budget": token_budget,
                "batch_wall_clock_s": wall_budget,
            })
            spec = "# Deterministic control ordering probe\n\n```json\n" + json.dumps(MANIFEST, indent=2) + "\n```\n"
            pid = station.create(spec, commands=True)["project_id"]
            batch = station.batch(pid)
            project = station.store.project(pid)
            export = {"attempted": False, "succeeded": False, "error": None, "files": []}
            if all(t["state"] == "integrated" for t in project["tasks"]):
                export["attempted"] = True
                try:
                    art = station.export(pid)
                    _, raw = station.store.artifact(art["id"])
                    with zipfile.ZipFile(io.BytesIO(raw)) as z:
                        export["files"] = sorted(z.namelist())
                    export["succeeded"] = True
                    export["artifact_id"] = art["id"]
                except Exception as exc:
                    export["error"] = f"{type(exc).__name__}: {exc}"
            ev = station.store.events(pid, 0, 100000)
            task = station.store.project(pid)["tasks"][0]
            return {
                "name": name,
                "settings": {"token_budget": token_budget, "wall_clock_s": wall_budget, "provider_delay_s": delay_s},
                "batch": batch,
                "metrics": station.metrics(pid),
                "task": task_view(task),
                "provider_calls": list(state.calls),
                "events": ev,
                "export_after_control": export,
                "findings": {
                    "aborted_with_integration": batch["control"]["outcome"] == "aborted" and batch["integrated"] > 0,
                    "export_succeeded_after_abort": batch["control"]["outcome"] == "aborted" and export["succeeded"],
                    "approved_with_negative_findings": bool(task.get("review", {}).get("approved") is True and task.get("review", {}).get("findings")),
                },
            }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="runs/m6-stress-deterministic/evidence.json")
    a = p.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "campaign": "M6-STRESS-B",
        "baseline_sha": "699e2869e294fe157b4bfd73a272057683a2f7e0",
        "experiments": {
            "STRESS-B1-token-ordering": run_case("STRESS-B1-token-ordering", token_budget=1, wall_budget=600),
            "STRESS-B2-wall-ordering": run_case("STRESS-B2-wall-ordering", token_budget=100000, wall_budget=1, delay_s=1.1),
            "STRESS-B3-review-consistency": run_case("STRESS-B3-review-consistency", token_budget=100000, wall_budget=600, contradictory_review=True),
        },
    }
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("STRESS_DETERMINISTIC_EVIDENCE=" + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
