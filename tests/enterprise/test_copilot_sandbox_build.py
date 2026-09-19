"""Qualification tests for the namespace-isolated Firmware build worker."""
from __future__ import annotations

import os
from pathlib import Path

from residual.factory.m4_sandbox import IsolatedResult, SANDBOX_PROFILE
from residual.integrations.copilot_studio import EncryptedMissionQueueBackend, RepositoryCatalog, RepositoryResource
from residual.integrations.copilot_studio.sandbox_build import BuildCommand, BuildProfile, BuildProfileCatalog, FirmwareSandboxBuildWorker
from tests.enterprise.test_copilot_worker import _backend, _repo
from tests.enterprise.test_copilot_studio import make_api, payload, submit


def _catalog(tmp_path):
    root=_repo(tmp_path)
    return RepositoryCatalog((RepositoryResource("firmware_sample",root,("README.md","src/boot.c")),)),root


def _submit(backend, request_id="build-e2e", profile="debug_build"):
    api,_,_=make_api(backend=backend)
    response=submit(api,body=payload(request_id=request_id,template_id="firmware-sandbox-build",inputs={"repository_id":"firmware_sample","build_profile_id":profile}))
    assert response.status==202
    return response.body["mission_id"]


class FakeRunner:
    def __init__(self,results=None):
        self.calls=[]
        self.results=list(results or [])
    def __call__(self,argv,worktree,**kwargs):
        self.calls.append((argv,Path(worktree),kwargs))
        if self.results: return self.results.pop(0)
        return IsolatedResult("pass",0,"a"*64,"b"*64,"exit",SANDBOX_PROFILE,False)


def _profiles():
    return BuildProfileCatalog((BuildProfile("debug_build",(
        BuildCommand("syntax",("python","-B","-c","print('ok')"),timeout_s=10,output_limit=4096,memory_mb=128),
        BuildCommand("tests",("python","-B","-c","print('tests')"),timeout_s=10,output_limit=4096,memory_mb=128),
    )),))


def test_build_worker_runs_only_profile_commands_against_detached_commit(tmp_path):
    backend=_backend(tmp_path); catalog,root=_catalog(tmp_path); mid=_submit(backend)
    runner=FakeRunner()
    worker=FirmwareSandboxBuildWorker(backend,catalog,_profiles(),runtime_root=tmp_path/"runtime",runner=runner)
    assert worker.run_once()["state"]=="completed"
    assert len(runner.calls)==2
    assert all(call[0] in {("python","-B","-c","print('ok')"),("python","-B","-c","print('tests')")} for call in runner.calls)
    evidence=backend.evidence(mid)
    assert sum(e.get("evidence_type")=="sandbox_command" for e in evidence)==2
    assert all(e.get("execution_boundary")==SANDBOX_PROFILE for e in evidence if e.get("evidence_type")=="sandbox_command")
    assert os.popen(f"git -C {root} status --porcelain").read().strip()==""


def test_unknown_build_profile_fails_without_command_execution(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend,profile="not_configured")
    runner=FakeRunner()
    worker=FirmwareSandboxBuildWorker(backend,catalog,_profiles(),runtime_root=tmp_path/"runtime",runner=runner)
    assert worker.run_once()["state"]=="failed"
    assert runner.calls==[]
    assert backend.status(mid)["state"]=="failed"


def test_failed_sandbox_command_stops_following_commands(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend)
    runner=FakeRunner([IsolatedResult("fail",1,"a"*64,"b"*64,"exit",SANDBOX_PROFILE,False)])
    worker=FirmwareSandboxBuildWorker(backend,catalog,_profiles(),runtime_root=tmp_path/"runtime",runner=runner)
    assert worker.run_once()["state"]=="failed"
    assert len(runner.calls)==1
    assert backend.status(mid)["state"]=="failed"


def test_isolation_unavailable_fails_closed(tmp_path):
    backend=_backend(tmp_path); catalog,_=_catalog(tmp_path); mid=_submit(backend)
    runner=FakeRunner([IsolatedResult("unknown",None,"a"*64,"b"*64,"isolation_unavailable:test",SANDBOX_PROFILE,False)])
    worker=FirmwareSandboxBuildWorker(backend,catalog,_profiles(),runtime_root=tmp_path/"runtime",runner=runner)
    assert worker.run_once()["state"]=="failed"
    assert backend.status(mid)["state"]=="failed"


def test_build_profile_is_content_addressed():
    p=_profiles().resolve("debug_build")
    assert p.profile_hash==_profiles().resolve("debug_build").profile_hash
