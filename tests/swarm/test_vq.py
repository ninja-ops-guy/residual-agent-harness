"""SPEC-SWARM-VQ-002: verifier quality framework tests.

Every requirement VQ-R1..VQ-R9 maps to at least one test below; the
traceability table lives in docs/swarm/vq-002.md.
"""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from residual.vq import (
    AggregationPolicy, EscalationError, FrozenWorkloadFixture, GateDecision,
    LabeledOutcome, LabelSource, OutcomeStore, QualityGate, SelfReportRejected,
    VerifierBenchmark, VerifierEnsemble, VerifierIdentity,
    VerifierQualityProfile, attach_snapshot_to_receipt, load_frozen_fixture,
    wilson_interval, VerifierQualitySnapshot,
)
from residual.vq.frozen import FixtureCase, dumps_fixture, loads_fixture
from residual.vq.profile import MetricEstimate
from residual.vq.evidence import (
    EvidenceVerificationError, load_verified_evidence,
    verify_artifact_profiles,
)
