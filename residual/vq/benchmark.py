"""VQ-002 acceptance: reproducible verifier benchmark.

Runs a verifier callable over a frozen labeled-defect fixture, records
raw labeled outcomes (independently labeled by the fixture), computes
the quality profile, applies the fail-closed quality gate, and emits a
hash-bound machine-readable report (Gate B). The report can be
recomputed from the retained raw outcomes and must hash identically
(Gate C — reproduction).
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

from .frozen import FrozenWorkloadFixture
from .gate import QualityGate, GateDecision, GateResult
from .identity import VerifierIdentity, hash_payload
from .outcomes import LabeledOutcome, LabelSource, OutcomeStore
from .profile import VerifierQualityProfile, DEFAULT_MIN_SAMPLES
from .snapshot import VerifierQualitySnapshot

BENCHMARK_SCHEMA = "residual.vq.benchmark.v1"


def _git_identity(repo_dir: str) -> dict:
    def run(*args):
        try:
            return subprocess.run(["git", "-C", repo_dir, *args],
                                  capture_output=True, text=True,
                                  check=True).stdout.strip()
        except Exception:
            return "unavailable"
    return {"commit": run("rev-parse", "HEAD"),
            "tree": run("rev-parse", "HEAD^{tree}")}


@dataclass(frozen=True)
class BenchmarkReport:
    """Machine-readable, hash-bound benchmark result."""
    schema: str
    identity: dict
    config: dict
    runtime: dict
    fixture: dict
    raw_labeled_outcomes: list
    profile: dict
    gate: dict
    escalations: list

    @property
    def report_hash(self) -> str:
        return hash_payload({
            "schema": self.schema,
            "identity": self.identity,
            "config": self.config,
            "fixture": self.fixture,
            "raw_labeled_outcomes": self.raw_labeled_outcomes,
            "profile": self.profile,
            "gate": self.gate,
            "escalations": self.escalations,
        })

    def to_dict(self) -> dict:
        d = {
            "schema": self.schema,
            "identity": self.identity,
            "config": self.config,
            "runtime": self.runtime,
            "fixture": self.fixture,
            "raw_labeled_outcomes": self.raw_labeled_outcomes,
            "profile": self.profile,
            "gate": self.gate,
            "escalations": self.escalations,
            "report_hash": self.report_hash,
        }
        return d


class VerifierBenchmark:
    """Reproducible benchmark of one verifier against a frozen fixture."""

    def __init__(self, gate: Optional[QualityGate] = None,
                 min_samples: int = DEFAULT_MIN_SAMPLES):
        self.gate = gate or QualityGate()
        self.min_samples = min_samples

    def run(self, verifier_fn: Callable[[object], bool],
            identity: VerifierIdentity,
            fixture: FrozenWorkloadFixture,
            repo_dir: str = ".",
            safety_critical: bool = True) -> BenchmarkReport:
        store = OutcomeStore()
        for case in fixture.cases:
            verdict = bool(verifier_fn(case.artifact))
            # Fixture labels are independent ground truth (VQ-R3).
            store.add(LabeledOutcome(
                case_id=case.case_id,
                verifier_id=identity.name,
                verdict=verdict,
                ground_truth=case.ground_truth,
                label_source=LabelSource.FROZEN_WORKLOAD,
                safety_critical=case.safety_critical,
            ))
        return self._report(store, identity, fixture, repo_dir, safety_critical)

    def _report(self, store, identity, fixture, repo_dir,
                safety_critical) -> BenchmarkReport:
        profile = VerifierQualityProfile.from_outcomes(
            identity, list(store), min_samples=self.min_samples)
        gate_result = self.gate.evaluate(profile, safety_critical)
        escalations = []
        if gate_result.decision in (GateDecision.ESCALATE_HITL,
                                    GateDecision.UNKNOWN):
            escalations.append(gate_result.to_dict())
        return BenchmarkReport(
            schema=BENCHMARK_SCHEMA,
            identity=_git_identity(repo_dir),
            config={
                "gate_threshold": self.gate.threshold,
                "min_samples": self.min_samples,
                "safety_critical": safety_critical,
                "verifier": identity.to_dict(),
            },
            runtime={"python": platform.python_version(),
                     "platform": platform.platform()},
            fixture={"name": fixture.name,
                     "fixture_hash": fixture.fixture_hash,
                     "case_count": len(fixture.cases),
                     "defect_count": len(fixture.defect_cases)},
            raw_labeled_outcomes=store.to_dicts(),
            profile=profile.to_dict(),
            gate=gate_result.to_dict(),
            escalations=escalations,
        )

    @staticmethod
    def recompute_from_outcomes(identity: VerifierIdentity,
                                raw_labeled_outcomes: list,
                                min_samples: int = DEFAULT_MIN_SAMPLES,
                                threshold: float = 0.95) -> dict:
        """Gate C: recompute profile + gate from retained raw outcomes."""
        store = OutcomeStore()
        for d in raw_labeled_outcomes:
            store.add(LabeledOutcome(
                case_id=d["case_id"], verifier_id=d["verifier_id"],
                verdict=bool(d["verdict"]),
                ground_truth=bool(d["ground_truth"]),
                label_source=LabelSource(d["label_source"]),
                confidence=d.get("confidence"),
                safety_critical=bool(d.get("safety_critical", False)),
            ))
        profile = VerifierQualityProfile.from_outcomes(
            identity, list(store), min_samples=min_samples)
        gate = QualityGate(threshold).evaluate(
            profile, safety_critical=True)
        return {"profile": profile.to_dict(), "gate": gate.to_dict(),
                "snapshot_hash": VerifierQualitySnapshot(identity, profile).snapshot_hash}
