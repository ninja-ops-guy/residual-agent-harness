"""Pure R0 tests for the RESIDUAL OpenShell adapter.

No OpenShell binary, network access, credentials, Docker daemon, or live Station
is required. These tests cover the deterministic contract/policy/evidence layer
only; they are not live OpenShell qualification.
"""
from __future__ import annotations

import hashlib
import unittest

from residual.core import ContractError, digest
from residual.engines.openshell_adapter import (
    OpenShellExecutionEngine,
    OpenShellExecutionError,
    build_execution_request,
)
from residual.engines.openshell_client import OpenShellRunResult, OpenShellSandboxState
from residual.engines.openshell_contracts import OpenShellArtifact, OpenShellLaunchConfig
from residual.engines.openshell_policy import (
    OpenShellPolicyEnvelope,
    compile_policy,
    diff_policy,
)
from residual.engines.protocol import ContextAssembly, EngineHealth, TaskSpec


IMAGE_DIGEST = "1" * 64
OUTPUT_DIGEST = "2" * 64
SOURCE_ID = "residual@fixture"
OPENSHELL_ID = "openshell@fixture"
AGENT_ID = "hermes@fixture"


def make_policy(**overrides):
    values = {
        "readable_paths": ("/workspace/input",),
        "writable_paths": ("/workspace/output",),
        "executable_paths": ("/usr/bin/python3",),
        "network_destinations": ("https://api.example.test",),
        "provider_refs": ("provider-test",),
        "resource_budget": {"memory_mb": 512, "pids": 32},
        "inference_route_ref": "route-test",
    }
    values.update(overrides)
    return OpenShellPolicyEnvelope(**values)


def make_launch(**overrides):
    values = {
        "mission_id": "mission-1",
        "attempt_id": "attempt-1",
        "authority_ref": "authority-owner-gate-1",
        "agent_profile": "openshell/direct",
        "agent_command_argv": ("python3", "/workspace/input/agent.py"),
        "image_ref": "fixture:locked",
        "image_digest": IMAGE_DIGEST,
        "compute_driver_requirement": "docker",
        "sandbox_profile": "r0-fixture",
        "provider_refs": ("provider-test",),
        "inference_route_ref": "route-test",
        "resource_budget": {"memory_mb": 512, "pids": 32},
        "timeout_s": 30,
        "expected_outputs": ("/workspace/output/result.txt",),
        "output_contract_digest": OUTPUT_DIGEST,
        "correlation_ids": {"mission": "mission-1"},
        "created_at": "2026-09-30T14:00:00Z",
    }
    values.update(overrides)
    return OpenShellLaunchConfig(**values)


def make_task(metadata=None):
    return TaskSpec(
        task_id="task-1",
        capability="sandboxed_execution",
        input={"instruction": "write deterministic fixture"},
        metadata=metadata or {"token_budget": 100},
    )


class FakeClient:
    def __init__(self, state, run_result, *, healthy=True, destroy_fails=False):
        self.state = state
        self.run_result = run_result
        self.healthy = healthy
        self.destroy_fails = destroy_fails
        self.created = 0
        self.run_calls = 0
        self.destroyed = []

    def health(self):
        return self.healthy

    def create_sandbox(self, request, policy):
        self.created += 1
        self.request = request
        self.policy = policy
        return self.state

    def inspect_sandbox(self, sandbox_id):
        self.inspected_id = sandbox_id
        return self.state

    def run(self, sandbox_id, request):
        self.run_calls += 1
        self.run_request = request
        return self.run_result

    def destroy_sandbox(self, sandbox_id):
        self.destroyed.append(sandbox_id)
        if self.destroy_fails:
            raise RuntimeError("fixture cleanup failure")


