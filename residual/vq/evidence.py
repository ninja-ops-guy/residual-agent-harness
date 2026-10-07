"""VQ-002 Gate C hardening: fail-closed verification of retained evidence.

The benchmark artifact (evidence/vq/vq-002-benchmark.json) records
sha256 hashes and record counts for the retained raw-outcome chunks
(evidence/vq/outcomes-*.jsonl). This module is the code path that
consumes those hashes: it loads every referenced chunk from disk,
recomputes each chunk's sha256 and record count, refuses on any
mismatch (tampered content, missing chunk, extra chunk, or absent
hash/count field), and only then recomputes the VerifierQualityProfile
from the verified on-disk evidence and compares it against the profile
recorded in the artifact. Any discrepancy raises
EvidenceVerificationError (fail-closed, per the module's UNKNOWN
conventions: no silent degradation, no partial trust).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from residual.core import ContractError

from .gate import QualityGate
from .identity import VerifierIdentity
from .outcomes import LabeledOutcome, LabelSource, OutcomeStore
from .profile import VerifierQualityProfile, DEFAULT_MIN_SAMPLES

CHUNK_GLOB = "outcomes-*.jsonl"
REQUIRED_SCENARIOS = ("adequate", "degraded")


class EvidenceVerificationError(ContractError):
    """Raised when retained evidence fails verification (fail-closed)."""


def _fail(msg: str):
    raise EvidenceVerificationError(msg)


def _load_chunk_records(path: Path, expected: dict) -> list[dict]:
    """Read one chunk file and verify its recorded sha256 and count."""
    name = path.name
    if not path.is_file():
        _fail(f"missing retained evidence chunk: {name}")
    body = path.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    recorded = expected.get("sha256")
    if not recorded:
        _fail(f"artifact lacks sha256 for chunk {name} (fail-closed)")
    if digest != recorded:
        _fail(f"sha256 mismatch for chunk {name}: "
              f"artifact={recorded} disk={digest}")
    recorded_count = expected.get("count")
    if recorded_count is None:
        _fail(f"artifact lacks record count for chunk {name} (fail-closed)")
    lines = [ln for ln in body.decode("utf-8").splitlines() if ln.strip()]
    if len(lines) != recorded_count:
        _fail(f"record count mismatch for chunk {name}: "
              f"artifact={recorded_count} disk={len(lines)}")
    return [json.loads(ln) for ln in lines]


def _identity_from_artifact(verifier: dict) -> VerifierIdentity:
    for field in ("name", "implementation_hash", "configuration_hash",
                  "policy_hash"):
        if not verifier.get(field):
            _fail(f"artifact verifier identity missing {field} (fail-closed)")
    return VerifierIdentity(
        name=verifier["name"],
        implementation_hash=verifier["implementation_hash"],
        configuration_hash=verifier["configuration_hash"],
        policy_hash=verifier["policy_hash"],
        proof_hash=verifier.get("proof_hash"),
    )


def load_verified_evidence(artifact_path, evidence_dir=None) -> dict:
    """Fail-closed loader for a VQ-002 benchmark artifact.

    Returns {"adequate": [...outcomes...], "degraded": [...]} — outcome
    dicts reconstructed from the verified on-disk chunks — or raises
    EvidenceVerificationError on any integrity failure.
    """
    artifact_path = Path(artifact_path)
    if not artifact_path.is_file():
        _fail(f"benchmark artifact not found: {artifact_path}")
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    evidence_dir = Path(evidence_dir) if evidence_dir else artifact_path.parent

    manifest = artifact.get("raw_outcome_files")
    if not isinstance(manifest, dict):
        _fail("artifact has no raw_outcome_files manifest (fail-closed)")

    referenced = {}
    verified = {}
    for scenario in REQUIRED_SCENARIOS:
        entries = manifest.get(scenario)
        if not isinstance(entries, list) or not entries:
            _fail(f"artifact manifest missing scenario '{scenario}'")
        outcomes = []
        for entry in entries:
            name = entry.get("file") if isinstance(entry, dict) else None
            if not name:
                _fail(f"manifest entry for '{scenario}' lacks file name")
            if name in referenced and referenced[name] is not entry:
                # same chunk referenced by both scenarios is fine only if
                # the recorded hash/count agree
                prev = referenced[name]
                if (prev.get("sha256") != entry.get("sha256")
                        or prev.get("count") != entry.get("count")):
                    _fail(f"conflicting manifest records for chunk {name}")
                records = verified[name]
            else:
                referenced[name] = entry
                records = _load_chunk_records(evidence_dir / name, entry)
                verified[name] = records
            outcomes.extend(records)
        verified[scenario] = outcomes

    # Extra on-disk chunks not bound by the artifact => refusal.
    for extra in sorted(evidence_dir.glob(CHUNK_GLOB)):
        if extra.name not in referenced:
            _fail(f"unreferenced evidence chunk on disk: {extra.name}")

    return {"adequate": verified["adequate"],
            "degraded": verified["degraded"],
            "artifact": artifact,
            "evidence_dir": evidence_dir}


def _profile_from_records(identity: VerifierIdentity, records: list[dict],
                          min_samples: int) -> VerifierQualityProfile:
    store = OutcomeStore()
    for d in records:
        store.add(LabeledOutcome(
            case_id=d["case_id"], verifier_id=d["verifier_id"],
            verdict=bool(d["verdict"]),
            ground_truth=bool(d["ground_truth"]),
            label_source=LabelSource(d["label_source"]),
            confidence=d.get("confidence"),
            safety_critical=bool(d.get("safety_critical", False)),
        ))
    return VerifierQualityProfile.from_outcomes(
        identity, list(store), min_samples=min_samples)


def verify_artifact_profiles(artifact_path, evidence_dir=None) -> dict:
    """Gate C on retained evidence: verify chunks, then recompute each
    scenario's profile and gate from the verified on-disk chunks and
    compare against what the artifact recorded. Returns the recomputed
    {"profile", "gate"} per scenario. Raises EvidenceVerificationError
    on any mismatch.
    """
    loaded = load_verified_evidence(artifact_path, evidence_dir)
    artifact = loaded["artifact"]
    results = {}
    for scenario in REQUIRED_SCENARIOS:
        bench = artifact.get(f"benchmark_{scenario}")
        if not isinstance(bench, dict):
            _fail(f"artifact missing benchmark_{scenario} (fail-closed)")
        config = bench.get("config") or {}
        identity = _identity_from_artifact(config.get("verifier") or {})
        min_samples = int(config.get("min_samples", DEFAULT_MIN_SAMPLES))
        threshold = float(config.get("gate_threshold", 0.95))
        safety_critical = bool(config.get("safety_critical", True))

        profile = _profile_from_records(identity, loaded[scenario],
                                        min_samples)
        recorded_profile = bench.get("profile")
        if recorded_profile is None:
            _fail(f"artifact benchmark_{scenario} lacks profile (fail-closed)")
        if profile.to_dict() != recorded_profile:
            _fail(f"recomputed profile for '{scenario}' does not match "
                  f"the profile recorded in the artifact")
        gate = QualityGate(threshold).evaluate(profile,
                                               safety_critical=safety_critical)
        recorded_gate = bench.get("gate")
        if recorded_gate is None:
            _fail(f"artifact benchmark_{scenario} lacks gate (fail-closed)")
        if gate.to_dict() != recorded_gate:
            _fail(f"recomputed gate for '{scenario}' does not match "
                  f"the gate recorded in the artifact")
        results[scenario] = {"profile": profile.to_dict(),
                             "gate": gate.to_dict()}
    return results
