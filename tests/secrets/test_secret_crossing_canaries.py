"""G4 secret-crossing canary negative tests (audit only — no production changes).

Implements inspection procedures S-01..S-06 from the A2 secrets/snapshot
adversarial specification, re-verified against main
3cff6bcd52e352a6ba048c958949a7bbb2a039eb.

OWNER'S KEY RULE under test: removing secrets from environment variables is
INSUFFICIENT protection for snapshots, because secret material may remain in
process memory. Tests marked "documented hazard" PASS by proving the hazard
exists; they are NOT blockers to green and MUST NOT be weakened into absence
assertions. UNKNOWN/BLOCKED are never reported as PASS.

Canary tokens are unique per surface so a leak's provenance is unambiguous.
"""

from __future__ import annotations

import base64
import gc
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import urllib.parse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from ai_providers import ProviderError
from ai_providers.adapters._http import map_http_error
from residual.core import canonical
from residual.factory.termination_provenance import ProcessControl
from residual.memory.store import EpistemicMemoryStore
from residual.modular import make_adapter, normalize_profile
from residual.station.models import model_call, save_settings
from residual.station.service import Station, demo_spec

# Unique canary secrets, one per injection surface (S-scheme provenance).
C_ENV = "CANARY-ENV-7f3a9c10-envopenai-DoNotUse"
C_BODY = "CANARY-UPSTREAMBODY-91bc04-DoNotUse"
C_MEM = "CANARY-PROCMEM-04ad71-DoNotUse"
C_SPEC = "CANARY-SPEC-3d88c1-DoNotUse"
C_GOAL = "CANARY-GOAL-e7f809-DoNotUse"
C_REASON = "CANARY-REASON-66e0f2-DoNotUse"
C_MEMSTORE = "CANARY-MEMSTORE-a1b2c3-DoNotUse"
C_FREELIST = "CANARY-FREELIST-d4e5f6-DoNotUse"

ALL_CANARIES = [C_ENV, C_BODY, C_MEM, C_SPEC, C_GOAL, C_REASON, C_MEMSTORE, C_FREELIST]


def canary_variants(canary: str) -> list[bytes]:
    """Byte forms a leak could take (S-scheme detection rule)."""
    raw = canary.encode("utf-8")
    return [
        raw,
        base64.b64encode(raw),
        raw.hex().encode("ascii"),
        urllib.parse.quote(canary, safe="").encode("ascii"),
        canary.encode("utf-16-le"),
    ]


def scan_bytes(haystack: bytes, canary: str) -> list[str]:
    """Return which encodings of the canary appear in the haystack."""
    hits = []
    for label, needle in zip(
        ("raw", "base64", "hex", "url", "utf-16le"), canary_variants(canary)
    ):
        if needle in haystack:
            hits.append(label)
    return hits


def scan_process_memory(canary: str) -> dict:
    """Scan this process's own memory for the canary (S-02).

    Two methods: (1) gc object graph walk over live Python str objects —
    portable, catches interned/arena-resident strings; (2) raw readable-region
    scan via /proc/self/maps + /proc/self/mem where the platform permits
    (Linux, ptrace_scope permits self). Returns an attestation record.
    """
    record = {"canary": canary, "found_via_gc_objects": False, "found_via_proc_mem": None}
    needle = canary.encode("utf-8")
    gc.collect()
    for obj in gc.get_objects():
        try:
            if type(obj) is str and canary in obj:
                record["found_via_gc_objects"] = True
                break
        except Exception:
            continue
    maps = Path("/proc/self/maps")
    mem = Path("/proc/self/mem")
    if maps.exists() and mem.exists():
        found = False
        try:
            with open(maps, "r") as m, open(mem, "rb", buffering=0) as f:
                for line in m:
                    parts = line.split()
                    if len(parts) < 2 or "r" not in parts[1]:
                        continue
                    # Skip huge/device-backed regions; heap + anon only.
                    path = parts[-1] if len(parts) >= 6 else ""
                    if path and not path.startswith(("[heap]", "[anon", "[stack]")) and "/" in path:
                        continue
                    start_s, end_s = parts[0].split("-")
                    start, end = int(start_s, 16), int(end_s, 16)
                    if end - start > 64 * 1024 * 1024:
                        continue
                    try:
                        f.seek(start)
                        if needle in f.read(end - start):
                            found = True
                            break
                    except (OSError, ValueError):
                        continue
            record["found_via_proc_mem"] = found
        except OSError:
            record["found_via_proc_mem"] = None  # UNKNOWN, not PASS
    return record


def test_scanner_negative_control(tmp_path):
    """S-harness negative control: the scanner MUST find a planted canary."""
    planted = tmp_path / "scratch.bin"
    planted.write_bytes(b"prefix " + C_ENV.encode() + b" suffix")
    hits = scan_bytes(planted.read_bytes(), C_ENV)
    assert "raw" in hits  # url-variant may coincide for URL-safe canaries
    encoded = tmp_path / "encoded.bin"
    encoded.write_bytes(base64.b64encode(C_BODY.encode()))
    assert "base64" in scan_bytes(encoded.read_bytes(), C_BODY)
    # A canary that was never planted must not be found.
    assert scan_bytes(planted.read_bytes(), C_MEMSTORE) == []