def make_state(policy_digest, **overrides):
    values = {
        "sandbox_id": "sandbox-1",
        "generation": "generation-1",
        "openshell_identity": OPENSHELL_ID,
        "nemoclaw_identity": None,
        "compute_driver": "docker",
        "platform_class": "linux-x86_64-fixture",
        "agent_identity": AGENT_ID,
        "image_digest": IMAGE_DIGEST,
        "residual_policy_digest": policy_digest,
        "base_policy_digest": "5" * 64,
        "effective_policy_digest": "6" * 64,
        "policy_revision": "policy-rev-1",
        "provider_attachment_refs": ("provider-test",),
        "inference_route_ref": "route-test",
    }
    values.update(overrides)
    return OpenShellSandboxState(**values)


def make_success(**overrides):
    values = {
        "candidate": {"result": "ok"},
        "normalized_outcome": "SUCCEEDED",
        "vendor_outcome": "completed",
        "exit_code": 0,
        "stdout": b"fixture stdout",
        "stderr": b"",
        "artifacts": {"/workspace/output/result.txt": b"exact artifact bytes"},
        "lifecycle_events": ({"state": "RUNNING"}, {"state": "TERMINAL"}),
        "security_observations": ({"type": "network", "decision": "allow"},),
        "first_failure": None,
        "started_at": "2026-09-30T14:00:01Z",
        "ended_at": "2026-09-30T14:00:02Z",
    }
    values.update(overrides)
    return OpenShellRunResult(**values)


def make_engine(client, launch=None, policy=None, capabilities=("sandboxed_execution",)):
    launch = launch or make_launch()
    policy = policy or make_policy()
    return OpenShellExecutionEngine(
        client=client,
        launch_factory=lambda _task, _context: launch,
        policy_factory=lambda _task, _context: policy,
        residual_source_identity=SOURCE_ID,
        expected_openshell_identity=OPENSHELL_ID,
        expected_agent_identity=AGENT_ID,
        expected_nemoclaw_identity=None,
        qualified_capabilities=capabilities,
    )


class OpenShellContractTests(unittest.TestCase):
    def test_request_digest_is_deterministic_and_token_budget_is_not_secret(self):
        task = make_task({"token_budget": 100})
        context = ContextAssembly(values={"fixture": True})
        policy = compile_policy(make_policy())
        launch = make_launch()
        first = build_execution_request(
            task, context, launch, policy, engine_name="openshell", engine_version="r0",
        )
        second = build_execution_request(
            task, context, launch, policy, engine_name="openshell", engine_version="r0",
        )
        self.assertEqual(first.request_digest, second.request_digest)
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(first.base_policy_digest, policy.policy_digest)

    def test_inline_api_key_is_rejected_before_request_creation(self):
        task = make_task({"api_key": "do-not-forward"})
        with self.assertRaisesRegex(ContractError, "inline secret"):
            build_execution_request(
                task,
                ContextAssembly(values={}),
                make_launch(),
                compile_policy(make_policy()),
                engine_name="openshell",
                engine_version="r0",
            )

    def test_launch_inline_access_token_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "inline secret"):
            make_launch(correlation_ids={"access_token": "secret"})

    def test_artifact_digest_changes_on_one_byte_mutation(self):
        a = OpenShellArtifact.from_bytes(
            "a", "/workspace/output/a", b"abc", producing_request_digest="a" * 64,
        )
        b = OpenShellArtifact.from_bytes(
            "a", "/workspace/output/a", b"abd", producing_request_digest="a" * 64,
        )
        self.assertNotEqual(a.sha256, b.sha256)
        self.assertEqual(a.byte_length, b.byte_length)


