"""Local HTTP/SSE projection for Residual Studio.

The service is deliberately thin: snapshots are derived from the durable
RuntimeJournal; mutations are delegated to an injected authoritative
ControlAdapter. The HTTP layer never mints receipts or mutates Factory state
on its own.
"""
from __future__ import annotations
import argparse, hmac, json, os, time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Protocol
from .runtime_journal import RuntimeJournal
from .studio_control import AuthoritativeStudioControl

class ControlAdapter(Protocol):
    def control(self, action: str, payload: dict) -> dict: ...

@dataclass
class ReadOnlyControl:
    def control(self, action: str, payload: dict) -> dict:
        raise PermissionError("Factory control adapter is not configured")

class StudioProjection:
    def __init__(self, journal: RuntimeJournal, *, model: str = "local"):
        self.journal,self.model=journal,model
    def snapshot(self)->dict:
        attempts=self.journal.attempts()
        workers=[]
        accepted=blocked=0
        plan_hash="—"
        for row in attempts:
            plan_hash=row["plan_hash"]
            state=row["state"]
            ui={"RESERVED":"idle","RUNNING":"running","CANDIDATE":"verified","VIOLATED":"failed","FAILED":"failed","CANCELLED":"failed","AUDIT_FAILED":"failed","PURGED":"idle"}.get(state,"idle")
            if state=="CANDIDATE": accepted+=1
            workers.append({"id":row["worker_id"],"role":"Worker","state":ui,"task":row["task_id"]})
        return {"runId":self.journal.trace_id,"status":"running" if any(x["state"] in ("RESERVED","RUNNING") for x in attempts) else "idle","planHash":plan_hash,"accepted":accepted,"total":len(attempts),"ready":sum(1 for x in attempts if x["state"]=="RESERVED"),"blocked":blocked,"receipts":accepted,"model":self.model,"workers":workers,"updatedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}

class StudioHandler(BaseHTTPRequestHandler):
    projection: StudioProjection
    control_adapter: ControlAdapter
    token: str
    def log_message(self, fmt, *args): return
    def _json(self,status,value):
        data=(json.dumps(value,separators=(",",":"))+"\n").encode()
        self.send_response(status);self.send_header("content-type","application/json");self.send_header("content-length",str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=="/v1/factory/snapshot": return self._json(200,self.projection.snapshot())
        if self.path=="/v1/factory/events":
            self.send_response(200);self.send_header("content-type","text/event-stream");self.send_header("cache-control","no-cache");self.end_headers()
            last=None
            try:
                for _ in range(120):
                    value=self.projection.snapshot(); encoded=json.dumps(value,separators=(",",":"))
                    if encoded!=last:self.wfile.write(("data: "+encoded+"\n\n").encode());self.wfile.flush();last=encoded
                    time.sleep(1)
            except (BrokenPipeError,ConnectionResetError): pass
            return
        self._json(404,{"error":"not found"})
    def do_POST(self):
        if self.path!="/v1/factory/control": return self._json(404,{"error":"not found"})
        auth=self.headers.get("authorization","")
        expected="Bearer "+self.token
        if not self.token or not hmac.compare_digest(auth,expected): return self._json(401,{"error":"unauthorized"})
        try:
            length=int(self.headers.get("content-length","0"))
            if length<=0 or length>65536: raise ValueError
            payload=json.loads(self.rfile.read(length))
            action=payload.get("action")
            if action not in {"plan","approve","run","cancel","integrate"}: return self._json(400,{"error":"unsupported action"})
            result=self.control_adapter.control(action,payload)
            self._json(200,{"ok":True,**result})
        except PermissionError as exc:self._json(403,{"ok":False,"error":str(exc)})
        except Exception:self._json(400,{"ok":False,"error":"control request rejected"})

def serve(journal_path: str, trace_id: str, *, host="127.0.0.1", port=8765, token="", model="local", control_adapter=None, state_dir=None):
    journal=RuntimeJournal(journal_path,trace_id=trace_id)
    handler=type("ConfiguredStudioHandler",(StudioHandler,),{"projection":StudioProjection(journal,model=model),"control_adapter":control_adapter or (AuthoritativeStudioControl(state_dir) if state_dir else ReadOnlyControl()),"token":token})
    server=ThreadingHTTPServer((host,port),handler)
    server.serve_forever()

def main(argv=None):
    p=argparse.ArgumentParser(description="Local Residual Studio Factory API")
    p.add_argument("--journal",required=True);p.add_argument("--trace-id",required=True);p.add_argument("--host",default="127.0.0.1");p.add_argument("--port",type=int,default=8765);p.add_argument("--model",default="local");p.add_argument("--state-dir");p.add_argument("--token",default=os.environ.get("RESIDUAL_STUDIO_CONTROL_TOKEN",""))
    a=p.parse_args(argv);serve(a.journal,a.trace_id,host=a.host,port=a.port,token=a.token,model=a.model,state_dir=a.state_dir)
if __name__=="__main__": raise SystemExit(main())
