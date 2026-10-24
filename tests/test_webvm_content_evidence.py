"""Content-bound evidence: opt-in retention binds worker-visible payloads.

Browser/workbench missions enable retention so Mission Control evidence shows
what the model was asked, what it returned, and what was accepted. The core
Harness default stays hash-only.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from residual.core import Obligation, Registry, Task, Verdict, canonical
from residual.engine import Harness, Limits
from residual.providers import CallableProvider, Reply, Usage
from residual.storage import verify_ledger
from residual.workbench.build import execute_build


def _reply(updates):
    return Reply(canonical({"updates": updates, "requests": []}), Usage(100, 20, 0, "reported"))


def _run(retain):
    registry = Registry()
    registry.check("host:echo", lambda value, ctx: Verdict.passed(), "1")
    task = Task("t1", "Return a marker.", {}, (Obligation("a", "Return the marker value.", "host:echo"),))
    provider = CallableProvider("local", lambda packet, max_tokens: _reply({"a": "MARKER_CONTENT"}))
    harness = Harness(registry, provider, None, Limits(local_rounds=1), retain_content=retain)
    return harness, harness.run(task)


class CoreRetentionTests(unittest.TestCase):
    def test_default_harness_events_stay_hash_only(self):
        harness, result = _run(False)
        self.assertTrue(result["success"])
        completed = next(e for e in harness.ledger.events if e["kind"] == "call_completed")
        self.assertNotIn("response_text", completed["data"])
        self.assertNotIn("MARKER_CONTENT", canonical(harness.ledger.events))

    def test_retained_events_bind_goal_packet_response_and_value(self):
        harness, result = _run(True)
        self.assertTrue(result["success"])
        data = {e["kind"]: e["data"] for e in harness.ledger.events}
        self.assertEqual(data["run_started"]["goal"], "Return a marker.")
        self.assertIn("packet", data["call_reserved"])
        self.assertIn("Return the marker value.", canonical(data["call_reserved"]["packet"]))
        self.assertIn("MARKER_CONTENT", data["call_completed"]["response_text"])
        self.assertEqual(data["obligation_accepted"]["value"], "MARKER_CONTENT")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            harness.ledger.write(path)
            self.assertEqual(verify_ledger(path, result["trace_root"])["root"], result["trace_root"])


class BrowserChainVerificationTests(unittest.TestCase):
    def test_shipped_browser_verifier_matches_ledger_and_rejects_tamper(self):
        harness, result = _run(True)
        mid = "m-" + "e" * 32
        frames = [canonical({"data": event, "kind": "evidence", "mission_id": mid})
                  for event in harness.ledger.events]
        script = """
import fs from 'node:fs';
let source = fs.readFileSync('demo/vm/mission-control.js', 'utf8');
source = source.replace(/^import .*;\\n/gm, '');
const moduleUrl = 'data:text/javascript;base64,' + Buffer.from(source).toString('base64');
const verifier = await import(moduleUrl);
const frames = JSON.parse(process.argv[1]);
const missionId = process.argv[2];
const traceRoot = process.argv[3];
const good = await verifier.verifyEvidenceChain(frames, missionId, traceRoot);
const tampered = [...frames];
const outer = JSON.parse(tampered[0]);
outer.data.data.task_id = 'tampered';
tampered[0] = JSON.stringify(outer);
const bad = await verifier.verifyEvidenceChain(tampered, missionId, traceRoot);
console.log(JSON.stringify({good, bad}));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script, json.dumps(frames), mid, result["trace_root"]],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        proof = json.loads(completed.stdout)
        self.assertTrue(proof["good"]["ok"], proof)
        self.assertEqual(proof["good"]["head"], result["trace_root"])
        self.assertFalse(proof["bad"]["ok"], proof)
        self.assertIn("digest mismatch", proof["bad"]["reason"])


class WorkbenchRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.out = self.root / "runs"; self.mail = self.root / "mail"
        self.mail.mkdir()

    def _observer(self, value):
        def callback(event):
            if event['kind'] != 'inference_requested':
                return
            request = event['data']
            reply = {'request_id': request['request_id'], 'ok': True,
                     'text': canonical({'updates': {'build': value}, 'requests': []})}
            (self.mail / f"{event['mission_id']}-{request['request_id']}.json").write_text(canonical(reply))
        return callback

    def _request(self, mid, prompt, required):
        return {'id': mid, 'mode': 'build', 'prompt': prompt, 'files': [], 'model': 'gpt-5-nano',
                'max_calls': 1, 'max_output_tokens': 1536, 'cloud_consent': True, 'required_text': required}

    def _events(self, mid):
        return [json.loads(line) for line in (self.out / mid / 'trace.jsonl').read_text().splitlines()]

    def test_browser_build_trace_binds_what_the_model_did(self):
        value = {'summary': 'Calculator', 'files': [{'path': 'index.html', 'content': '<h1>Calculator</h1>'}]}
        mid = 'm-' + 'c' * 32
        summary = execute_build(self._request(mid, 'Build a calculator', ['Calculator']), root=self.root,
                                output_root=self.out, mailbox=self.mail, observer=self._observer(value))
        self.assertTrue(summary['result']['success'])
        data = {e['kind']: e['data'] for e in self._events(mid)}
        self.assertEqual(data['run_started']['goal'], 'Build a calculator')
        self.assertIn('packet', data['call_reserved'])
        self.assertIn('Build a calculator', data['call_reserved']['packet']['obligations'][0]['instruction'])
        self.assertIn('response_text', data['call_completed'])
        self.assertIn('Calculator', data['call_completed']['response_text'])
        self.assertEqual(data['obligation_accepted']['value'], value)

    def test_failed_verification_retains_verifier_message(self):
        value = {'summary': 'Unrelated', 'files': [{'path': 'index.html', 'content': '<h1>Other</h1>'}]}
        mid = 'm-' + 'd' * 32
        summary = execute_build(self._request(mid, 'Build something', ['Calculator']), root=self.root,
                                output_root=self.out, mailbox=self.mail, observer=self._observer(value))
        self.assertFalse(summary['result']['success'])
        check = next(e for e in self._events(mid) if e['kind'] == 'verification')
        self.assertEqual(check['data']['status'], 'fail')
        self.assertEqual(check['data']['code'], 'required_text_missing')
        self.assertTrue(check['data']['message'])


if __name__ == '__main__':
    unittest.main()
