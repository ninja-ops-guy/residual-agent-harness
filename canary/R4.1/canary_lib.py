#!/usr/bin/env python3
import hashlib, json, os, pathlib, subprocess, sys, time

EXPECTED_HEAD = "8701367db6d3202f24b3eb9f4696b0cadf657985"
EXPECTED_TREE = "79bfe6ed1743907065ed44aeb9c460c47527e0c6"
EXPECTED_PARENT = "eada7577cf6f2de875b508c6a82f47870e3aa673"
GO_VALUE = "R4.1-CANARY-8701367D"
TIMEOUT_SECONDS = 120

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def read_json(path):
    with open(path,encoding="utf-8") as f: return json.load(f)

def write_json(path,obj):
    pathlib.Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def command(argv, timeout=15, env=None, cwd=None):
    return subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env,cwd=cwd,check=False)

def safe_dir(raw, forbidden):
    p=pathlib.Path(raw)
    if not p.is_absolute() or p.is_symlink(): return False
    rp=p.resolve()
    if str(rp) in ("/",str(pathlib.Path.home().resolve())): return False
    return all(rp != pathlib.Path(x).resolve() and pathlib.Path(x).resolve() not in rp.parents for x in forbidden)

def refuse(msg, code=2):
    print("REFUSE: "+msg,file=sys.stderr); raise SystemExit(code)
