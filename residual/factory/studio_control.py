"""Authoritative, filesystem-backed Studio control adapter.

This adapter intentionally implements only operations that can be bound to
existing Factory authority without inventing missing worker/integration inputs:
plan compilation, exact-hash approval, and runtime cancellation. Run and
integrate fail closed until a caller supplies the already-approved contracts,
worker source, verified receipts, verification policy and HITL resolutions.
"""
from __future__ import annotations
import json, os
from pathlib import Path
from residual.core import strict_json
from .compiler import RequirementCompiler
from .models import ExecutionPlan, FrozenPlan
from .runtime import FactoryRuntime\nfrom .runtime_journal import private_directory

class StudioControlError(RuntimeError): pass

class AuthoritativeStudioControl:
    def __init__(self, state_dir: str|Path, *, runtime: FactoryRuntime|None=None):
        self.root=private_directory(Path(state_dir).absolute())
        self.runtime=runtime
    @property
    def plan_path(self): return self.root/"plan.json"
    @property
    def approval_path(self): return self.root/"approval.json"
    def _write(self,path:Path,value:dict):
        data=(json.dumps(value,indent=2,sort_keys=True)+"\\n").encode("utf-8")\n        tmp=path.with_suffix(path.suffix+".tmp")\n        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)\n        with os.fdopen(fd,"wb") as stream: stream.write(data);stream.flush();os.fsync(stream.fileno())\n        os.replace(tmp,path)
    def _plan(self)->ExecutionPlan:
        if not self.plan_path.exists(): raise StudioControlError("no compiled plan")
        return ExecutionPlan.from_dict(strict_json(self.plan_path.read_text(encoding="utf-8")))
    def control(self,action:str,payload:dict)->dict:
        if action=="plan":
            document=payload.get("document")
            if not isinstance(document,dict): raise StudioControlError("structured plan document required")
            result=RequirementCompiler().compile(document)
            if not result.ready:return {"status":"needs_clarification","questions":list(result.questions)}
            self._write(self.plan_path,result.plan.to_dict());return {"status":"draft","graph_hash":result.plan.graph_hash}
        plan=self._plan()
        supplied=payload.get("plan_hash")
        if supplied!=plan.graph_hash: raise StudioControlError("control request plan hash does not match authoritative plan")
        if action=="approve":
            approved_by=payload.get("approved_by")
            approval=FrozenPlan.approve(plan,approved_by)
            self._write(self.approval_path,approval.to_dict());return {"status":"approved","graph_hash":approval.graph_hash}
        if action=="cancel":
            if self.runtime is None: raise StudioControlError("runtime cancellation is not configured")
            attempt_id=payload.get("attempt_id")
            if not isinstance(attempt_id,str) or not attempt_id: raise StudioControlError("attempt_id required")
            if not self.runtime.cancel(attempt_id): raise StudioControlError("attempt is not cancellable")
            return {"status":"cancelled","attempt_id":attempt_id}
        if action=="run":
            raise StudioControlError("run requires approved WorkerContracts and worker source; use the Factory execution adapter")
        if action=="integrate":
            raise StudioControlError("integrate requires verified M3 receipts, verification policy, Station identity and HITL resolutions")
        raise StudioControlError("unsupported action")
