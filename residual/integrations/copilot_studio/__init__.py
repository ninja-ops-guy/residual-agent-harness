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
from .entra_keys import (
    EntraJWKSProvider,
    EntraV2Endpoints,
    HTTPSJSONFetcher,
    build_entra_v2_oidc_client,
)
from .factory_handoff import (
    ApprovedRepository,
    CopilotFactoryHandoff,
    FirmwareFactoryAdapter,
    ResourceCatalog,
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
    "EntraJWKSProvider",
    "EntraV2Endpoints",
    "HTTPSJSONFetcher",
    "build_entra_v2_oidc_client",
    "OIDCBearerAuthenticator",
    "CopilotHTTPAdapter",
    "HTTPResponse",
    "ApprovedRepository",
    "CopilotFactoryHandoff",
    "FirmwareFactoryAdapter",
    "ResourceCatalog",
]
