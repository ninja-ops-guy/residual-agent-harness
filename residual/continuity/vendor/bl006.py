"""
BL-006 — MODEL ADMISSION PREFLIGHT — IMPLEMENTATION
Author: Hermes (LEGION, b_wqvgdcponfcmoij) — Candidate A base
Candidate B author: Mason (LEGION, b_swjen7ya26ehj2b)
Authority: Ghost's verified design v1.1 (df4b5b5b…) + reaping addendum (90c384c0…)
Target: MODEL_ADMISSION_PREFLIGHT_QUALIFIED
Isolation: No provider calls, no model loads, FreeLLMAPI runtime untouched.

Candidate B corrections (Piston receipt cff9f950…):
  F1 HIGH   — admission TTL enforced at consume (fail-closed admission_expired)
  F2 MOD    — M6a MEASURED_DERIVED lookup order implemented
  F3 LOW    — hardcoded sys.path removed from test file
  M5        — consume-time manifest version check enforced
"""

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

# ─── Canonical JSON helpers ─────────────────────────────────────────────────

def canonical_json(obj: Any) -> str:
    """Canonical form: sorted keys, UTF-8, no trailing newline."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ─── Telemetry schema (M4: pinned) ─────────────────────────────────────────

TELEMETRY_SCHEMA_VERSION = 1

@dataclass
class TelemetrySnapshot:
    collected_at: str
    available_ram_bytes: int
    available_vram_bytes: Optional[int]
    load1: float
    core_count: int
    resident_runtime_rss_sum: int
    vram_used_bytes: Optional[int]
    runtime_census_digest: str
    schema_version: int = TELEMETRY_SCHEMA_VERSION

    def canonical(self) -> str:
        return canonical_json(asdict(self))

    def digest(self) -> str:
        return sha256_hex(self.canonical())

# ─── Manifest row ────────────────────────────────────────────────────────────

@dataclass
class ManifestRow:
    manifest_key: str           # (model_identity, quantization, runtime_version, host_class)
    manifest_version: int       # M5: monotonic per key
    supersedes_digest: Optional[str]
    model_identity: str
    quantization: str
    runtime_version: str
    host_class: str
    footprint_bytes: int
    footprint_class: str        # CLAIMED | MEASURED
    kv_per_token_bytes: int
    kv_class: str               # CLAIMED | MEASURED
    max_context_tokens: int
    runtime_overhead_bytes: int
    device_class: str           # M3: cpu | cuda

    def canonical(self) -> str:
        return canonical_json(asdict(self))

    def digest(self) -> str:
        return sha256_hex(self.canonical())

# ─── Admission envelope ─────────────────────────────────────────────────────

@dataclass
class AdmissionEnvelope:
    admission_id: str
    assignment_binding: Optional[str]
    model_identity: str
    quantization: str
    requested_context_tokens: int
    requested_max_tokens: int
    host_identity: str
    evaluator_version: str
    device_class: str           # M3: cpu | cuda, absent defaults cpu
    created_at: str
    expires_at: str

    def canonical(self) -> str:
        return canonical_json(asdict(self))

    def digest(self) -> str:
        return sha256_hex(self.canonical())

# ─── Evaluator ───────────────────────────────────────────────────────────────

# Ratified thresholds (M4: change only via evaluator_version bump)
TELEMETRY_FRESHNESS_SECONDS = 60
ADMISSION_TTL_MINUTES = 15
WARN_HEADROOM_FRACTION = 0.25
KV_CLAIMED_LARGE_CONTEXT = 4096

class AdmissionEvaluator:
    """Pure function: (envelope, telemetry, manifest) → (verdict, reason_codes)."""

    def __init__(self, evaluator_version: str):
        self.evaluator_version = evaluator_version

    def evaluate(
        self,
        envelope: AdmissionEnvelope,
        telemetry: TelemetrySnapshot,
        manifest: ManifestRow,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        reasons: List[str] = []
        inputs: Dict[str, Any] = {}

        # ── freshness check ──
        collected = datetime.fromisoformat(telemetry.collected_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - collected).total_seconds()
        if age > TELEMETRY_FRESHNESS_SECONDS:
            return "REJECT", ["telemetry_unavailable"], {"telemetry_age_s": age}

        # ── identity resolution ──
        if manifest is None:
            return "REJECT", ["model_unresolved"], {}

        # ── context bound ──
        if envelope.requested_context_tokens > manifest.max_context_tokens:
            return "REJECT", ["context_exceeds_model"], {
                "requested": envelope.requested_context_tokens,
                "max": manifest.max_context_tokens,
            }

        # ── device-aware headroom (M3) ──
        kv_requirement = manifest.kv_per_token_bytes * envelope.requested_context_tokens
        total_need = manifest.footprint_bytes + kv_requirement + manifest.runtime_overhead_bytes

        if envelope.device_class == "cuda" and telemetry.available_vram_bytes is not None:
            headroom = telemetry.available_vram_bytes - total_need
            vram_headroom = headroom
            ram_headroom = telemetry.available_ram_bytes - total_need
        else:
            headroom = telemetry.available_ram_bytes - total_need
            vram_headroom = None
            ram_headroom = headroom

        inputs = {
            "available_ram_bytes": telemetry.available_ram_bytes,
            "available_vram_bytes": telemetry.available_vram_bytes,
            "footprint_bytes": manifest.footprint_bytes,
            "footprint_class": manifest.footprint_class,
            "kv_requirement_bytes": kv_requirement,
            "kv_class": manifest.kv_class,
            "runtime_overhead_bytes": manifest.runtime_overhead_bytes,
            "projected_headroom_bytes": headroom,
            "vram_headroom_bytes": vram_headroom,
            "ram_headroom_bytes": ram_headroom,
            "device_class": envelope.device_class,
        }

        # ── hard REJECT ──
        if headroom < 0:
            return "REJECT", ["insufficient_headroom"], inputs

        # ── WARN conditions ──
        warn_reasons = []
        available = telemetry.available_vram_bytes if envelope.device_class == "cuda" else telemetry.available_ram_bytes
        if available and headroom < WARN_HEADROOM_FRACTION * available:
            warn_reasons.append("thin_headroom")
        if telemetry.load1 > telemetry.core_count:
            warn_reasons.append("elevated_pressure")
        if manifest.footprint_class == "CLAIMED":
            warn_reasons.append("unmeasured_profile")
        if manifest.kv_class == "CLAIMED" and envelope.requested_context_tokens > KV_CLAIMED_LARGE_CONTEXT:
            warn_reasons.append("kv_estimated_large_context")

        if warn_reasons:
            return "WARN", warn_reasons, inputs

        return "PASS", [], inputs

# ─── Evidence store ─────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS admission_evaluations(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  admission_id TEXT NOT NULL UNIQUE,
  assignment_binding TEXT,
  envelope_canonical TEXT NOT NULL,
  envelope_digest TEXT NOT NULL,
  telemetry_snapshot_canonical TEXT NOT NULL,
  manifest_row_digest TEXT NOT NULL,
  verdict TEXT NOT NULL,
  reason_codes TEXT NOT NULL,
  state TEXT NOT NULL,
  confirmed_by TEXT,
  confirmed_at TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admission_measurements(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  measurement_id TEXT NOT NULL UNIQUE,
  admission_id TEXT NOT NULL,
  model_identity TEXT NOT NULL,
  quantization TEXT NOT NULL,
  runtime_version TEXT NOT NULL,
  host_identity TEXT NOT NULL,
  context_bucket TEXT NOT NULL,
  cold_load_ms INTEGER NOT NULL,
  ttft_ms INTEGER NOT NULL,
  tokens_per_sec REAL NOT NULL,
  peak_rss_bytes INTEGER NOT NULL,
  peak_vram_bytes INTEGER,
  measured_at TEXT NOT NULL,
  FOREIGN KEY(admission_id) REFERENCES admission_run_provenance(provenance_id)
);

CREATE TABLE IF NOT EXISTS receipts(
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  receipt_digest TEXT NOT NULL UNIQUE,
  record_canonical TEXT NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admission_run_provenance(
  provenance_id TEXT PRIMARY KEY,
  admission_id TEXT NOT NULL,
  assignment_binding TEXT,
  model_identity TEXT NOT NULL,
  quantization TEXT NOT NULL,
  runtime_version TEXT NOT NULL,
  host_identity TEXT NOT NULL,
  device_class TEXT NOT NULL DEFAULT 'cpu',
  verdict TEXT NOT NULL,
  consumed_at TEXT NOT NULL,
  receipt_digest TEXT NOT NULL
);
"""

