"""Execution-substrate SPI, qualification registry, routing, and self-build tests."""
from __future__ import annotations

import unittest

from residual.core import ContractError, digest
from residual.engines.openshell_adapter import OpenShellExecutionEngine, OpenShellExecutionError
from residual.engines.openshell_client import OpenShellRunResult, OpenShellSandboxState
from residual.engines.openshell_contracts import OpenShellLaunchConfig
from residual.engines.openshell_policy import OpenShellPolicyEnvelope, compile_policy
from residual.engines.protocol import ContextAssembly, TaskSpec
from residual.substrates.protocol import (
    ExecutionSubstrate,
    SubstrateHealth,
    SubstrateRuntimeIdentity,
)
from residual.substrates.qualification import (
    QualificationGate,
    SubstrateQualificationRecord,
    SubstrateQualificationRegistry,
    SubstrateQualificationTuple,
    inference_route_digest,
    provider_set_digest,
)
from residual.substrates.router import QualifiedSubstrateRouter, SubstrateRoutingError
from residual.substrates.self_build import (
    SelfBuildCompletionEvidence,
    SelfBuildContract,
    admit_self_build,
)


IMAGE = "1" * 64
POLICY = "2" * 64
EVIDENCE = "3" * 64
ROOT = "4" * 64
OPENSHELL_SOURCE = "openshell:v0.1.1@fixture"
OPENSHELL_VERSION = "0.1.1"


def qtuple(**overrides):
    values = {
        "substrate_name": "openshell",
        "substrate_version": OPENSHELL_VERSION,
        "substrate_source_identity": OPENSHELL_SOURCE,
        "driver": "docker",
        "platform_class": "linux-x86_64",
        "agent_profile": "openshell/direct",
        "agent_identity": "hermes@fixture",
        "image_digest": IMAGE,
        "requested_policy_digest": POLICY,
        "provider_set_digest": provider_set_digest(("provider-a",)),
        "inference_route_digest": inference_route_digest("route-a"),
    }
    values.update(overrides)
    return SubstrateQualificationTuple(**values)


def record(
    qt=None,
    *,
    status="PASS",
    capabilities=(
        "sandboxed_execution",
        "filesystem_policy",
        "network_policy",
        "artifact_manifest",
    ),
    attempt=1,
    evidence=EVIDENCE,
):
    qt = qt or qtuple()
    gate = QualificationGate(
        gate_id="Q0",
        status=status,
        evidence_digest=evidence,
        attempt=attempt,
        required=True,
    )
    return SubstrateQualificationRecord(
        qualification_tuple=qt,
        gates=(gate,),
        capabilities=capabilities,
        evidence_root_digest=ROOT,
        limitations=("gpu_execution:not_qualified",),
    )


class FakeSubstrate:
    name = "openshell"
    version = OPENSHELL_VERSION
    locality = "local"

    def __init__(self, *, health=SubstrateHealth.HEALTHY, driver="docker"):
        self._health = health
        self._driver = driver

    def substrate_identity(self):
        return SubstrateRuntimeIdentity(
            name=self.name,
            version=self.version,
            source_identity=OPENSHELL_SOURCE,
            driver=self._driver,
            platform_class="linux-x86_64",
            locality=self.locality,
        )

    def substrate_health(self):
        return self._health


class QualificationTests(unittest.TestCase):
    def test_pass_is_derived_from_required_gates(self):
        passed = record()
        self.assertEqual(passed.overall, "PASS")
        self.assertIn("sandboxed_execution", passed.qualified_capabilities)

        failed = record(status="FAIL")
        self.assertEqual(failed.overall, "FAIL")
        self.assertEqual(failed.qualified_capabilities, frozenset())

    def test_blocked_and_unknown_do_not_publish_capabilities(self):
        for status in ("BLOCKED", "UNKNOWN"):
            with self.subTest(status=status):
                item = record(status=status)
                self.assertEqual(item.overall, status)
                self.assertEqual(item.qualified_capabilities, frozenset())

    def test_registry_requires_pinning_when_multiple_passes_exist(self):
        qt = qtuple()
        registry = SubstrateQualificationRegistry()
        first = record(qt, attempt=1, evidence="5" * 64)
        second = record(qt, attempt=2, evidence="6" * 64)
        registry.add(first)
        registry.add(second)
        with self.assertRaisesRegex(ContractError, "multiple PASS"):
            registry.get(qt)
        self.assertEqual(
            registry.get(qt, record_digest=first.record_digest).record_digest,
            first.record_digest,
        )

    def test_registry_require_is_fail_closed_for_unqualified_capability(self):
        qt = qtuple()
        registry = SubstrateQualificationRegistry()
        item = record(qt, capabilities=("sandboxed_execution",))
        registry.add(item)
        with self.assertRaisesRegex(ContractError, "not qualified"):
            registry.require(qt, "gpu_execution", record_digest=item.record_digest)

    def test_tuple_digest_changes_with_driver_policy_provider_or_route(self):
        baseline = qtuple()
        variants = (
            qtuple(driver="podman"),
            qtuple(requested_policy_digest="7" * 64),
            qtuple(provider_set_digest=provider_set_digest(("provider-b",))),
            qtuple(inference_route_digest=inference_route_digest("route-b")),
        )
        for variant in variants:
            self.assertNotEqual(baseline.tuple_digest, variant.tuple_digest)


