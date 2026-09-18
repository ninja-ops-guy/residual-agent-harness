"""Deterministic Copilot Studio -> Factory handoff for the first read-only pilot.

The adapter resolves caller-approved opaque IDs through a server-owned catalog.
It produces an existing Factory ExecutionPlan and WorkerContract; it does not
execute worker source, manufacture an approval, or expand authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Mapping

from ...core import ContractError, digest
from ...factory.compiler import RequirementCompiler
from ...factory.models import ExecutionPlan
from ...factory.worker_contract import WorkerContract
from .contracts import external_id
from .policy import FirmwarePolicy
from .service import CopilotMissionRecord


_GIT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def _selector(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError("catalog selector must be nonempty")
    body = value[:-1] if value.endswith("/") else value
    if (
        value.startswith("/")
        or "\\" in value
        or any(ch in value for ch in ":*?[]")
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
        or any(part in {"", ".", ".."} for part in body.split("/"))
    ):
        raise ContractError("catalog selector must be normalized and relative")
    return value


def _absolute_posix(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or value == "/"
        or "\\" in value
        or value.startswith("//")
        or str(PurePosixPath(value)) != value
        or ".." in PurePosixPath(value).parts
    ):
        raise ContractError("repository root must be an absolute normalized POSIX path")
    return value


@dataclass(frozen=True)
class ApprovedRepository:
    repository_id: str
    repository_root: str
    input_commit: str
    read_selectors: tuple[str, ...]
    forbidden_selectors: tuple[str, ...]
    analysis_profiles: frozenset[str]

    def __post_init__(self):
        external_id(self.repository_id, "repository_id")
        object.__setattr__(
            self, "repository_root", _absolute_posix(self.repository_root)
        )
        if not isinstance(self.input_commit, str) or not _GIT_ID.fullmatch(
            self.input_commit
        ):
            raise ContractError("catalog input_commit must be a full Git object ID")
        if not isinstance(self.read_selectors, tuple) or not self.read_selectors:
            raise ContractError("catalog requires read selectors")
        object.__setattr__(
            self,
            "read_selectors",
            tuple(sorted({_selector(value) for value in self.read_selectors})),
        )
        if not isinstance(self.forbidden_selectors, tuple):
            raise ContractError("forbidden selectors must be a tuple")
        object.__setattr__(
            self,
            "forbidden_selectors",
            tuple(sorted({_selector(value) for value in self.forbidden_selectors})),
        )
        if not isinstance(self.analysis_profiles, frozenset) or not self.analysis_profiles:
            raise ContractError("catalog requires an analysis profile allowlist")
        for profile in self.analysis_profiles:
            external_id(profile, "analysis_profile_id")

    def payload(self) -> dict:
        return {
            "repository_id": self.repository_id,
            "repository_root": self.repository_root,
            "input_commit": self.input_commit,
            "read_selectors": list(self.read_selectors),
            "forbidden_selectors": list(self.forbidden_selectors),
            "analysis_profiles": sorted(self.analysis_profiles),
        }


@dataclass(frozen=True, init=False)
class ResourceCatalog:
    repositories: Mapping[str, ApprovedRepository]

    def __init__(self, repositories: tuple[ApprovedRepository, ...]):
        if not isinstance(repositories, tuple) or not repositories:
            raise ContractError("resource catalog requires repositories")
        mapping: dict[str, ApprovedRepository] = {}
        for resource in repositories:
            if not isinstance(resource, ApprovedRepository):
                raise ContractError("resource catalog entries must be ApprovedRepository")
            if resource.repository_id in mapping:
                raise ContractError("duplicate repository_id in resource catalog")
            mapping[resource.repository_id] = resource
        object.__setattr__(
            self,
            "repositories",
            MappingProxyType(dict(sorted(mapping.items()))),
        )

    @property
    def catalog_hash(self) -> str:
        return digest({
            name: resource.payload()
            for name, resource in self.repositories.items()
        })

    def repository(self, repository_id: str) -> ApprovedRepository:
        external_id(repository_id, "repository_id")
        value = self.repositories.get(repository_id)
        if value is None:
            raise ContractError("repository_id is not present in the approved catalog")
        return value


@dataclass(frozen=True)
class CopilotFactoryHandoff:
    mission_id: str
    revision_id: str
    catalog_hash: str
    repository_id: str
    analysis_profile_id: str
    repository_root: str
    plan: ExecutionPlan
    contract: WorkerContract
    copilot_plan_hash: str

    @property
    def binding_hash(self) -> str:
        return digest({
            "mission_id": self.mission_id,
            "revision_id": self.revision_id,
            "catalog_hash": self.catalog_hash,
            "repository_id": self.repository_id,
            "analysis_profile_id": self.analysis_profile_id,
            "repository_root": self.repository_root,
            "factory_plan_hash": self.plan.graph_hash,
            "worker_contract_hash": self.contract.contract_hash,
            "copilot_plan_hash": self.copilot_plan_hash,
        })


class FirmwareFactoryAdapter:
    """Prepare one low-risk Firmware repository-analysis Factory mission."""

    template_id = "firmware-repository-analysis"
    required_capabilities = frozenset({
        "repository.analyze",
        "evidence.read_own",
    })

    def __init__(
        self,
        catalog: ResourceCatalog,
        *,
        policy: FirmwarePolicy,
        workspace_root: str = "/var/lib/residual/copilot",
    ):
        if not isinstance(catalog, ResourceCatalog):
            raise ContractError("FirmwareFactoryAdapter requires a ResourceCatalog")
        if not isinstance(policy, FirmwarePolicy):
            raise ContractError("FirmwareFactoryAdapter requires the active FirmwarePolicy")
        self.catalog = catalog
        self.policy = policy
        self.workspace_root = _absolute_posix(workspace_root)

    def _assert_record_authority(self, record: CopilotMissionRecord) -> None:
        if not isinstance(record, CopilotMissionRecord):
            raise ContractError("CopilotMissionRecord required")
        if record.state != "prepared":
            raise ContractError("only a prepared Copilot mission can enter Factory")
        if record.template_id != FirmwareFactoryAdapter.template_id:
            raise ContractError(
                "this Factory adapter only supports firmware repository analysis"
            )
        if record.revision.mission_id != record.mission.mission_id:
            raise ContractError("Copilot revision does not match mission id")
        if record.revision.policy_hash != self.policy.policy_hash:
            raise ContractError(
                "Copilot mission policy is stale for the active Factory policy"
            )
        actions = {grant.action for grant in record.revision.capability_grants}
        if actions != FirmwareFactoryAdapter.required_capabilities:
            raise ContractError("Copilot capability set does not match Factory profile")
        expected_plan_hash = digest({
            "template_id": record.template_id,
            "objective": record.revision.objective,
            "inputs": record.template_inputs,
            "capabilities": sorted(actions),
        })
        if record.revision.plan_hash != expected_plan_hash:
            raise ContractError(
                "authorized template inputs do not match Copilot plan binding"
            )
        for grant in record.revision.capability_grants:
            if grant.subject != record.mission.principal_id:
                raise ContractError("capability subject does not match mission owner")
            if grant.resource != record.profile_id:
                raise ContractError("capability resource does not match mission profile")
            if grant.scope.get("mission_id") != record.mission.mission_id:
                raise ContractError("capability scope does not match mission id")
            if grant.scope.get("tenant_id") != record.mission.tenant_id:
                raise ContractError("capability scope does not match tenant")
            if grant.scope.get("template_id") != record.template_id:
                raise ContractError("capability scope does not match mission template")
            if grant.constraints.get("claims_hash") != record.claims_hash:
                raise ContractError("capability claims binding does not match mission")

    def prepare(self, record: CopilotMissionRecord) -> CopilotFactoryHandoff:
        self._assert_record_authority(record)
        inputs = record.template_inputs
        if set(inputs) != {"repository_id", "analysis_profile_id"}:
            raise ContractError("authorized template inputs do not match analysis contract")
        repository_id = external_id(inputs["repository_id"], "repository_id")
        profile_id = external_id(
            inputs["analysis_profile_id"], "analysis_profile_id"
        )
        resource = self.catalog.repository(repository_id)
        if profile_id not in resource.analysis_profiles:
            raise ContractError("analysis profile is not approved for repository")

        document = {
            "intent": record.revision.objective,
            "requirements": [
                {
                    "id": "REQ.analysis",
                    "statement": (
                        "Analyze only the approved immutable firmware repository "
                        "snapshot and produce the declared report."
                    ),
                    "acceptance": [
                        "analysis-report",
                        "approved-snapshot-only",
                        "no-external-side-effects",
                    ],
                    "depends_on": [],
                }
            ],
            "tasks": [
                {
                    "id": "analysis",
                    "description": (
                        "Produce reports/firmware-analysis.json from approved "
                        "repository inputs."
                    ),
                    "requirement_ids": ["REQ.analysis"],
                    "depends_on": [],
                    "swarm": "firmware",
                }
            ],
        }
        compiled = RequirementCompiler().compile(document)
        if not compiled.ready or compiled.plan is None:
            raise ContractError("deterministic Factory plan compilation failed")
        plan = compiled.plan

        suffix = record.mission.mission_id.removeprefix("cps-")[:24]
        attempt_id = f"copilot-{suffix}"
        contract = WorkerContract(
            task_id="analysis",
            worker_id="firmware-analyzer",
            swarm_id="firmware",
            execution_plan_hash=plan.graph_hash,
            attempt_id=attempt_id,
            lease_id=f"lease-{suffix}",
            lease_generation=1,
            input_commit=resource.input_commit,
            workspace_root=f"{self.workspace_root}/{record.mission.mission_id}/{attempt_id}",
            inputs=resource.read_selectors,
            allowed_outputs=("reports/firmware-analysis.json",),
            forbidden=resource.forbidden_selectors,
            requirements=("REQ.analysis",),
            acceptance=(
                "analysis-report",
                "approved-snapshot-only",
                "no-external-side-effects",
            ),
            dependencies=(),
            allowed_tools=("read_file", "write_file"),
            forbidden_tools=("network", "shell"),
            token_budget=0,
            wall_clock_budget_s=30,
            max_tool_calls=64,
            max_file_writes=1,
            memory_limit_mb=128,
            engine_hint="scripted-firmware-analysis",
            engine_class="local",
        )
        contract.assert_matches_plan(plan)
        return CopilotFactoryHandoff(
            mission_id=record.mission.mission_id,
            revision_id=record.revision.revision_id,
            catalog_hash=self.catalog.catalog_hash,
            repository_id=repository_id,
            analysis_profile_id=profile_id,
            repository_root=resource.repository_root,
            plan=plan,
            contract=contract,
            copilot_plan_hash=record.revision.plan_hash,
        )
