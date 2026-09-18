"""Environment qualification for delayed/replayed M6 experiments."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .core import ContractError, digest


class EnvironmentRequirement(str, Enum):
    REQUIRED_EXACT = "required_exact"
    REQUIRED_COMPATIBLE = "required_compatible"
    OBSERVATIONAL = "observational"


class EnvironmentStatus(str, Enum):
    PASS = "pass"
    COMPATIBILITY_REQUIRED = "compatibility_required"
    FAIL = "fail"


@dataclass(frozen=True)
class EnvironmentContract:
    fields: Mapping[str, tuple[EnvironmentRequirement, Any]]
    revision: str = "residual.environment.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.fields, Mapping) or not self.fields:
            raise ContractError("environment contract fields are required")
        normalized={}
        for name,item in self.fields.items():
            if not isinstance(name,str) or not name:
                raise ContractError("environment field name is required")
            if not isinstance(item,tuple) or len(item)!=2:
                raise ContractError("environment field must be (requirement, expected)")
            req,expected=item
            if not isinstance(req,EnvironmentRequirement):
                req=EnvironmentRequirement(req)
            normalized[name]=(req,expected)
        object.__setattr__(self,"fields",MappingProxyType(normalized))

    @property
    def contract_hash(self) -> str:
        return digest({
            "revision":self.revision,
            "fields":{
                name:{"requirement":req.value,"expected":expected}
                for name,(req,expected) in sorted(self.fields.items())
            },
        })


@dataclass(frozen=True)
class EnvironmentVerdict:
    status: EnvironmentStatus
    exact_mismatches: tuple[str,...]
    compatibility_checks: tuple[str,...]
    observations: Mapping[str,Any]
    observed_environment_hash: str


def qualify_environment(
    contract: EnvironmentContract,
    observed: Mapping[str,Any],
) -> EnvironmentVerdict:
    if not isinstance(observed,Mapping):
        raise ContractError("observed environment must be a mapping")
    exact=[]
    compat=[]
    observations={}
    for name,(requirement,expected) in contract.fields.items():
        actual=observed.get(name)
        if requirement == EnvironmentRequirement.REQUIRED_EXACT:
            if actual != expected:
                exact.append(name)
        elif requirement == EnvironmentRequirement.REQUIRED_COMPATIBLE:
            if actual != expected:
                compat.append(name)
        else:
            observations[name]=actual
    status=(
        EnvironmentStatus.FAIL if exact else
        EnvironmentStatus.COMPATIBILITY_REQUIRED if compat else
        EnvironmentStatus.PASS
    )
    return EnvironmentVerdict(
        status=status,
        exact_mismatches=tuple(sorted(exact)),
        compatibility_checks=tuple(sorted(compat)),
        observations=MappingProxyType(dict(sorted(observations.items()))),
        observed_environment_hash=digest(dict(sorted(observed.items()))),
    )
