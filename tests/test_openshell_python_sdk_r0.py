"""Pure tests for the exact-release OpenShell Python SDK binding seam."""
from __future__ import annotations

from dataclasses import dataclass

import unittest

from residual.engines.openshell_adapter import build_execution_request
from residual.engines.openshell_client import OpenShellSandboxState
from residual.engines.openshell_contracts import OpenShellLaunchConfig
from residual.engines.openshell_policy import OpenShellPolicyEnvelope, compile_policy
from residual.engines.openshell_python_sdk import (
    OpenShellSDKBindingError,
    PythonSDKOpenShellClient,
    PythonSDKReleaseBinding,
)
from residual.engines.protocol import ContextAssembly, TaskSpec


SDK_VERSION = "0.1.fixture"
SOURCE_ID = "openshell@5acaaba19281cb6b30171afeb8602ce83edd9e45"
IMAGE_DIGEST = "3" * 64
OUTPUT_DIGEST = "4" * 64


@dataclass
class Obj:
    version: str | None = None
    id: str | None = None
    name: str | None = None
    sandbox_id: str | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None


class FakeSDK:
    def __init__(self, *, version=SDK_VERSION):
        self.version = version
        self.calls = []
        self.sandbox_id = "os-sandbox-1"
        self.name = None

    def health(self):
        self.calls.append(("health",))
        return Obj(version=self.version)

    def create(self, *, workspace, spec, name, labels):
        self.calls.append(("create", workspace, spec, name, dict(labels)))
        self.name = name
        return Obj(id=self.sandbox_id, name=name)

    def wait_ready(self, name, *, workspace, timeout_seconds):
        self.calls.append(("wait_ready", name, workspace, timeout_seconds))

    def get(self, name, *, workspace):
        self.calls.append(("get", name, workspace))
        return Obj(id=self.sandbox_id, name=name)

    def exec(
        self,
        name,
        command,
        *,
        workspace,
        timeout_seconds,
        no_login_shell,
    ):
        self.calls.append(
            ("exec", name, tuple(command), workspace, timeout_seconds, no_login_shell)
        )
        return Obj(exit_code=0, stdout="candidate-output", stderr="")

    def delete(self, name, *, workspace, allow_missing):
        self.calls.append(("delete", name, workspace, allow_missing))
        return Obj(sandbox_id=self.sandbox_id)

    def wait_deleted(self, name, *, workspace, expected_sandbox_id):
        self.calls.append(("wait_deleted", name, workspace, expected_sandbox_id))


def make_policy():
    return compile_policy(OpenShellPolicyEnvelope(
        readable_paths=("/workspace/input",),
        writable_paths=("/workspace/output",),
        executable_paths=("/usr/bin/python3",),
        network_destinations=("https://api.example.test",),
        provider_refs=("provider-test",),
        resource_budget={"memory_mb": 256},
        inference_route_ref="route-test",
    ))


def make_request(policy):
    task = TaskSpec(
        task_id="task-sdk",
        capability="sandboxed_execution",
        input={"instruction": "fixture"},
        metadata={},
    )
    context = ContextAssembly(values={})
    launch = OpenShellLaunchConfig(
        mission_id="mission-sdk",
        attempt_id="attempt-sdk",
        authority_ref="owner-gate",
        agent_profile="openshell/direct",
        agent_command_argv=("python3", "/workspace/input/agent.py"),
        image_ref="fixture@sha256:" + IMAGE_DIGEST,
        image_digest=IMAGE_DIGEST,
        compute_driver_requirement="docker",
        sandbox_profile="sdk-fixture",
        provider_refs=("provider-test",),
        inference_route_ref="route-test",
        resource_budget={"memory_mb": 256},
        timeout_s=19,
        expected_outputs=("/workspace/output/result.txt",),
        output_contract_digest=OUTPUT_DIGEST,
        correlation_ids={},
        created_at="2026-09-30T15:00:00Z",
    )
    return build_execution_request(
        task,
        context,
        launch,
        policy,
        engine_name="openshell",
        engine_version="r0",
    )


def make_binding():
    def spec_factory(request, policy):
        return {
            "image_digest": request.image_digest,
            "policy_digest": policy.policy_digest,
            "providers": tuple(policy.providers),
        }

    def state_resolver(_sdk, ref, request, policy):
        return OpenShellSandboxState(
            sandbox_id=ref.id,
            generation="policy-v1",
            openshell_identity=SOURCE_ID,
            nemoclaw_identity=None,
            compute_driver=request.compute_driver_requirement,
            platform_class="linux-x86_64-fixture",
            agent_identity="fixture-agent@1",
            image_digest=request.image_digest,
            residual_policy_digest=policy.policy_digest,
            base_policy_digest="5" * 64,
            effective_policy_digest="6" * 64,
            policy_revision="1",
            provider_attachment_refs=request.provider_refs,
            inference_route_ref=request.inference_route_ref,
        )

    def artifact_collector(_sdk, _name, _workspace, paths):
        return {path: b"artifact:" + path.encode("utf-8") for path in paths}

    def observation_collector(_sdk, name, workspace):
        return (
            ({"state": "READY", "sandbox": name, "workspace": workspace},),
            ({"type": "fixture-security-observation"},),
        )

    def candidate_parser(exec_result, _artifacts):
        return {"stdout": exec_result.stdout}

    return PythonSDKReleaseBinding(
        sdk_version=SDK_VERSION,
        openshell_source_identity=SOURCE_ID,
        spec_factory=spec_factory,
        state_resolver=state_resolver,
        artifact_collector=artifact_collector,
        observation_collector=observation_collector,
        candidate_parser=candidate_parser,
    )


