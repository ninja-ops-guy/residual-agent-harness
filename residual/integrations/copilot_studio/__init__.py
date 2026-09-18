"""Microsoft Copilot Studio integration boundary.

This package intentionally does not reimplement Copilot Studio orchestration,
knowledge, Entra authentication UX, or Power Platform governance.  It accepts a
verified end-user bearer identity and compiles only bounded RESIDUAL authority.
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
]
