from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .evidence import EvidenceEnvelope, GateResult, evidence_digest, load_envelope

MANIFEST_SCHEMA = "residual.qualification.manifest.v1"


@dataclass(frozen=True)
class QualificationManifest:
    commit: str
    tree: str
    result: GateResult
    required_gates: list[str]
    gates: dict[str, dict]
    missing_gates: list[str] = field(default_factory=list)
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    schema: str = MANIFEST_SCHEMA

    def to_dict(self) -> dict:
        doc = asdict(self)
        doc["result"] = self.result.value
        return doc


def aggregate_manifest(
    evidence_paths: Iterable[Path | str],
    *,
    required_gates: Iterable[str],
    artifact_paths: Iterable[Path | str] = (),
) -> QualificationManifest:
    envelopes = [load_envelope(path) for path in evidence_paths]
    if not envelopes:
        raise ValueError("qualification requires at least one evidence envelope")

    commits = {e.source.get("commit") for e in envelopes}
    trees = {e.source.get("tree") for e in envelopes}
    if len(commits) != 1 or None in commits or len(trees) != 1 or None in trees:
        raise ValueError("qualification evidence is not bound to one commit/tree")

    commit = next(iter(commits))
    tree = next(iter(trees))
    by_gate: dict[str, EvidenceEnvelope] = {}
    for envelope in envelopes:
        if envelope.gate_id in by_gate:
            raise ValueError(f"duplicate evidence for gate {envelope.gate_id!r}")
        by_gate[envelope.gate_id] = envelope

    required = sorted(set(required_gates))
    missing = [gate for gate in required if gate not in by_gate]
    reasons: list[str] = []
    if missing:
        reasons.append("missing required gates: " + ", ".join(missing))

    for gate in required:
        envelope = by_gate.get(gate)
        if envelope is None:
            continue
        if envelope.result != GateResult.PASS:
            reasons.append(f"{gate}={envelope.result.value}")
        # Skip policy is enforced by the producing gate (for example --zero-skips).
        # A general regression suite may legitimately contain capability skips, so
        # aggregate qualification must not reinterpret informational skip counts.
        if envelope.unknown_count:
            reasons.append(f"{gate} has {envelope.unknown_count} UNKNOWN checks")

    artifacts: dict[str, str] = {}
    for value in artifact_paths:
        path = Path(value)
        if not path.is_file():
            reasons.append(f"missing artifact: {path}")
            continue
        artifacts[str(path)] = evidence_digest(path)

    result = GateResult.PASS if not reasons else GateResult.FAIL
    return QualificationManifest(
        commit=commit,
        tree=tree,
        result=result,
        required_gates=required,
        gates={gate: envelope.to_dict() for gate, envelope in sorted(by_gate.items())},
        missing_gates=missing,
        artifact_hashes=artifacts,
        reasons=reasons,
    )


def write_manifest(manifest: QualificationManifest, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
