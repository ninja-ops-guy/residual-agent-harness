"""Exact-module tests using a real SQLite Station-schema fixture.

The fixture is intentionally NOT a replacement for whole-Station qualification.
Run tests/test_station_mission_sync.py in the complete repository as well.
"""
import concurrent.futures
import contextlib
import hashlib
import http.server
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
# Import the actual delivered modules without executing unrelated package roots.
PKG = "mission_sync_under_test"
package = types.ModuleType(PKG)
package.__path__ = [str(ROOT / "residual/station")]
sys.modules[PKG] = package
M = importlib.import_module(PKG + ".mission_sync")
C = importlib.import_module(PKG + ".mission_client")
R = importlib.import_module(PKG + ".mission_routes")


class Fixture:
    def __init__(self, root):
        self.db = Path(root) / "station.sqlite3"
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:
            c.executescript('CREATE TABLE projects(id TEXT PRIMARY KEY,value TEXT); CREATE TABLE tasks(project TEXT,id TEXT,value TEXT,PRIMARY KEY(project,id));')
            for pid in ("p1", "p2"):
                p = {"id":pid,"name":"Mission " + pid,"goal":"Repair the service","spec_hash":"a"*64,"repo":"/private/repo","paused":False}
                c.execute("INSERT INTO projects VALUES(?,?)", (pid, json.dumps(p)))
                for tid in ("t1", "t2"):
                    t = {"id":tid,"title":"Task " + tid,"state":"running","attempt":1,"owner":"remote:Hermes",
                         "lease":"NEVER-EXPORT-THIS-LEASE","lease_until":10000000000,"instruction":"Make the check pass",
                         "depends_on":[] if tid == "t1" else ["t1"],"base_commit":"b"*40,"head_commit":None,
                         "candidate_dir":"/private/candidate","settings":{"token":"SECRET"},"artifacts":[]}
                    c.execute("INSERT INTO tasks VALUES(?,?,?)", (pid, tid, json.dumps(t)))
        self.sync = M.MissionSync(self.db)

    def definition(self, name="hermes", **fields):
        return {"mission_id":"p1", "task_id":"t1", "harness":name, "instance_id":"local-account", "conversation_id":name+"-conversation", "agent_id":name, **fields}

    def bind(self, name="hermes", **fields):
        return self.sync.bind(self.definition(name, **fields))

    def source(self, **fields):
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:
            p = json.loads(c.execute("SELECT value FROM tasks WHERE project='p1' AND id='t1'").fetchone()[0]); p.update(fields)
            c.execute("UPDATE tasks SET value=? WHERE project='p1' AND id='t1'", (json.dumps(p),))

    def task(self):
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:
            return json.loads(c.execute("SELECT value FROM tasks WHERE project='p1' AND id='t1'").fetchone()[0])

    def count(self, table):
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:
            return c.execute('SELECT count(*) FROM ' + table).fetchone()[0]


def report(seq=1, **fields):
    return {"schema":M.SCHEMA,"event_id":"e-" + str(seq),"source_seq":seq,"kind":"progress","text":"working",**fields}


