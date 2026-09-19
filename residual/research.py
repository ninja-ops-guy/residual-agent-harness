"""Versioned Research Workbench backed by a separate Git research branch."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

DEFAULT_REMOTE="origin"
DEFAULT_BRANCH="research/experiment-catalog"
CATALOG_PATH="research/catalog.json"
DEFAULT_REPOSITORY="ninja-ops-guy/residual-agent-harness"

def _json_bytes(v): return (json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def _sha(b): return hashlib.sha256(b).hexdigest()
def _git(*args, cwd=None):
    p=subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True,timeout=60)
    if p.returncode: raise RuntimeError("research catalog git operation failed")
    return p.stdout.strip()
def repo_root(cwd=None): return Path(_git("rev-parse","--show-toplevel",cwd=cwd))

def _repository():
    value=os.environ.get("RESIDUAL_RESEARCH_REPOSITORY",DEFAULT_REPOSITORY)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",value): raise ValueError("invalid research repository")
    return value

def _http_catalog(branch):
    repository=_repository()
    encoded=urllib.parse.quote(branch,safe="")
    req=urllib.request.Request(f"https://api.github.com/repos/{repository}/branches/{encoded}",headers={"User-Agent":"Residual-Research-Workbench/1"})
    with urllib.request.urlopen(req,timeout=30) as response:
        payload=response.read(1_000_001)
    if len(payload)>1_000_000: raise ValueError("research branch response too large")
    commit=json.loads(payload.decode("utf-8"))["commit"]["sha"]
    if not re.fullmatch(r"[a-f0-9]{40}",commit): raise ValueError("invalid research commit")
    path="/".join(urllib.parse.quote(part,safe="") for part in CATALOG_PATH.split("/"))
    raw_url=f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"
    req=urllib.request.Request(raw_url,headers={"User-Agent":"Residual-Research-Workbench/1"})
    with urllib.request.urlopen(req,timeout=30) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError("research catalog too large")
    return commit,raw

def _product_identity():
    head=None
    try:
        root=repo_root(Path(__file__).resolve().parent)
        head=_git("rev-parse","HEAD",cwd=root)
    except (OSError,RuntimeError):
        pass
    try: version=metadata.version("residual-agent-harness")
    except metadata.PackageNotFoundError: version=None
    return {"git_head":head,"package_version":version}
def state_root():
    p=os.environ.get("RESIDUAL_RESEARCH_HOME")
    return Path(p).expanduser() if p else Path.home()/".local"/"state"/"residual"/"research"
def sync(root=None, remote=DEFAULT_REMOTE, branch=DEFAULT_BRANCH):
    try:
        git_root=repo_root(Path(__file__).resolve().parent if root is None else root)
        _git("fetch","--quiet","--no-tags",remote,branch,cwd=git_root)
        commit=_git("rev-parse","FETCH_HEAD",cwd=git_root)
        raw=_git("show",f"{commit}:{CATALOG_PATH}",cwd=git_root).encode()
    except (OSError,RuntimeError):
        commit,raw=_http_catalog(branch)
    catalog=json.loads(raw)
    if catalog.get("schema_version")!=1 or not isinstance(catalog.get("experiments"),list): raise ValueError("unsupported research catalog")
    ids=[x.get("id") for x in catalog["experiments"] if isinstance(x,dict)]
    if len(ids)!=len(catalog["experiments"]) or any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        raise ValueError("research catalog experiment ids must be unique nonempty strings")
    dest=state_root()/"catalogs"/commit
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"catalog.json").write_bytes(raw)
    current=state_root()/"current.json"
    current.parent.mkdir(parents=True,exist_ok=True)
    current.write_text(json.dumps({"commit":commit,"branch":branch,"catalog_sha256":_sha(raw)},indent=2)+"\n")
    return catalog,commit
def current(branch=DEFAULT_BRANCH):
    meta=json.loads((state_root()/"current.json").read_text())
    if meta.get("branch") != branch: raise ValueError("cached research catalog branch mismatch")
    raw=(state_root()/"catalogs"/meta["commit"]/"catalog.json").read_bytes()
    if _sha(raw)!=meta["catalog_sha256"]: raise ValueError("cached research catalog integrity failure")
    return json.loads(raw),meta["commit"]
def get_experiment(exp_id,catalog):
    found=[x for x in catalog["experiments"] if x.get("id")==exp_id]
    if len(found)!=1: raise ValueError("experiment id missing or ambiguous")
    return found[0]
def import_experiment(exp_id, output=None, do_sync=True, branch=DEFAULT_BRANCH):
    catalog,commit=sync(branch=branch) if do_sync else current(branch)
    exp=get_experiment(exp_id,catalog)
    out=Path(output or f"runs/research/{exp_id}")
    if out.exists() and any(out.iterdir()): raise FileExistsError("experiment workspace already exists")
    out.mkdir(parents=True,exist_ok=True)
    definition=_json_bytes(exp); (out/"experiment.json").write_bytes(definition)
    identity=_product_identity()
    manifest={"schema_version":1,"experiment_id":exp_id,"catalog_commit":commit,
      "experiment_sha256":_sha(definition),"created_at":datetime.now(timezone.utc).isoformat(),
      **identity,"status":"IMPORTED",
      "usage_policy":"unknown-is-null","authority":"experiment definitions do not grant tool/model authority"}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (out/"events.jsonl").touch()
    for d in ("attempts","receipts","release"): (out/d).mkdir()
    return out,manifest
def main(argv=None):
    p=argparse.ArgumentParser(prog="residual research",description="RESIDUAL Research Workbench")
    p.add_argument("--branch",default=DEFAULT_BRANCH)
    s=p.add_subparsers(dest="cmd")
    s.add_parser("sync"); s.add_parser("list")
    imp=s.add_parser("import"); imp.add_argument("experiment_id"); imp.add_argument("--output")
    args=p.parse_args(argv)
    cmd=args.cmd or "list"
    try:
      if cmd=="sync":
        c,commit=sync(branch=args.branch); print(json.dumps({"status":"synced","commit":commit,"experiments":len(c["experiments"])})); return 0
      if cmd=="list":
        try: c,commit=sync(branch=args.branch)
        except Exception: c,commit=current(args.branch)
        print(f"Research catalog {commit[:12]}")
        for e in c["experiments"]: print(f'{e["id"]}\t{e.get("status","")}\t{e.get("title","")}')
        return 0
      if cmd=="import":
        out,m=import_experiment(args.experiment_id,args.output,branch=args.branch); print(json.dumps({"status":"imported","output":str(out),"manifest":m})); return 0
    except (OSError,ValueError,RuntimeError,FileNotFoundError,FileExistsError,json.JSONDecodeError):
      print("residual research: workbench operation failed closed",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
