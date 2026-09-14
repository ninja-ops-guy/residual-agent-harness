from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

INPUT_COMMIT = "35d17ee0aa7cf39f405baf12e3a71e211111787f"
EXPECTED_OUTPUT_COMMIT = "efbe57071650782261916655e90205cff0278ba9"
GIT_ENV = {"GIT_AUTHOR_NAME":"Residual Benchmark","GIT_AUTHOR_EMAIL":"benchmark@residual.local","GIT_COMMITTER_NAME":"Residual Benchmark","GIT_COMMITTER_EMAIL":"benchmark@residual.local","GIT_AUTHOR_DATE":"2026-01-01T00:00:00+0000","GIT_COMMITTER_DATE":"2026-01-01T00:00:00+0000"}

INPUT_FILES = {
    "service/__init__.py":"# FB002 fixture\n",
    "service/text.py":"def slugify(value: str) -> str:\n    raise NotImplementedError\n",
    "service/retry.py":"def retry_delay(attempt: int, base: float = 0.25, cap: float = 8.0) -> float:\n    raise NotImplementedError\n",
    "service/paths.py":"def safe_join(root: str, child: str) -> str:\n    raise NotImplementedError\n",
    "service/config.py":"def parse_bool(value: str) -> bool:\n    raise NotImplementedError\n",
    "service/summary.py":"def config_summary(name: str, enabled: str) -> str:\n    raise NotImplementedError\n",
    "service/banner.py":"def service_banner(name: str, attempt: int, root: str, child: str) -> str:\n    raise NotImplementedError\n",
    "README.md":"# FB002 fixture\n\nImplement the six service helpers.\n",
}

