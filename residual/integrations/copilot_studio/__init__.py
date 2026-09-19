"""Microsoft Copilot Studio integration boundary for RESIDUAL.

This package intentionally keeps Copilot Studio responsible for conversational
orchestration and Microsoft-native governance. RESIDUAL independently verifies
identity, authorizes a department profile, compiles a bounded Factory plan, and
binds evidence to the authenticated caller.
"""

from .auth import CopilotIdentityVerifier, CopilotPrincipal
from .triage import FirmwareTestTriageWorker
from .readiness import QualificationRecord, build_readiness_bundle, verify_readiness_bundle
from .demo import DemoExpectation, HybridEntraDemoHarness
from .deployment import EnterpriseCopilotDeployment
from .departments import DepartmentGroups, department_catalog
from .entra import EntraDeploymentConfig, EntraJWKSProvider, MicrosoftGraphGroupResolver
from .hitl import CopilotExternalWriteGate, ExternalWriteApproval, ExternalWriteIntent
from .sandbox_build import BuildCommand, BuildProfile, BuildProfileCatalog, FirmwareSandboxBuildWorker
from .backend import EncryptedMissionQueueBackend, QueuedMissionWork
from .resources import RepositoryCatalog, RepositoryResource, RepositorySnapshot
from .worker import FirmwareAnalysisResult, FirmwareRepositoryAnalysisWorker
from .policy import (
    DepartmentProfile,
    MissionTemplate,
    firmware_profile,
    firmware_templates,
)
from .store import (
    InMemoryMissionStore,
    MissionRecord,
    MissionStore,
    SQLiteMissionStore,
)
from .http import CopilotHTTPServer, FixedWindowRateLimiter, create_server, make_handler
from .gateway import (
    APIResponse,
    CopilotAPI,
    CopilotAccessError,
    CopilotMissionGateway,
    InMemoryMissionBackend,
    MissionBinding,
    MissionRequest,
)

__all__ = [
    "FirmwareTestTriageWorker",
    "verify_readiness_bundle",
    "build_readiness_bundle",
    "QualificationRecord",
    "HybridEntraDemoHarness",
    "DemoExpectation",
    "EnterpriseCopilotDeployment",
    "department_catalog",
    "MicrosoftGraphGroupResolver",
    "FirmwareSandboxBuildWorker",
    "ExternalWriteIntent",
    "ExternalWriteApproval",
    "EntraJWKSProvider",
    "EntraDeploymentConfig",
    "DepartmentGroups",
    "CopilotExternalWriteGate",
    "BuildProfileCatalog",
    "BuildProfile",
    "BuildCommand",
    "APIResponse",
    "CopilotAPI",
    "CopilotAccessError",
    "CopilotIdentityVerifier",
    "CopilotHTTPServer",
    "CopilotMissionGateway",
    "CopilotPrincipal",
    "DepartmentProfile",
    "EncryptedMissionQueueBackend",
    "FirmwareAnalysisResult",
    "FirmwareRepositoryAnalysisWorker",
    "FixedWindowRateLimiter",
    "InMemoryMissionBackend",
    "InMemoryMissionStore",
    "MissionBinding",
    "MissionRecord",
    "MissionRequest",
    "MissionStore",
    "MissionTemplate",
    "QueuedMissionWork",
    "RepositoryCatalog",
    "RepositoryResource",
    "RepositorySnapshot",
    "SQLiteMissionStore",
    "create_server",
    "make_handler",
    "firmware_profile",
    "firmware_templates",
]
