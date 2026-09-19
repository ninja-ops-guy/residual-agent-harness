"""Typed deployment configuration for the RESIDUAL Copilot Studio solution."""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Mapping

from ...core import ContractError, digest
from .departments import DepartmentGroups, department_catalog
from .entra import EntraDeploymentConfig

_GUID=re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _guid(value,name):
    if not isinstance(value,str) or not _GUID.fullmatch(value.strip()):
        raise ContractError(f"{name} must be a GUID")
    return value.strip().lower()


@dataclass(frozen=True)
class EnterpriseCopilotDeployment:
    api_base_url:str
    tenant_id:str
    api_client_id:str
    connector_client_app_id:str
    firmware_group_id:str
    mechanical_group_id:str
    electromechanical_group_id:str
    automated_testing_group_id:str
    qa_group_id:str
    reviewers_group_id:str
    leads_group_id:str
    auditors_group_id:str

    def __post_init__(self):
        parsed=urllib.parse.urlsplit(self.api_base_url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ContractError("api_base_url must be a clean HTTPS origin")
        object.__setattr__(self,"api_base_url",self.api_base_url.rstrip("/"))
        for name in (
            "tenant_id","api_client_id","connector_client_app_id","firmware_group_id",
            "mechanical_group_id","electromechanical_group_id","automated_testing_group_id",
            "qa_group_id","reviewers_group_id","leads_group_id","auditors_group_id",
        ):
            object.__setattr__(self,name,_guid(getattr(self,name),name))

    @classmethod
    def from_mapping(cls,data:Mapping[str,str]):
        keys={
            "RESIDUAL_API_BASE_URL":"api_base_url",
            "RESIDUAL_ENTRA_TENANT_ID":"tenant_id",
            "RESIDUAL_API_CLIENT_ID":"api_client_id",
            "RESIDUAL_CONNECTOR_CLIENT_APP_ID":"connector_client_app_id",
            "RESIDUAL_FIRMWARE_GROUP_ID":"firmware_group_id",
            "RESIDUAL_MECHANICAL_GROUP_ID":"mechanical_group_id",
            "RESIDUAL_ELECTROMECHANICAL_GROUP_ID":"electromechanical_group_id",
            "RESIDUAL_AUTOMATED_TESTING_GROUP_ID":"automated_testing_group_id",
            "RESIDUAL_QA_GROUP_ID":"qa_group_id",
            "RESIDUAL_ENGINEERING_REVIEWERS_GROUP_ID":"reviewers_group_id",
            "RESIDUAL_ENGINEERING_LEADS_GROUP_ID":"leads_group_id",
            "RESIDUAL_ENGINEERING_AUDITORS_GROUP_ID":"auditors_group_id",
        }
        missing=[k for k in keys if not data.get(k)]
        if missing: raise ContractError("missing deployment variable: "+sorted(missing)[0])
        return cls(**{field:data[key] for key,field in keys.items()})

    @property
    def config_hash(self):
        return digest(self.to_dict())

    def to_dict(self):
        return {name:getattr(self,name) for name in self.__dataclass_fields__}

    def entra(self):
        return EntraDeploymentConfig(
            self.tenant_id,self.api_client_id,frozenset({self.connector_client_app_id})
        )

    def departments(self):
        shared_review=frozenset({self.reviewers_group_id})
        shared_leads=frozenset({self.leads_group_id})
        shared_audit=frozenset({self.auditors_group_id})
        groups={
            "firmware":DepartmentGroups(frozenset({self.firmware_group_id}),shared_review,shared_leads,shared_audit),
            "mechanical":DepartmentGroups(frozenset({self.mechanical_group_id}),shared_review,shared_leads,shared_audit),
            "electromechanical":DepartmentGroups(frozenset({self.electromechanical_group_id}),shared_review,shared_leads,shared_audit),
            "automated_testing":DepartmentGroups(frozenset({self.automated_testing_group_id}),shared_review,shared_leads,shared_audit),
            "quality_assurance":DepartmentGroups(frozenset({self.qa_group_id}),shared_review,shared_leads,shared_audit),
        }
        return department_catalog(groups)
