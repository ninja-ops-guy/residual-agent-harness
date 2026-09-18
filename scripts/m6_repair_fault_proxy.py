from __future__ import annotations

import argparse
import hashlib
import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class State:
    def __init__(self, model: str, upstream: str, events: Path, faults: int):
        self.model = model
        self.upstream = upstream.rstrip("/")
        self.events = events
        self.faults = faults
        self.injected = 0
        self.lock = threading.Lock()

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
    server_version = "ResidualRepairStressProxy/1"
    def log_message(self, *_args):
        pass

    @property
    def state(self) -> State:
        return self.server.state

    def _send(self, status: int, body: bytes, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _forward_bytes(self, raw: bytes):
        request = urllib.request.Request(self.state.upstream + self.path, data=raw,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.read(), response.status, response.headers.get_content_type()

    def do_GET(self):
        try:
            with urllib.request.urlopen(self.state.upstream + self.path, timeout=30) as response:
                self._send(response.status, response.read(), response.headers.get_content_type())
        except Exception as exc:
            self._send(502, json.dumps({"error": type(exc).__name__}).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if self.path != "/api/chat":
            try:
                body, status, ctype = self._forward_bytes(raw)
                return self._send(status, body, ctype)
            except Exception as exc:
                return self._send(502, json.dumps({"error": type(exc).__name__}).encode())

        try:
            packet = json.loads(raw)
            packet["model"] = self.state.model
            messages = packet.get("messages") or []
            system = messages[0].get("content", "") if messages else ""
            role = "reviewer" if "Review a candidate implementation" in system else "runner"
            task_id = None
            if len(messages) > 1:
                try:
                    user = json.loads(messages[1].get("content", "{}"))
                    task_id = user.get("task_id") or (user.get("task") or {}).get("id")
                except Exception:
                    pass
            body, status, ctype = self._forward_bytes(json.dumps(packet, separators=(",", ":")).encode())
            injected = False
            if status == 200 and role == "runner" and task_id == "REPAIR-001":
                with self.state.lock:
                    should = self.state.injected < self.state.faults
                    if should:
                        self.state.injected += 1
                        number = self.state.injected
                    else:
                        number = self.state.injected
                if should:
                    data = json.loads(body)
                    original = ((data.get("message") or {}).get("content") or "")
                    proposal = {"files": {"counter.py": "def increment(value):\n    return (\n"}}
                    data.setdefault("message", {})["content"] = json.dumps(proposal, separators=(",", ":"))
                    body = json.dumps(data, separators=(",", ":")).encode()
                    injected = True
                    self.state.record({
                        "event": "fault_injected",
                        "fault_number": number,
                        "task_id": task_id,
                        "role": role,
                        "original_content_sha256": hashlib.sha256(original.encode()).hexdigest(),
                        "fault": "deterministic SyntaxError in counter.py",
                    })
            self.state.record({
                "event": "route",
                "task_id": task_id,
                "role": role,
                "model": self.state.model,
                "fault_injected": injected,
                "status": status,
            })
            self._send(status, body, ctype)
        except Exception as exc:
            self.state.record({"event": "proxy_error", "error": type(exc).__name__})
            self._send(500, json.dumps({"error": type(exc).__name__}).encode())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--listen", default="127.0.0.1")
    p.add_argument("--port", type=int, default=11436)
    p.add_argument("--upstream", default="http://127.0.0.1:11434")
    p.add_argument("--model", required=True)
    p.add_argument("--faults", type=int, default=2)
    p.add_argument("--events", default="/tmp/residual-repair-proxy-events.jsonl")
    a = p.parse_args()
    server = Proxy((a.listen, a.port), State(a.model, a.upstream, Path(a.events), a.faults))
    print(f"repair stress proxy listening on {a.listen}:{a.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
