#!/usr/bin/env python3
import argparse, json, os, pathlib, subprocess, sys, time
from canary_lib import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--candidate",required=True); ap.add_argument("--seal",required=True); ap.add_argument("--evidence",required=True); ap.add_argument("--authorization-receipt",required=True); ap.add_argument("--adapter",required=True); ap.add_argument("--operation-id",required=True); ap.add_argument("--execute",action="store_true"); a=ap.parse_args()
    if not a.execute: refuse("dry-run is the default; no canary executed")
    if os.environ.get("RESIDUAL_R4_CANARY_GO")!=GO_VALUE: refuse("explicit operator GO is absent or incorrect")
    pre=[sys.executable,str(pathlib.Path(__file__).with_name("preflight.py")),"--candidate",a.candidate,"--seal",a.seal,"--evidence",a.evidence,"--authorization-receipt",a.authorization_receipt,"--adapter",a.adapter,"--operation-id",a.operation_id,"--execute"]
    p=command(pre,timeout=30,env=os.environ.copy())
    if p.returncode: refuse("preflight failed: "+p.stderr.strip())
    ev=pathlib.Path(a.evidence); started=time.time(); scope={"operation_id":a.operation_id,"scope":"R4_CONTINUITY_SINGLE_OPERATION","max_initial_posts":1,"max_receipt_lookups":1,"deadline_epoch":started+TIMEOUT_SECONDS}; write_json(ev/"scope.json",scope)
    env=os.environ.copy(); env.update({"R4_CANARY_EVIDENCE":str(ev),"R4_CANARY_OPERATION_ID":a.operation_id,"R4_CANARY_SCOPE":str(ev/"scope.json")})
    steps=["preflight","prestate","single-post-and-interrupt","receipt-first-reconcile","poststate","rollback-readiness"]
    transcript=[]
    try:
        for step in steps:
            remaining=max(1,int(started+TIMEOUT_SECONDS-time.time()))
            r=command([a.adapter,step],timeout=remaining,env=env); transcript.append({"step":step,"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr,"timestamp_epoch":time.time()})
            if r.returncode: raise RuntimeError(step+" failed")
        write_json(ev/"runner.json",{"completed":True,"duration_seconds":round(time.time()-started,3),"operation_id":a.operation_id,"steps":transcript,"timeout_seconds":TIMEOUT_SECONDS})
    except Exception as exc:
        write_json(ev/"runner.json",{"completed":False,"duration_seconds":round(time.time()-started,3),"error":str(exc),"operation_id":a.operation_id,"steps":transcript,"timeout_seconds":TIMEOUT_SECONDS}); refuse(str(exc),1)
    print("CANARY_RUN_COMPLETE_EVIDENCE_REQUIRES_VERIFICATION")
if __name__=="__main__": main()
