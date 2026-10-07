"""Stub API + static file server for the Residual Studio frontend.

SPEC NOTE (Track H, Swarm 8): the stub API MUST serve the M2 contract shape
(``WorkerContract`` / ``WorkerReceipt``, STUDIO-R9/R11) from local fixtures.
It is a development surface only; it MUST NOT be presented as the real swarm
runtime. All mutating endpoints are in-memory only (approvals reset on
restart). The server is stdlib-only so the Studio UI has no build step.

Endpoints:
    GET  /api/plan               requirement graph + plan metadata (STUDIO-R5/R7)
    GET  /api/contracts          worker contracts (STUDIO-R9 shape)
    GET  /api/swarm/status       swarm panel payload incl. metrics (STUDIO-R25/R33)
    GET  /api/evidence/receipts  worker receipts (STUDIO-R11 shape)
    GET  /api/workers/timeline   per-worker attempt timeline
    GET  /api/approvals          pending/decided approval items (HITL)
    POST /api/approvals/{id}     record an approve/reject decision
    GET  /*                      static UI from ./static

Launch:  python3 -m residual.studio_frontend.stub_server [--port 8787]
"""
from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .contracts import WorkerContract, WorkerReceipt

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
STATIC = HERE / "static"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


def load_fixtures(fixtures_dir: Path = FIXTURES) -> dict:
    """Load and validate fixtures against the stub contract shapes."""
    plan = json.loads((fixtures_dir / "plan.json").read_text())
    contracts = [
        WorkerContract.from_dict(c).to_dict()
        for c in json.loads((fixtures_dir / "contracts.json").read_text())
    ]
    receipts = [
        WorkerReceipt.from_dict(r).to_dict()
        for r in json.loads((fixtures_dir / "receipts.json").read_text())
    ]
    swarm = json.loads((fixtures_dir / "swarm.json").read_text())
    approvals = json.loads((fixtures_dir / "approvals.json").read_text())
    timeline = _build_timeline(receipts, swarm)
    return {
        "plan": plan,
        "contracts": contracts,
        "receipts": receipts,
        "swarm": swarm,
        "approvals": approvals,
        "timeline": timeline,
    }


def _build_timeline(receipts: list[dict], swarm: dict) -> list[dict]:
    """Derive per-worker attempt spans from receipts (STUDIO worker timeline)."""
    owner = {}
    for s in swarm.get("swarms", []):
        for w in s.get("workers", []):
            owner.setdefault(w.get("task_id"), w.get("id"))
    spans = []
    for r in receipts:
        spans.append({
            "task_id": r["task_id"],
            "attempt_id": r["attempt_id"],
            "worker_id": owner.get(r["task_id"], "unassigned"),
            "node_id": r["node_id"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "status": r["status"],
        })
    spans.sort(key=lambda s: (s["started_at"], s["task_id"]))
    return spans


class StudioStubHandler(BaseHTTPRequestHandler):
    state: dict = {}
    static_dir: Path = STATIC

    def log_message(self, fmt, *args):  # keep test output clean
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json({"error": "not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        routes = {
            "/api/plan": "plan",
            "/api/contracts": "contracts",
            "/api/swarm/status": "swarm",
            "/api/evidence/receipts": "receipts",
            "/api/workers/timeline": "timeline",
            "/api/approvals": "approvals",
        }
        if path in routes:
            self._send_json(self.state[routes[path]])
            return
        if path.startswith("/api/"):
            self._send_json({"error": "unknown endpoint"}, 404)
            return
        if path in ("/", ""):
            self._send_file(self.static_dir / "index.html")
            return
        candidate = (self.static_dir / path.lstrip("/")).resolve()
        if candidate.is_relative_to(self.static_dir.resolve()) and candidate.is_file():
            self._send_file(candidate)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/approvals/([A-Za-z0-9_.-]+)", path)
        if not match:
            self._send_json({"error": "unknown endpoint"}, 404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, 400)
            return
        decision = payload.get("decision")
        if decision not in ("approve", "reject"):
            self._send_json({"error": "decision must be 'approve' or 'reject'"}, 400)
            return
        for item in self.state["approvals"]:
            if item["approval_id"] == match.group(1):
                if item["status"] != "pending":
                    self._send_json({"error": "approval already decided"}, 409)
                    return
                item["status"] = "decided"
                item["decision"] = decision
                item["decided_by"] = str(payload.get("decided_by", "studio-operator"))
                item["note"] = payload.get("note")
                from datetime import datetime, timezone
                item["decided_at"] = datetime.now(timezone.utc).isoformat()
                self._send_json(item)
                return
        self._send_json({"error": "approval not found"}, 404)


def serve(port: int = 8787, fixtures_dir: Path = FIXTURES) -> ThreadingHTTPServer:
    state = load_fixtures(fixtures_dir)
    handler = type("BoundStudioStubHandler", (StudioStubHandler,), {"state": state})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Residual Studio stub server (dev surface)")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    args = parser.parse_args(argv)
    server = serve(args.port, args.fixtures)
    print(f"Residual Studio (stub) at http://127.0.0.1:{args.port}/ — Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
