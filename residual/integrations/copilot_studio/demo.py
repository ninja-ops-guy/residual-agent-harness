"""Redacted hybrid-Entra acceptance walkthrough harness."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ...core import ContractError, digest
from .gateway import CopilotAPI


@dataclass(frozen=True)
class DemoExpectation:
    name:str
    method:str
    path:str
    authorization:str
    expected_status:int
    payload:dict[str,Any]|None=None
    expected_code:str|None=None

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name.strip(): raise ContractError("demo step name required")
        if self.method not in {"GET","POST"}: raise ContractError("demo method invalid")
        if not isinstance(self.path,str) or not self.path.startswith("/"): raise ContractError("demo path invalid")
        if not isinstance(self.authorization,str) or not self.authorization.startswith("Bearer "): raise ContractError("demo authorization required")
        if type(self.expected_status) is not int: raise ContractError("demo expected_status invalid")


class HybridEntraDemoHarness:
    """Run redacted API scenarios against the same CopilotAPI used by deployment.

    Hybrid join, Conditional Access, MFA and device-compliance are upstream
    Microsoft controls. This harness records that they were part of the test
    environment as operator-supplied metadata; it never treats that metadata as
    RESIDUAL authorization evidence.
    """

    def __init__(self,api:CopilotAPI,*,now:int,worker_pump:Callable[[],Any]|None=None,
                 upstream_controls:dict[str,bool]|None=None):
        if not isinstance(api,CopilotAPI): raise ContractError("CopilotAPI required")
        if type(now) is not int: raise ContractError("demo now must be integer")
        if worker_pump is not None and not callable(worker_pump): raise ContractError("worker_pump must be callable")
        controls=dict(upstream_controls or {})
        if any(type(v) is not bool for v in controls.values()): raise ContractError("upstream control values must be boolean")
        self.api=api; self.now=now; self.worker_pump=worker_pump; self.controls=controls
        self.records=[]

    def step(self,expectation:DemoExpectation):
        response=self.api.handle(
            expectation.method,expectation.path,expectation.authorization,
            expectation.payload,now=self.now,
        )
        passed=response.status==expectation.expected_status
        if expectation.expected_code is not None:
            passed=passed and response.body.get("code")==expectation.expected_code
        record={
            "name":expectation.name,
            "method":expectation.method,
            "path":expectation.path,
            "expected_status":expectation.expected_status,
            "actual_status":response.status,
            "expected_code":expectation.expected_code,
            "actual_code":response.body.get("code"),
            "passed":passed,
            "response_hash":digest(response.body),
        }
        self.records.append(record)
        if not passed:
            raise ContractError("enterprise demo expectation failed: "+expectation.name)
        return response

    def pump_workers(self,max_iterations:int=20):
        if self.worker_pump is None: return ()
        if type(max_iterations) is not int or not 1<=max_iterations<=100: raise ContractError("max_iterations invalid")
        out=[]
        for _ in range(max_iterations):
            result=self.worker_pump()
            if result is None: break
            out.append(result)
        return tuple(out)

    def report(self):
        return {
            "schema_version":"residual.copilot.hybrid-entra-demo.v1",
            "upstream_controls_observed":dict(sorted(self.controls.items())),
            "upstream_controls_authoritative_for_residual":False,
            "steps":list(self.records),
            "all_passed":all(r["passed"] for r in self.records),
        }
