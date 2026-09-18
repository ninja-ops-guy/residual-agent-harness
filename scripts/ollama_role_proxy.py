from __future__ import annotations

import argparse
import hashlib
import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class State:
    def __init__(self, runner_model: str, reviewer_model: str, upstream: str, events: Path):
        self.runner_model = runner_model
        self.reviewer_model = reviewer_model
        self.upstream = upstream.rstrip("/")
        self.events = events
        self.lock = threading.Lock()
        self.injected = False

    def record(self, event: dict) -> None:
        with self.lock:
            self.events.parent.mkdir(parents=True, exist_ok=True)
            with self.events.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, sort_keys=True) + "\n")


class Proxy(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, state: State):
        self.state = state
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "ResidualOllamaRoleProxy/1"

    def log_message(self, *_args):
        pass

    @property
    def state(self) -> State:
        return self.server.state

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            with urllib.request.urlopen(self.state.upstream + self.path, timeout=30) as response:
                self._send(response.status, response.read(), response.headers.get_content_type())
        except Exception as exc:
            self._send(502, json.dumps({"error": type(exc).__name__}).encode())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if self.path != "/api/chat":
            return self._forward(raw)

        try:
            packet = json.loads(raw)
            messages = packet.get("messages") or []
            system = messages[0].get("content", "") if messages else ""
            role = "reviewer" if "Review a candidate implementation" in system else "runner"
            task_id = None
            if len(messages) > 1:
                try:
                    user_packet = json.loads(messages[1].get("content", "{}"))
                    task_id = user_packet.get("task_id") or (user_packet.get("task") or {}).get("id")
                except Exception:
                    task_id = None

            routed_model = self.state.reviewer_model if role == "reviewer" else self.state.runner_model
            packet["model"] = routed_model
            upstream_body = json.dumps(packet, separators=(",", ":")).encode()
            response_body, status, content_type = self._forward_bytes(upstream_body)

            injected = False
            if status == 200 and role == "runner" and task_id == "CORE-001":
                with self.state.lock:
                    should_inject = not self.state.injected
                    if should_inject:
                        self.state.injected = True
                if should_inject:
                    data = json.loads(response_body)
                    content = (data.get("message") or {}).get("content", "")
                    try:
                        proposal = json.loads(content)
                    except Exception:
                        proposal = {"files": {}}
                    original = str((proposal.get("files") or {}).get("math_core.py", ""))
                    proposal["files"] = {
                        "math_core.py": "def clamp(value, low, high):\n    return (\n"
                    }
                    data["message"]["content"] = json.dumps(proposal, separators=(",", ":"))
                    response_body = json.dumps(data, separators=(",", ":")).encode()
                    injected = True
                    self.state.record({
                        "event": "fault_injected",
                        "task_id": task_id,
                        "role": role,
                        "routed_model": routed_model,
                        "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
                        "fault": "replace math_core.py with deterministic SyntaxError candidate"
                    })

            self.state.record({
                "event": "route",
                "task_id": task_id,
                "role": role,
                "routed_model": routed_model,
                "fault_injected": injected,
                "status": status
            })
            self._send(status, response_body, content_type)
        except Exception as exc:
            self.state.record({"event": "proxy_error", "error": type(exc).__name__})
            self._send(500, json.dumps({"error": type(exc).__name__}).encode())

    def _forward(self, raw: bytes) -> None:
        body, status, content_type = self._forward_bytes(raw)
        self._send(status, body, content_type)

    def _forward_bytes(self, raw: bytes) -> tuple[bytes, int, str]:
        request = urllib.request.Request(
            self.state.upstream + self.path,
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), response.status, response.headers.get_content_type()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11434)
    parser.add_argument("--upstream", default="http://127.0.0.1:11435")
    parser.add_argument("--runner-model", required=True)
    parser.add_argument("--reviewer-model", required=True)
    parser.add_argument("--events", default="/tmp/residual-role-proxy-events.jsonl")
    args = parser.parse_args()

    state = State(args.runner_model, args.reviewer_model, args.upstream, Path(args.events))
    server = Proxy((args.listen, args.port), state)
    print(f"role proxy listening on http://{args.listen}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
