from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from residual.core import canonical
from residual.station.models import save_settings
from residual.station.service import Station


SPEC = """# Simple calculator mission

Implement the smallest possible calculator module and prove it works with deterministic checks.

```json
{
  "schema_version": 1,
  "name": "Simple Calculator Smoke Mission",
  "goal": "Create a tiny calculator module with a correct add(a, b) function.",
  "tasks": [
    {
      "id": "CALC-001",
      "title": "Implement addition",
      "instruction": "Create calculator.py with a pure add(a, b) function that returns a + b. Keep the implementation minimal.",
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
            "from calculator import add; assert add(2, 3) == 5; assert add(-7, 2) == -5; assert add(0, 0) == 0"
          ]
        }
      ]
    }
  ]
}
```
"""


class FakeOllama(BaseHTTPRequestHandler):
    calls: list[dict] = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        packet = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.__class__.calls.append(packet)
        system = packet["messages"][0]["content"]

        if "Review a candidate implementation" in system:
            content = canonical({"approved": True, "findings": []})
        else:
            content = canonical({
                "files": {
                    "calculator.py": (
                        '"""Tiny calculator generated for the RESIDUAL smoke mission."""\\n\\n'
                        "def add(a, b):\\n"
                        "    return a + b\\n"
                    )
                }
            })

        body = canonical({
            "model": "residual-simple-smoke",
            "message": {"role": "assistant", "content": content},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 64,
            "eval_count": 24
        }).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class SimpleMissionSmoke(unittest.TestCase):
    def test_live_simple_spec_executes_end_to_end(self):
        FakeOllama.calls = []
        http = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()

        try:
            with tempfile.TemporaryDirectory() as root:
                station = Station(root)
                save_settings(station.store, {
                    "local": {
                        "kind": "ollama",
                        "model": "residual-simple-smoke",
                        "base_url": f"http://127.0.0.1:{http.server_port}",
                        "output_token_field": "max_tokens"
                    },
                    "review_placement": "local",
                    "workers": 1
                })

                pid = station.create(SPEC, commands=True)["project_id"]
                result = station.batch(pid)
                project = station.store.project(pid)
                task = project["tasks"][0]
                diagnostic = {
                    "result": result,
                    "task": {
                        "state": task["state"],
                        "attempt": task["attempt"],
                        "findings": task["findings"],
                        "checks_result": task["checks_result"],
                        "review": task.get("review"),
                        "head_commit": task.get("head_commit"),
                    },
                    "provider_call_count": len(FakeOllama.calls),
                    "events": [
                        {
                            "type": event["event_type"],
                            "task_id": event["task_id"],
                            "data": event["data"],
                        }
                        for event in station.store.events(pid, 0, 500)
                        if event["event_type"] in {
                            "task.transition", "task.finding", "usage.recorded",
                            "checks.completed", "review.completed", "integration.completed", "project.note"
                        }
                    ],
                }
                print("SIMPLE_MISSION_DIAGNOSTIC=" + canonical(diagnostic))

                self.assertEqual(result["integrated"], 1)
                self.assertEqual(result["total"], 1)
                self.assertEqual(task["state"], "integrated")
                self.assertTrue(task["review"]["approved"])
                self.assertEqual(task["review"]["head_commit"], task["head_commit"])
                self.assertTrue(all(check["passed"] for check in task["checks_result"]))
                self.assertTrue(task.get("verification_receipt"))
                self.assertEqual(len(FakeOllama.calls), 2)

                roles = [
                    "reviewer" if "Review a candidate implementation" in call["messages"][0]["content"] else "runner"
                    for call in FakeOllama.calls
                ]
                self.assertEqual(roles, ["runner", "reviewer"])

                artifact = station.export(pid)
                _, release = station.store.artifact(artifact["id"])
                with zipfile.ZipFile(io.BytesIO(release)) as bundle:
                    self.assertIn("calculator.py", bundle.namelist())
                    generated = bundle.read("calculator.py").decode("utf-8")
                self.assertIn("def add(a, b):", generated)
                self.assertIn("return a + b", generated)

                evidence = {
                    "mission": project["name"],
                    "goal": project["goal"],
                    "project_id": pid,
                    "batch": result,
                    "task_state": task["state"],
                    "checks": [
                        {"kind": check["kind"], "passed": check["passed"], "detail": check["detail"]}
                        for check in task["checks_result"]
                    ],
                    "review_approved": task["review"]["approved"],
                    "provider_calls": roles,
                    "reported_calls": station.metrics(pid)["calls"],
                    "reported_tokens": station.metrics(pid)["reported_tokens"],
                    "export_contains": ["calculator.py"],
                    "generated_source": generated,
                    "head_commit": task["head_commit"],
                    "verification_receipt": bool(task.get("verification_receipt")),
                }
                print("SIMPLE_MISSION_EVIDENCE=" + canonical(evidence))
        finally:
            http.shutdown()
            http.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
