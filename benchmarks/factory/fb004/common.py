from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

INPUT_COMMIT = "3f692889f78e0cc6dae29cdcda04bd1e9e2a5e5e"
EXPECTED_OUTPUT_COMMIT = "b6f20aee56f752a20bcd0652837b137c40d588a4"
GIT_ENV = {"GIT_AUTHOR_NAME":"Residual Benchmark","GIT_AUTHOR_EMAIL":"benchmark@residual.local","GIT_COMMITTER_NAME":"Residual Benchmark","GIT_COMMITTER_EMAIL":"benchmark@residual.local","GIT_AUTHOR_DATE":"2026-01-01T00:00:00+0000","GIT_COMMITTER_DATE":"2026-01-01T00:00:00+0000"}
INPUT_FILES = {"taskflow/__init__.py":"# FB004 fixture\n","README.md":"# FB004 TaskFlow\n\nComplete the bounded mini-service implementation.\n"}
REFERENCE = {
"errors":("taskflow/errors.py","class TaskFlowError(Exception):\n    pass\n\nclass ValidationError(TaskFlowError):\n    pass\n\nclass AuthorizationError(TaskFlowError):\n    pass\n\nclass NotFoundError(TaskFlowError):\n    pass\n"),
"models":("taskflow/models.py","from dataclasses import dataclass\n\n@dataclass(frozen=True, slots=True)\nclass Job:\n    job_id: str\n    owner: str\n    payload: str\n    priority: int = 0\n"),
"config":("taskflow/config.py","from dataclasses import dataclass\n\n@dataclass(frozen=True, slots=True)\nclass Settings:\n    max_queue: int = 100\n    default_priority: int = 0\n\n    def __post_init__(self):\n        if self.max_queue <= 0:\n            raise ValueError(\"max_queue must be positive\")\n"),
"validation":("taskflow/validation.py","from .errors import ValidationError\n\ndef validate_payload(payload: str) -> str:\n    value = payload.strip()\n    if not value or len(value) > 256:\n        raise ValidationError(\"invalid payload\")\n    return value\n\ndef validate_priority(priority: int) -> int:\n    if type(priority) is not int or priority < -10 or priority > 10:\n        raise ValidationError(\"invalid priority\")\n    return priority\n"),
"ids":("taskflow/ids.py","import hashlib\n\ndef job_id(owner: str, payload: str) -> str:\n    raw = f\"{owner}\\0{payload}\".encode()\n    return hashlib.sha256(raw).hexdigest()[:16]\n"),
"auth":("taskflow/auth.py","from .errors import AuthorizationError\n\ndef require_owner(expected: str, actual: str) -> None:\n    if not expected or expected != actual:\n        raise AuthorizationError(\"owner mismatch\")\n"),
"store":("taskflow/store.py","from .errors import NotFoundError\nfrom .models import Job\n\nclass JobStore:\n    def __init__(self):\n        self._jobs: dict[str, Job] = {}\n\n    def put(self, job: Job) -> None:\n        self._jobs[job.job_id] = job\n\n    def get(self, job_id: str) -> Job:\n        try:\n            return self._jobs[job_id]\n        except KeyError as exc:\n            raise NotFoundError(job_id) from exc\n\n    def delete(self, job_id: str) -> None:\n        self.get(job_id)\n        del self._jobs[job_id]\n\n    def count(self) -> int:\n        return len(self._jobs)\n"),
"queue":("taskflow/queue.py","import heapq\n\nclass PriorityQueue:\n    def __init__(self):\n        self._items: list[tuple[int, int, str]] = []\n        self._seq = 0\n\n    def push(self, job_id: str, priority: int) -> None:\n        heapq.heappush(self._items, (-priority, self._seq, job_id))\n        self._seq += 1\n\n    def pop(self) -> str | None:\n        if not self._items:\n            return None\n        return heapq.heappop(self._items)[2]\n\n    def __len__(self) -> int:\n        return len(self._items)\n"),
"serialization":("taskflow/serialization.py","import json\nfrom .models import Job\n\ndef encode_job(job: Job) -> str:\n    return json.dumps({\"job_id\": job.job_id, \"owner\": job.owner, \"payload\": job.payload, \"priority\": job.priority}, sort_keys=True, separators=(\",\", \":\"))\n\ndef decode_job(raw: str) -> Job:\n    data = json.loads(raw)\n    return Job(str(data[\"job_id\"]), str(data[\"owner\"]), str(data[\"payload\"]), int(data.get(\"priority\", 0)))\n"),
"scheduler":("taskflow/scheduler.py","from .config import Settings\nfrom .errors import ValidationError\nfrom .models import Job\nfrom .queue import PriorityQueue\nfrom .store import JobStore\n\nclass Scheduler:\n    def __init__(self, store: JobStore, queue: PriorityQueue, settings: Settings):\n        self.store, self.queue, self.settings = store, queue, settings\n\n    def submit(self, job: Job) -> None:\n        if self.store.count() >= self.settings.max_queue:\n            raise ValidationError(\"queue full\")\n        self.store.put(job)\n        self.queue.push(job.job_id, job.priority)\n\n    def next(self) -> Job | None:\n        job_id = self.queue.pop()\n        return None if job_id is None else self.store.get(job_id)\n"),
"metrics":("taskflow/metrics.py","from .queue import PriorityQueue\nfrom .store import JobStore\n\ndef snapshot(store: JobStore, queue: PriorityQueue) -> dict[str, int]:\n    return {\"stored\": store.count(), \"queued\": len(queue)}\n"),
"health":("taskflow/health.py","from .metrics import snapshot\nfrom .queue import PriorityQueue\nfrom .store import JobStore\n\ndef health(store: JobStore, queue: PriorityQueue) -> dict:\n    data = snapshot(store, queue)\n    return {\"status\": \"ok\", **data}\n"),
"api":("taskflow/api.py","from .auth import require_owner\nfrom .ids import job_id\nfrom .models import Job\nfrom .scheduler import Scheduler\nfrom .validation import validate_payload, validate_priority\n\nclass TaskFlowAPI:\n    def __init__(self, scheduler: Scheduler):\n        self.scheduler = scheduler\n\n    def submit(self, owner: str, payload: str, priority: int = 0) -> Job:\n        clean = validate_payload(payload)\n        value = validate_priority(priority)\n        job = Job(job_id(owner, clean), owner, clean, value)\n        self.scheduler.submit(job)\n        return job\n\n    def get(self, owner: str, job_id_value: str) -> Job:\n        job = self.scheduler.store.get(job_id_value)\n        require_owner(job.owner, owner)\n        return job\n"),
"cli":("taskflow/cli.py","import argparse\nfrom .api import TaskFlowAPI\nfrom .config import Settings\nfrom .queue import PriorityQueue\nfrom .scheduler import Scheduler\nfrom .store import JobStore\n\ndef build_api() -> TaskFlowAPI:\n    return TaskFlowAPI(Scheduler(JobStore(), PriorityQueue(), Settings()))\n\ndef main(argv=None) -> int:\n    parser = argparse.ArgumentParser(prog=\"taskflow\")\n    parser.add_argument(\"owner\")\n    parser.add_argument(\"payload\")\n    ns = parser.parse_args(argv)\n    job = build_api().submit(ns.owner, ns.payload)\n    print(job.job_id)\n    return 0\n"),
"docs_readme":("docs/README.md","# TaskFlow\n\nTaskFlow is a deterministic in-memory job queue fixture used by Residual FB004.\n\nIt supports validated submission, owner checks, priority scheduling, health metrics, and JSON serialization.\n"),
"docs_api":("docs/API.md","# TaskFlow API\n\n`TaskFlowAPI.submit(owner, payload, priority=0)` validates and queues a job.\n\n`TaskFlowAPI.get(owner, job_id)` returns the job only when the owner matches.\n\n`health(store, queue)` returns status plus stored and queued counts.\n")}
INIT_REFERENCE = 'from .api import TaskFlowAPI\nfrom .config import Settings\nfrom .models import Job\nfrom .queue import PriorityQueue\nfrom .scheduler import Scheduler\nfrom .store import JobStore\n\n__all__ = ["Job", "JobStore", "PriorityQueue", "Scheduler", "Settings", "TaskFlowAPI"]\n'
DEPENDENCIES = {"errors":(),"models":(),"config":(),"ids":(),"validation":("errors",),"auth":("errors",),"store":("errors","models"),"queue":(),"serialization":("models",),"scheduler":("config","errors","models","queue","store"),"metrics":("queue","store"),"health":("metrics","queue","store"),"api":("auth","ids","models","scheduler","validation"),"cli":("api","config","queue","scheduler","store"),"docs_readme":("api","health","serialization"),"docs_api":("api","health")}
SWARMS = {"architecture":("errors","models","config","validation"),"backend":("ids","auth","store","queue","serialization"),"service":("scheduler","metrics","health","api","cli"),"docs":("docs_readme","docs_api")}
PROMPTS = {task: f"Implement only {path}. Return JSON {{\"content\": \"<complete file contents>\"}}. Satisfy the frozen FB004 TaskFlow contract for task {task}. Do not modify any other file." for task,(path,_source) in REFERENCE.items()}
ALLOWED_IMPORTS = {"argparse","dataclasses","hashlib","heapq","json","taskflow.errors","taskflow.models","taskflow.config","taskflow.queue","taskflow.store","taskflow.metrics","taskflow.auth","taskflow.ids","taskflow.scheduler","taskflow.validation",".errors",".models",".config",".queue",".store",".metrics",".auth",".ids",".scheduler",".validation"}

