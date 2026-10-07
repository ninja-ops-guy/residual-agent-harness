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


def make_identity(name="vq-test-verifier", impl_marker=1):
    return VerifierIdentity.build(
        name=name,
        implementation={"logic": "contains_expected", "marker": impl_marker},
        configuration={"timeout_ms": 100},
        policy={"mode": "strict"},
    )


def make_outcome(case_id, verdict, truth, source=LabelSource.INDEPENDENT_AUDIT,
                 confidence=None, safety_critical=True):
    return LabeledOutcome(case_id=case_id, verifier_id="vq-test-verifier",
                          verdict=verdict, ground_truth=truth,
                          label_source=source, confidence=confidence,
                          safety_critical=safety_critical)


# ---------------------------------------------------------------- VQ-R1

class TestR1QualityProfile:
    def test_profile_fields(self):
        ident = make_identity()
        outcomes = [
            make_outcome(f"c{i}", verdict=True, truth=True) for i in range(9)
        ] + [make_outcome("c9", verdict=True, truth=False),
             make_outcome("c10", verdict=False, truth=True),
             make_outcome("c11", verdict=False, truth=False)]
        p = VerifierQualityProfile.from_outcomes(ident, outcomes, min_samples=2)
        assert p.sample_count == 12
        assert p.precision.estimate == pytest.approx(0.9)
        assert p.recall.estimate == pytest.approx(0.9)
        assert p.coverage.estimate == pytest.approx(1.0)
        assert p.false_accept.estimate == pytest.approx(0.5)
        assert p.false_reject.estimate == pytest.approx(0.1)

    def test_calibration_from_confidence(self):
        ident = make_identity()
        outcomes = [
            make_outcome("a", True, True, confidence=0.9),
            make_outcome("b", True, True, confidence=0.9),
            make_outcome("c", True, False, confidence=0.9),
            make_outcome("d", False, False, confidence=0.8),
            make_outcome("e", False, True, confidence=0.8),
        ]
        p = VerifierQualityProfile.from_outcomes(ident, outcomes, min_samples=2)
        # errors: |.9-1|*2 + |.9-0| + |.8-1| + |.8-0| = .2+.9+.2+.8=2.1 /5=.42
        assert p.calibration.estimate == pytest.approx(1 - 0.42)
        assert p.calibration.status == "KNOWN"

    def test_profile_rejects_non_outcomes(self):
        with pytest.raises(TypeError):
            VerifierQualityProfile.from_outcomes(make_identity(), [{"x": 1}])


# ---------------------------------------------------------------- VQ-R2

class TestR2VersionedIdentity:
    def test_identity_hashes_and_revision(self):
        ident = make_identity()
        d = ident.to_dict()
        for f in ("implementation_hash", "configuration_hash", "policy_hash",
                  "revision"):
            assert d[f] and isinstance(d[f], str)
        assert d["proof_hash"] is None

    def test_optional_proof_hash(self):
        ident = VerifierIdentity.build(
            name="v", implementation={"a": 1}, configuration={"b": 2},
            policy={"c": 3}, proof={"theorem": "sound"})
        assert ident.proof_hash

    def test_component_change_changes_revision(self):
        a = make_identity(impl_marker=1)
        b = make_identity(impl_marker=2)
        assert a.revision != b.revision

    def test_identity_requires_hashes(self):
        from residual.core import ContractError
        with pytest.raises(ContractError):
            VerifierIdentity(name="", implementation_hash="x",
                             configuration_hash="y", policy_hash="z")


# ---------------------------------------------------------------- VQ-R3

class TestR3IndependentLabelsOnly:
    def test_self_report_rejected_at_construction(self):
        with pytest.raises(SelfReportRejected):
            make_outcome("s1", True, True,
                         source=LabelSource.WORKER_SELF_REPORT)

    def test_store_accepts_independent_sources(self):
        store = OutcomeStore()
        for i, src in enumerate((LabelSource.INDEPENDENT_AUDIT,
                                 LabelSource.FROZEN_WORKLOAD,
                                 LabelSource.EXTERNAL_ORACLE)):
            store.add(make_outcome(f"c{i}", True, True, source=src))
        assert len(store) == 3

    def test_store_rejects_self_report_boundary(self):
        store = OutcomeStore()
        o = make_outcome("c0", True, True)
        # simulate a tampered object bypassing construction
        object.__setattr__(o, "label_source", LabelSource.WORKER_SELF_REPORT)
        with pytest.raises(SelfReportRejected):
            store.add(o)


