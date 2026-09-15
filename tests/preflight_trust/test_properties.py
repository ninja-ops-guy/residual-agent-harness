"""Bounded metamorphic properties against a separately selected M4 checkout.

Hypothesis is optional. Its absence skips this module explicitly, while the
ordinary architecture/red-team modules remain collectable and runnable.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import importlib.util
from unittest.mock import patch

import pytest

hypothesis = pytest.importorskip("hypothesis", reason="preflight properties require optional Hypothesis")
from hypothesis import given, settings, strategies as st

settings.register_profile("trust-preflight", max_examples=60, deadline=None, derandomize=True, database=None)
settings.load_profile("trust-preflight")
SEGMENT = st.text(alphabet="abcdef0123456789_-", min_size=1, max_size=16)
PATHS = st.lists(SEGMENT, min_size=1, max_size=4).map("/".join)
BYTES = st.binary(max_size=256)


@given(PATHS)
def test_canonical_path_round_trip(api, path):
    safety = api("residual.factory.m4_safety", "artifact_parts")
    assert "/".join(safety.artifact_parts(path)) == path


@given(PATHS, st.sampled_from(["parent", "absolute", "duplicate", "dot", "git", "backslash", "nul"]))
def test_path_aliases_never_normalize_to_authorized_name(api, path, mutation):
    safety = api("residual.factory.m4_safety", "artifact_parts")
    invalid = {"parent": "../" + path, "absolute": "/" + path,
               "duplicate": path + "//leaf", "dot": path + "/./leaf",
               "git": path + "/.GiT/config", "backslash": path + "\\leaf",
               "nul": path + "\0"}[mutation]
    with pytest.raises(safety.M4SafetyError):
        safety.artifact_parts(invalid)


@given(st.dictionaries(SEGMENT, BYTES, min_size=1, max_size=8))
def test_snapshot_matches_independent_hashes_and_ignores_creation_order(api, files):
    safety = api("residual.factory.m4_safety", "snapshot", "apply_artifact")
    with tempfile.TemporaryDirectory() as directory:
        a, b = Path(directory) / "a", Path(directory) / "b"
        a.mkdir(); b.mkdir()
        for name, data in files.items():
            safety.apply_artifact(a, name, data)
        for name, data in reversed(list(files.items())):
            safety.apply_artifact(b, name, data)
        first = safety.snapshot(a)
        assert first == safety.snapshot(b)
        assert first == {name: ("file", 0o644, hashlib.sha256(data).hexdigest()) for name, data in files.items()}
        changed = next(iter(files))
        safety.apply_artifact(b, changed, files[changed] + b"\0")
        assert safety.snapshot(b) != first
        safety.apply_artifact(b, changed, files[changed])
        assert safety.snapshot(b) == first
        (b / changed).chmod(0o755)
        assert safety.snapshot(b) != first


@given(PATHS, BYTES)
def test_write_delete_round_trip_preserves_unrelated_bytes(api, path, data):
    safety = api("residual.factory.m4_safety", "snapshot", "apply_artifact")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "sentinel.txt").write_bytes(b"unchanged")
        safety.apply_artifact(root, path, data)
        assert (root / path).read_bytes() == data
        safety.apply_artifact(root, path, None)
        assert not (root / path).exists()
        assert (root / "sentinel.txt").read_bytes() == b"unchanged"
        # Empty parent directories remain visible; deletion is not tree equivalence.
        assert "sentinel.txt" in safety.snapshot(root)


def receipt(api, data=b"payload"):
    r = api("residual.factory.evidence_receipts", "WorkerReceipt", "ArtifactBinding")
    return r.WorkerReceipt(
        receipt_id="receipt", execution_plan_hash="1" * 64, task_id="task", worker_id="worker",
        swarm_id="swarm", attempt_id="attempt", engine_name="fixture", engine_version="1",
        input_commit="a" * 40, output_commit="b" * 40, contract_hash="2" * 64,
        artifacts=(r.ArtifactBinding("out.txt", hashlib.sha256(data).hexdigest(), len(data)),),
        requirements_met=(("R1", True),), verification_results=(("check", "pass"),),
        overall_verdict="pass", verifier_identity="station:fixture", verifier_revision="3" * 64,
        issued_at_ns=1, station_key_id="4" * 64, station_signature="00")


@given(BYTES)
def test_receipt_json_roundtrip_and_mapping_order_invariance(api, data):
    r = receipt(api, data)
    encoded = json.loads(json.dumps(r.to_dict(), ensure_ascii=False))
    reverse = dict(reversed(list(encoded.items())))
    assert type(r).from_dict(reverse) == r
    assert type(r).from_dict(reverse).receipt_hash == r.receipt_hash


@given(st.sampled_from(["task_id", "attempt_id", "input_commit", "verifier_identity", "engine_version"]), SEGMENT)
def test_receipt_metadata_tampering_invalidates_retained_hash(api, field, value):
    r = receipt(api)
    document = r.to_dict()
    document[field] += value
    evidence = api("residual.factory.evidence_receipts", "EvidenceError")
    with pytest.raises(evidence.EvidenceError):
        type(r).from_dict(document)


@given(st.sampled_from(["artifacts", "requirements_met", "verification_results"]), st.sampled_from([None, 1, True, "invalid"]))
def test_malformed_receipt_collection_is_rejected(api, field, value):
    r = receipt(api)
    document = r.to_dict(); document[field] = value
    evidence = api("residual.factory.evidence_receipts", "EvidenceError")
    with pytest.raises(evidence.EvidenceError):
        type(r).from_dict(document)


@given(st.integers(min_value=-255, max_value=255).filter(lambda x: x != 0), PATHS)
def test_unvalidated_git_base_is_unknown_not_absent(api, code, path):
    git = api("residual.factory.m4_git_evidence", "read_base_blob")
    with patch.object(git, "_run", return_value=(code, b"")):
        result = git.read_base_blob(Path("."), "a" * 40, path)
    assert result.state is git.GitEvidenceState.UNKNOWN
    assert result.data is None


@given(PATHS, BYTES)
def test_git_present_roundtrip_with_independent_object_identity(api, path, data):
    git = api("residual.factory.m4_git_evidence", "read_base_blob")
    commit = "a" * 40
    oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest().encode()
    responses = [(0, commit.encode() + b"\n"),
                 (0, b"100644 blob " + oid + b"\t" + path.encode() + b"\0"),
                 (0, str(len(data)).encode()), (0, data), (0, oid + b"\n")]
    with patch.object(git, "_run", side_effect=responses):
        result = git.read_base_blob(Path("."), commit, path)
    assert result.state is git.GitEvidenceState.PRESENT and result.data == data


@given(st.binary(max_size=80).filter(lambda b: bool(b) and b"\t" not in b))
def test_malformed_git_listing_is_error_not_absent(api, listing):
    git = api("residual.factory.m4_git_evidence", "read_base_blob")
    commit = "a" * 40
    with patch.object(git, "_run", side_effect=[(0, commit.encode()), (0, listing)]):
        result = git.read_base_blob(Path("."), commit, "candidate.txt")
    assert result.state is git.GitEvidenceState.ERROR


def scheduler(api):
    m = api("residual.factory.models", "ExecutionPlan", "Requirement", "FactoryTask")
    s = api("residual.factory.m4_scheduler", "M4AdaptiveScheduler", "SchedulerNode")
    market = api("residual.assurance.market", "VerifiedComputeMarket", "MarketProfile")
    plan = m.ExecutionPlan("independent trust preflight", (m.Requirement("R1", "test", ("unit",)),),
                           (m.FactoryTask("task", "test", ("R1",)),))
    pool = market.VerifiedComputeMarket()
    pool.register(market.MarketProfile("fixture@1", frozenset({"python"}), .01, 1., location="local"))
    return s.M4AdaptiveScheduler(plan, pool, (s.SchedulerNode("node", "fixture@1", "local", frozenset({"python"}), 8),))


@given(st.lists(st.tuples(st.integers(0, 30), st.integers(0, 30), st.integers(0, 10)), min_size=1, max_size=20))
def test_scheduler_transition_sequences_preserve_capacity_and_plan(api, sequence):
    s = api("residual.factory.m4_scheduler", "SchedulerCapacity", "SchedulerMeasurements")
    controller = scheduler(api)
    before = controller.plan.graph_hash
    capacity = s.SchedulerCapacity(4, 2, max_workers=8, max_verifiers=4)
    for ready, blocked, conflicts in sequence:
        measure = s.SchedulerMeasurements("0" * 64, .5, 0., ready, 0., ready, blocked, 1, 2, conflicts, 10)
        next_capacity, actions = controller.resize(measure, capacity)
        assert 1 <= next_capacity.workers <= 8 and 1 <= next_capacity.verifiers <= 4
        assert controller.plan.graph_hash == before
        assert all(a.measurement_hash == measure.measurement_hash for a in actions)
        if conflicts > controller.policy.integration_conflict_threshold:
            assert next_capacity == capacity and all(a.action == "pause" for a in actions)
        capacity = next_capacity


@settings(max_examples=10, deadline=None)
@given(st.dictionaries(SEGMENT.map(lambda x: x + ".txt"), BYTES, min_size=1, max_size=4))
def test_accepted_git_tree_equals_receipted_bytes_under_fixture_verification(api, files):
    """Reuse the target's setup helper; independently derive accepted-byte oracle.

    This exercises Git, the real EvidenceBus, signing, materialization and M4.
    The three reviewed no-op fixture checks do NOT establish verifier isolation.
    """
    package = api("residual")
    integrator = api("residual.factory.m4_integrator", "INTEGRATION_SCHEMA")
    if integrator.INTEGRATION_SCHEMA != "factory-integration-receipt-v2":
        pytest.skip("target lacks pinned PR81 integration receipt v2")
    fixture_path = Path(package.__file__).parent.parent / "tests/test_factory_m4_integrator.py"
    if not fixture_path.exists():
        pytest.skip("source checkout setup fixture unavailable; install alone cannot run tree integration")
    spec = importlib.util.spec_from_file_location("_independent_trust_fixture", fixture_path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    fixture = module.M4IntegratorTests(methodName="runTest")
    fixture.setUp()
    try:
        r = fixture.issue("task1", "R1", artifacts=files, index=1)
        plan = fixture.m4.integration_plan((r.receipt_hash,))
        outcome = fixture.integrator.integrate(plan, policy=fixture.policy(), station_identity=fixture.identity)
        git = api("residual.factory.runtime_workspace", "git").git
        commit = outcome.receipt.output_commit
        assert git(fixture.repo, "rev-parse", commit + "^{tree}").decode().strip() == outcome.output_tree
        assert outcome.receipt.verify_signature(fixture.identity.public_bytes())
        assert outcome.receipt.evidence_level == "development_fixture"
        expected = {"shared.txt": b"a\nb\nc\n", "base.txt": b"base\n", **files}
        actual_names = git(fixture.repo, "ls-tree", "-r", "--name-only", "-z", commit).split(b"\0")[:-1]
        assert {n.decode() for n in actual_names} == set(expected)
        for name, data in expected.items():
            assert git(fixture.repo, "show", f"{commit}:{name}") == data
    finally:
        fixture.tearDown()