class PythonSDKBindingTests(unittest.TestCase):
    def test_version_mismatch_is_unhealthy_and_blocks_create(self):
        sdk = FakeSDK(version="wrong-version")
        client = PythonSDKOpenShellClient(
            sdk,
            workspace="default",
            binding=make_binding(),
        )
        self.assertFalse(client.health())
        policy = make_policy()
        request = make_request(policy)
        with self.assertRaisesRegex(OpenShellSDKBindingError, "version mismatch"):
            client.create_sandbox(request, policy)
        self.assertFalse(any(call[0] == "create" for call in sdk.calls))

    def test_public_sdk_lifecycle_is_request_bound(self):
        sdk = FakeSDK()
        client = PythonSDKOpenShellClient(
            sdk,
            workspace="default",
            binding=make_binding(),
        )
        policy = make_policy()
        request = make_request(policy)

        self.assertTrue(client.health())
        state = client.create_sandbox(request, policy)
        self.assertEqual(state.sandbox_id, sdk.sandbox_id)
        self.assertEqual(state.residual_policy_digest, policy.policy_digest)
        self.assertEqual(state.base_policy_digest, "5" * 64)
        self.assertEqual(state.effective_policy_digest, "6" * 64)
        self.assertEqual(state.openshell_identity, SOURCE_ID)

        inspected = client.inspect_sandbox(state.sandbox_id)
        self.assertEqual(inspected.sandbox_id, state.sandbox_id)

        result = client.run(state.sandbox_id, request)
        self.assertEqual(result.normalized_outcome, "SUCCEEDED")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.candidate, {"stdout": "candidate-output"})
        self.assertEqual(
            result.artifacts["/workspace/output/result.txt"],
            b"artifact:/workspace/output/result.txt",
        )

        create = next(call for call in sdk.calls if call[0] == "create")
        self.assertEqual(create[1], "default")
        self.assertEqual(create[2]["policy_digest"], policy.policy_digest)
        self.assertEqual(
            create[4]["residual_request_digest"],
            request.request_digest,
        )
        exec_call = next(call for call in sdk.calls if call[0] == "exec")
        self.assertEqual(exec_call[2], request.agent_command_argv)
        self.assertEqual(exec_call[4], request.timeout_s)
        self.assertTrue(exec_call[5])

        client.destroy_sandbox(state.sandbox_id)
        self.assertTrue(any(call[0] == "delete" for call in sdk.calls))
        self.assertTrue(any(call[0] == "wait_deleted" for call in sdk.calls))
        with self.assertRaisesRegex(OpenShellSDKBindingError, "unknown"):
            client.inspect_sandbox(state.sandbox_id)

    def test_different_request_cannot_reuse_created_sandbox(self):
        sdk = FakeSDK()
        client = PythonSDKOpenShellClient(
            sdk,
            workspace="default",
            binding=make_binding(),
        )
        policy = make_policy()
        first = make_request(policy)
        state = client.create_sandbox(first, policy)

        task = TaskSpec("different-task", "sandboxed_execution", {"x": 2}, {})
        second = build_execution_request(
            task,
            ContextAssembly(values={}),
            OpenShellLaunchConfig(
                mission_id="mission-sdk",
                attempt_id="attempt-sdk-2",
                authority_ref="owner-gate",
                agent_profile="openshell/direct",
                agent_command_argv=("python3", "/workspace/input/agent.py"),
                image_ref="fixture@sha256:" + IMAGE_DIGEST,
                image_digest=IMAGE_DIGEST,
                compute_driver_requirement="docker",
                sandbox_profile="sdk-fixture",
                provider_refs=("provider-test",),
                inference_route_ref="route-test",
                resource_budget={"memory_mb": 256},
                timeout_s=19,
                expected_outputs=("/workspace/output/result.txt",),
                output_contract_digest=OUTPUT_DIGEST,
                correlation_ids={},
                created_at="2026-09-30T15:00:00Z",
            ),
            policy,
            engine_name="openshell",
            engine_version="r0",
        )
        with self.assertRaisesRegex(OpenShellSDKBindingError, "differs"):
            client.run(state.sandbox_id, second)

    def test_delete_identity_mismatch_is_not_treated_as_cleanup_success(self):
        class WrongDeleteSDK(FakeSDK):
            def delete(self, name, *, workspace, allow_missing):
                self.calls.append(("delete", name, workspace, allow_missing))
                return Obj(sandbox_id="different-sandbox")

        sdk = WrongDeleteSDK()
        client = PythonSDKOpenShellClient(
            sdk,
            workspace="default",
            binding=make_binding(),
        )
        policy = make_policy()
        request = make_request(policy)
        state = client.create_sandbox(request, policy)
        with self.assertRaisesRegex(OpenShellSDKBindingError, "different sandbox"):
            client.destroy_sandbox(state.sandbox_id)


if __name__ == "__main__":
    unittest.main()
