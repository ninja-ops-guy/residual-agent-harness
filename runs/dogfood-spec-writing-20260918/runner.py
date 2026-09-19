#!/usr/bin/env python3
"""Dogfood: use an installed RESIDUAL Station to write one spec (Wave A ledger spec).

Attempt A: no provider configured -> honest BLOCKED/UNKNOWN evidence.
Attempt B: scripted local openai-compatible provider supplies the file bytes;
           Station's mission machinery (triage/claim/verify/review/integrate/export)
           executes for real. Fixture substitution is explicitly declared.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys
sys.path.insert(0, str(Path.home() / "dogfood"))

from residual.station.models import save_settings
from residual.station.service import Station

OUT = Path.home() / "dogfood-work"
WORK = OUT / "station-data"

SPEC_TEXT = Path("/mnt/agents/output/wave-a/a1/ledger-schema.md").read_text(encoding="utf-8")
SPEC_TEXT += """

## Appendix A — Normative summary (dogfood mission anchor)

- The ledger enforces the **exactly-one-terminal** invariant: every attempt reaches at most
  one terminal state, enforced by a **CAS** state transition (`terminal_state IS NULL` predicate
  with `rowcount == 1` verification) plus storage-level uniqueness — never by a watchdog.
- The single writer-service follows **commit-before-ack**: an acknowledgement is returned only
  after `COMMIT` returns; a client crash between write and ack retries with the same `event_id`
  and resolves as a duplicate.
"""
TARGET = "docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md"

MISSION = """# Dogfood mission: author the control-plane ledger spec

Write one specification document derived from the Wave A control-plane design.

```json
{
  "schema_version": 1,
  "name": "Dogfood Ledger Spec",
  "goal": "Produce docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md, the durable control-plane ledger specification.",
  "tasks": [
    {
      "id": "SPEC-1",
      "title": "Write the ledger specification",
      "instruction": "Write docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md. It must specify the durable ledger schema, the attempt state machine, and the exactly-one-terminal invariant enforced by CAS plus storage uniqueness, with a writer-service commit-before-ack protocol.",
      "files": ["docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md"],
      "context": [],
      "depends_on": [],
      "route": "local",
      "checks": [
        {"kind": "exists", "path": "docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md"},
        {"kind": "contains", "path": "docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md", "text": "exactly-one-terminal"},
        {"kind": "contains", "path": "docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md", "text": "CAS"},
        {"kind": "contains", "path": "docs/specs/SPEC-CONTROL-PLANE-LEDGER-001.md", "text": "commit-before-ack"}
      ]
    }
  ]
}
```
"""


class ScriptedProvider(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size))
        messages = body.get("messages") or []
        system = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        if "Implement the assigned software specification" in system:
            content = json.dumps({"files": {TARGET: SPEC_TEXT}})
        else:
            content = json.dumps({"approved": True, "findings": []})
        payload = json.dumps({
            "id": "dogfood-provider", "model": body.get("model", "scripted-local"),
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def snap(station, pid):
    return {
        "task": station.store.task(pid, "SPEC-1"),
        "jobs": station.store.jobs(),
    }


def main():
    import shutil
    if WORK.exists():
        shutil.rmtree(WORK)
    report = {"head": None, "attempt_a": None, "attempt_b": None}
    import subprocess
    report["head"] = subprocess.run(
        ["git", "-C", str(Path.home() / "dogfood"), "rev-parse", "HEAD"],
        capture_output=True, text=True).stdout.strip()

    station = Station(WORK)
    pid = station.create(MISSION, source=str(OUT / "source-repo"), allow_cloud=False, commands=False)["project_id"]
    station.triage(pid)
    state = station.store.task(pid, "SPEC-1")["state"]

    # ---- Attempt A: no provider configured (real local route) ----
    t0 = time.monotonic()
    run = station.run_one(pid, "SPEC-1", owner="dogfood-a")
    a_state = station.store.task(pid, "SPEC-1")["state"]
    report["attempt_a"] = {
        "label": "real local model route, no provider configured",
        "run_returned": run,
        "task_state": a_state,
        "elapsed_s": round(time.monotonic() - t0, 3),
    }

    # ---- Attempt B: scripted local provider, real mission machinery ----
    server = ThreadingHTTPServer(("127.0.0.1", 0), ScriptedProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        save_settings(station.store, {
            "local": {"kind": "openai_compatible", "model": "scripted-local",
                      "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                      "output_token_field": "max_tokens"},
            "local_credentials": {"api_key": "DOGFOOD-NOT-A-SECRET"},
            "review_placement": "local",
        })
        t0 = time.monotonic()
        run_b = station.run_one(pid, "SPEC-1", owner="dogfood-b")
        state_b = station.store.task(pid, "SPEC-1")["state"]
        review = station.review(pid, "SPEC-1")
        state_r = station.store.task(pid, "SPEC-1")["state"]
        integrated = station.integrate(pid, "SPEC-1")
        state_i = station.store.task(pid, "SPEC-1")["state"]
        release = station.export(pid)
        meta, blob = station.store.artifact(release["id"])
        task = station.store.task(pid, "SPEC-1")
        obs = station.store.observation_export(pid)
        report["attempt_b"] = {
            "label": "scripted local openai-compatible provider; real triage/claim/verify/review/integrate/export",
            "run_returned_state": state_b,
            "review": review, "review_state": state_r,
            "integrated_head": integrated["head_commit"], "final_state": state_i,
            "release_id": release["id"], "release_sha256": hashlib.sha256(blob).hexdigest(),
            "release_size": len(blob),
            "verification_receipt_hash": (task.get("verification_receipt") or {}).get("receipt", {}).get("receipt_hash"),
            "metrics": station.metrics(pid),
            "observation_export_sha256": hashlib.sha256(obs.encode()).hexdigest(),
            "elapsed_s": round(time.monotonic() - t0, 3),
        }
    finally:
        server.shutdown()
        server.server_close()

    (OUT / "dogfood-result.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True, default=str)[:4000])


if __name__ == "__main__":
    main()
