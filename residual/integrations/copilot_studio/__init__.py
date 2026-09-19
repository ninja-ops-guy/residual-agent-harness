"""Microsoft Copilot Studio integration boundary for RESIDUAL.

This package intentionally keeps Copilot Studio responsible for conversational
orchestration and Microsoft-native governance. RESIDUAL independently verifies
identity, authorizes a department profile, compiles a bounded Factory plan, and
binds evidence to the authenticated caller.
"""

from .auth import CopilotIdentityVerifier, CopilotPrincipal
from .policy import DepartmentProfile, MissionTemplate, firmware_profile, firmware_templates\nfrom .store import InMemoryMissionStore, MissionRecord, MissionStore, SQLiteMissionStore
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
    "CopilotMissionGateway",
    "CopilotPrincipal",
    "DepartmentProfile",
    "InMemoryMissionBackend",\n    "InMemoryMissionStore",
    "MissionBinding",\n    "MissionRecord",\n    "MissionStore",
    "MissionRequest",
    "MissionTemplate",\n    "SQLiteMissionStore",
    "firmware_profile",
    "firmware_templates",
]
