"""SPEC-SWARM-VQ-002: Verifier Quality Framework.

Measures and gates the quality of the acceptance boundary instead of
assuming verifier correctness. Public API re-exported here.
"""
from .identity import VerifierIdentity, hash_payload
from .outcomes import LabeledOutcome, LabelSource, OutcomeStore, SelfReportRejected
from .profile import VerifierQualityProfile, wilson_interval
from .gate import QualityGate, GateDecision, EscalationError
from .ensemble import AggregationPolicy, VerifierEnsemble
from .frozen import FrozenWorkloadFixture, load_frozen_fixture
from .snapshot import VerifierQualitySnapshot, attach_snapshot_to_receipt
from .benchmark import VerifierBenchmark, BenchmarkReport

__all__ = [
    "VerifierIdentity", "hash_payload",
    "LabeledOutcome", "LabelSource", "OutcomeStore", "SelfReportRejected",
    "VerifierQualityProfile", "wilson_interval",
    "QualityGate", "GateDecision", "EscalationError",
    "AggregationPolicy", "VerifierEnsemble",
    "FrozenWorkloadFixture", "load_frozen_fixture",
    "VerifierQualitySnapshot", "attach_snapshot_to_receipt",
    "VerifierBenchmark", "BenchmarkReport",
]

VQ_SCHEMA = "residual.vq.v1"
