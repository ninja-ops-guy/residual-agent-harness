#!/usr/bin/env python3
import pathlib, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parent
def run(args,env=None): return subprocess.run(args,text=True,capture_output=True,env=env)
def main():
    with tempfile.TemporaryDirectory() as td:
        v=run([sys.executable,str(ROOT/"verify_canary.py"),td]); assert v.stdout.strip()=="EVIDENCE_INCOMPLETE"
        r=run([sys.executable,str(ROOT/"run_canary.py"),"--candidate",td,"--seal",td,"--evidence",td+"/e","--authorization-receipt",td+"/a","--adapter",td+"/x","--operation-id","test"]); assert r.returncode==2 and "dry-run" in r.stderr
        rb=run([sys.executable,str(ROOT/"rollback.py"),"--adapter",td+"/x","--evidence",td,"--operation-id","test"]); assert rb.returncode==2 and "dry-run" in rb.stderr
    print("SELF_TEST_PASS: refusal defaults and incomplete-evidence disposition")
if __name__=="__main__": main()