class EvidenceStore:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, isolation_level=None)
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def transaction(self):
        return self.conn

    def insert_evaluation(
        self,
        envelope: AdmissionEnvelope,
        telemetry: TelemetrySnapshot,
        manifest: ManifestRow,
        verdict: str,
        reason_codes: List[str],
    ) -> str:
        receipt_record = {
            "admission_id": envelope.admission_id,
            "envelope_digest": envelope.digest(),
            "telemetry_snapshot_digest": telemetry.digest(),
            "manifest_row_digest": manifest.digest(),
            "inputs": {},  # filled by evaluator
            "verdict": verdict,
            "reason_codes": reason_codes,
            "evaluator_version": envelope.evaluator_version,
            "evaluated_at": now_rfc3339(),
        }
        receipt_canonical = canonical_json(receipt_record)
        receipt_digest = sha256_hex(receipt_canonical)

        with self.conn:
            self.conn.execute(
                """INSERT INTO admission_evaluations
                   (admission_id, assignment_binding, envelope_canonical, envelope_digest,
                    telemetry_snapshot_canonical, manifest_row_digest, verdict, reason_codes,
                    state, created_at, expires_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    envelope.admission_id,
                    envelope.assignment_binding,
                    envelope.canonical(),
                    envelope.digest(),
                    telemetry.canonical(),
                    manifest.digest(),
                    verdict,
                    canonical_json(reason_codes),
                    "EVALUATED",
                    envelope.created_at,
                    envelope.expires_at,
                ),
            )
            self.conn.execute(
                """INSERT INTO receipts (receipt_digest, record_canonical, recorded_at)
                   VALUES (?,?,?)""",
                (receipt_digest, receipt_canonical, now_rfc3339()),
            )

        return receipt_digest

    def confirm_warn(self, admission_id: str, confirmed_by: str, ui_session_digest: str) -> bool:
        with self.conn:
            cur = self.conn.execute(
                """UPDATE admission_evaluations
                   SET state='WARN_CONFIRMED', confirmed_by=?, confirmed_at=?
                   WHERE admission_id=? AND state='EVALUATED' AND verdict='WARN'""",
                (confirmed_by, now_rfc3339(), admission_id),
            )
            return cur.rowcount == 1

    def consume(self, admission_id: str, host_identity: str, manifest_row_digest: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Atomic CONSUME transition + provenance write (A1-class CAS).
        
        F1: TTL enforced — expired admissions refuse with admission_expired.
        M5: manifest version check — if manifest_row_digest provided, must match bound digest.
        """
        with self.conn:
            row = self.conn.execute(
                "SELECT * FROM admission_evaluations WHERE admission_id=?", (admission_id,)
            ).fetchone()
            if not row:
                return False, "admission_not_valid"

            cols = [d[0] for d in self.conn.execute("SELECT * FROM admission_evaluations LIMIT 0").description]
            rec = dict(zip(cols, row))

            if rec["state"] not in ("EVALUATED", "WARN_CONFIRMED"):
                return False, "admission_not_valid"
            if rec["state"] == "EVALUATED" and rec["verdict"] == "WARN":
                return False, "warn_not_confirmed"

            # F1: TTL enforcement — expired admissions refuse fail-closed
            now_dt = datetime.now(timezone.utc)
            expires_dt = datetime.fromisoformat(rec["expires_at"].replace("Z", "+00:00"))
            if now_dt > expires_dt:
                return False, "admission_expired"

            # M6b: host_mismatch check
            env = json.loads(rec["envelope_canonical"])
            if env.get("host_identity") != host_identity:
                return False, "host_mismatch"

            # M5: manifest version check at consume time
            if manifest_row_digest is not None and manifest_row_digest != rec["manifest_row_digest"]:
                return False, "manifest_version_mismatch"

            now = now_rfc3339()
            receipt_digest = sha256_hex(rec["envelope_canonical"] + now)

            self.conn.execute(
                "UPDATE admission_evaluations SET state='CONSUMED' WHERE admission_id=? AND state=?",
                (admission_id, rec["state"]),
            )
            self.conn.execute(
                """INSERT INTO admission_run_provenance
                   (provenance_id, admission_id, assignment_binding, model_identity,
                    quantization, runtime_version, host_identity, device_class, verdict,
                    consumed_at, receipt_digest)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    admission_id,
                    admission_id,
                    rec["assignment_binding"],
                    env["model_identity"],
                    env["quantization"],
                    env.get("evaluator_version", "unknown"),
                    host_identity,
                    env.get("device_class", "cpu"),
                    rec["verdict"],
                    now,
                    receipt_digest,
                ),
            )
            return True, receipt_digest

    def insert_measurement(
        self,
        admission_id: str,
        model_identity: str,
        quantization: str,
        runtime_version: str,
        host_identity: str,
        context_bucket: str,
        cold_load_ms: int,
        ttft_ms: int,
        tokens_per_sec: float,
        peak_rss_bytes: int,
        peak_vram_bytes: Optional[int],
    ) -> str:
        measurement_id = str(uuid.uuid4())
        with self.conn:
            self.conn.execute(
                """INSERT INTO admission_measurements
                   (measurement_id, admission_id, model_identity, quantization, runtime_version,
                    host_identity, context_bucket, cold_load_ms, ttft_ms, tokens_per_sec,
                    peak_rss_bytes, peak_vram_bytes, measured_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    measurement_id,
                    admission_id,
                    model_identity,
                    quantization,
                    runtime_version,
                    host_identity,
                    context_bucket,
                    cold_load_ms,
                    ttft_ms,
                    tokens_per_sec,
                    peak_rss_bytes,
                    peak_vram_bytes,
                    now_rfc3339(),
                ),
            )
        return measurement_id

    def get_state(self, admission_id: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT state FROM admission_evaluations WHERE admission_id=?", (admission_id,)
        ).fetchone()
        return row[0] if row else None

    def lookup_measured_profile(
        self,
        model_identity: str,
        quantization: str,
        runtime_version: str,
        host_identity: str,
        context_bucket: str,
    ) -> Tuple[Optional[Dict[str, Any]], str, Optional[int]]:
        """M6a: MEASURED_DERIVED lookup order.
        
        Returns (profile_dict_or_None, class_string, bucket_delta_or_None).
        Lookup order: exact-key MEASURED → nearest-bucket MEASURED_DERIVED → None.
        """
        with self.conn:
            # Exact key lookup
            row = self.conn.execute(
                """SELECT * FROM admission_measurements 
                   WHERE model_identity=? AND quantization=? AND runtime_version=? 
                   AND host_identity=? AND context_bucket=?
                   ORDER BY measured_at DESC LIMIT 1""",
                (model_identity, quantization, runtime_version, host_identity, context_bucket),
            ).fetchone()
            if row:
                cols = [d[0] for d in self.conn.execute("SELECT * FROM admission_measurements LIMIT 0").description]
                return dict(zip(cols, row)), "MEASURED", None
            
            # Nearest bucket lookup — parse bucket sizes, find closest
            all_rows = self.conn.execute(
                """SELECT * FROM admission_measurements 
                   WHERE model_identity=? AND quantization=? AND runtime_version=? 
                   AND host_identity=?""",
                (model_identity, quantization, runtime_version, host_identity),
            ).fetchall()
            
            if not all_rows:
                return None, "CLAIMED", None
            
            cols = [d[0] for d in self.conn.execute("SELECT * FROM admission_measurements LIMIT 0").description]
            
            def bucket_to_tokens(bucket_str: str) -> int:
                """Parse '8k' → 8192, '16k' → 16384, etc."""
                try:
                    if bucket_str.endswith('k'):
                        return int(bucket_str[:-1]) * 1024
                    return int(bucket_str)
                except (ValueError, AttributeError):
                    return 0
            
            target_tokens = bucket_to_tokens(context_bucket)
            best_row = None
            best_delta = None
            
            for r in all_rows:
                d = dict(zip(cols, r))
                row_tokens = bucket_to_tokens(d.get("context_bucket", ""))
                delta = abs(row_tokens - target_tokens)
                if best_delta is None or delta < best_delta:
                    best_delta = delta
                    best_row = d
            
            if best_row:
                return best_row, "MEASURED_DERIVED", best_delta
            
            return None, "CLAIMED", None

# ─── Module-level convenience ───────────────────────────────────────────────

_default_store: Optional[EvidenceStore] = None

def get_store(db_path: str = ":memory:") -> EvidenceStore:
    global _default_store
    if _default_store is None:
        _default_store = EvidenceStore(db_path)
    return _default_store

def create_envelope(
    model_identity: str,
    quantization: str,
    requested_context_tokens: int,
    requested_max_tokens: int,
    host_identity: str,
    evaluator_version: str,
    assignment_binding: Optional[str] = None,
    device_class: str = "cpu",
    ttl_minutes: int = ADMISSION_TTL_MINUTES,
) -> AdmissionEnvelope:
    now = datetime.now(timezone.utc)
    return AdmissionEnvelope(
        admission_id=str(uuid.uuid4()),
        assignment_binding=assignment_binding,
        model_identity=model_identity,
        quantization=quantization,
        requested_context_tokens=requested_context_tokens,
        requested_max_tokens=requested_max_tokens,
        host_identity=host_identity,
        evaluator_version=evaluator_version,
        device_class=device_class,
        created_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_at=(now + timedelta(minutes=ttl_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

def create_telemetry(
    available_ram_bytes: int,
    available_vram_bytes: Optional[int],
    load1: float,
    core_count: int,
    resident_runtime_rss_sum: int = 0,
    vram_used_bytes: Optional[int] = None,
    runtime_census_digest: str = "",
) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        collected_at=now_rfc3339(),
        available_ram_bytes=available_ram_bytes,
        available_vram_bytes=available_vram_bytes,
        load1=load1,
        core_count=core_count,
        resident_runtime_rss_sum=resident_runtime_rss_sum,
        vram_used_bytes=vram_used_bytes,
        runtime_census_digest=runtime_census_digest,
    )

def create_manifest(
    model_identity: str,
    quantization: str,
    runtime_version: str,
    host_class: str,
    footprint_bytes: int,
    kv_per_token_bytes: int,
    max_context_tokens: int,
    runtime_overhead_bytes: int,
    footprint_class: str = "CLAIMED",
    kv_class: str = "CLAIMED",
    device_class: str = "cpu",
    manifest_version: int = 1,
    supersedes_digest: Optional[str] = None,
) -> ManifestRow:
    key = f"{model_identity}:{quantization}:{runtime_version}:{host_class}"
    return ManifestRow(
        manifest_key=key,
        manifest_version=manifest_version,
        supersedes_digest=supersedes_digest,
        model_identity=model_identity,
        quantization=quantization,
        runtime_version=runtime_version,
        host_class=host_class,
        footprint_bytes=footprint_bytes,
        footprint_class=footprint_class,
        kv_per_token_bytes=kv_per_token_bytes,
        kv_class=kv_class,
        max_context_tokens=max_context_tokens,
        runtime_overhead_bytes=runtime_overhead_bytes,
        device_class=device_class,
    )