class OpenShellPolicyTests(unittest.TestCase):
    def test_policy_is_canonical_and_default_deny(self):
        first = compile_policy(make_policy(
            network_destinations=("https://b.test", "https://a.test"),
        ))
        second = compile_policy(make_policy(
            network_destinations=("https://a.test", "https://b.test"),
        ))
        self.assertEqual(first.policy_digest, second.policy_digest)
        self.assertEqual(first.default_action, "deny")

    def test_broad_network_or_filesystem_policy_is_rejected(self):
        with self.assertRaisesRegex(ContractError, "broad network"):
            make_policy(network_destinations=("*",))
        with self.assertRaisesRegex(ContractError, "broad filesystem"):
            make_policy(writable_paths=("/",))

    def test_only_network_change_is_dynamic_in_r0(self):
        current = compile_policy(make_policy())
        network = compile_policy(make_policy(
            network_destinations=("https://other.example.test",),
        ))
        network_delta = diff_policy(current, network)
        self.assertTrue(network_delta.has_changes)
        self.assertFalse(network_delta.requires_recreate)
        self.assertEqual(network_delta.dynamic_changes, ("network.destinations",))

        filesystem = compile_policy(make_policy(
            writable_paths=("/workspace/other",),
        ))
        fs_delta = diff_policy(current, filesystem)
        self.assertTrue(fs_delta.requires_recreate)
        self.assertIn("filesystem", fs_delta.static_changes)


