"""Dependency-free local web application. State-changing endpoints require a session token."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import mimetypes
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from .contracts import bounded, parse_spec
from .models import model_call, public_settings, save_settings, credentials_for
from residual.modular import normalize_profile, make_adapter
from ai_providers import ProviderError as ModularError
from .service import Station, demo_spec

STATIC = Path(__file__).parent / "static"
SESSION_COOKIE = "residual_session"


def _loopback_host(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_exposure(host, allowed_hosts, enabled=False, public_url=""):
    """Return a normalized public origin, or None for the default loopback-only mode."""
    if _loopback_host(host):
        return None
    if not enabled:
        raise ContractError("Non-loopback Station exposure is disabled. Set RESIDUAL_REMOTE_EXPOSURE=1 only behind an authenticated TLS proxy or equivalent protected transport.")
    allowed = {value.strip() for value in allowed_hosts.split(",") if value.strip()}
    if not allowed:
        raise ContractError("Non-loopback Station exposure requires explicit RESIDUAL_ALLOWED_HOSTS")
    parsed = urllib.parse.urlsplit(public_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ContractError("Non-loopback Station exposure requires RESIDUAL_PUBLIC_URL as an HTTPS origin")
    if parsed.netloc not in allowed:
        raise ContractError("RESIDUAL_PUBLIC_URL must match an entry in RESIDUAL_ALLOWED_HOSTS")
    return f"https://{parsed.netloc}"


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, station, launch_token=None, secure_cookie=False):
        self.station = station
        self._launch_token_hash = hashlib.sha256(launch_token.encode()).hexdigest() if launch_token else None
        self._launch_lock = threading.Lock()
        self.secure_cookie = bool(secure_cookie)
        super().__init__(address, Handler)
        self.allowed_hosts = {f"localhost:{self.server_port}", f"127.0.0.1:{self.server_port}"}
        self.allowed_hosts.update(h.strip() for h in os.environ.get("RESIDUAL_ALLOWED_HOSTS", "").split(",") if h.strip())
        self._register_legacy_worker_key()

    def consume_launch_token(self, value):
        if not value or not self._launch_token_hash:
            return False
        digest = hashlib.sha256(value.encode()).hexdigest()
        with self._launch_lock:
            if not self._launch_token_hash or not secrets.compare_digest(digest, self._launch_token_hash):
                return False
            self._launch_token_hash = None
            return True

    def _register_legacy_worker_key(self):
        """Migrate the pre-AUD-1 station-wide key into a first-use scoped credential."""
        with self.station.store.lock:
            settings = self.station.store.settings()
            token = settings.get("worker_token")
            credentials = dict(settings.get("worker_credentials", {}))
            if not token:
                token = secrets.token_urlsafe(32)
                settings["worker_token"] = token
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if not any(c.get("active") and secrets.compare_digest(c.get("token_hash", ""), token_hash) for c in credentials.values()):
                cid = "legacy-" + secrets.token_hex(8)
                credentials[cid] = {"token_hash": token_hash, "project_id": None, "runner": None, "active": True}
                self.station.store.settings({"worker_token": token, "worker_credentials": credentials})

    def issue_worker_credential(self, rotate=False):
        with self.station.store.lock:
            settings = self.station.store.settings()
            credentials = dict(settings.get("worker_credentials", {}))
            if rotate:
                credentials = {cid: {**record, "active": False} for cid, record in credentials.items()}
            # Keep only a bounded recent credential set; inactive entries are retained only
            # long enough to make rotation semantics explicit and inspectable.
            if len(credentials) > 64:
                active = {cid: record for cid, record in credentials.items() if record.get("active")}
                credentials = dict(list(active.items())[-32:])
            cid = secrets.token_hex(8)
            secret = secrets.token_urlsafe(32)
            token = f"{cid}.{secret}"
            credentials[cid] = {
                "token_hash": hashlib.sha256(token.encode()).hexdigest(),
                "project_id": None,
                "runner": None,
                "active": True,
            }
            self.station.store.settings({"worker_token": token, "worker_credentials": credentials})
            return token

    def worker_identity(self, token):
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        settings = self.station.store.settings()
        for cid, record in settings.get("worker_credentials", {}).items():
            if record.get("active") and secrets.compare_digest(record.get("token_hash", ""), token_hash):
                return {"credential_id": cid, "project_id": record.get("project_id"), "runner": record.get("runner")}
        return None

    def bind_worker_identity(self, credential_id, project_id, runner):
        with self.station.store.lock:
            settings = self.station.store.settings()
            credentials = dict(settings.get("worker_credentials", {}))
            record = dict(credentials.get(credential_id, {}))
            if not record.get("active"):
                raise PermissionError("Runner credential is no longer active")
            self.station.store.project(project_id)
            if record.get("project_id") is None:
                record.update(project_id=project_id, runner=runner)
                credentials[credential_id] = record
                self.station.store.settings({"worker_credentials": credentials})
                self.station.store.event(project_id, "worker.joined", {"runner": runner, "credential_id": credential_id}, actor="coordinator")
            elif record.get("project_id") != project_id or record.get("runner") != runner:
                raise PermissionError("Runner credential is scoped to another project or runner")
            return {"credential_id": credential_id, "project_id": record["project_id"], "runner": record["runner"]}


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

    def establish_session(self, launch_token):
        if not self.server.consume_launch_token(launch_token):
            raise PermissionError("Launch link is invalid or has already been used")
        token = self.station.store.settings()["session_token"]
        cookie = f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/"
        if self.server.secure_cookie:
            cookie += "; Secure"
        self.send_response(303)
        self.headers_common()
        self.send_header("Set-Cookie", cookie)
        self.send_header("Location", "/#overview")
        self.send_header("Content-Length", "0")
        self.end_headers()

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

    def _cookie_session(self):
        raw = self.headers.get("Cookie", "")
        if not raw:
            return ""
        try:
            cookie = SimpleCookie(); cookie.load(raw)
            morsel = cookie.get(SESSION_COOKIE)
            return morsel.value if morsel else ""
        except Exception:
            return ""

    def auth(self, worker=False):
        self.check_host()
        settings = self.station.store.settings()
        if worker:
            provided = self.headers.get("Authorization", "").removeprefix("Bearer ")
            identity = self.server.worker_identity(provided)
            if not identity:
                raise PermissionError("Runner credential is invalid or expired")
            if not settings.get("remote_workers_enabled", False):
                raise PermissionError("Remote workers are disabled")
            return identity
        expected = settings["session_token"]
        header = self.headers.get("X-Station-Token", "")
        cookie = self._cookie_session()
        if not ((header and secrets.compare_digest(header, expected)) or (cookie and secrets.compare_digest(cookie, expected))):
            raise PermissionError("Session expired. Reopen the launch link from the Station console.")
        return {"role": "operator"}

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
            if path.startswith("/auth/"):
                return self.establish_session(urllib.parse.unquote(path[len("/auth/"):]))
            if path == "/api/bootstrap":
                # Public bootstrap is metadata only. Operator authority is delivered out-of-band
                # through the one-time launch capability and an HttpOnly same-site cookie.
                return self.respond({"version": "0.3.0", "settings": public_settings(self.station.store), "demo_spec": demo_spec()})
            if path.startswith("/api/worker/"):
                identity = self.auth(worker=True)
                if path == "/api/worker/projects":
                    if not identity.get("project_id"):
                        return self.respond({"projects": []})
                    project = self.station.store.project(identity["project_id"])
                    return self.respond({"projects": [{"id": project["id"], "name": project["name"]}] if project["mode"] == "live" else []})
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
            if path.startswith("/api/worker/"):
                identity = self.auth(worker=True)
                data = self.body()
                result = self.worker_post(path, data, identity)
            else:
                self.auth()
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

    def _require_worker_scope(self, identity, pid, tid=None):
        if not identity.get("project_id") or identity["project_id"] != pid:
            raise PermissionError("Runner credential is not scoped to this project")
        owner = "remote:" + identity["credential_id"]
        if tid is not None:
            task = self.station.store.task(pid, tid)
            if task.get("owner") != owner:
                raise PermissionError("Task authority belongs to another runner")
        return owner

    def worker_post(self, path, data, identity):
        """Strict worker capability surface. Worker routes cannot invoke operator transitions."""
        s = self.station
        if path == "/api/worker/claim":
            name = bounded(data.get("name"), "Runner name", 60)
            pid = bounded(data.get("project_id"), "Project ID", 80)
            identity = self.server.bind_worker_identity(identity["credential_id"], pid, name)
            owner = self._require_worker_scope(identity, pid)
            work = s.prepare(pid, owner, data.get("task_id"))
            if not work:
                return {"work": None}
            t = work["task"]
            return {"work": {"project_id": work["project_id"], "task_id": t["id"], "attempt": t["attempt"], "lease": work["lease"], "packet": work["packet"], "allow_cloud": s.store.project(work["project_id"])["allow_cloud"]}}
        if path == "/api/worker/heartbeat":
            pid, tid = data["project_id"], data["task_id"]
            self._require_worker_scope(identity, pid, tid)
            s.store.heartbeat(pid, tid, data["lease"])
            return {"ok": True}
        if path == "/api/worker/result":
            pid, tid = data["project_id"], data["task_id"]
            self._require_worker_scope(identity, pid, tid)
            # Remote workers submit candidates only; coordinator-side verification owns all state transitions.
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
        raise ContractError("Unknown worker operation")

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
            token = None
            if enabled:
                token = self.server.issue_worker_credential(rotate=bool(data.get("rotate")))
            s.store.settings({"remote_workers_enabled": enabled})
            return {"enabled": enabled, "token": token}
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
    allowed_hosts = os.environ.get("RESIDUAL_ALLOWED_HOSTS", "")
    try:
        public_origin = validate_exposure(
            args.host,
            allowed_hosts,
            os.environ.get("RESIDUAL_REMOTE_EXPOSURE", "") == "1",
            os.environ.get("RESIDUAL_PUBLIC_URL", ""),
        )
    except ContractError as e:
        parser.error(str(e))
    station = Station(args.data)
    launch_token = secrets.token_urlsafe(32)
    server = Server((args.host, args.port), station, launch_token=launch_token, secure_cookie=bool(public_origin))
    if args.start_ollama:
        try:
            station.ollama.start()
        except ContractError as e:
            print(str(e), file=sys.stderr)
    origin = public_origin or f"http://localhost:{server.server_port}"
    url = f"{origin}/auth/{urllib.parse.quote(launch_token, safe='')}"
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
