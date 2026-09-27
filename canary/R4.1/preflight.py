#!/usr/bin/env python3
import argparse, datetime, json, os, pathlib, shutil, sys
from canary_lib import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--candidate",required=True); ap.add_argument("--seal",required=True); ap.add_argument("--evidence",required=True); ap.add_argument("--authorization-receipt",required=True); ap.add_argument("--adapter",required=True); ap.add_argument("--operation-id",required=True); ap.add_argument("--execute",action="store_true"); a=ap.parse_args()
    if not a.execute: refuse("dry-run is the default; --execute and explicit GO are required")
    if os.environ.get("RESIDUAL_R4_CANARY_GO") != GO_VALUE: refuse("explicit operator GO is absent or incorrect")
    candidate=pathlib.Path(a.candidate).resolve(); seal=pathlib.Path(a.seal).resolve(); evidence=pathlib.Path(a.evidence)
    if not safe_dir(a.evidence,[candidate,seal,seal.parent]): refuse("unsafe evidence destination")
    if evidence.exists() and (evidence.is_symlink() or any(evidence.iterdir())): refuse("evidence destination must be new or empty")
    adapter=pathlib.Path(a.adapter); receipt=pathlib.Path(a.authorization_receipt)
    if not adapter.is_absolute() or not adapter.is_file() or not os.access(adapter,os.X_OK): refuse("adapter must be an absolute executable file")
    if not receipt.is_absolute() or not receipt.is_file() or receipt.is_symlink(): refuse("authorization receipt must be an absolute regular file")
    for label,args,expected in [("HEAD",["git","-C",str(candidate),"rev-parse","HEAD"],EXPECTED_HEAD),("tree",["git","-C",str(candidate),"rev-parse","HEAD^{tree}"],EXPECTED_TREE),("parent",["git","-C",str(candidate),"rev-parse","HEAD^"],EXPECTED_PARENT)]:
        r=command(args); 
        if r.returncode or r.stdout.strip()!=expected: refuse("candidate "+label+" mismatch")
    if command(["git","-C",str(candidate),"status","--porcelain=v1"]).stdout.strip(): refuse("candidate is dirty")
    rem=command(["git","-C",str(candidate),"remote"]).stdout.strip()
    if rem: refuse("unexpected Git remotes: "+rem)
    sums=command(["sha256sum","-c","SHA256SUMS"],timeout=15,cwd=seal)
    if sums.returncode: refuse("seal verification failed")
    sj=read_json(seal/"SEAL.json")
    if sj.get("qualification",{}).get("disposition")!="READY_FOR_CANARY" or sj.get("canary_execution_occurred") is not False: refuse("seal disposition is invalid")
    auth=read_json(receipt)
    if auth.get("operation_id")!=a.operation_id or auth.get("scope")!="R4_CONTINUITY_SINGLE_OPERATION" or not auth.get("approver") or not auth.get("expires_at_utc"): refuse("authorization receipt scope/operation is invalid")
    try: expires=datetime.datetime.fromisoformat(auth["expires_at_utc"].replace("Z","+00:00"))
    except ValueError: refuse("authorization receipt expiry is invalid")
    if expires <= datetime.datetime.now(datetime.timezone.utc): refuse("authorization receipt has expired")
    evidence.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(receipt,evidence/"authorization-receipt.json")
    result={"authorization_receipt_sha256":sha256(receipt),"candidate":{"head":EXPECTED_HEAD,"tree":EXPECTED_TREE,"parent":EXPECTED_PARENT,"clean":True,"remotes":[]},"operation_id":a.operation_id,"seal_verified":True,"status":"PASS"}
    write_json(evidence/"preflight.json",result); print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()
