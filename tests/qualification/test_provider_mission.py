from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts.qualification_provider_mission import run_mission


class _Provider(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size))
        messages = body.get("messages") or []
        system = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        if "Implement the assigned software specification" in system:
            content = json.dumps({"files": {"app.py": "def add(a, b):\n    return a + b\n"}})
        elif "Review the candidate" in system or "independent review" in system.lower():
            content = json.dumps({"approved": True, "findings": []})
        else:
            # RESPONSE_SCHEMA requests prepend a schema system message. Fall back
            # to the semantic shape inferred from the requested response schema.
            schema_text = system.lower()
            if '"approved"' in schema_text:
                content = json.dumps({"approved": True, "findings": []})
            else:
                content = json.dumps({"files": {"app.py": "def add(a, b):\n    return a + b\n"}})
        payload = json.dumps({
            "id": "provider-mission-test",
            "model": body.get("model", "qa-model"),
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def test_full_provider_mission_qualifier_exercises_implementation_review_and_release(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = run_mission(
            provider="openai_compatible",
            model="qa-model",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            root=tmp_path / "station",
        )
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)

    assert report["result"] == "PASS", report
    assert report["authority_path"] == "run_controlled_batch"
    assert report["run_control"]["outcome"] == "success"
    assert report["run_control"]["project_head"] == report["integrated_head"]
    assert report["metrics"]["calls"] == 2
    assert report["release"]["size"] > 0
    assert len(report["verification_receipt_hash"]) == 64
