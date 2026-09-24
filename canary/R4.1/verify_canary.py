#!/usr/bin/env python3
import argparse, pathlib, subprocess
from canary_lib import read_json

REQUIRED=["authorization-receipt.json","preflight.json","scope.json","runner.json","prestate.json","poststate.json","network-actions.json","outbox-transitions.json","receipt-result.json","receiver-count.json","service-state-before.json","service-state-after.json","rollback-readiness.json","safety-counters.json","operator-interventions.json","SHA256SUMS"]
def disposition(root):
    if any(not (root/x).is_file() for x in REQUIRED): return "EVIDENCE_INCOMPLETE"
    c=subprocess.run(["sha256sum","-c","SHA256SUMS"],cwd=root,text=True,capture_output=True)
    if c.returncode: return "EVIDENCE_INCOMPLETE"
    try:
        pf,scope,run=read_json(root/"preflight.json"),read_json(root/"scope.json"),read_json(root/"runner.json")
        actions=read_json(root/"network-actions.json")["actions"]; outbox=read_json(root/"outbox-transitions.json")["states"]
        receipt=read_json(root/"receipt-result.json"); count=read_json(root/"receiver-count.json")["count"]
        before,after=read_json(root/"service-state-before.json"),read_json(root/"service-state-after.json")
        safe=read_json(root/"safety-counters.json"); interventions=read_json(root/"operator-interventions.json")
        oid=scope["operation_id"]
        posts=[i for i,x in enumerate(actions) if x.get("method")=="POST"]
        gets=[i for i,x in enumerate(actions) if x.get("method")=="GET" and x.get("path")=="comms/receipt"]
        ok=(pf["status"]=="PASS" and run["completed"] and run["duration_seconds"]<=120 and pf["operation_id"]==oid==run["operation_id"] and len(posts)==1 and len(gets)==1 and posts[0]<gets[0] and not any(i>gets[0] for i in posts) and outbox==["PENDING","SENT_INDETERMINATE","ACKED"] and receipt.get("found") is True and receipt.get("operation_id")==oid and count==1 and before==after and all(v==0 for v in safe.values()) and interventions==[] and read_json(root/"rollback-readiness.json").get("available") is True)
        return "CANARY_PASS" if ok else "CANARY_FAIL"
    except Exception: return "EVIDENCE_INCOMPLETE"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("evidence"); a=ap.parse_args(); d=disposition(pathlib.Path(a.evidence).resolve()); print(d); raise SystemExit(0 if d=="CANARY_PASS" else 1)
if __name__=="__main__": main()
