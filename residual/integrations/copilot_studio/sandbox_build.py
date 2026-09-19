"""OS-isolated Firmware build/test worker for Copilot Studio."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ...core import ContractError, canonical, digest, identifier
from ...factory.m4_sandbox import IsolatedResult, run_isolated
from ...factory.runtime_journal import private_directory
from ...factory.runtime_workspace import WorkerContractError, git
from .backend import EncryptedMissionQueueBackend, QueuedMissionWork
from .resources import RepositoryCatalog

BUILD_TEMPLATE = "firmware-sandbox-build"
AUTOMATED_TEST_TEMPLATE = "automated-test-isolated-run"
_FIRMWARE_CAPABILITIES = frozenset({
    "repository.analyze", "sandbox.build", "tests.run_approved", "evidence.read_own",
})
_AUTOMATED_TEST_CAPABILITIES = frozenset({
    "sandbox.build", "tests.run_approved", "evidence.read_own",
})


@dataclass(frozen=True)
class BuildCommand:
    command_id: str
    argv: tuple[str, ...]
    timeout_s: float = 120.0
    output_limit: int = 1024 * 1024
    memory_mb: int = 512
    cpu_s: float | None = None

    def __post_init__(self):
        identifier(self.command_id)
        if (
            not isinstance(self.argv, tuple)
            or not self.argv
            or any(not isinstance(x, str) or not x or "\x00" in x for x in self.argv)
        ):
            raise ContractError("build command argv must be a non-empty tuple")
        if any(len(x) > 2048 for x in self.argv):
            raise ContractError("build command argument is too long")
        if type(self.timeout_s) not in (int, float) or not 1 <= self.timeout_s <= 900:
            raise ContractError("build command timeout is out of bounds")
        if type(self.output_limit) is not int or not 1 <= self.output_limit <= 16 * 1024 * 1024:
            raise ContractError("build command output limit is out of bounds")
        if type(self.memory_mb) is not int or not 32 <= self.memory_mb <= 4096:
            raise ContractError("build command memory limit is out of bounds")
        if self.cpu_s is not None and (
            type(self.cpu_s) not in (int, float) or not 1 <= self.cpu_s <= self.timeout_s
        ):
            raise ContractError("build command CPU limit is out of bounds")


@dataclass(frozen=True)
class BuildProfile:
    profile_id: str
    commands: tuple[BuildCommand, ...]

    def __post_init__(self):
        identifier(self.profile_id)
        if not isinstance(self.commands, tuple) or not self.commands:
            raise ContractError("build profile requires commands")
        if any(not isinstance(cmd, BuildCommand) for cmd in self.commands):
            raise ContractError("build profile commands must be BuildCommand values")
        names = [cmd.command_id for cmd in self.commands]
        if len(names) != len(set(names)):
            raise ContractError("duplicate build command id")

    @property
    def profile_hash(self) -> str:
        return digest({
            "profile_id": self.profile_id,
            "commands": [
                {
                    "command_id": c.command_id,
                    "argv": list(c.argv),
                    "timeout_s": c.timeout_s,
                    "output_limit": c.output_limit,
                    "memory_mb": c.memory_mb,
                    "cpu_s": c.cpu_s,
                }
                for c in self.commands
            ],
        })


class BuildProfileCatalog:
    def __init__(self, profiles: tuple[BuildProfile, ...]):
        if not isinstance(profiles, tuple) or not profiles:
            raise ContractError("build profile catalog requires profiles")
        table = {}
        for profile in profiles:
            if not isinstance(profile, BuildProfile):
                raise ContractError("invalid build profile")
            if profile.profile_id in table:
                raise ContractError("duplicate build profile")
            table[profile.profile_id] = profile
        self._profiles = table

    def resolve(self, profile_id: str) -> BuildProfile:
        identifier(profile_id)
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ContractError("build_profile_id is not configured")
        return profile


SandboxRunner = Callable[..., IsolatedResult]


class FirmwareSandboxBuildWorker:
    """Run approved build/test commands against one exact Git commit.

    Commands are deployment-owned BuildProfile entries, never prompt/model output.
    The worktree is detached at the repository's frozen HEAD and the existing M4
    sandbox mounts it read-only with private user/mount/PID/network/IPC/UTS
    namespaces. No result is authoritative unless every command returns PASS.
    """

    def __init__(
        self,
        backend: EncryptedMissionQueueBackend,
        repositories: RepositoryCatalog,
        profiles: BuildProfileCatalog,
        *,
        runtime_root: str | Path,
        worker_id: str = "firmware_build_worker",
        lease_seconds: float = 300.0,
        runner: SandboxRunner = run_isolated,
        template_capabilities: dict[str, frozenset[str]] | None = None,
    ):
        if not isinstance(backend, EncryptedMissionQueueBackend):
            raise ContractError("build worker requires EncryptedMissionQueueBackend")
        if not isinstance(repositories, RepositoryCatalog):
            raise ContractError("build worker requires RepositoryCatalog")
        if not isinstance(profiles, BuildProfileCatalog):
            raise ContractError("build worker requires BuildProfileCatalog")
        identifier(worker_id)
        if type(lease_seconds) not in (int, float) or not 1 <= lease_seconds <= 3600:
            raise ContractError("build worker lease_seconds is out of bounds")
        if not callable(runner):
            raise ContractError("sandbox runner must be callable")
        self.backend = backend
        self.repositories = repositories
        self.profiles = profiles
        self.runtime_root = private_directory(Path(runtime_root).absolute())
        self.worker_id = worker_id
        self.lease_seconds = float(lease_seconds)
        self.runner = runner
        self.template_capabilities = dict(template_capabilities or {
            BUILD_TEMPLATE: _FIRMWARE_CAPABILITIES,
        })
        if not self.template_capabilities:
            raise ContractError("sandbox worker requires template capability bindings")
        for template_id, capabilities in self.template_capabilities.items():
            identifier(template_id)
            if not isinstance(capabilities, frozenset) or not capabilities:
                raise ContractError("sandbox template capabilities must be non-empty")

    def _validate_work(self, work: QueuedMissionWork) -> None:
        required = self.template_capabilities.get(work.binding.template_id)
        if required is None or work.request.template_id != work.binding.template_id:
            raise ContractError("build worker received unsupported template")
        if set(work.binding.capabilities) != set(required):
            raise ContractError("build mission capability binding mismatch")
        if work.binding.plan_hash != work.plan.graph_hash:
            raise ContractError("build mission plan binding mismatch")
        if work.binding.request_hash != work.request.request_hash:
            raise ContractError("build mission request binding mismatch")

    def _run(self, work: QueuedMissionWork) -> tuple[dict, ...]:
        self._validate_work(work)
        repository_id = work.request.inputs.get("repository_id")
        profile_id = work.request.inputs.get("build_profile_id")
        if not isinstance(repository_id, str) or not isinstance(profile_id, str):
            raise ContractError("build mission requires repository_id and build_profile_id")
        resource = self.repositories.resolve(repository_id)
        profile = self.profiles.resolve(profile_id)
        snapshot = resource.snapshot()

        mission_root = self.runtime_root / work.binding.mission_id
        if mission_root.exists():
            raise ContractError("build runtime directory already exists")
        mission_root.mkdir(mode=0o700, parents=True)
        worktree = mission_root / "worktree"
        try:
            resolved = git(resource.root, "rev-parse", "--verify", f"{snapshot.commit}^{{commit}}").decode().strip()
            if resolved != snapshot.commit:
                raise ContractError("repository snapshot moved before build")
            git(resource.root, "worktree", "add", "--detach", str(worktree), snapshot.commit)
            evidence = [{
                "evidence_type": "sandbox_build_profile",
                "repository_id": repository_id,
                "commit": snapshot.commit,
                "snapshot_hash": snapshot.snapshot_hash,
                "build_profile_id": profile.profile_id,
                "build_profile_hash": profile.profile_hash,
            }]
            for command in profile.commands:
                if self.backend.cancellation_requested(work.binding.mission_id, work.lease_id):
                    raise ContractError("build mission cancellation requested")
                self.backend.heartbeat(
                    work.binding.mission_id, work.lease_id,
                    lease_seconds=self.lease_seconds,
                )
                result = self.runner(
                    command.argv,
                    worktree,
                    timeout_s=command.timeout_s,
                    output_limit=command.output_limit,
                    memory_mb=command.memory_mb,
                    cpu_s=command.cpu_s,
                )
                if not isinstance(result, IsolatedResult):
                    raise ContractError("sandbox runner returned invalid result")
                item = {
                    "evidence_type": "sandbox_command",
                    "command_id": command.command_id,
                    "status": result.status,
                    "returncode": result.returncode,
                    "stdout_sha256": result.stdout_sha256,
                    "stderr_sha256": result.stderr_sha256,
                    "reason": result.reason,
                    "execution_boundary": result.execution_boundary,
                    "timed_out": result.timed_out,
                }
                evidence.append(item)
                if result.status != "pass":
                    raise ContractError("approved sandbox command did not pass")
            return tuple(evidence)
        finally:
            if worktree.exists():
                try:
                    git(resource.root, "worktree", "remove", "--force", str(worktree))
                except WorkerContractError:
                    pass
            # Keep no checkout after the mission. The queue/evidence ledger is
            # authoritative; sandbox stdout/stderr are represented only by hashes.
            try:
                import shutil
                shutil.rmtree(mission_root, ignore_errors=True)
            except Exception:
                pass

    def run_once(self) -> dict | None:
        work = self.backend.claim_next(
            self.worker_id,
            lease_seconds=self.lease_seconds,
            template_ids=frozenset(self.template_capabilities),
        )
        if work is None:
            return None
        mission_id = work.binding.mission_id
        try:
            evidence = self._run(work)
            self.backend.heartbeat(mission_id, work.lease_id, lease_seconds=self.lease_seconds)
            if self.backend.cancellation_requested(mission_id, work.lease_id):
                row = self.backend.acknowledge_cancel(
                    mission_id, work.lease_id,
                    evidence=({"reason": "worker_observed_cancellation"},),
                )
            else:
                row = self.backend.complete(mission_id, work.lease_id, evidence=evidence)
            return {"mission_id": mission_id, "state": row["state"]}
        except ContractError as exc:
            try:
                if self.backend.cancellation_requested(mission_id, work.lease_id):
                    row = self.backend.acknowledge_cancel(
                        mission_id, work.lease_id,
                        evidence=({"reason": "worker_observed_cancellation"},),
                    )
                    return {"mission_id": mission_id, "state": row["state"]}
            except ContractError:
                pass
            try:
                row = self.backend.fail(
                    mission_id, work.lease_id,
                    error_code="sandbox_build_failure",
                    evidence=({"error_type": type(exc).__name__},),
                )
                return {"mission_id": mission_id, "state": row["state"]}
            except ContractError:
                raise


class AutomatedTestSandboxWorker(FirmwareSandboxBuildWorker):
    """Same isolation path for the Automated Testing department."""

    def __init__(self, backend, repositories, profiles, *, runtime_root,
                 worker_id="automated_test_worker", lease_seconds=300.0,
                 runner=run_isolated):
        super().__init__(
            backend, repositories, profiles,
            runtime_root=runtime_root,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            runner=runner,
            template_capabilities={
                AUTOMATED_TEST_TEMPLATE: _AUTOMATED_TEST_CAPABILITIES,
            },
        )
