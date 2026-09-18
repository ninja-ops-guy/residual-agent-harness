"""Microsoft Copilot Studio integration boundary.

This package intentionally does not reimplement Copilot Studio orchestration,
knowledge, Entra authentication UX, or Power Platform governance.
"""

from .contracts import CopilotAPIError, MissionRequest, VerifiedPrincipal
from .policy import FirmwarePolicy, PolicyDecision
from .service import (
    CopilotMissionRecord,
    CopilotMissionStore,
    CopilotStudioService,
    MissionEvidenceRef,
    OIDCBearerAuthenticator,
)
from .http import CopilotHTTPAdapter, HTTPResponse
from .persistence import SQLiteCopilotMissionStore
from .factory_handoff import (
    ApprovedRepository,
    CopilotFactoryHandoff,
    FirmwareFactoryAdapter,
    ResourceCatalog,
)
from .departments import (
    AgentTemplate,
    DepartmentProfile,
    DepartmentRegistry,
    ResidualDepartmentBinding,
)

__all__ = [
    "CopilotAPIError",
    "MissionRequest",
    "VerifiedPrincipal",
    "FirmwarePolicy",
    "PolicyDecision",
    "CopilotMissionRecord",
    "CopilotMissionStore",
    "CopilotStudioService",
    "MissionEvidenceRef",
    "SQLiteCopilotMissionStore",
    "OIDCBearerAuthenticator",
    "CopilotHTTPAdapter",
    "HTTPResponse",
    "ApprovedRepository",
    "CopilotFactoryHandoff",
    "FirmwareFactoryAdapter",
    "ResourceCatalog",
    "AgentTemplate",
    "DepartmentProfile",
    "DepartmentRegistry",
    "ResidualDepartmentBinding",
]
