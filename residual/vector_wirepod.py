"""Experimental RESIDUAL boundary for an existing Wire-Pod/MCP Vector transport."""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from hashlib import sha256
import json,time
from typing import Any,Callable,Mapping,Protocol,Sequence
@dataclass(frozen=True)
class CapabilityPolicy: allowed_tools:frozenset[str]; max_calls:int=64; max_duration_s:float=120.0
@dataclass(frozen=True)
class BehaviorSpec:
 behavior_id:str; source:str; required_tools:tuple[str,...]; acceptance:Mapping[str,Any]; environment:Mapping[str,str]
 def digest(self): return sha256(json.dumps({"id":self.behavior_id,"source":self.source,"tools":self.required_tools,"acceptance":dict(self.acceptance),"environment":dict(self.environment)},sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True)
class QualificationReceipt:
 behavior_id:str; artifact_digest:str; environment_digest:str; policy_pass:bool; test_pass:bool; hardware_pass:bool; accepted:bool; evidence:tuple[Mapping[str,Any],...]
 def canonical_json(self): return json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=list)
class ToolTransport(Protocol):
 def call(self,name:str,arguments:Mapping[str,Any])->Any: ...
class PolicyViolation(RuntimeError): pass
class GuardedVectorSession:
 def __init__(self,transport:ToolTransport,policy:CapabilityPolicy): self.transport=transport; self.policy=policy; self.started=time.monotonic(); self.calls=0; self.evidence=[]
 def call(self,name,arguments):
  if name not in self.policy.allowed_tools: raise PolicyViolation(f"tool not authorized: {name}")
  if self.calls>=self.policy.max_calls: raise PolicyViolation("tool-call budget exhausted")
  if time.monotonic()-self.started>self.policy.max_duration_s: raise PolicyViolation("mission duration exceeded")
  self.calls+=1; result=self.transport.call(name,arguments); self.evidence.append({"seq":self.calls,"tool":name,"arguments":dict(arguments),"result":result}); return result
class VectorQualifier:
 def __init__(self,policy): self.policy=policy
 @staticmethod
 def env_digest(env): return sha256(json.dumps(dict(env),sort_keys=True,separators=(",",":")).encode()).hexdigest()
 def qualify(self,spec,tests:Sequence[Callable],hardware_probe=None):
  policy_pass=set(spec.required_tools)<=self.policy.allowed_tools; results=[bool(t(spec)) for t in tests] if policy_pass else []; test_pass=bool(results) and all(results); hardware_pass=False; evidence=[{"policy_pass":policy_pass,"tests":results}]
  if policy_pass and test_pass and hardware_probe is not None: hardware_pass,ev=hardware_probe(spec); evidence.extend(ev)
  return QualificationReceipt(spec.behavior_id,spec.digest(),self.env_digest(spec.environment),policy_pass,test_pass,hardware_pass,policy_pass and test_pass and hardware_pass,tuple(evidence))
def qualification_is_current(r,s): return r.accepted and r.artifact_digest==s.digest() and r.environment_digest==VectorQualifier.env_digest(s.environment)
@dataclass(frozen=True)
class OODACycle: cycle_id:str; observation:Mapping[str,Any]; orientation:Mapping[str,Any]; decision:Mapping[str,Any]; action:Mapping[str,Any]; outcome:Mapping[str,Any]
class ExperienceLedger:
 def __init__(self): self._cycles=[]
 def append(self,c): self._cycles.append(c)
 def snapshot(self): return tuple(self._cycles)
 def outcomes(self,behavior_id): return tuple(c for c in self._cycles if c.action.get("behavior_id")==behavior_id)