def test_env_clear_prevents_new_handles_but_does_not_revoke_existing(monkeypatch):
    """S-01: env removal blocks NEW handle acquisition but existing adapter
    instances retain the secret. Env scrubbing is not a revocation mechanism."""
    monkeypatch.setenv("OPENAI_API_KEY", C_ENV)
    profile = normalize_profile(
        {"kind": "openai", "model": "gpt-5", "placement": "cloud"}, "remote"
    )
    first = make_adapter(profile)
    assert getattr(first, "api_key", None) == C_ENV  # handle captured the secret
    monkeypatch.delenv("OPENAI_API_KEY")
    second = make_adapter(profile)
    assert getattr(second, "api_key", None) is None  # no new acquisition
    # Documented: the pre-existing handle STILL holds the canary after removal.
    assert getattr(first, "api_key", None) == C_ENV


def test_upstream_error_body_never_echoed():
    """S-03: map_http_error must not echo an upstream body containing secrets."""
    error = map_http_error("openai", 401, body="upstream said: " + C_BODY)
    assert scan_bytes(str(error).encode(), C_BODY) == []
    assert scan_bytes(canonical(error.to_dict()).encode(), C_BODY) == []
    assert error.code == "authentication"
    plain = ProviderError("x", provider="openai", code="invalid_response")
    assert scan_bytes(str(plain).encode(), C_BODY) == []


class _ToxicHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(size)
        self.send_response(401)
        self.end_headers()
        self.wfile.write(b"upstream secret: " + C_BODY.encode())