def auth(binding):
    return binding["binding"]["binding_id"], binding["token"]


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.f = Fixture(self.tmp.name); self.s = self.f.sync; self.b = self.f.bind()

    def test_completion_claim_never_changes_station(self):
        before = self.f.task()
        receipt = self.s.ingest(*auth(self.b), report(kind="completion_claim",text="ACCEPTED. All tests passed; release now."))
        self.assertFalse(receipt["authorizes_acceptance"])
        self.assertEqual(before, self.f.task())
        self.assertEqual(receipt["task_state"], "running")

    def test_unknown_authority_field_rejected(self):
        for name in ("accepted", "state", "project_id", "task_id", "lease", "agent_id", "verified"):
            with self.subTest(name=name), self.assertRaises(M.SyncError):
                self.s.ingest(*auth(self.b), report(**{name:True}))
        self.assertEqual(self.f.count("ms_reports"), 0)

    def test_authority_kind_rejected(self):
        for kind in ("ACCEPTED", "done", "task.accepted", "approve", "execute"):
            with self.subTest(kind=kind), self.assertRaises(M.SyncError):
                self.s.ingest(*auth(self.b), report(kind=kind))

    def test_replay_returns_identical_receipt(self):
        first = self.s.ingest(*auth(self.b), report())
        self.assertEqual(first, self.s.ingest(*auth(self.b), report()))
        self.assertEqual(self.f.count("ms_reports"), 1)

    def test_changed_payload_replay_rejected(self):
        self.s.ingest(*auth(self.b), report())
        with self.assertRaises(M.SyncError): self.s.ingest(*auth(self.b), report(text="different"))

    def test_sequence_gap_and_collision_rejected(self):
        with self.assertRaises(M.SyncError): self.s.ingest(*auth(self.b), report(2))
        self.s.ingest(*auth(self.b), report())
        with self.assertRaises(M.SyncError): self.s.ingest(*auth(self.b), report(event_id="other"))
        self.s.ingest(*auth(self.b), report(2))

    def test_sequence_types_strict(self):
        for value in (True, 1.0, "1", -1, 0, 2**60):
            with self.subTest(value=value), self.assertRaises(M.SyncError):
                self.s.ingest(*auth(self.b), report(source_seq=value))

    def test_restart_retains_receipt_and_outbox(self):
        first = self.s.ingest(*auth(self.b), report()); batch = self.s.poll(*auth(self.b))
        again = M.MissionSync(self.f.db)
        self.assertEqual(first, again.ingest(*auth(self.b), report()))
        self.assertEqual(batch["deliveries"], again.poll(*auth(self.b))["deliveries"])

    def test_concurrent_duplicate_admission(self):
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            receipts = list(pool.map(lambda _:self.s.ingest(*auth(self.b), report()), range(16)))
        self.assertTrue(all(r == receipts[0] for r in receipts)); self.assertEqual(self.f.count("ms_reports"), 1)

    def test_wrong_token_and_cross_binding_rejected(self):
        other = self.f.bind("openclaw")
        with self.assertRaises(PermissionError): self.s.poll(auth(self.b)[0], other["token"])
        with self.assertRaises(PermissionError): self.s.ingest(auth(self.b)[0], "bad", report())

    def test_revocation_survives_restart(self):
        self.s.revoke(auth(self.b)[0]); self.s = M.MissionSync(self.f.db)
        for op in (lambda:self.s.poll(*auth(self.b)), lambda:self.s.ingest(*auth(self.b), report())):
            with self.assertRaises(PermissionError): op()

    def test_expiry_boundary(self):
        now = [1000.0]; s = M.MissionSync(self.f.db, clock=lambda:now[0])
        # Remove the high-water created by setUp's operator binding, for this isolated clock fixture.
        with s.connect() as c: c.execute("DELETE FROM ms_meta WHERE key='clock_high_water'")
        b = s.bind(self.f.definition("clock", ttl_seconds=60)); now[0] = 1060
        with self.assertRaises(PermissionError): s.poll(*auth(b))

    def test_clock_rollback_rejected(self):
        self.s.clock = lambda:1
        with self.assertRaises(M.SyncError): self.s.poll(*auth(self.b))

    def test_stale_attempt_rejects_read_write_and_ack(self):
        batch = self.s.poll(*auth(self.b)); item=batch["deliveries"][0]
        self.f.source(attempt=2)
        for op in (lambda:self.s.poll(*auth(self.b)), lambda:self.s.ingest(*auth(self.b),report()), lambda:self.s.acknowledge(*auth(self.b),item["payload"]["delivery_id"],item["sha256"])):
            with self.assertRaises(M.SyncError): op()
        self.assertEqual(self.s.overview()["missions"][1]["tasks"][0]["conversations"][0]["sync_state"], "STALE")

    def test_stale_spec_rejected(self):
        with self.s.connect() as c:
            p=json.loads(c.execute("SELECT value FROM projects WHERE id='p1'").fetchone()[0]);p["spec_hash"]="z"*64
            c.execute("UPDATE projects SET value=? WHERE id='p1'",(json.dumps(p),))
        with self.assertRaises(M.SyncError): self.s.continuation(*auth(self.b))

    def test_new_binding_on_current_attempt(self):
        self.f.source(attempt=2); fresh=self.f.bind("successor")
        self.assertEqual(self.s.continuation(*auth(fresh))["packet"]["task"]["attempt"],2)
        self.assertEqual(self.f.task()["lease"],"NEVER-EXPORT-THIS-LEASE")

    def test_projection_does_not_leak_internal_fields(self):
        combined=json.dumps([self.s.overview(),self.s.continuation(*auth(self.b)),self.s.poll(*auth(self.b))])
        for secret in ("NEVER-EXPORT", "/private/", '"settings"', self.b["token"]): self.assertNotIn(secret,combined)

    def test_no_implicit_text_fanout(self):
        other=self.f.bind("other",share_messages=True)
        self.s.ingest(*auth(self.b),report(kind="message",text="private text"))
        self.assertNotIn("private text",json.dumps(self.s.poll(*auth(other))))

    def test_explicit_two_way_conversation_fanout(self):
        a=self.f.bind("source",share_messages=True);b=self.f.bind("target",share_messages=True)
        self.s.ingest(*auth(a),report(text="bounded update"))
        items=self.s.poll(*auth(b))["deliveries"]
        self.assertEqual(items[0]["payload"]["kind"],"conversation.observation")
        self.assertFalse(items[0]["payload"]["data"]["authorizes_acceptance"])

    def test_cross_task_and_project_isolation(self):
        a=self.f.bind("source",share_messages=True)
        others=[self.f.bind("differenttask",task_id="t2",share_messages=True),self.f.bind("differentproject",mission_id="p2",share_messages=True)]
        self.s.ingest(*auth(a),report(text="scoped-secret"))
        for other in others: self.assertNotIn("scoped-secret",json.dumps(self.s.poll(*auth(other))))

    def test_direction_boundaries(self):
        inbound=self.f.bind("inbound",direction="inbound"); outbound=self.f.bind("outbound",direction="outbound")
        with self.assertRaises(PermissionError):self.s.poll(*auth(inbound))
        with self.assertRaises(PermissionError):self.s.ingest(*auth(outbound),report())
        self.s.ingest(*auth(inbound),report())

    def test_unknown_and_cross_binding_ack_rejected(self):
        other=self.f.bind("other"); item=self.s.poll(*auth(self.b))["deliveries"][0]
        with self.assertRaises(M.SyncError):self.s.acknowledge(*auth(other),item["payload"]["delivery_id"],item["sha256"])
        with self.assertRaises(M.SyncError):self.s.acknowledge(*auth(self.b),"unknown","a"*64)
        with self.assertRaises(M.SyncError):self.s.acknowledge(*auth(self.b),item["payload"]["delivery_id"],"a"*64)

    def test_ack_is_durable_and_idempotent(self):
        item=self.s.poll(*auth(self.b))["deliveries"][0]
        args=(*auth(self.b),item["payload"]["delivery_id"],item["sha256"])
        self.assertEqual(self.s.acknowledge(*args),self.s.acknowledge(*args))
        self.assertEqual(M.MissionSync(self.f.db).poll(*auth(self.b))["deliveries"],[])

    def test_station_state_changes_produce_new_snapshot(self):
        first=self.s.poll(*auth(self.b))["deliveries"][0]
        self.s.acknowledge(*auth(self.b),first["payload"]["delivery_id"],first["sha256"])
        self.f.source(state="integrated")
        second=self.s.poll(*auth(self.b))["deliveries"][0]
        self.assertEqual(second["payload"]["data"]["task"]["state"],"integrated")
        self.assertNotEqual(first["sha256"],second["sha256"])

    def test_echo_suppression_requires_offered_scoped_id(self):
        with self.assertRaises(M.SyncError):self.s.ingest(*auth(self.b),report(echo_delivery_id="invented"))
        item=self.s.poll(*auth(self.b))["deliveries"][0]
        receipt=self.s.ingest(*auth(self.b),report(echo_delivery_id=item["payload"]["delivery_id"]))
        self.assertTrue(receipt["echo_suppressed"])

    def test_backpressure_rolls_back_report_and_sequence(self):
        a=self.f.bind("source",share_messages=True);b=self.f.bind("target",share_messages=True)
        with mock.patch.object(M,"MAX_PENDING",1):
            self.s.ingest(*auth(a),report())
            before=self.f.count("ms_journal")
            with self.assertRaises(M.SyncError):self.s.ingest(*auth(a),report(2))
            self.assertEqual(self.f.count("ms_reports"),1);self.assertEqual(before,self.f.count("ms_journal"))
            # A full queue is still drainable; snapshot creation cannot deadlock it.
            batch=self.s.poll(*auth(b)); self.assertFalse(batch["current_snapshot_queued"])
            item=batch["deliveries"][0];self.s.acknowledge(*auth(b),item["payload"]["delivery_id"],item["sha256"])
            self.s.ingest(*auth(a),report(2))

    def test_report_and_journal_rollback_on_fanout_failure(self):
        a=self.f.bind("source",share_messages=True);self.f.bind("target",share_messages=True)
        before=self.f.count("ms_journal")
        with mock.patch.object(self.s,"_enqueue",side_effect=OSError("injected disk fault")):
            with self.assertRaises(OSError):self.s.ingest(*auth(a),report())
        self.assertEqual(before,self.f.count("ms_journal"));self.assertEqual(self.f.count("ms_reports"),0)
        self.s.ingest(*auth(a),report())

    def test_hash_chain_and_pagination(self):
        self.s.ingest(*auth(self.b),report())
        prev="0"*64;after=0;seen=0
        while True:
            page=self.s.journal("p1",after,1)
            if not page["events"]:break
            for item in page["events"]:
                self.assertEqual(item["prev_hash"],prev);self.assertEqual(item["hash"],M.digest({"previous":prev,"event":item["event"]}));prev=item["hash"];seen+=1
            after=page["next_after"]
        self.assertEqual(seen,2)

    def test_references_remain_claims(self):
        receipt=self.s.ingest(*auth(self.b),report(kind="artifact_reference",references=[{"label":"receipt","sha256":"a"*64}]))
        self.assertFalse(receipt["authorizes_acceptance"]);self.assertEqual(self.f.task()["artifacts"],[])
        with self.assertRaises(M.SyncError):self.s.ingest(*auth(self.b),report(2,references=[{"label":"r","sha256":"bad"}]))

    def test_strict_json_rejects_duplicates_nonfinite_and_root(self):
        for raw in ('{"a":1,"a":2}','{"x":{"a":1,"a":2}}','{"a":NaN}','{"a":1e999}','[]','{"x":"'+'x'*50000+'"}'):
            with self.subTest(raw=raw[:30]),self.assertRaises(M.SyncError):M.strict_json(raw)

    def test_oversize_and_control_char_report_rejected(self):
        for value in ("x"*8001,"bad\x00text",1,None):
            with self.subTest(value=str(value)[:20]),self.assertRaises(M.SyncError):self.s.ingest(*auth(self.b),report(text=value))

    def test_token_not_in_journal_or_database_values(self):
        with self.s.connect() as c:
            for table in ("ms_bindings","ms_journal"):
                for row in c.execute('SELECT * FROM '+table):self.assertNotIn(self.b["token"],str(tuple(row)))


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.f=Fixture(self.tmp.name);self.b=self.f.bind();self.s=self.f.sync
        self.config={"url":"http://127.0.0.1:8765","binding_id":auth(self.b)[0],"token":auth(self.b)[1],"conversation_id":"hermes-conversation","spool":str(Path(self.tmp.name)/'spool.sqlite3')}
        self.client=C.MissionClient(self.config,request=self.request)
    def request(self, action, data):
        if action=='report':return self.s.ingest(*auth(self.b),data)
        if action=='poll':return self.s.poll(*auth(self.b),**data)
        if action=='ack':return self.s.acknowledge(*auth(self.b),**data)
        if action=='context':return self.s.continuation(*auth(self.b))
        raise AssertionError(action)
    def test_durable_outgoing_after_restart(self):
        eid=self.client.record('progress','working',native_event_id='native-1')
        another=C.MissionClient(self.config,request=self.request);another.pump()
        self.assertEqual(self.f.count('ms_reports'),1)
        self.assertEqual(eid,another.record('progress','working',native_event_id='native-1'))
    def test_lost_server_ack_retries_exact_report(self):
        self.client.record('progress','working')
        def drop(action,data):
            value=self.request(action,data)
            if action=='report':raise OSError('lost ACK after commit')
            return value
        self.client.request=drop
        with self.assertRaises(OSError):self.client.pump()
        self.client.request=self.request;self.client.pump();self.assertEqual(self.f.count('ms_reports'),1)
    def test_incoming_commits_before_ack(self):
        def check(action,data):
            if action=='ack':
                with self.client.connect() as c:self.assertIsNotNone(c.execute('SELECT id FROM incoming WHERE id=?',(data['delivery_id'],)).fetchone())
            return self.request(action,data)
        self.client.request=check;self.client.pump()
    def test_peek_context_does_not_consume_conversation(self):
        # Replace initial private binding with an explicitly shared target.
        self.b=self.f.bind('target',share_messages=True)
        self.config.update(binding_id=auth(self.b)[0],token=auth(self.b)[1],conversation_id='target-conversation',spool=str(Path(self.tmp.name)/'target.sqlite3'))
        self.client=C.MissionClient(self.config,request=self.request)
        source=self.f.bind('source',share_messages=True)
        self.s.ingest(*auth(source),report(text='Do not lose this observation'))
        self.client.pump()
        self.assertIn('Do not lose',self.client.context(consume=False));self.assertIn('Do not lose',self.client.context())
        self.assertNotIn('Do not lose',self.client.context())
    def test_foreign_spool_rejected(self):
        with self.assertRaises(M.SyncError):C.MissionClient({**self.config,'binding_id':'other'},request=self.request)
    def test_native_id_content_conflict(self):
        self.client.record('progress','first',native_event_id='x')
        with self.assertRaises(M.SyncError):self.client.record('progress','second',native_event_id='x')
    def test_remote_url_and_credentials_rejected(self):
        for url in ('https://example.com','http://localhost:8765','http://127.0.0.1:8765/?token=x','http://a:b@127.0.0.1:8765'):
            with self.subTest(url=url),self.assertRaises(M.SyncError):C.MissionClient({**self.config,'url':url},request=self.request)
    def test_wrong_native_conversation_config_rejected(self):
        self.client.config['conversation_id']='wrong'
        with self.assertRaises(M.SyncError):self.client.context()
    def test_false_ack_does_not_discard_outgoing(self):
        self.client.record('progress','x');self.client.request=lambda *_:{'recorded':True}
        with self.assertRaises(M.SyncError):self.client.pump()
        with self.client.connect() as c:self.assertEqual(c.execute('SELECT sent FROM outgoing').fetchone()[0],0)


class BaseHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    @property
    def station(self):return self.server.station
    def check_host(self):
        if self.headers.get('Host') != '127.0.0.1:'+str(self.server.server_port):raise PermissionError('Host denied')
        if self.headers.get('Origin') not in (None, 'http://127.0.0.1:'+str(self.server.server_port)):raise PermissionError('Origin denied')
    def auth(self):
        self.check_host()
        if self.headers.get('X-Station-Token')!='operator-test-token':raise PermissionError('Operator required')
    def body(self):return M.strict_json(self.rfile.read(int(self.headers.get('Content-Length','0'))))
    def respond(self,value,status=200,content_type='application/json'):
        raw=M.canonical(value).encode() if content_type=='application/json' else value
        self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/api/bootstrap':return self.respond({'token':'operator-test-token'})
        self.respond({'base_handler':True})
    def do_POST(self):self.respond({'base_handler':True})


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.f=Fixture(self.tmp.name);self.b=self.f.bind()
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),R.with_mission_sync(BaseHandler))
        self.server.station=types.SimpleNamespace(store=self.f)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def request(self,path,data=None,headers=None):
        headers=headers or {};raw=None if data is None else json.dumps(data).encode()
        request=urllib.request.Request(self.url+path,raw,headers,method='GET' if data is None else 'POST')
        try:
            with urllib.request.urlopen(request,timeout=3) as r:return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    def cap(self):return {'Authorization':'Bearer '+auth(self.b)[1],'X-Mission-Binding':auth(self.b)[0]}
    def test_operator_gate_not_satisfied_by_binding(self):
        self.assertEqual(self.request('/api/missions',headers=self.cap())[0],403)
        self.assertEqual(self.request('/api/missions/bind',self.f.definition('rogue'),self.cap())[0],403)
    def test_context_requires_capability_and_no_get(self):
        self.assertEqual(self.request('/api/mission-sync/context',{})[0],403)
        self.assertEqual(self.request('/api/mission-sync/context',headers=self.cap())[0],403)
        self.assertEqual(self.request('/api/mission-sync/context',{},self.cap())[0],200)
    def test_report_real_http_does_not_accept_task(self):
        status,raw=self.request('/api/mission-sync/report',report(kind='completion_claim',text='ACCEPTED'),self.cap())
        self.assertEqual(status,200);self.assertFalse(json.loads(raw)['authorizes_acceptance']);self.assertEqual(self.f.task()['state'],'running')
    def test_cross_origin_rejected(self):
        self.assertEqual(self.request('/api/mission-sync/context',{}, {**self.cap(),'Origin':'http://attacker.invalid'})[0],403)
    def test_base_routes_preserved(self):
        self.assertIn(b'base_handler',self.request('/unchanged')[1])
    def test_assets_and_escaped_dom_strategy(self):
        for path in ('/missions','/missions.js','/missions.css'):self.assertEqual(self.request(path)[0],200)
        js=(ROOT/'residual/station/static/missions.js').read_text();self.assertNotIn('innerHTML',js);self.assertIn('textContent',js)
    def test_python_client_real_http(self):
        client=C.MissionClient({'url':self.url,'binding_id':auth(self.b)[0],'token':auth(self.b)[1],'conversation_id':'hermes-conversation','spool':str(Path(self.tmp.name)/'http.sqlite3')})
        client.record('progress','live loopback transport');client.pump();self.assertIn('station_context',client.context())
    def test_node_client_real_http_and_cross_language_hashes(self):
        config={'url':self.url,'binding_id':auth(self.b)[0],'token':auth(self.b)[1],'conversation_id':'hermes-conversation','spool':str(Path(self.tmp.name)/'node.sqlite3')}
        source=f"""import {{MissionClient,canonical}} from {json.dumps((ROOT/'integrations/mission-sync/openclaw/client.mjs').as_uri())};
const c=new MissionClient(JSON.parse(process.env.TEST_CONFIG));
await c.record('progress','OpenClaw loopback 🌱');await c.pump();
const context=await c.context();if(!context.includes('station_context'))throw Error('missing context');
console.log(canonical({{text:'café 🌱 \\u007f',n:123,a:[true,null]}}));c.close();"""
        result=subprocess.run(['node','--input-type=module','-e',source],env={**os.environ,'TEST_CONFIG':json.dumps(config)},text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),M.canonical({'text':'café 🌱 \x7f','n':123,'a':[True,None]}))
        self.assertEqual(self.f.count('ms_reports'),1)


if __name__=='__main__':unittest.main()