REFERENCE = {
    "text":("service/text.py",'import re\n\ndef slugify(value: str) -> str:\n    value = value.strip().lower()\n    value = re.sub(r"[^a-z0-9]+", "-", value)\n    return value.strip("-")\n'),
    "retry":("service/retry.py",'def retry_delay(attempt: int, base: float = 0.25, cap: float = 8.0) -> float:\n    if attempt < 0:\n        raise ValueError("attempt must be non-negative")\n    return min(cap, base * (2 ** attempt))\n'),
    "paths":("service/paths.py",'from pathlib import Path\n\ndef safe_join(root: str, child: str) -> str:\n    base = Path(root).resolve()\n    target = (base / child).resolve()\n    if target != base and base not in target.parents:\n        raise ValueError("path escapes root")\n    return str(target)\n'),
    "config":("service/config.py",'def parse_bool(value: str) -> bool:\n    normalized = value.strip().lower()\n    if normalized in {"1", "true", "yes", "on"}:\n        return True\n    if normalized in {"0", "false", "no", "off"}:\n        return False\n    raise ValueError("invalid boolean")\n'),
    "summary":("service/summary.py",'from .config import parse_bool\nfrom .text import slugify\n\ndef config_summary(name: str, enabled: str) -> str:\n    return f"{slugify(name)}:{\'enabled\' if parse_bool(enabled) else \'disabled\'}"\n'),
    "banner":("service/banner.py",'from .paths import safe_join\nfrom .retry import retry_delay\n\ndef service_banner(name: str, attempt: int, root: str, child: str) -> str:\n    return f"{name}|delay={retry_delay(attempt):.2f}|path={safe_join(root, child)}"\n'),
}
INIT_REFERENCE='from .banner import service_banner\nfrom .config import parse_bool\nfrom .paths import safe_join\nfrom .retry import retry_delay\nfrom .summary import config_summary\nfrom .text import slugify\n\n__all__ = ["config_summary", "parse_bool", "retry_delay", "safe_join", "service_banner", "slugify"]\n'
DEPENDENCIES={"text":(),"retry":(),"paths":(),"config":(),"summary":("text","config"),"banner":("retry","paths")}
PROMPTS={
"text":"Implement only service/text.py. Define slugify(value: str) -> str. Strip outer whitespace, lowercase, replace every run of non-ASCII-alphanumeric characters with one hyphen, then strip leading/trailing hyphens. Return JSON {\"code\": \"<complete module source>\"}. You may import re only.",
"retry":"Implement only service/retry.py. Define retry_delay(attempt: int, base: float = 0.25, cap: float = 8.0) -> float. Negative attempt raises ValueError. Otherwise return min(cap, base * 2**attempt). Return JSON {\"code\": \"<complete module source>\"}. No imports.",
"paths":"Implement only service/paths.py. Define safe_join(root: str, child: str) -> str using pathlib.Path.resolve. Return the resolved target when it is root or below root; otherwise raise ValueError. Return JSON {\"code\": \"<complete module source>\"}. You may import pathlib only.",
"config":"Implement only service/config.py. Define parse_bool(value: str) -> bool. Case-insensitive trimmed true values: 1,true,yes,on. False values: 0,false,no,off. Anything else raises ValueError. Return JSON {\"code\": \"<complete module source>\"}. No imports.",
"summary":"Implement only service/summary.py. Define config_summary(name: str, enabled: str) -> str. Use service.text.slugify and service.config.parse_bool. Return '<slug>:enabled' or '<slug>:disabled'. Return JSON {\"code\": \"<complete module source>\"}. Only relative imports from .text and .config are allowed.",
"banner":"Implement only service/banner.py. Define service_banner(name: str, attempt: int, root: str, child: str) -> str. Use retry_delay and safe_join and return '<name>|delay=<delay with 2 decimals>|path=<resolved path>'. Return JSON {\"code\": \"<complete module source>\"}. Only relative imports from .retry and .paths are allowed.",}
TEST_SNIPPETS={
"text":"from service.text import slugify; assert slugify('  Hello, World!  ') == 'hello-world'; assert slugify('A___B') == 'a-b'; assert slugify('---') == ''",
"retry":"from service.retry import retry_delay; assert retry_delay(0)==0.25; assert retry_delay(3)==2.0; assert retry_delay(99)==8.0;\ntry:\n retry_delay(-1); raise AssertionError\nexcept ValueError: pass",
"paths":"import tempfile, pathlib; from service.paths import safe_join; d=tempfile.mkdtemp(); assert safe_join(d,'a/b') == str((pathlib.Path(d)/'a/b').resolve());\ntry:\n safe_join(d,'../escape'); raise AssertionError\nexcept ValueError: pass",
"config":"from service.config import parse_bool; assert parse_bool(' YES ') is True; assert parse_bool('off') is False;\ntry:\n parse_bool('maybe'); raise AssertionError\nexcept ValueError: pass",
"summary":"from service.summary import config_summary; assert config_summary(' My API ', 'on') == 'my-api:enabled'; assert config_summary('My API','0') == 'my-api:disabled'",
"banner":"import tempfile, pathlib; from service.banner import service_banner; d=tempfile.mkdtemp(); expected=f\"svc|delay=1.00|path={(pathlib.Path(d)/'x').resolve()}\"; assert service_banner('svc',2,d,'x') == expected",}
ALLOWED_IMPORTS={"text":{"re"},"retry":set(),"paths":{"pathlib"},"config":set(),"summary":{".text",".config"},"banner":{".retry",".paths"}}
BANNED_CALLS={"eval","exec","compile","open","input","__import__","getattr","setattr","delattr","globals","locals","vars","breakpoint"}
BANNED_ATTRS={"read_text","read_bytes","write_text","write_bytes","open","unlink","rename","replace","rmdir","mkdir","touch","chmod","symlink_to","hardlink_to"}

def _git(repo:Path,*args:str)->str:
    env=os.environ.copy();env.update(GIT_ENV)
    return subprocess.check_output(["git",*args],cwd=repo,env=env,text=True).strip()