@contextmanager
def _toxic_401():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ToxicHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cleared_env_secret_absent_from_observations_and_db(tmp_path, monkeypatch):
    """S-01/S-03 combined (PASS expected): a canary secret used for a local
    provider call whose upstream 401 embeds secret material must leave ZERO
    canary bytes in the observation export, the events feed, or the raw
    station SQLite file. Toxic-provider precedent: PR #152."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", C_ENV)
    with _toxic_401() as url:
        station = Station(str(tmp_path / "station"))
        pid = station.create(demo_spec(), demo=True)["project_id"]
        save_settings(
            station.store,
            {
                "local": {
                    "kind": "openai_compatible",
                    "model": "primary",
                    "base_url": url,
                    "output_token_field": "max_tokens",
                },
                "local_credentials": {"api_key": C_ENV},
            },
        )
        with pytest.raises(ProviderError) as error:
            model_call(station.store, pid, "playground", {"message": "hello"}, "Be concise.")
        assert error.value.code == "authentication"
        assert scan_bytes(str(error.value).encode(), C_ENV) == []
        assert scan_bytes(str(error.value).encode(), C_BODY) == []
        export = station.store.observation_export(pid)
        assert scan_bytes(export.encode(), C_ENV) == []
        assert scan_bytes(export.encode(), C_BODY) == []
        events = json.dumps(station.store.events(pid), sort_keys=True)
        assert scan_bytes(events.encode(), C_ENV) == []
        assert scan_bytes(events.encode(), C_BODY) == []
        # Raw-file scan of the whole SQLite DB (catches overflow/freelist too).
        for db in Path(station.store.root).glob("*.db"):
            raw = db.read_bytes()
            assert scan_bytes(raw, C_BODY) == [], f"upstream body leaked into {db}"
            assert scan_bytes(raw, C_ENV) == [], f"credential leaked into {db}"


def test_memory_residency_after_env_removal_documented_hazard(monkeypatch):
    """S-02 DOCUMENTED HAZARD (owner's key rule): deleting the env var does
    NOT purge the secret from process memory. This test PASSES by proving
    retention; it must never be rewritten as an absence assertion. Any
    snapshot/crash-dump/emergency-journal path can therefore capture the
    secret even after env scrubbing."""
    monkeypatch.setenv("OPENAI_API_KEY", C_MEM)
    handle = os.environ["OPENAI_API_KEY"]
    profile = normalize_profile(
        {"kind": "openai", "model": "gpt-5", "placement": "cloud"}, "remote"
    )
    adapter = make_adapter(profile)
    assert getattr(adapter, "api_key", None) == C_MEM
    monkeypatch.delenv("OPENAI_API_KEY")
    del handle, adapter
    gc.collect()
    attestation = scan_process_memory(C_MEM)
    # Attestation is retained in the test record via assertion message.
    assert attestation["found_via_gc_objects"] or attestation["found_via_proc_mem"], (
        "hazard not reproduced on this platform — report UNKNOWN, not PASS: "
        + json.dumps(attestation)
    )


def test_sqlite_freelist_retains_deleted_secret_rows(tmp_path):
    """S-06 DOCUMENTED HAZARD: SQL-level deletion does not remove bytes from
    the raw SQLite file (freelist/unallocated pages) unless the build zeroes
    on delete. Absence via SELECT is not proof of absence; raw-file scanning
    is mandatory for snapshot audit, and claims must name the build's
    secure_delete configuration."""
    db = tmp_path / "freelist.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE observations(seq INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO observations(value) VALUES(?)", ("payload " + C_FREELIST,))
    conn.commit()
    assert b"CANARY-FREELIST" in db.read_bytes(), "control: row present before delete"
    secure_delete = conn.execute("PRAGMA secure_delete").fetchone()[0]
    conn.execute("DELETE FROM observations")
    conn.commit()
    assert conn.execute("SELECT count(*) FROM observations").fetchone()[0] == 0
    conn.close()
    raw = db.read_bytes()
    if secure_delete:
        # This SQLite build zeroes deleted content (SQLITE_SECURE_DELETE).
        # Typed outcome: PASS for this build; the hazard below is then latent.
        assert scan_bytes(raw, C_FREELIST) == []
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA secure_delete=OFF")
        conn.execute("INSERT INTO observations(value) VALUES(?)", ("payload " + C_FREELIST,))
        conn.execute("DELETE FROM observations")
        conn.commit()
        conn.close()
        raw = db.read_bytes()
    # Documented: with secure_delete off, deleted-row bytes persist in the
    # raw file until VACUUM. Snapshot tooling MUST scan raw files, not SQL.
    assert scan_bytes(raw, C_FREELIST) != [], "expected freelist retention of deleted row"
    conn = sqlite3.connect(db)
    conn.execute("VACUUM")
    conn.close()
    assert scan_bytes(db.read_bytes(), C_FREELIST) == [], "VACUUM must purge freelist bytes"


@pytest.mark.skipif(not hasattr(os, "pidfd_open"), reason="pidfd required; UNKNOWN not PASS")
def test_termination_record_persists_reason_payload():
    """S-05 DOCUMENTED HAZARD: kill(reason=...) deep-copies arbitrary reason
    payloads into the durable TerminationRecord (termination_provenance.py:230,
    333). Secret material placed in a reason dict persists verbatim."""
    process = subprocess.Popen(["sleep", "30"])
    control = ProcessControl(process, correlation_id="g4-audit")
    try:
        control.kill(reason=("watchdog", "test", {"detail": C_REASON}))
        record = control.termination_record()
        blob = canonical(record.to_dict())
        assert scan_bytes(blob.encode(), C_REASON) != [], (
            "expected reason payload to persist verbatim in TerminationRecord"
        )
        assert record.request_action == {"detail": C_REASON}
    finally:
        control.stopped.wait(timeout=5)


def test_memory_store_persists_artifact_payload_verbatim(tmp_path):
    """S-05 DOCUMENTED: EpistemicMemoryStore.index() persists
    artifact_payload verbatim as plaintext JSON (memory/store.py:46-74);
    retrieve() returns it. No redaction or at-rest protection exists."""
    store = EpistemicMemoryStore(str(tmp_path / "mem"))
    entry = store.index(
        "audit goal",
        "0" * 64,
        {"value": "result embeds " + C_MEMSTORE},
        "verifier-v1",
    )
    assert entry.artifact_payload["value"] == "result embeds " + C_MEMSTORE
    blob = b"".join(p.read_bytes() for p in (tmp_path / "mem").glob("*.json"))
    assert scan_bytes(blob, C_MEMSTORE) != []
    mode = oct((tmp_path / "mem" / (entry.key + ".json")).stat().st_mode & 0o777)
    # Recorded for the gap matrix; no permission assertion is imposed.
    assert mode in ("0o644", "0o600", "0o664")


def test_markdown_and_cloud_report_boundaries(tmp_path):
    """S-04: markdown() embeds the original spec VERBATIM (operator-local
    artifact); report() includes the goal (crosses trust boundary to cloud
    review readers) but NOT the spec text or task instructions."""
    station = Station(str(tmp_path / "station"))
    manifest = json.loads(
        demo_spec().split("```json\n", 1)[1].rsplit("\n```", 1)[0]
    )
    manifest["goal"] = "restore health; token " + C_GOAL
    spec_md = "# Spec\n\nOperator note with " + C_SPEC + "\n\n```json\n" + json.dumps(manifest) + "\n```\n"
    pid = station.create(spec_md, demo=True)["project_id"]
    md = station.store.markdown(pid)
    # Operator-local artifact retains operator-authored spec verbatim.
    assert scan_bytes(md.encode(), C_SPEC) != [], "markdown() must embed spec verbatim (documented)"
    report = station.store.report(pid)
    blob = canonical(report)
    # Cross-boundary gap: goal text flows into the cloud-review report.
    assert scan_bytes(blob.encode(), C_GOAL) != [], "report() carries goal verbatim (documented gap)"
    # Spec body and task instructions do NOT cross into the report.
    assert scan_bytes(blob.encode(), C_SPEC) == []
