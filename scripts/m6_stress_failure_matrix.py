from __future__ import annotations

import argparse
import json
import threading
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from residual.station.models import save_settings
from residual.station.service import Station


MANIFEST = {
    "schema_version": 1,
    "name": "Deterministic Failure Matrix",
    "goal": "Implement calculator.py with add(a,b) returning a+b.",
    "tasks": [{
        "id": "FAIL-001",
        "title": "Implement addition",
        "instruction": "Create calculator.py with add(a, b) returning a + b. Modify only calculator.py.",
        "files": ["calculator.py"],
        "context": [],
        "depends_on": [],
        "route": "local",
        "checks": [
            {"kind": "python_compile", "path": "calculator.py"},
            {"kind": "command", "argv": ["{python}", "-c",
             "from calculator import add; assert add(2,3)==5; assert add(-2,5)==3"], "timeout": 30},
        ],
    }],
}


class State:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.runner_calls = 0
        self.reviewer_calls = 0
        self.http_failures = 0
        self.records = []
        self.lock = threading.Lock()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, state: State):
        self.state = state
        super().__init__(("127.0.0.1", 0), Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_json(self, status: int, value: dict):
        raw = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_json(404, {"error": "not_found"})
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        packet = json.loads(raw)
        messages = packet.get("messages") or []
        system = messages[0].get("content", "") if messages else ""
        role = "reviewer" if "Review a candidate implementation" in system else "runner"
        s = self.server.state

        with s.lock:
            if role == "runner":
                s.runner_calls += 1
                call_no = s.runner_calls
            else:
                s.reviewer_calls += 1
                call_no = s.reviewer_calls

        if s.scenario == "transient_500" and role == "runner" and call_no == 1:
            with s.lock:
                s.http_failures += 1
                s.records.append({"role": role, "call": call_no, "status": 500})
            return self.send_json(500, {"error": "transient_failure"})

        if role == "runner":
            if s.scenario == "malformed_json":
                content = "{ definitely not json"
            else:
                content = json.dumps({"files": {"calculator.py": "def add(a, b):\n    return a + b\n"}}, separators=(",", ":"))
        else:
            if s.scenario == "invalid_reviewer":
                content = json.dumps({"approved": "yes", "findings": []}, separators=(",", ":"))
            elif s.scenario == "deny_then_approve" and call_no == 1:
                content = json.dumps({"approved": False, "findings": ["semantic review requests one repair"]}, separators=(",", ":"))
            else:
                content = json.dumps({"approved": True, "findings": []}, separators=(",", ":"))

        response = {
            "model": "deterministic:test",
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": "stop",
        }
        if s.scenario != "missing_usage":
            response.update(prompt_eval_count=100, eval_count=20)

        with s.lock:
            s.records.append({"role": role, "call": call_no, "status": 200, "content": content})
        self.send_json(200, response)


def task_view(t):
    return {k: t.get(k) for k in (
        "id","state","attempt","findings","checks_result","review",
        "head_commit","checks_hash","verification_receipt"
    )}


def run_scenario(name: str):
    state = State(name)
    server = Server(state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="residual-failure-matrix-") as root:
            station = Station(root)
            save_settings(station.store, {
                "local": {"kind": "ollama", "model": "deterministic:test",
                          "base_url": f"http://127.0.0.1:{server.server_address[1]}",
                          "output_token_field": "max_tokens"},
                "review_placement": "local",
                "workers": 1,
                "max_output_tokens": 768,
                "batch_max_passes": 3,
                "batch_token_budget": 100000,
                "batch_wall_clock_s": 600,
            })
            spec = "# Deterministic failure matrix\n\n```json\n" + json.dumps(MANIFEST, indent=2) + "\n```\n"
            pid = station.create(spec, commands=True)["project_id"]
            result = station.batch(pid)
            project = station.store.project(pid)
            task = project["tasks"][0]
            ev = station.store.events(pid, 0, 100000)
            return {
                "scenario": name,
                "batch": result,
                "metrics": station.metrics(pid),
                "task": task_view(task),
                "provider_records": list(state.records),
                "runner_calls": state.runner_calls,
                "reviewer_calls": state.reviewer_calls,
                "http_failures": state.http_failures,
                "events": ev,
                "integration_events": sum(1 for e in ev if e["event_type"] == "integration.completed"),
                "usage_events": [e["data"] for e in ev if e["event_type"] == "usage.recorded"],
            }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="runs/m6-stress-failure-matrix/evidence.json")
    a = p.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    names = ["malformed_json", "transient_500", "missing_usage", "invalid_reviewer", "deny_then_approve"]
    data = {
        "schema_version": 1,
        "campaign": "M6-STRESS-C",
        "baseline_sha": "699e2869e294fe157b4bfd73a272057683a2f7e0",
        "experiments": {name: run_scenario(name) for name in names},
    }
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("STRESS_FAILURE_MATRIX_EVIDENCE=" + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