# ---------------------------------------------------------------- VQ-R4

class TestR4FailClosedHITLEscalation:
    def degraded_profile(self, fp=3, tp=10, min_samples=2):
        ident = make_identity()
        outcomes = [make_outcome(f"tp{i}", True, True) for i in range(tp)]
        outcomes += [make_outcome(f"fp{i}", True, False) for i in range(fp)]
        return VerifierQualityProfile.from_outcomes(ident, outcomes,
                                                    min_samples=min_samples)

    def test_degraded_precision_escalates(self):
        gate = QualityGate(threshold=0.95)
        result = gate.evaluate(self.degraded_profile(), safety_critical=True)
        assert result.decision == GateDecision.ESCALATE_HITL
        assert "fail-closed" in result.reason

    def test_accept_or_escalate_raises_fail_closed(self):
        gate = QualityGate(threshold=0.95)
        with pytest.raises(EscalationError):
            gate.accept_or_escalate(self.degraded_profile(), safety_critical=True)

    def test_no_silent_acceptance_path(self):
        gate = QualityGate(threshold=0.95)
        # UNKNOWN precision on safety-critical verifier also fails closed.
        p = self.degraded_profile(min_samples=1000)
        assert p.precision.status == "UNKNOWN"
        with pytest.raises(EscalationError):
            gate.accept_or_escalate(p, safety_critical=True)

    def test_adequate_precision_accepts(self):
        ident = make_identity()
        outcomes = [make_outcome(f"c{i}", True, True) for i in range(200)]
        p = VerifierQualityProfile.from_outcomes(ident, outcomes, min_samples=5)
        result = QualityGate(0.95).evaluate(p, safety_critical=True)
        assert result.decision == GateDecision.ACCEPT

    def test_non_safety_critical_not_gated(self):
        result = QualityGate(0.95).evaluate(self.degraded_profile(),
                                            safety_critical=False)
        assert result.decision == GateDecision.ACCEPT


# ---------------------------------------------------------------- VQ-R5

class TestR5DeterministicEnsemble:
    def members(self):
        return {
            "v_len": lambda a: len(a) > 2,
            "v_alpha": lambda a: str(a).isalpha(),
            "v_lower": lambda a: str(a).islower(),
        }

    def test_majority_aggregation(self):
        e = VerifierEnsemble(self.members(), AggregationPolicy.MAJORITY)
        v = e.aggregate("abc")   # len ok, alpha ok, lower ok
        assert v.verdict and v.accepts == 3
        v2 = e.aggregate("ABC")  # lower fails
        assert v2.verdict and v2.accepts == 2

    def test_determinism_across_runs_and_order(self):
        a = VerifierEnsemble(self.members(), AggregationPolicy.MAJORITY)
        b = VerifierEnsemble(dict(reversed(list(self.members().items()))),
                             AggregationPolicy.MAJORITY)
        for cand in ("abc", "ABC", "ab", "a1", ""):
            assert a.aggregate(cand).to_dict() == b.aggregate(cand).to_dict()

    def test_unanimous_and_any(self):
        assert not VerifierEnsemble(self.members(),
                                    AggregationPolicy.UNANIMOUS).aggregate("ABC").verdict
        assert VerifierEnsemble(self.members(),
                                AggregationPolicy.ANY).aggregate("ab1").verdict

    def test_explicit_tie_break(self):
        two = {"y": lambda a: True, "n": lambda a: False}
        e = VerifierEnsemble(two, AggregationPolicy.MAJORITY, tie_break="reject")
        v = e.aggregate(object())
        assert v.tie and v.tie_break == "reject" and not v.verdict
        e2 = VerifierEnsemble(two, AggregationPolicy.MAJORITY, tie_break="accept")
        assert e2.aggregate(object()).verdict

    def test_empty_ensemble_rejected(self):
        from residual.core import ContractError
        with pytest.raises(ContractError):
            VerifierEnsemble({})


# ---------------------------------------------------------------- VQ-R6