def _commit(repo:Path,message:str)->str:
    env=os.environ.copy();env.update(GIT_ENV)
    subprocess.run(["git","add","."],cwd=repo,env=env,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(["git","-c","commit.gpgsign=false","commit","-q","-m",message],cwd=repo,env=env,check=True)
    return _git(repo,"rev-parse","HEAD")

def create_fixture(repo:Path,*,known_good:bool=False)->tuple[str,str|None]:
    repo.mkdir(parents=True,exist_ok=False);subprocess.run(["git","init","-q"],cwd=repo,check=True)
    for name,content in INPUT_FILES.items():
        p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding="utf-8")
    input_commit=_commit(repo,"FB002 input")
    if input_commit!=INPUT_COMMIT: raise RuntimeError(f"FB002 input commit drift: {input_commit}")
    if not known_good:return input_commit,None
    for _,(name,content) in REFERENCE.items():(repo/name).write_text(content,encoding="utf-8")
    (repo/"service/__init__.py").write_text(INIT_REFERENCE,encoding="utf-8")
    output_commit=_commit(repo,"FB002 known-good output")
    if output_commit!=EXPECTED_OUTPUT_COMMIT: raise RuntimeError(f"FB002 output commit drift: {output_commit}")
    return input_commit,output_commit

def _validate_ast(task_id:str,source:str)->None:
    if task_id not in REFERENCE or not isinstance(source,str) or not source.strip() or len(source)>5000: raise ValueError("invalid candidate source")
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,(ast.Global,ast.Nonlocal,ast.AsyncFunctionDef,ast.ClassDef,ast.Lambda,ast.With,ast.AsyncWith)): raise ValueError("candidate uses disallowed construct")
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in BANNED_CALLS: raise ValueError("candidate uses disallowed call")
        if isinstance(node,ast.Attribute) and (node.attr.startswith("_") or node.attr in BANNED_ATTRS): raise ValueError("candidate uses disallowed attribute")
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS[task_id]: raise ValueError("candidate import not allowed")
        if isinstance(node,ast.ImportFrom):
            module=("."*node.level)+(node.module or "")
            if module not in ALLOWED_IMPORTS[task_id]: raise ValueError("candidate import not allowed")

def verify_candidate(task_id:str,source:str)->bool:
    if task_id not in REFERENCE:return False
    try:
        _validate_ast(task_id,source)
        with tempfile.TemporaryDirectory(prefix="fb002-verify-") as td:
            repo=Path(td)/"repo";create_fixture(repo)
            for dep in DEPENDENCIES[task_id]:
                name,content=REFERENCE[dep];(repo/name).write_text(content,encoding="utf-8")
            target,_=REFERENCE[task_id];(repo/target).write_text(source.rstrip()+"\n",encoding="utf-8")
            code="import sys; sys.path.insert(0, r'%s'); %s"%(str(repo),TEST_SNIPPETS[task_id])
            return subprocess.run([sys.executable,"-c",code],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
    except (ValueError,SyntaxError,subprocess.TimeoutExpired,RuntimeError):return False

def finalize(repo:Path,accepted:dict[str,str])->tuple[str,int,int]:
    if set(accepted)!=set(REFERENCE):raise ValueError("FB002 requires all six accepted tasks")
    for task_id,source in accepted.items():
        if not verify_candidate(task_id,source):raise ValueError(f"unverified candidate: {task_id}")
    for _,(name,canonical_source) in REFERENCE.items():(repo/name).write_text(canonical_source,encoding="utf-8")
    (repo/"service/__init__.py").write_text(INIT_REFERENCE,encoding="utf-8")
    commit=_commit(repo,"FB002 known-good output");checks=[]
    for task_id in REFERENCE:
        code="import sys; sys.path.insert(0, r'%s'); %s"%(str(repo),TEST_SNIPPETS[task_id])
        checks.append(subprocess.run([sys.executable,"-c",code],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0)
    checks.append(commit==EXPECTED_OUTPUT_COMMIT)
    return commit,sum(checks),len(checks)
