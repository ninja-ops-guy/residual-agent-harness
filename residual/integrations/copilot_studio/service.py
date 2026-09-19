"""Production-shaped service composition for department Copilot agents."""
from __future__ import annotations

import ssl

from ...core import ContractError
from .backend import EncryptedMissionQueueBackend
from .deployment import EnterpriseCopilotDeployment
from .gateway import AuditSink, CopilotAPI, CopilotMissionGateway, MissionBackend
from .http import create_server
from .store import MissionStore


class DepartmentCopilotService:
    """Compose one department agent over the shared RESIDUAL trust boundary."""

    def __init__(self,department:str,deployment:EnterpriseCopilotDeployment,
                 backend:MissionBackend,store:MissionStore,*,group_resolver=None,
                 jwks_provider=None,audit:AuditSink|None=None):
        if not isinstance(deployment,EnterpriseCopilotDeployment):
            raise ContractError("deployment must be EnterpriseCopilotDeployment")
        catalog=deployment.departments()
        if department not in catalog:
            raise ContractError("unknown department service")
        profile,templates=catalog[department]
        verifier=deployment.entra().build_verifier(
            group_resolver=group_resolver,jwks_provider=jwks_provider,
        )
        self.department=department; self.deployment=deployment
        self.profile=profile; self.templates=templates
        self.gateway=CopilotMissionGateway(verifier,profile,templates,backend,store=store)
        self.api=CopilotAPI(self.gateway,audit=audit)

    def create_http_server(self,host:str,port:int,*,ssl_context:ssl.SSLContext|None=None,
                           trusted_reverse_proxy:bool=False,**handler_options):
        return create_server(
            host,port,self.api,ssl_context=ssl_context,
            trusted_reverse_proxy=trusted_reverse_proxy,**handler_options,
        )