class TestR6FrozenWorkloadDefectCases:
    def fixture(self):
        cases = tuple(
            [FixtureCase(f"good{i}", {"expected": 1, "value": 1}, True)
             for i in range(8)]
            + [FixtureCase(f"bad{i}", {"expected": 1, "value": 0}, False,
                           defect_kind="wrong_value") for i in range(4)]
        )
        return FrozenWorkloadFixture("recall-fixture", cases)

    def test_fixture_requires_known_defects(self):
        from residual.core import ContractError
        with pytest.raises(ContractError, match="known-defect"):
            FrozenWorkloadFixture("no-defects",
                                  (FixtureCase("g", {}, True),))

    def test_fixture_hash_stable_and_tamper_detected(self):
        f = self.fixture()
        payload = f.to_dict()
        assert load_frozen_fixture(payload).fixture_hash == f.fixture_hash
        payload["cases"][0]["ground_truth"] = False
        from residual.core import ContractError
        with pytest.raises(ContractError, match="hash mismatch"):
            load_frozen_fixture(payload)

    def test_roundtrip(self):
        f = self.fixture()
        assert loads_fixture(dumps_fixture(f)).fixture_hash == f.fixture_hash

    def test_recall_measured_from_defect_cases(self):
        f = self.fixture()
        # verifier that catches half the defects
        caught = {"bad0", "bad1"}
        outcomes = []
        for c in f.cases:
            verdict = c.ground_truth or (c.case_id in caught)
            outcomes.append(make_outcome(c.case_id, verdict, c.ground_truth,
                                         source=LabelSource.FROZEN_WORKLOAD))
        p = VerifierQualityProfile.from_outcomes(make_identity(), outcomes,
                                                 min_samples=2)
        assert p.recall.estimate == pytest.approx(1.0)
        assert p.precision.estimate == pytest.approx(0.8)


# ---------------------------------------------------------------- VQ-R7

class TestR7AdversarialVerifier:
    """Adversarial cases engineered to induce false acceptance/rejection."""

    def adversarial_fixture(self):
        # look-alike artifacts: near-correct defects + unusual-but-correct
        cases = [
            # adversarial false-accept bait: defect hidden in near-match
            FixtureCase("fa_bait_1", {"expected": "abc", "value": "abc\x00"},
                        False, defect_kind="hidden_suffix"),
            FixtureCase("fa_bait_2", {"expected": "abc", "value": "abc "},
                        False, defect_kind="trailing_space"),
            FixtureCase("fa_bait_3", {"expected": "abc", "value": "abc"},
                        True),  # exact — must be accepted
            # adversarial false-reject bait: correct but unusual encoding
            FixtureCase("fr_bait_1", {"expected": "abc", "value": "ABC"},
                        True, defect_kind="case_variant_ok"),
            FixtureCase("fr_bait_2", {"expected": "abc", "value": " abc "},
                        True, defect_kind="padded_ok"),
        ]
        return FrozenWorkloadFixture("adversarial", tuple(cases))

    def test_induced_false_acceptance_measured(self):
        """Naive prefix verifier accepts hidden defects -> false accepts."""
        naive = lambda a: str(a["value"]).startswith(a["expected"])
        f = self.adversarial_fixture()
        outcomes = [make_outcome(c.case_id, naive(c.artifact), c.ground_truth,
                                 source=LabelSource.FROZEN_WORKLOAD)
                    for c in f.cases]
        p = VerifierQualityProfile.from_outcomes(make_identity(), outcomes,
                                                 min_samples=2)
        # fa_bait_1/2 accepted though defective
        assert any(o.is_false_accept for o in outcomes)
        assert p.false_accept.estimate > 0

    def test_induced_false_rejection_measured(self):
        """Strict exact verifier rejects correct variants -> false rejects."""
        strict = lambda a: a["value"] == a["expected"]
        f = self.adversarial_fixture()
        outcomes = [make_outcome(c.case_id, strict(c.artifact), c.ground_truth,
                                 source=LabelSource.FROZEN_WORKLOAD)
                    for c in f.cases]
        p = VerifierQualityProfile.from_outcomes(make_identity(), outcomes,
                                                 min_samples=2)
        assert any(o.is_false_reject for o in outcomes)
        assert p.false_reject.estimate > 0
        assert p.recall.estimate < 1.0


# ---------------------------------------------------------------- VQ-R8