class RouterTests(unittest.TestCase):
    def test_router_implements_execution_substrate_protocol(self):
        self.assertIsInstance(FakeSubstrate(), ExecutionSubstrate)

    def test_router_requires_pinned_pass_and_runtime_identity_match(self):
        qt = qtuple()
        registry = SubstrateQualificationRegistry()
        item = record(qt)
        registry.add(item)

        router = QualifiedSubstrateRouter(registry)
        router.register(FakeSubstrate(), qt, record_digest=item.record_digest)
        selected = router.route(("sandboxed_execution", "filesystem_policy"))
        self.assertEqual(selected.qualification_record_digest, item.record_digest)

        bad_router = QualifiedSubstrateRouter(registry)
        with self.assertRaisesRegex(SubstrateRoutingError, "runtime identity"):
            bad_router.register(
                FakeSubstrate(driver="podman"),
                qt,
                record_digest=item.record_digest,
            )

    def test_router_rejects_unhealthy_or_missing_capabilities(self):
        qt = qtuple()
        registry = SubstrateQualificationRegistry()
        item = record(qt, capabilities=("sandboxed_execution",))
        registry.add(item)
        router = QualifiedSubstrateRouter(registry)
        router.register(
            FakeSubstrate(health=SubstrateHealth.UNAVAILABLE),
            qt,
            record_digest=item.record_digest,
        )
        with self.assertRaises(SubstrateRoutingError):
            router.route(("sandboxed_execution",))

        healthy = QualifiedSubstrateRouter(registry)
        healthy.register(FakeSubstrate(), qt, record_digest=item.record_digest)
        with self.assertRaisesRegex(SubstrateRoutingError, "missing=filesystem_policy"):
            healthy.route(("sandboxed_execution", "filesystem_policy"))


class SelfBuildTests(unittest.TestCase):
    def make_contract(self, **overrides):
        values = {
            "mission_id": "self-build-1",
            "authority_ref": "owner-gate-1",
            "source_identity": "residual@fixture",
            "disposable_target_id": "candidate/self-build-1",
            "allowed_write_paths": ("tests/fixtures/self_build/",),
            "test_commands": (("python", "-m", "unittest", "tests.test_fixture"),),
            "expected_artifacts": ("patch.diff",),
        }
        values.update(overrides)
        return SelfBuildContract(**values)

    def test_r0_self_build_cannot_hold_merge_or_repo_write_authority(self):
        for field in (
            "merge_authority",
            "repository_write_authority",
            "accepted_state_write_authority",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ContractError, "cannot hold"):
                    self.make_contract(**{field: True})

    def test_self_build_requires_exact_qualified_capabilities(self):
        qt = qtuple()
        registry = SubstrateQualificationRegistry()
        insufficient = record(
            qt,
            capabilities=("sandboxed_execution", "filesystem_policy"),
        )
        registry.add(insufficient)
        with self.assertRaisesRegex(ContractError, "artifact_manifest"):
            admit_self_build(
                self.make_contract(),
                qt,
                registry,
                record_digest=insufficient.record_digest,
            )

        registry = SubstrateQualificationRegistry()
        sufficient = record(qt)
        registry.add(sufficient)
        admission = admit_self_build(
            self.make_contract(),
            qt,
            registry,
            record_digest=sufficient.record_digest,
        )
        self.assertEqual(admission.verdict, "ADMITTED")
        self.assertEqual(admission.qualification_record_digest, sufficient.record_digest)

    def test_completion_proves_integration_without_accepted_state_authority(self):
        completion = SelfBuildCompletionEvidence(
            contract_digest="1" * 64,
            qualification_record_digest="2" * 64,
            artifact_manifest_digest="3" * 64,
            byte_verification_digest="4" * 64,
            independent_verifier_digest="5" * 64,
            deterministic_integration_receipt_digest="6" * 64,
            disposable_target_id="candidate/self-build-1",
        )
        self.assertEqual(completion.status, "SELF_BUILD_BOUNDED_PASS")
        self.assertFalse(completion.merge_performed)

        with self.assertRaisesRegex(ContractError, "cannot include merge"):
            SelfBuildCompletionEvidence(
                contract_digest="1" * 64,
                qualification_record_digest="2" * 64,
                artifact_manifest_digest="3" * 64,
                byte_verification_digest="4" * 64,
                independent_verifier_digest="5" * 64,
                deterministic_integration_receipt_digest="6" * 64,
                disposable_target_id="candidate/self-build-1",
                merge_performed=True,
            )


class FakeOpenShellClient:
    def __init__(self, state, result):
        self.state = state
        self.result = result
        self.created = 0
        self.destroyed = 0

    def health(self):
        return True

    def create_sandbox(self, request, policy):
        self.created += 1
        return self.state

    def inspect_sandbox(self, sandbox_id):
        return self.state

    def run(self, sandbox_id, request):
        return self.result

    def destroy_sandbox(self, sandbox_id):
        self.destroyed += 1


