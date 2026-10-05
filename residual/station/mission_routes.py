"""Add mission routes without altering existing Station auth or worker routes."""
from __future__ import annotations

import threading
import urllib.parse
from pathlib import Path

from .mission_sync import MissionSync, SyncError, exact

_INIT_LOCK = threading.Lock()
_STATIC = Path(__file__).parent / "static"


def with_mission_sync(base):
    class MissionHandler(base):
        @property
        def mission_sync(self):
            with _INIT_LOCK:
                if not hasattr(self.server, "mission_sync"):
                    self.server.mission_sync = MissionSync(self.station.store.db)
            return self.server.mission_sync

        def _mission_request(self, path, *, post=False):
            try:
                self.check_host()
                if path in {"/missions", "/missions.js", "/missions.css"} and not post:
                    name, mime = {
                        "/missions": ("missions.html", "text/html; charset=utf-8"),
                        "/missions.js": ("missions.js", "text/javascript; charset=utf-8"),
                        "/missions.css": ("missions.css", "text/css; charset=utf-8"),
                    }[path]
                    return self.respond((_STATIC / name).read_bytes(), content_type=mime)
                external = path.startswith("/api/mission-sync/")
                if external:
                    if not post:
                        raise PermissionError("Capability endpoints require POST")
                    auth = self.headers.get("Authorization", "")
                    if not auth.startswith("Bearer "):
                        raise PermissionError("Binding capability required")
                    token = auth[7:]
                    bid = self.headers.get("X-Mission-Binding", "")
                else:
                    self.auth()  # The existing operator trust boundary, never worker auth.
                data = self.body() if post else {}
                sync = self.mission_sync
                if path == "/api/missions" and not post:
                    result = sync.overview()
                elif path == "/api/missions/journal" and not post:
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    result = sync.journal(query.get("mission_id", [""])[0], int(query.get("after", ["0"])[0]))
                elif path == "/api/missions/bind" and post:
                    result = sync.bind(data)
                elif path == "/api/missions/revoke" and post:
                    exact(data, {"binding_id"})
                    result = sync.revoke(data["binding_id"])
                elif path == "/api/mission-sync/report" and post:
                    result = sync.ingest(bid, token, data)
                elif path == "/api/mission-sync/poll" and post:
                    exact(data, set(), {"limit"})
                    result = sync.poll(bid, token, limit=data.get("limit", 25))
                elif path == "/api/mission-sync/context" and post:
                    exact(data, set())
                    result = sync.continuation(bid, token)
                elif path == "/api/mission-sync/ack" and post:
                    exact(data, {"delivery_id", "sha256"})
                    result = sync.acknowledge(bid, token, data["delivery_id"], data["sha256"])
                else:
                    raise SyncError("Unknown mission endpoint")
                return self.respond(result)
            except PermissionError as exc:
                return self.respond({"error": str(exc)}, 403)
            except (SyncError, ValueError, KeyError, TypeError) as exc:
                return self.respond({"error": str(exc)[:240]}, 400)
            except (BrokenPipeError, ConnectionResetError):
                return None
            except Exception:
                return self.respond({"error": "Mission sync unavailable; no success acknowledged"}, 500)

        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if path in {"/missions", "/missions.js", "/missions.css", "/api/missions", "/api/missions/journal"} or path.startswith("/api/mission-sync/"):
                return self._mission_request(path)
            return super().do_GET()

        def do_POST(self):
            path = urllib.parse.urlsplit(self.path).path
            if path.startswith("/api/missions/") or path.startswith("/api/mission-sync/"):
                return self._mission_request(path, post=True)
            return super().do_POST()
    return MissionHandler