class TestR8ReceiptSnapshot:
    def test_receipt_carries_quality_snapshot(self):
        ident = make_identity()
        outcomes = [make_outcome(f"c{i}", True, True) for i in range(10)]
        p = VerifierQualityProfile.from_outcomes(ident, outcomes, min_samples=2)
        snap = VerifierQualitySnapshot(ident, p)
        payload = {"task_id": "t1", "verdict": "pass"}
        out = attach_snapshot_to_receipt(payload, snap)
        assert out["verifier_quality"]["verifier_revision"] == ident.revision
        assert out["verifier_quality"]["snapshot_hash"] == snap.snapshot_hash
        assert out["verifier_quality"]["precision"]["estimate"] == 1.0
        # input not mutated
        assert "verifier_quality" not in payload

    def test_snapshot_hash_changes_with_profile(self):
        ident = make_identity()
        p1 = VerifierQualityProfile.from_outcomes(
            ident, [make_outcome(f"c{i}", True, True) for i in range(10)],
            min_samples=2)
        p2 = VerifierQualityProfile.from_outcomes(
            ident, [make_outcome(f"c{i}", True, True) for i in range(9)]
            + [make_outcome("c9", True, False)], min_samples=2)
        assert (VerifierQualitySnapshot(ident, p1).snapshot_hash
                != VerifierQualitySnapshot(ident, p2).snapshot_hash)


# ---------------------------------------------------------------- VQ-R9

class TestR9UncertaintyReporting:
    def test_insufficient_samples_unknown(self):
        p = VerifierQualityProfile.from_outcomes(
            make_identity(), [make_outcome("only", True, True)], min_samples=5)
        for m in (p.precision, p.recall, p.coverage, p.false_accept,
                  p.false_reject, p.calibration):
            assert m.status == "UNKNOWN"
            assert m.estimate is None and m.lower is None and m.upper is None

    def test_wilson_interval_properties(self):
        lo, hi = wilson_interval(9, 10)
        assert 0.5 < lo < 0.9 < hi <= 1.0
        assert wilson_interval(0, 0) == (0.0, 1.0)

    def test_interval_widens_as_n_shrinks(self):
        _, hi_big = wilson_interval(90, 100)
        _, hi_small = wilson_interval(9, 10)
        assert hi_small > hi_big

    def test_point_estimate_never_without_interval(self):
        p = VerifierQualityProfile.from_outcomes(
            make_identity(),
            [make_outcome(f"c{i}", True, True) for i in range(10)],
            min_samples=5)
        assert p.precision.lower is not None and p.precision.upper is not None
        assert p.precision.lower <= p.precision.estimate <= p.precision.upper


# ------------------------------------------------- acceptance / gates B,C

class TestAcceptanceBenchmark:
    def good_verifier(self, a):
        return a["value"] == a["expected"]

    def degraded_verifier(self, a):
        # false-accepts a third of defects
        if a["value"] == a["expected"]:
            return True
        return a.get("defect_tag", 0) % 3 == 0

    def bench_fixture(self, safety_critical=True):
        cases = []
        for i in range(100):  # n large enough for Wilson lower bound >= 0.95
            cases.append(FixtureCase(f"good{i}", {"expected": 1, "value": 1},
                                     True, safety_critical=safety_critical))
        for i in range(30):
            cases.append(FixtureCase(f"bad{i}",
                                     {"expected": 1, "value": 0,
                                      "defect_tag": i},
                                     False, defect_kind="wrong_value",
                                     safety_critical=safety_critical))
        return FrozenWorkloadFixture("bench", tuple(cases))

    def test_benchmark_demonstrates_profile_update_and_escalation(self):
        ident = make_identity()
        fixture = self.bench_fixture()
        bench = VerifierBenchmark()
        report = bench.run(self.degraded_verifier, ident, fixture)
        # profile updated from labeled outcomes
        assert report.profile["sample_count"] == 130
        assert report.profile["precision"]["estimate"] == pytest.approx(100 / 110)
        # fail-closed HITL escalation caused by degraded precision
        assert report.gate["decision"] == GateDecision.ESCALATE_HITL.value
        assert len(report.escalations) == 1
        assert report.raw_labeled_outcomes  # raw outcomes retained

    def test_reproduction_hash_matches(self):
        """Gate C: recompute profile from retained outcomes; hashes match."""
        ident = make_identity()
        fixture = self.bench_fixture()
        bench = VerifierBenchmark()
        report = bench.run(self.degraded_verifier, ident, fixture)
        recomputed = VerifierBenchmark.recompute_from_outcomes(
            ident, report.raw_labeled_outcomes)
        assert recomputed["profile"] == report.profile
        assert recomputed["gate"] == report.gate
        # deterministic full-report reproduction (repo identity aside)
        assert report.to_dict()["report_hash"] == report.report_hash

    def test_adequate_verifier_does_not_escalate(self):
        ident = make_identity()
        report = VerifierBenchmark().run(self.good_verifier, ident,
                                         self.bench_fixture())
        assert report.gate["decision"] == GateDecision.ACCEPT.value
        assert report.escalations == []


