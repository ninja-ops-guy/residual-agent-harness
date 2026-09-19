"""Microsoft Copilot Studio integration boundary for RESIDUAL.

This package intentionally keeps Copilot Studio responsible for conversational
orchestration and Microsoft-native governance. RESIDUAL independently verifies
identity, authorizes a department profile, compiles a bounded Factory plan, and
binds evidence to the authenticated caller.
"""

from .auth import CopilotIdentityVerifier, CopilotPrincipal
from .backend import EncryptedMissionQueueBackend, QueuedMissionWork
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
    "APIResponse",
    "CopilotAPI",
    "CopilotAccessError",
    "CopilotIdentityVerifier",
    "CopilotHTTPServer",
    "CopilotMissionGateway",
    "CopilotPrincipal",
    "DepartmentProfile",
    "EncryptedMissionQueueBackend",
    "FixedWindowRateLimiter",
    "InMemoryMissionBackend",
    "InMemoryMissionStore",
    "MissionBinding",
    "MissionRecord",
    "MissionRequest",
    "MissionStore",
    "MissionTemplate",
    "QueuedMissionWork",
    "SQLiteMissionStore",
    "create_server",
    "make_handler",
    "firmware_profile",
    "firmware_templates",
]
