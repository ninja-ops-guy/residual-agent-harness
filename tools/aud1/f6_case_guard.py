#!/usr/bin/env python3
"""Strict AUD-1 F6 physical-evidence front end for PR #403.

Uses the existing read-only collector primitives, but adds release-critical guards the
first helper lacked: raw git identity (so 40-char SHAs are not redacted), live Station
process provenance, required phase/remote artifacts, timing and ownership validation,
explicit stale-result HTTP 403 proof, and closed-world manifest verification.
"""
from __future__ import annotations
import argparse, datetime as dt, importlib.util, json, os, pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("f6_collect_base", HERE / "f6_collect.py")
base = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(base)
TARGET_SHA = base.TARGET_SHA
SCHEMA = "residual.aud1.f6.physical.v2"
GRACE = 180.0
LABELS = {
 "F6-A-inside-window": ["00-preflight","01-owned-before-interrupt","02-transport-down","03-reconnected-inside-window","04-terminal"],
 "F6-B-outside-window": ["00-preflight","01-owned-before-interrupt","02-transport-down","03-after-worker-authority-grace","04-reassigned","05-old-runner-returned","06-stale-result-boundary"],
}
ATTACH = {
 "F6-A-inside-window": ["remote-01-owned-before.json","remote-02-transport-down.json","remote-03-reconnected.json","remote-04-terminal.json"],
 "F6-B-outside-window": ["remote-01-owned-before.json","remote-02-transport-down.json","remote-03-after-grace.json","remote-04-reassigned.json","remote-05-old-returned.json","stale-result-rejection.json"],
}