# --------------------------- Gate C: retained-evidence verification

EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "evidence" / "vq"
BENCHMARK_ARTIFACT = EVIDENCE_DIR / "vq-002-benchmark.json"


def _copy_evidence(tmp_path):
    """Copy the committed artifact + chunks to a temp dir for tampering.

    Tampering tests must never mutate the committed evidence.
    """
    dst = tmp_path / "vq"
    shutil.copytree(EVIDENCE_DIR, dst)
    return dst / "vq-002-benchmark.json", dst


class TestRetainedEvidenceVerification:
    def test_committed_artifact_verifies_green(self):
        """(a) The committed artifact + chunks verify end-to-end."""
        results = verify_artifact_profiles(BENCHMARK_ARTIFACT)
        assert set(results) == {"adequate", "degraded"}
        assert results["adequate"]["gate"]["decision"] == "accept"
        assert results["degraded"]["gate"]["decision"] == "escalate_hitl"
        loaded = load_verified_evidence(BENCHMARK_ARTIFACT)
        assert len(loaded["adequate"]) == 130
        assert len(loaded["degraded"]) == 130

    def test_tampered_chunk_content_refused(self, tmp_path):
        """(b) Flipping one bit in a chunk => fail-closed refusal."""
        artifact, evdir = _copy_evidence(tmp_path)
        chunk = evdir / "outcomes-adequate.part0.jsonl"
        body = chunk.read_bytes()
        chunk.write_bytes(body[:-2] + b"X\n")  # tamper last record
        with pytest.raises(EvidenceVerificationError):
            load_verified_evidence(artifact)

    def test_missing_chunk_refused(self, tmp_path):
        """(c) A referenced chunk absent from disk => fail-closed refusal."""
        artifact, evdir = _copy_evidence(tmp_path)
        (evdir / "outcomes-degraded.part2.jsonl").unlink()
        with pytest.raises(EvidenceVerificationError):
            load_verified_evidence(artifact)

    def test_corrupted_artifact_hash_field_refused(self, tmp_path):
        """(d) A wrong/absent hash recorded in the artifact => refusal."""
        artifact, evdir = _copy_evidence(tmp_path)
        doc = json.loads(artifact.read_text())
        entry = doc["raw_outcome_files"]["adequate"][0]
        entry["sha256"] = "0" * 64  # corrupt recorded hash
        artifact.write_text(json.dumps(doc, indent=1))
        with pytest.raises(EvidenceVerificationError):
            verify_artifact_profiles(artifact)

        doc = json.loads(BENCHMARK_ARTIFACT.read_text())
        del doc["raw_outcome_files"]["degraded"][1]["sha256"]  # absent hash
        artifact.write_text(json.dumps(doc, indent=1))
        with pytest.raises(EvidenceVerificationError):
            verify_artifact_profiles(artifact)

    def test_tamper_defeats_profile_match_not_just_hash(self, tmp_path):
        """A chunk whose recorded hash is updated to match tampered content
        still fails Gate C: the recomputed profile diverges from the
        profile recorded in the artifact."""
        artifact, evdir = _copy_evidence(tmp_path)
        chunk = evdir / "outcomes-degraded.part2.jsonl"
        lines = chunk.read_text().splitlines()
        rec = json.loads(lines[0])
        rec["verdict"] = not rec["verdict"]  # flip one verdict
        lines[0] = json.dumps(rec, sort_keys=True)
        chunk.write_text("\n".join(lines) + "\n")
        doc = json.loads(artifact.read_text())
        entry = next(e for e in doc["raw_outcome_files"]["degraded"]
                     if e["file"] == chunk.name)
        entry["sha256"] = hashlib.sha256(chunk.read_bytes()).hexdigest()
        artifact.write_text(json.dumps(doc, indent=1))
        with pytest.raises(EvidenceVerificationError):
            verify_artifact_profiles(artifact)

    def test_extra_chunk_on_disk_refused(self, tmp_path):
        """An unreferenced chunk in the evidence dir => fail-closed."""
        artifact, evdir = _copy_evidence(tmp_path)
        (evdir / "outcomes-stowaway.part0.jsonl").write_text("{}\n")
        with pytest.raises(EvidenceVerificationError):
            load_verified_evidence(artifact)