def openshell_policy():
    return OpenShellPolicyEnvelope(
        readable_paths=("/workspace/input",),
        writable_paths=("/workspace/output",),
        executable_paths=("/usr/bin/python3",),
        network_destinations=("https://api.example.test",),
        provider_refs=("provider-a",),
        resource_budget={"memory_mb": 512},
        inference_route_ref="route-a",
    )


def openshell_launch(policy_digest, **overrides):
    values = {
        "mission_id": "mission-1",
        "attempt_id": "attempt-1",
        "authority_ref": "owner-gate-1",
        "agent_profile": "openshell/direct",
        "agent_command_argv": ("python3", "/workspace/input/agent.py"),
        "image_ref": "fixture@sha256:" + IMAGE,
        "image_digest": IMAGE,
        "compute_driver_requirement": "docker",
        "sandbox_profile": "r0",
        "provider_refs": ("provider-a",),
        "inference_route_ref": "route-a",
        "resource_budget": {"memory_mb": 512},
        "timeout_s": 30,
        "expected_outputs": ("/workspace/output/result.txt",),
        "output_contract_digest": digest({"outputs": ["/workspace/output/result.txt"]}),
        "created_at": "2026-09-30T19:00:00Z",
    }
    values.update(overrides)
    return OpenShellLaunchConfig(**values)


class OpenShellQualificationBindingTests(unittest.TestCase):
    def make_fixture(self, *, qualified_image=IMAGE, launch_image=IMAGE):
        policy_envelope = openshell_policy()
        policy = compile_policy(policy_envelope)
        qt = qtuple(
            requested_policy_digest=policy.policy_digest,
            image_digest=qualified_image,
        )
        registry = SubstrateQualificationRegistry()
        item = record(qt)
        registry.add(item)
        state = OpenShellSandboxState(
            sandbox_id="sandbox-1",
            generation="g1",
            openshell_identity=OPENSHELL_SOURCE,
            nemoclaw_identity=None,
            compute_driver="docker",
            platform_class="linux-x86_64",
            agent_identity="hermes@fixture",
            image_digest=launch_image,
            residual_policy_digest=policy.policy_digest,
            base_policy_digest="7" * 64,
            effective_policy_digest="8" * 64,
            policy_revision="rev-1",
            provider_attachment_refs=("provider-a",),
            inference_route_ref="route-a",
        )
        run_result = OpenShellRunResult(
            candidate={"ok": True},
            normalized_outcome="SUCCEEDED",
            vendor_outcome="completed",
            exit_code=0,
            artifacts={"/workspace/output/result.txt": b"ok"},
            started_at="2026-09-30T19:00:01Z",
            ended_at="2026-09-30T19:00:02Z",
        )
        client = FakeOpenShellClient(state, run_result)
        launch = openshell_launch(policy.policy_digest, image_digest=launch_image)
        engine = OpenShellExecutionEngine(
            client=client,
            launch_factory=lambda _task, _ctx: launch,
            policy_factory=lambda _task, _ctx: policy_envelope,
            residual_source_identity="residual@fixture",
            expected_openshell_identity=OPENSHELL_SOURCE,
            expected_agent_identity="hermes@fixture",
            qualification_registry=registry,
            qualification_tuple=qt,
            qualification_record_digest=item.record_digest,
            openshell_version=OPENSHELL_VERSION,
            expected_driver="docker",
            expected_platform_class="linux-x86_64",
            qualified_capabilities=(),
        )
        return engine, client, item

    def test_exact_qualification_record_is_bound_into_engine_result(self):
        engine, client, item = self.make_fixture()
        task = TaskSpec("task-1", "sandboxed_execution", {"work": "fixture"})
        result = engine.execute(task, ContextAssembly(values={}))
        self.assertEqual(client.created, 1)
        self.assertEqual(
            result.raw_metadata["substrate_qualification_record_digest"],
            item.record_digest,
        )
        self.assertEqual(
            result.raw_metadata["substrate_qualification_tuple_digest"],
            item.qualification_tuple.tuple_digest,
        )

    def test_request_drift_from_qualified_image_blocks_before_sandbox_creation(self):
        engine, client, _item = self.make_fixture(
            qualified_image=IMAGE,
            launch_image="9" * 64,
        )
        task = TaskSpec("task-1", "sandboxed_execution", {"work": "fixture"})
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(task, ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "ADAPTER_FAILED")
        self.assertIn("image_digest", caught.exception.reason)
        self.assertEqual(client.created, 0)

    def test_unqualified_capability_blocks_before_sandbox_creation(self):
        engine, client, _item = self.make_fixture()
        task = TaskSpec("task-1", "gpu_execution", {"work": "fixture"})
        with self.assertRaises(OpenShellExecutionError) as caught:
            engine.execute(task, ContextAssembly(values={}))
        self.assertEqual(caught.exception.outcome, "ADAPTER_FAILED")
        self.assertIn("not qualified", caught.exception.reason)
        self.assertEqual(client.created, 0)


if __name__ == "__main__":
    unittest.main()
