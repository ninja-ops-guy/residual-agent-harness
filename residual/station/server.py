"""Dependency-free local web application. State-changing endpoints require a session token."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from .contracts import bounded, parse_spec
from .models import model_call, public_settings, save_settings, credentials_for
from residual.modular import normalize_profile, make_adapter
from ai_providers import ProviderError as ModularError
from .service import Station, demo_spec

STATIC = Path(__file__).parent / "static"


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, station):
        self.station = station
        super().__init__(address, Handler)
        self.allowed_hosts = {f"localhost:{self.server_port}", f"127.0.0.1:{self.server_port}"}
        self.allowed_hosts.update(h.strip() for h in os.environ.get("RESIDUAL_ALLOWED_HOSTS", "").split(",") if h.strip())


class Handler(BaseHTTPRequestHandler):
    server_version = "ResidualStation/0.3"

    def log_message(self, *args):
        # Request URLs can carry identifiers. Routine HTTP access logging is deliberately quiet.
        pass

    @property
    def station(self):
        return self.server.station

    def headers_common(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    def respond(self, value, status=200, content_type="application/json; charset=utf-8", filename=None):
        data = canonical(value).encode() if content_type.startswith("application/json") else (value.encode() if isinstance(value, str) else value)
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            clean = "".join(c for c in filename if c.isalnum() or c in "._-")[:150]
            self.send_header("Content-Disposition", f'attachment; filename="{clean}"')
        self.end_headers()
        self.wfile.write(data)

    def check_host(self):
        if self.headers.get("Host", "") not in self.server.allowed_hosts:
            raise PermissionError("Host is not allowed")
        origin = self.headers.get("Origin")
        if origin:
            url = urllib.parse.urlsplit(origin)
            if url.scheme not in {"http", "https"} or url.netloc not in self.server.allowed_hosts:
                raise PermissionError("Origin is not allowed")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise PermissionError("Cross-site requests are not allowed")

    def auth(self, worker=False):
        self.check_host()
        settings = self.station.store.settings()
        provided = self.headers.get("Authorization", "").removeprefix("Bearer ") if worker else self.headers.get("X-Station-Token", "")
        expected = settings["worker_token" if worker else "session_token"]
        if not provided or not secrets.compare_digest(provided, expected):
            raise PermissionError("Session expired. Refresh the page.")
        if worker and not settings.get("remote_workers_enabled", False):
            raise PermissionError("Remote workers are disabled")

    def body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 500_000:
            raise ContractError("Request body must be JSON under 500 KB")
        if self.headers.get_content_type() != "application/json":
            raise ContractError("Use application/json")
        body = strict_json(self.rfile.read(size).decode("utf-8"))
        if not isinstance(body, dict):
            raise ContractError("Expected a JSON object")
        return body

    def do_GET(self):
        try:
            self.check_host()
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            if path == "/api/bootstrap":
                return self.respond({"token": self.station.store.settings()["session_token"], "version": "0.3.0", "settings": public_settings(self.station.store), "demo_spec": demo_spec()})
            if path.startswith("/api/worker/"):
                self.auth(worker=True)
                if path == "/api/worker/projects":
                    return self.respond({"projects": [{"id": p["id"], "name": p["name"]} for p in self.station.store.list_projects() if p["mode"] == "live"]})
                raise ContractError("Unknown worker endpoint")
            if path.startswith("/api/"):
                self.auth()
                if path == "/api/projects":
                    return self.respond({"projects": self.station.store.list_projects()})
                if path == "/api/jobs":
                    return self.respond({"jobs": self.station.store.jobs()})
                if path == "/api/models":
                    return self.respond(self.station.ollama.status())
                if path == "/api/settings":
                    return self.respond(public_settings(self.station.store))
                if path == "/api/diagnostics":
                    import platform, shutil
                    return self.respond({"version": "0.3.0", "python": platform.python_version(), "platform": platform.system(),
                        "git": bool(shutil.which("git")), "ollama": bool(self.station.ollama.binary()), "data_directory": str(self.station.store.root),
                        "database": "SQLite WAL", "event_contract": "LDD workflow v1", "remote_workers_enabled": self.station.store.settings().get("remote_workers_enabled", False)})
                if path in {"/api/observations", "/api/observations/summary", "/api/observations/export"}:
                    trace=query.get("trace", ["station"])[0]
                    if trace!="station": self.station.store.project(trace)
                    if path.endswith("summary"): return self.respond(self.station.store.observation_summary(trace))
                    if path.endswith("export"):
                        return self.respond(self.station.store.observation_export(trace),content_type="application/x-ndjson; charset=utf-8",filename="observations.jsonl")
                    return self.respond(self.station.store.observations(trace,after=int(query.get("after",["0"])[0]),kind=query.get("kind",[""])[0],provider=query.get("provider",[""])[0]))
                if path == "/api/artifact":
                    meta, data = self.station.store.artifact(query.get("id", [""])[0])
                    return self.respond(data, content_type="application/zip" if meta["kind"] == "release" else "text/plain; charset=utf-8", filename=meta["name"] if query.get("download") else None)
                parts = path.strip("/").split("/")
                if len(parts) >= 3 and parts[:2] == ["api", "projects"]:
                    pid = parts[2]
                    if len(parts) == 3:
                        return self.respond({"project": self.station.store.project(pid), "metrics": self.station.metrics(pid)})
                    if parts[3] == "events":
                        return self.respond({"events": self.station.store.events(pid, max(0, int(query.get("after", ["0"])[0])), 500)})
                    if parts[3] == "report":
                        return self.respond(self.station.store.report(pid))
                    if parts[3] == "markdown":
                        return self.respond(self.station.store.markdown(pid), content_type="text/markdown; charset=utf-8", filename="PROJECT.md")
                raise ContractError("Unknown endpoint")
            if path in {"/", "/index.html"}:
                return self.respond((STATIC / "index.html").read_bytes(), content_type="text/html; charset=utf-8")
            assets = {"/app.js": "text/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8", "/scene.svg": "image/svg+xml", "/favicon.svg": "image/svg+xml"}
            if path in assets:
                return self.respond((STATIC / path[1:]).read_bytes(), content_type=assets[path])
            self.respond({"error": "Page not found"}, 404)
        except PermissionError as e:
            self.respond({"error": str(e)}, 403)
        except (ContractError, ValueError, KeyError) as e:
            self.respond({"error": str(e)[:500]}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond({"error": "The request could not be completed. Check diagnostics."}, 500)

    def do_POST(self):
        try:
            path = urllib.parse.urlsplit(self.path).path
            self.auth(worker=path.startswith("/api/worker/"))
            data = self.body()
            result = self.post(path, data)
            self.respond(result if result is not None else {"ok": True})
        except PermissionError as e:
            self.respond({"error": str(e)}, 403)
        except ModularError as e:
            self.respond({"error":str(e), "provider_error":e.to_dict()}, 400)
        except (ContractError, ValueError, KeyError, TypeError) as e:
            self.respond({"error": str(e)[:500]}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond({"error": "Operation failed. Check the selected model, project state, and diagnostics."}, 500)

    def post(self, path, data):
        s = self.station
        if path == "/api/demo":
            return s.create(demo_spec(), demo=True)
        if path == "/api/spec/validate":
            m = parse_spec(data["markdown"])
            return {"valid": True, "tasks": len(m["tasks"]), "name": m["name"]}
        if path == "/api/projects":
            return s.create(data["markdown"], data.get("source", ""), data.get("allow_cloud", False), data.get("commands", False))
        if path == "/api/settings":
            save_settings(s.store, data)
            return public_settings(s.store)
        if path == "/api/models/start":
            return {"message": s.ollama.start()}
        if path == "/api/models/stop":
            s.ollama.stop(); return {"message": "Managed runtime stopped"}
        if path == "/api/models/install":
            return s.launch("install-runtime", s.ollama.install)
        if path == "/api/models/pull":
            return s.launch("pull-model", lambda progress: s.ollama.pull(data["model"], progress))
        if path == "/api/models/unload":
            s.ollama.unload(data["model"]); return {"message": "Model unloaded from memory"}
        if path == "/api/providers/models":
            placement=data.get("placement", "cloud")
            if placement not in {"local", "cloud"}: raise ContractError("Invalid model placement")
            settings=s.store.settings()
            profile=normalize_profile(settings[placement], "remote" if placement=="cloud" else "local")
            return s.launch("discover-models", lambda progress: {"models":make_adapter(profile,credentials_for(settings,profile["kind"],placement)).list_models(), "placement":placement})
        if path == "/api/models/test":
            placement = data.get("placement", "local")
            if placement not in {"local", "cloud"}:
                raise ContractError("Invalid model placement")
            return s.launch("test-" + placement, lambda progress: model_call(s.store, None, "connection_test", {"message": "Reply with: Station online."}, "You are a concise assistant.", placement=placement))
        if path == "/api/playground":
            prompt = bounded(data.get("prompt"), "Prompt", 6000)
            placement = data.get("placement", "local")
            if placement not in {"local", "cloud"}:
                raise ContractError("Invalid model placement")
            return s.launch("playground", lambda progress: model_call(s.store, None, "playground", {"message": prompt}, "You are the RESIDUAL station assistant. Help with code and operational questions. Be concise.", placement=placement))
        if path == "/api/plan":
            goal = bounded(data.get("goal"), "Goal", 10000)
            placement = data.get("placement", "local")
            if placement not in {"local", "cloud"}:
                raise ContractError("Invalid model placement")
            def plan(progress):
                reply = model_call(s.store, None, "planner", {"goal": goal, "example_format": demo_spec()},
                    "Write a Markdown implementation specification containing exactly one fenced json manifest using the example schema. Use only the stated goal. Create bounded tasks with explicit paths, dependencies, route local or cloud, and deterministic checks. Unknown repository details must be called out in prose. Do not claim tests have run. This is a draft for operator review.", placement=placement)
                parse_spec(reply["text"])
                return {"markdown": reply["text"]}
            return s.launch("draft-spec", plan)
        if path == "/api/workers/access":
            enabled = data.get("enabled")
            if type(enabled) is not bool:
                raise ContractError("enabled must be a boolean")
            if data.get("rotate"):
                s.store.settings({"worker_token": secrets.token_urlsafe(32)})
            s.store.settings({"remote_workers_enabled": enabled})
            return {"enabled": enabled, "token": s.store.settings()["worker_token"] if enabled else None}
        if path == "/api/worker/claim":
            name = bounded(data.get("name"), "Runner name", 60)
            work = s.prepare(data["project_id"], "remote:" + name, data.get("task_id"))
            if not work:
                return {"work": None}
            t = work["task"]
            return {"work": {"project_id": work["project_id"], "task_id": t["id"], "attempt": t["attempt"], "lease": work["lease"], "packet": work["packet"], "allow_cloud": s.store.project(work["project_id"])["allow_cloud"]}}
        if path == "/api/worker/heartbeat":
            s.store.heartbeat(data["project_id"], data["task_id"], data["lease"])
            return {"ok": True}
        if path == "/api/worker/result":
            # Remote workers submit candidates only; the coordinator owns testing and approval.
            pid, tid = data["project_id"], data["task_id"]
            with s.project_lock(pid):
                from .contracts import sha
                sid = bounded(data.get("submission_id"), "Submission ID", 100)
                fingerprint = sha(data)
                with s.store.connect() as c:
                    previous = c.execute("SELECT value FROM submissions WHERE id=?", (sid,)).fetchone()
                if previous:
                    previous = json.loads(previous[0])
                    if previous["fingerprint"] != fingerprint:
                        raise ContractError("Submission ID already belongs to another payload")
                    return previous["result"]
                t = s.store.task(pid, tid)
                work = {"project_id": pid, "task": t, "lease": data["lease"]}
                usage = data.get("usage")
                if usage is not None:
                    allowed = {"input_tokens", "output_tokens", "cached_input_tokens", "cache_write_input_tokens", "source", "placement", "role", "model", "request_bytes"}
                    if not isinstance(usage, dict) or set(usage) - allowed or any(usage.get(k) is not None and (type(usage[k]) is not int or not 0 <= usage[k] <= 100_000_000) for k in ("input_tokens", "output_tokens", "cached_input_tokens", "cache_write_input_tokens", "request_bytes")):
                        raise ContractError("Invalid remote usage receipt")
                    usage = {**usage, "source": "worker_reported", "role": "remote_runner", "model": bounded(usage.get("model", "unknown"), "Model", 200)}
                result = s.finish(work, data["response"], usage)
                with s.store.transaction() as c:
                    c.execute("INSERT INTO submissions VALUES(?,?)", (sid, canonical({"fingerprint": fingerprint, "result": result})))
                return result
        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "projects"]:
            pid, action = parts[2], parts[3]
            s.store.project(pid)
            if action == "triage":
                return s.launch("triage", lambda progress: s.triage(pid, progress), pid)
            if action == "run":
                return s.launch("batch", lambda progress: s.batch(pid, progress), pid)
            if action == "pause":
                s.store.pause(pid, bool(data.get("paused", True))); return {"ok": True}
            if action == "task":
                tid, op = data["task_id"], data["action"]
                if op == "run":
                    return s.launch("run-" + tid, lambda progress: s.run_one(pid, tid), pid)
                if op == "review":
                    return s.launch("review-" + tid, lambda progress: s.review(pid, tid), pid)
                if op == "integrate":
                    return s.launch("integrate-" + tid, lambda progress: s.integrate(pid, tid), pid)
                if op == "escalate":
                    p = s.store.project(pid); t = s.store.task(pid, tid)
                    if not p["allow_cloud"] or t["state"] not in {"ready", "repair_required", "blocked"}:
                        raise ContractError("Cloud must be enabled and the task must be ready, blocked, or awaiting repair")
                    s.store.update_task(pid, tid, route="cloud")
                    s.store.event(pid, "task.finding", {"message": "Operator routed the unresolved task to cloud"}, tid, "operator")
                    return {"ok": True}
            if action == "cloud-report":
                return s.launch("cloud-report", lambda progress: s.cloud_report(pid, progress), pid)
            if action == "export":
                return s.launch("release", lambda progress: s.export(pid), pid)
            if action == "note":
                note = bounded(data.get("message"), "Message", 2000)
                return s.store.event(pid, "project.note", {"message": note}, actor="operator")
        raise ContractError("Unknown operation")


def main(argv=None):
    parser = argparse.ArgumentParser(description="RESIDUAL Command Station")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data", default=os.environ.get("RESIDUAL_DATA", str(Path.home() / ".residual" / "station")))
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--start-ollama", action="store_true")
    args = parser.parse_args(argv)
    station = Station(args.data)
    server = Server((args.host, args.port), station)
    if args.start_ollama:
        try:
            station.ollama.start()
        except ContractError as e:
            print(str(e), file=sys.stderr)
    url = f"http://localhost:{server.server_port}"
    print(f"RESIDUAL Command Station 0.3\nOpen {url}\nPress Ctrl+C to stop.", flush=True)
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if station.ollama.process and station.ollama.process.poll() is None:
            station.ollama.stop()


if __name__ == "__main__":
    main()