def utcnow(): return dt.datetime.now(dt.timezone.utc).isoformat()
def parse_utc(v):
    x=dt.datetime.fromisoformat(v.replace("Z","+00:00")); return (x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
def git(repo,*args):
    p=subprocess.run(["git",*args],cwd=repo,text=True,capture_output=True,timeout=15,check=False)
    return p.returncode,p.stdout.strip(),p.stderr.strip()
def raw_identity(repo):
    repo=pathlib.Path(repo).resolve(); rh,h,eh=git(repo,"rev-parse","HEAD"); rs,s,es=git(repo,"status","--porcelain=v1"); rt,t,et=git(repo,"rev-parse","HEAD^{tree}")
    return {"path":str(repo),"expected_sha":TARGET_SHA,"head_sha":h,"tree_sha":t,"tracked_or_untracked_changes":s.splitlines() if s else [],"exact_head":rh==0 and h==TARGET_SHA,"clean_worktree":rs==0 and not s,"git_errors":[x for x in (eh,es,et) if x]}
def alive(pid):
    try: pid=int(pid)
    except Exception: return False
    if pid<=0:return False
    if os.name=="nt":
        try:
            import ctypes; h=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
            if not h:return False
            ctypes.windll.kernel32.CloseHandle(h); return True
        except Exception:return False
    try: os.kill(pid,0); return True
    except ProcessLookupError:return False
    except PermissionError:return True
    except OSError:return False
def within(child,parent):
    c=pathlib.Path(child).resolve(); p=pathlib.Path(parent).resolve(); return c==p or p in c.parents
def station_record(path,repo,db,url):
    p=pathlib.Path(path).resolve(); side=pathlib.Path(str(p)+".sha256"); errors=[]
    if not p.is_file(): return None,["station launch record missing"]
    if not side.is_file(): return None,["station launch record digest missing"]
    try: expected=side.read_text(encoding="utf-8").split()[0]; actual=base.sha256_file(p); rec=json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:return None,[f"station launch record unreadable: {e}"]
    if expected!=actual:errors.append("station launch record digest mismatch")
    r=pathlib.Path(repo).resolve(); d=pathlib.Path(db).resolve(); mod=pathlib.Path(rec.get("server_module",".")).resolve()
    if rec.get("schema")!="residual.aud1.f6.station-launch.v1":errors.append("station launch schema mismatch")
    if rec.get("candidate_head")!=TARGET_SHA:errors.append("station process not bound to target candidate")
    if pathlib.Path(rec.get("candidate_repo",".")).resolve()!=r:errors.append("station process candidate repo mismatch")
    if not within(mod,r) or not mod.is_file():errors.append("station module not inside exact candidate checkout")
    elif rec.get("server_module_sha256")!=base.sha256_file(mod):errors.append("station module bytes changed since launch")
    if pathlib.Path(rec.get("station_data",".")).resolve()!=d.parent:errors.append("station data/DB mismatch")
    if rec.get("station_url","").rstrip("/")!=url.rstrip("/"):errors.append("station URL mismatch")
    if not alive(rec.get("pid")):errors.append("station launch PID is not alive")
    safe=base.redact(rec); safe["record_sha256"]=actual; safe["process_alive"]=alive(rec.get("pid")); return safe,errors
def outdir(root,case):return pathlib.Path(root).resolve()/case

def capture(a):
    out=outdir(a.output,a.case); out.mkdir(parents=True,exist_ok=True); ident=raw_identity(a.candidate_repo)
    if not ident["exact_head"]:raise SystemExit(f"REFUSE: candidate is {ident['head_sha']!r}, expected {TARGET_SHA}")
    if not ident["clean_worktree"]:raise SystemExit("REFUSE: candidate checkout is dirty")
    proc,errors=station_record(a.station_record,a.candidate_repo,a.db,a.station_url)
    if errors:raise SystemExit("REFUSE: "+"; ".join(errors))
    probe=base.public_probe(a.station_url)
    if probe.get("status")!=200 or probe.get("authority_key_names_present"):raise SystemExit("REFUSE: public bootstrap metadata-only proof failed")
    seq=len(list(out.glob("snapshot-*.json")))+1
    payload={"schema":SCHEMA,"case":a.case,"label":a.label,"candidate":ident,"station_process":proc,"environment":base.environment_snapshot(),"station":base.station_snapshot(a.db,a.project,a.task),"public_probe":probe}
    path=out/f"snapshot-{seq:03d}-{a.label}.json"; base.atomic_json(path,payload); print(path); return 0

def delegate(name,a): return getattr(base,name)(a)
def readshots(out):
    d={}
    for p in sorted(out.glob("snapshot-*.json")):
        try:x=json.loads(p.read_text(encoding="utf-8")); d[x.get("label")]=x
        except Exception:pass
    return d
def ledger(out):
    p=out/"operator-ledger.jsonl"; rows=[]
    if not p.is_file():return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        try:rows.append(json.loads(line))
        except Exception:rows.append({"_invalid":line})
    return rows
def ltime(rows,kind,last=False):
    vals=[]
    for r in rows:
        if r.get("kind")==kind and r.get("timestamp"):
            try:vals.append(parse_utc(r["timestamp"]))
            except Exception:pass
    return vals[-1 if last else 0] if vals else None
def task(s):
    ts=s.get("station",{}).get("tasks",[]); return ts[0].get("value",{}) if ts else {}
def attached(out,name):
    p=out/"attachments"/name
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return None

def validate(out,case):
    errors=[]; shots=readshots(out); rows=ledger(out)
    for label in LABELS[case]:
        s=shots.get(label)
        if not s:errors.append(f"missing required snapshot: {label}"); continue
        if not s.get("candidate",{}).get("exact_head"):errors.append(f"snapshot {label} not target-bound")
        if not s.get("candidate",{}).get("clean_worktree"):errors.append(f"snapshot {label} dirty")
        if s.get("station_process",{}).get("candidate_head")!=TARGET_SHA:errors.append(f"snapshot {label} lacks Station process binding")
        if not s.get("station_process",{}).get("record_sha256"):errors.append(f"snapshot {label} lacks Station witness digest")
        q=s.get("public_probe") or {}
        if q.get("status")!=200 or q.get("authority_key_names_present"):errors.append(f"snapshot {label} bootstrap proof failed")
        if s.get("station",{}).get("sqlite_integrity")!="ok":errors.append(f"snapshot {label} SQLite integrity failed")
    for name in ATTACH[case]:
        if not (out/"attachments"/name).is_file():errors.append(f"missing required attachment: {name}")
        if not (out/"attachments"/(name+".meta.json")).is_file():errors.append(f"missing attachment metadata: {name}")
    down=ltime(rows,"TUNNEL_DOWN"); up=ltime(rows,"TUNNEL_UP",True)
    if not down:errors.append("operator ledger lacks TUNNEL_DOWN")
    if not any(r.get("kind")=="HITL" for r in rows):errors.append("operator ledger lacks ownership confirmation")
    if any(r.get("_invalid") for r in rows):errors.append("operator ledger contains invalid JSON")
    if case=="F6-A-inside-window":
        if not up:errors.append("operator ledger lacks TUNNEL_UP")
        elif down:
            sec=(up-down).total_seconds()
            if not 0<=sec<GRACE:errors.append(f"inside-window reconnect timing invalid: {sec:.3f}s")
        b=task(shots.get("01-owned-before-interrupt",{})); r=task(shots.get("03-reconnected-inside-window",{}))
        if not b.get("owner") or b.get("owner")!=r.get("owner"):errors.append("inside-window same owner not proven")
        if not b.get("lease") or b.get("lease")!=r.get("lease"):errors.append("inside-window same lease not proven")
    else:
        ds=shots.get("02-transport-down",{}).get("station",{}).get("captured_at"); gs=shots.get("03-after-worker-authority-grace",{}).get("station",{}).get("captured_at")
        if not ds or not gs:errors.append("outside-window timing snapshots incomplete")
        elif (parse_utc(gs)-parse_utc(ds)).total_seconds()<GRACE:errors.append("outside-window worker grace not exceeded")
        b=task(shots.get("01-owned-before-interrupt",{})); r=task(shots.get("04-reassigned",{})); old=task(shots.get("05-old-runner-returned",{}))
        if not b.get("owner"):errors.append("pre-interrupt owner missing")
        if not r.get("owner") or r.get("owner")==b.get("owner"):errors.append("reassignment to different owner not proven")
        if old.get("owner")!=r.get("owner"):errors.append("old runner return changed ownership")
        stale=attached(out,"stale-result-rejection.json")
        if not stale:errors.append("stale-result rejection artifact missing/invalid")
        else:
            if stale.get("schema")!="residual.aud1.f6.stale-probe.v1":errors.append("stale probe schema mismatch")
            if stale.get("observed_status")!=403 or stale.get("rejected") is not True:errors.append("stale result not explicitly rejected with HTTP 403")
            if stale.get("accepted") is True:errors.append("stale result was accepted")
        if not any(r.get("kind")=="REASSIGNMENT" for r in rows):errors.append("reassignment ledger entry missing")
        if not any(r.get("kind")=="STALE_RESULT" for r in rows):errors.append("stale-result rejection ledger entry missing")
    return {"ok":not errors,"validated_at":utcnow(),"case":case,"errors":errors,"required_labels":LABELS[case],"required_attachments":ATTACH[case]}

def freeze(a):
    out=outdir(a.output,a.case)
    if not out.is_dir():raise SystemExit(f"Case directory not found: {out}")
    v=validate(out,a.case); files=[]
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name not in {"manifest.json","manifest.sha256"}):files.append({"path":p.relative_to(out).as_posix(),"bytes":p.stat().st_size,"sha256":base.sha256_file(p)})
    m={"schema":SCHEMA,"case":a.case,"frozen_at":utcnow(),"target_sha":TARGET_SHA,"validation":v,"files":files}; raw=(json.dumps(m,indent=2,sort_keys=True)+"\n").encode(); (out/"manifest.json").write_bytes(raw); digest=base.sha256_bytes(raw); (out/"manifest.sha256").write_text(f"{digest}  manifest.json\n",encoding="utf-8"); print(json.dumps({"manifest_sha256":digest,"validation":v},indent=2)); return 0 if v["ok"] else 2