class OpenShellAdapterTests(unittest.TestCase):
    def test_success_binds_policy_identity_artifacts_and_non_authority_metadata(self):
        policy = compile_policy(make_policy())
        client = FakeClient(make_state(policy.policy_digest), make_success())
        engine = make_engine(client)

        self.assertEqual(engine.health(), EngineHealth.HEALTHY)
        self.assertTrue(engine.supports("sandboxed_execution"))
        self.assertFalse(engine.supports("gpu_execution"))

        result = engine.execute(make_task(), ContextAssembly(values={"fixture": True}))
        self.assertEqual(result.candidate, {"result": "ok"})
        self.assertEqual(client.run_calls, 1)
        self.assertEqual(client.destroyed, ["sandbox-1"])

        metadata = result.raw_metadata
        self.assertEqual(metadata["policy_digest"], policy.policy_digest)
        self.assertEqual(metadata["normalized_outcome"], "SUCCEEDED")
        self.assertEqual(metadata["candidate_state"], "unverified")
        self.assertFalse(metadata["merge_performed"])
        self.assertFalse(metadata["station_receipt_issued"])
        self.assertTrue(metadata["residual_policy_authoritative"])

        evidence = metadata["openshell_evidence"]
        self.assertEqual(evidence["requested_policy_digest"], policy.policy_digest)
        self.assertEqual(evidence["base_policy_digest"], "5" * 64)
        self.assertEqual(evidence["effective_policy_digest"], "6" * 64)
        self.assertEqual(evidence["openshell_identity"], OPENSHELL_ID)
        self.assertEqual(evidence["agent_identity"], AGENT_ID)
        manifest = metadata["artifact_manifest"]
        self.assertEqual(len(manifest), 1)
        self.assertEqual(
            manifest[0]["sha256"],
            hashlib.sha256(b"exact artifact bytes").hexdigest(),
        )
        self.assertEqual(
            evidence["artifact_manifest_digest"],
            digest(manifest),
        )

    def test_policy_translation_mismatch_fails_before_agent_run(self):
        policy = compile_policy(make_policy())
        client = FakeClient(
            make_state(policy.policy_digest, residual_policy_digest="f" * 64),
            make_success(),
        )
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("residual_policy_digest", caught.exception.reason)
        self.assertEqual(client.run_calls, 0)
        self.assertEqual(client.destroyed, ["sandbox-1"])

    def test_provider_enriched_effective_policy_may_differ_from_requested_policy(self):
        policy = compile_policy(make_policy())
        state = make_state(
            policy.policy_digest,
            base_policy_digest="7" * 64,
            effective_policy_digest="8" * 64,
        )
        client = FakeClient(state, make_success())
        result = make_engine(client).execute(make_task(), ContextAssembly(values={}))
        evidence = result.raw_metadata["openshell_evidence"]
        self.assertEqual(evidence["requested_policy_digest"], policy.policy_digest)
        self.assertEqual(evidence["base_policy_digest"], "7" * 64)
        self.assertEqual(evidence["effective_policy_digest"], "8" * 64)

    def test_missing_effective_policy_evidence_fails_before_agent_run(self):
        policy = compile_policy(make_policy())
        client = FakeClient(
            make_state(policy.policy_digest, effective_policy_digest=None),
            make_success(),
        )
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("effective_policy_digest_unavailable", caught.exception.reason)
        self.assertEqual(client.run_calls, 0)

    def test_driver_identity_mismatch_fails_closed(self):
        policy = compile_policy(make_policy())
        client = FakeClient(
            make_state(policy.policy_digest, compute_driver="podman"),
            make_success(),
        )
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertIn("compute_driver", caught.exception.reason)
        self.assertEqual(client.run_calls, 0)

    def test_undeclared_artifact_fails_closed(self):
        policy = compile_policy(make_policy())
        raw = make_success(artifacts={
            "/workspace/output/result.txt": b"exact artifact bytes",
            "/workspace/output/surprise.txt": b"undeclared",
        })
        client = FakeClient(make_state(policy.policy_digest), raw)
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("undeclared=", caught.exception.reason)

    def test_missing_expected_artifact_fails_closed(self):
        policy = compile_policy(make_policy())
        client = FakeClient(make_state(policy.policy_digest), make_success(artifacts={}))
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("missing=", caught.exception.reason)

    def test_inspected_sandbox_identity_must_match_created_identity(self):
        policy = compile_policy(make_policy())

        class IdentityDriftClient(FakeClient):
            def inspect_sandbox(self, sandbox_id):
                self.inspected_id = sandbox_id
                return make_state(policy.policy_digest, sandbox_id="sandbox-other")

        client = IdentityDriftClient(make_state(policy.policy_digest), make_success())
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("inspection identity", caught.exception.reason)
        self.assertEqual(client.run_calls, 0)
        self.assertEqual(client.destroyed, ["sandbox-1"])

    def test_policy_denial_preserves_first_failure_evidence(self):
        policy = compile_policy(make_policy())
        raw = make_success(
            candidate=None,
            normalized_outcome="POLICY_DENIED",
            vendor_outcome="denied",
            exit_code=77,
            first_failure={"class": "NETWORK_POLICY_DENIED"},
        )
        client = FakeClient(make_state(policy.policy_digest), raw)
        engine = make_engine(client)

        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        exc = caught.exception
        self.assertEqual(exc.outcome, "POLICY_DENIED")
        self.assertIsNotNone(exc.evidence)
        self.assertEqual(
            exc.evidence.first_failure["class"],
            "NETWORK_POLICY_DENIED",
        )
        self.assertEqual(client.destroyed, ["sandbox-1"])

    def test_success_with_hidden_first_failure_is_not_admissible(self):
        policy = compile_policy(make_policy())
        raw = make_success(first_failure={"class": "EARLIER_FAILURE"})
        client = FakeClient(make_state(policy.policy_digest), raw)
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIn("hidden retry", caught.exception.reason)

    def test_cleanup_failure_converts_success_to_unknown(self):
        policy = compile_policy(make_policy())
        client = FakeClient(
            make_state(policy.policy_digest),
            make_success(),
            destroy_fails=True,
        )
        engine = make_engine(client)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "UNKNOWN")
        self.assertIsNotNone(caught.exception.evidence)
        self.assertIn("cleanup failure", caught.exception.cleanup_error)

    def test_unhealthy_client_never_creates_sandbox(self):
        policy = compile_policy(make_policy())
        client = FakeClient(
            make_state(policy.policy_digest),
            make_success(),
            healthy=False,
        )
        engine = make_engine(client)
        self.assertEqual(engine.health(), EngineHealth.UNAVAILABLE)
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(make_task(), ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "ADAPTER_FAILED")
        self.assertEqual(client.created, 0)


if __name__ == "__main__":
    unittest.main()
