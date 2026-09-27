#!/usr/bin/env python3
import argparse, os, pathlib
from canary_lib import *
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--adapter",required=True); ap.add_argument("--evidence",required=True); ap.add_argument("--operation-id",required=True); ap.add_argument("--execute",action="store_true"); a=ap.parse_args()
    if not a.execute: refuse("rollback defaults to dry-run")
    if os.environ.get("RESIDUAL_R4_ROLLBACK_GO")!="R4.1-ROLLBACK-8701367D": refuse("explicit rollback authorization absent")
    env=os.environ.copy(); env.update({"R4_CANARY_EVIDENCE":str(pathlib.Path(a.evidence).resolve()),"R4_CANARY_OPERATION_ID":a.operation_id})
    r=command([a.adapter,"rollback"],timeout=30,env=env); write_json(pathlib.Path(a.evidence)/"rollback.json",{"operation_id":a.operation_id,"returncode":r.returncode,"stderr":r.stderr,"stdout":r.stdout})
    raise SystemExit(0 if r.returncode==0 else 1)
if __name__=="__main__": main()