def verify(a):
    out=outdir(a.output,a.case); mp=out/"manifest.json"; dp=out/"manifest.sha256"; errors=[]
    if not mp.is_file() or not dp.is_file():print(json.dumps({"ok":False,"errors":["manifest files missing"]},indent=2));return 2
    m=json.loads(mp.read_text(encoding="utf-8")); expected={x["path"] for x in m.get("files",[])}; actual={p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file() and p.name not in {"manifest.json","manifest.sha256"}}
    errors += [f"missing: {x}" for x in sorted(expected-actual)] + [f"unexpected after freeze: {x}" for x in sorted(actual-expected)]
    for x in m.get("files",[]):
        p=out/x["path"]
        if p.is_file() and base.sha256_file(p)!=x["sha256"]:errors.append(f"hash mismatch: {x['path']}")
    if dp.read_text(encoding="utf-8").split()[0]!=base.sha256_file(mp):errors.append("manifest hash mismatch")
    if not m.get("validation",{}).get("ok"):errors.append("manifest records failed physical-evidence validation")
    print(json.dumps({"verified_at":utcnow(),"case":a.case,"ok":not errors,"errors":errors,"manifest_sha256":base.sha256_file(mp)},indent=2));return 0 if not errors else 2

def parser():
    p=argparse.ArgumentParser();p.add_argument("--output",default="AUD1-F6-EVIDENCE");s=p.add_subparsers(dest="cmd",required=True)
    c=s.add_parser("capture");c.add_argument("--case",required=True,choices=list(LABELS));c.add_argument("--label",required=True);c.add_argument("--candidate-repo",required=True);c.add_argument("--station-record",required=True);c.add_argument("--db",required=True);c.add_argument("--project",required=True);c.add_argument("--task");c.add_argument("--station-url",required=True);c.set_defaults(func=capture)
    n=s.add_parser("note");n.add_argument("--case",required=True,choices=list(LABELS));n.add_argument("--kind",required=True,choices=["HITL","TUNNEL_DOWN","TUNNEL_UP","OBSERVATION","REASSIGNMENT","STALE_RESULT","ERROR"]);n.add_argument("--message",required=True);n.set_defaults(func=lambda a:delegate("note",a))
    a=s.add_parser("attach");a.add_argument("--case",required=True,choices=list(LABELS));a.add_argument("--file",required=True);a.add_argument("--name",default="");a.set_defaults(func=lambda x:delegate("attach",x))
    f=s.add_parser("freeze");f.add_argument("--case",required=True,choices=list(LABELS));f.set_defaults(func=freeze)
    v=s.add_parser("verify");v.add_argument("--case",required=True,choices=list(LABELS));v.set_defaults(func=verify)
    return p

def main(argv=None):a=parser().parse_args(argv);return a.func(a)
if __name__=="__main__":raise SystemExit(main())
