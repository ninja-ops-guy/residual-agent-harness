"""Qualification for Firmware isolated test-triage proposal worker."""
from __future__ import annotations

from residual.engines.protocol import EngineHealth, EngineResult
from residual.factory.m4_sandbox import IsolatedResult,SANDBOX_PROFILE
from residual.integrations.copilot_studio.sandbox_build import BuildCommand,BuildProfile,BuildProfileCatalog
from residual.integrations.copilot_studio.triage import FirmwareTestTriageWorker
from residual.runtime.router import RuntimeCapabilityRouter
from tests.enterprise.test_copilot_worker import _backend,_catalog
from tests.enterprise.test_copilot_studio import make_api,payload,submit


class Runner:
    def __init__(self,result=None): self.calls=[]; self.result=result or IsolatedResult("fail",1,"a"*64,"b"*64,"exit",SANDBOX_PROFILE,False)
    def __call__(self,*args,**kwargs): self.calls.append((args,kwargs)); return self.result


class Engine:
    name="triage-local"; version="1"; capability_class="deterministic_local"; locality="local"
    def __init__(self,candidate=None,tool_calls=()): self.calls=[]; self.candidate=candidate or {
        "summary":"Boot regression appears isolated.",
        "findings":["Observed failure in boot path."],
        "patches":[{"path":"src/boot.c","proposal":"Change the guarded branch and add a regression check."}],
        "draft_pr":{"title":"Propose boot regression fix","body":"Evidence-backed proposal only."},
    }; self.tool_calls=tool_calls
    def supports(self,c): return c=="patch.propose"
    def health(self): return EngineHealth.HEALTHY
    def execute(self,task,context): self.calls.append((task,context)); return EngineResult(candidate=self.candidate,tool_calls=self.tool_calls)
    def normalize(self,x): return x


def _profiles():
    return BuildProfileCatalog((BuildProfile("boot_tests",(BuildCommand("boot-test",("python","-B","-c","print('test')"),10,4096,128),)),))


def _router(engine):
    router=RuntimeCapabilityRouter(); router.register(engine,("patch.propose",)); return router


def _submit(backend,rid="triage"):
    api,_,_=make_api(backend=backend)
    r=submit(api,body=payload(request_id=rid,template_id="firmware-test-triage",
        inputs={"repository_id":"firmware_sample","test_profile_id":"boot_tests"}))
    assert r.status==202
    return r.body["mission_id"]


def test_triage_runs_approved_tests_and_returns_proposal_without_repo_mutation(tmp_path):
    backend=_backend(tmp_path); catalog,root=_catalog(tmp_path); mid=_submit(backend)
    runner=Runner(); engine=Engine()
    worker=FirmwareTestTriageWorker(backend,catalog,_profiles(),_router(engine),runtime_root=tmp_path/"triage",runner=runner)
    assert worker.run_once()["state"]=="completed"
    assert len(runner.calls)==1 and len(engine.calls)==1
    evidence=backend.evidence(mid)
    proposal=next(e for e in evidence if e.get("evidence_type")=="patch_proposal")
    assert proposal["proposal"]["patches"][0]["path"]=="src/boot.c"
    import subprocess
    assert subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).strip()==""


def test_triage_tool_call_fails_closed(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend,"triage-tool")
    engine=Engine(tool_calls=({"name":"shell"},))
    worker=FirmwareTestTriageWorker(backend,catalog,_profiles(),_router(engine),runtime_root=tmp_path/"triage",runner=Runner())
    assert worker.run_once()["state"]=="failed"
    assert backend.status(mid)["state"]=="failed"


def test_triage_cannot_propose_unapproved_path(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend,"triage-path")
    bad=Engine(candidate={
        "summary":"x","findings":[],"patches":[{"path":"secrets.txt","proposal":"write"}],
        "draft_pr":{"title":"x","body":""},
    })
    worker=FirmwareTestTriageWorker(backend,catalog,_profiles(),_router(bad),runtime_root=tmp_path/"triage",runner=Runner())
    assert worker.run_once()["state"]=="failed"
    assert backend.status(mid)["state"]=="failed"


def test_triage_rejects_cloud_or_provider_chat_engine_before_source_disclosure(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path)
    for i,(locality,klass) in enumerate((("cloud","test"),("local","provider_chat"))):
        mid=_submit(backend,f"triage-disclosure-{i}")
        engine=Engine(); engine.locality=locality; engine.capability_class=klass
        worker=FirmwareTestTriageWorker(backend,catalog,_profiles(),_router(engine),runtime_root=tmp_path/f"triage-{i}",runner=Runner())
        assert worker.run_once()["state"]=="failed"
        assert engine.calls==[]
        assert backend.status(mid)["state"]=="failed"


def test_triage_isolation_unknown_fails_before_engine(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend,"triage-isolation")
    runner=Runner(IsolatedResult("unknown",None,"a"*64,"b"*64,"isolation_unavailable:test",SANDBOX_PROFILE,False))
    engine=Engine()
    worker=FirmwareTestTriageWorker(backend,catalog,_profiles(),_router(engine),runtime_root=tmp_path/"triage",runner=runner)
    assert worker.run_once()["state"]=="failed"
    assert engine.calls==[]
    assert backend.status(mid)["state"]=="failed"