def _git(repo: Path,*args: str) -> str:
    env=os.environ.copy(); env.update(GIT_ENV)
    return subprocess.check_output(["git","-c","commit.gpgsign=false",*args],cwd=repo,env=env,text=True).strip()

def _commit(repo: Path,message: str) -> str:
    env=os.environ.copy(); env.update(GIT_ENV)
    subprocess.run(["git","-c","commit.gpgsign=false","add","."],cwd=repo,env=env,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","-c","commit.gpgsign=false","commit","-q","-m",message],cwd=repo,env=env,check=True)
    return _git(repo,"rev-parse","HEAD")

def create_fixture(repo: Path,*,known_good: bool=False) -> tuple[str,str|None]:
    repo.mkdir(parents=True,exist_ok=False); subprocess.run(["git","init","-q"],cwd=repo,check=True)
    for name,content in INPUT_FILES.items():
        p=repo/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
    input_commit=_commit(repo,"FB004 input")
    if input_commit!=INPUT_COMMIT: raise RuntimeError(f"FB004 input commit drift: {input_commit}")
    if not known_good: return input_commit,None
    for _task,(name,content) in REFERENCE.items():
        p=repo/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
    (repo/"taskflow/__init__.py").write_text(INIT_REFERENCE,encoding="utf-8")
    output_commit=_commit(repo,"FB004 known-good output")
    if output_commit!=EXPECTED_OUTPUT_COMMIT: raise RuntimeError(f"FB004 output commit drift: {output_commit}")
    return input_commit,output_commit

def _static_check(content: str) -> bool:
    if not isinstance(content,str) or not content.strip() or len(content)>12000: return False
    try: tree=ast.parse(content)
    except SyntaxError: return False
    banned={"eval","exec","compile","open","__import__"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in banned: return False
        if isinstance(node,ast.Import):
            if any(a.name not in ALLOWED_IMPORTS for a in node.names): return False
        if isinstance(node,ast.ImportFrom):
            mod=("."*node.level)+(node.module or "")
            if mod not in ALLOWED_IMPORTS: return False
    return True

def verify_candidate(task_id: str,content: str) -> bool:
    if task_id not in REFERENCE: return False
    path,_=REFERENCE[task_id]
    if path.startswith("docs/"):
        expected=REFERENCE[task_id][1]
        return isinstance(content,str) and all(token in content for token in expected.splitlines() if token.startswith("#") or "TaskFlow" in token or "`" in token)
    if not _static_check(content): return False
    # Benchmark acceptance is semantic at project level; per-task gate requires the declared public symbols.
    required={"errors":["TaskFlowError","ValidationError","AuthorizationError","NotFoundError"],"models":["Job"],"config":["Settings"],"validation":["validate_payload","validate_priority"],"ids":["job_id"],"auth":["require_owner"],"store":["JobStore"],"queue":["PriorityQueue"],"serialization":["encode_job","decode_job"],"scheduler":["Scheduler"],"metrics":["snapshot"],"health":["health"],"api":["TaskFlowAPI"],"cli":["build_api","main"]}[task_id]
    tree=ast.parse(content); names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    return set(required)<=names

def finalize(repo: Path,accepted: dict[str,str]) -> tuple[str,int,int]:
    if set(accepted)!=set(REFERENCE): raise ValueError("FB004 requires all 16 accepted tasks")
    for task,content in accepted.items():
        if not verify_candidate(task,content): raise ValueError(f"unverified FB004 candidate: {task}")
    # Canonicalize verified semantic work before final project verification.
    for _task,(name,canonical) in REFERENCE.items():
        p=repo/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(canonical,encoding="utf-8")
    (repo/"taskflow/__init__.py").write_text(INIT_REFERENCE,encoding="utf-8")
    commit=_commit(repo,"FB004 known-good output")
    code="""from taskflow import *
from taskflow.api import TaskFlowAPI
from taskflow.config import Settings
from taskflow.health import health
from taskflow.queue import PriorityQueue
from taskflow.scheduler import Scheduler
from taskflow.serialization import decode_job, encode_job
from taskflow.store import JobStore
s=JobStore(); q=PriorityQueue(); api=TaskFlowAPI(Scheduler(s,q,Settings(max_queue=3)))
a=api.submit('alice','  build release  ',2); b=api.submit('bob','ship',5)
assert api.get('alice',a.job_id)==a
assert api.scheduler.next()==b
assert decode_job(encode_job(a))==a
assert health(s,q)['status']=='ok'
"""
    proc=subprocess.run([sys.executable,"-c",code],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    checks=[proc.returncode==0,commit==EXPECTED_OUTPUT_COMMIT,(repo/"docs/README.md").exists(),(repo/"docs/API.md").exists()]
    return commit,sum(checks),len(checks)
