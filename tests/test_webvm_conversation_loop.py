"""Conversation-loop workbench tests. Provider responses are explicit test doubles."""
import json
from pathlib import Path
import tempfile
import unittest

from residual.core import ContractError, canonical
from residual.workbench.conversation_build import execute, verified_parent_bundle


class ConversationBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / 'residual').mkdir()
        self.out = self.root / 'runs'; self.mail = self.root / 'mail'; self.mail.mkdir()
        self.cid = 'c-' + 'a' * 32

    def observer(self, value, inspect=None):
        def callback(event):
            if event['kind'] != 'inference_requested': return
            request = event['data']
            packet = json.loads(request['messages'][-1]['content'])
            if inspect: inspect(packet)
            reply = {'request_id': request['request_id'], 'ok': True,
                     'text': canonical({'updates': {'build': value}, 'requests': []})}
            (self.mail / f"{event['mission_id']}-{request['request_id']}.json").write_text(canonical(reply))
        return callback

    def request(self, mid, prompt, parent=None):
        value = {'id': mid, 'conversation_id': self.cid, 'mode': 'build', 'prompt': prompt,
                 'files': [], 'model': 'gpt-5-nano', 'max_calls': 1,
                 'max_output_tokens': 1536, 'cloud_consent': True, 'required_text': ['Calculator']}
        if parent: value['parent_mission_id'] = parent
        return value

    def test_follow_up_freezes_verified_parent_and_records_lineage(self):
        first = 'm-' + '1' * 32
        initial = {'summary': 'Calculator v1', 'files': [
            {'path': 'index.html', 'content': '<h1>Calculator</h1><button>Add</button>'},
            {'path': 'app.js', 'content': 'const add=(a,b)=>a+b;'}]}
        one = execute(self.request(first, 'Build a calculator'), root=self.root, output_root=self.out,
                      mailbox=self.mail, observer=self.observer(initial))
        self.assertTrue(one['result']['success']); self.assertEqual(one['lineage']['revision'], 1)
        seen = {}
        def inspect(packet):
            seen['ids'] = [item['artifact_id'] for item in packet['evidence']]
            seen['text'] = '\n'.join(item['text'] for item in packet['evidence'])
            seen['instruction'] = packet['obligations'][0]['instruction']
        second = 'm-' + '2' * 32
        revised = {'summary': 'Calculator v2 dark mode', 'files': [
            {'path': 'index.html', 'content': '<body class="dark"><h1>Calculator</h1><button>Add</button></body>'},
            {'path': 'app.js', 'content': 'const add=(a,b)=>a+b;'}]}
        two = execute(self.request(second, 'Make it dark mode', first), root=self.root, output_root=self.out,
                      mailbox=self.mail, observer=self.observer(revised, inspect))
        self.assertTrue(two['result']['success'])
        self.assertEqual(two['lineage']['conversation_id'], self.cid)
        self.assertEqual(two['lineage']['parent_mission_id'], first)
        self.assertEqual(two['lineage']['parent_trace_root'], one['result']['trace_root'])
        self.assertEqual(two['lineage']['revision'], 2)
        self.assertIn('prior-lineage', seen['ids']); self.assertIn('prior-0', seen['ids'])
        self.assertIn(first, seen['text']); self.assertIn(one['result']['trace_root'], seen['text']); self.assertIn('Calculator', seen['text'])
        self.assertIn('COMPLETE replacement deliverable', seen['instruction'])
        self.assertIn('Preserve unrelated working behavior', seen['instruction'])
        self.assertEqual((self.out / second / 'artifacts/index.html').read_text(), revised['files'][0]['content'])

    def test_parent_tamper_is_rejected_before_provider_dispatch(self):
        first = 'm-' + '3' * 32
        bundle = {'summary': 'Calculator', 'files': [{'path': 'index.html', 'content': '<h1>Calculator</h1>'}]}
        execute(self.request(first, 'Build a calculator'), root=self.root, output_root=self.out,
                mailbox=self.mail, observer=self.observer(bundle))
        (self.out / first / 'artifacts/index.html').write_text('<h1>TAMPERED</h1>')
        called = []
        with self.assertRaises(ContractError):
            execute(self.request('m-' + '4' * 32, 'Make it blue', first), root=self.root, output_root=self.out,
                    mailbox=self.mail, observer=lambda event: called.append(event))
        self.assertFalse(any(event.get('kind') == 'inference_requested' for event in called))

    def test_invalid_conversation_and_cross_run_parent_fail_closed(self):
        with self.assertRaises(ContractError):
            execute(self.request('m-' + '5' * 32, 'Build a calculator') | {'conversation_id': '../bad'},
                    root=self.root, output_root=self.out, mailbox=self.mail)
        with self.assertRaises(ContractError):
            verified_parent_bundle(self.out, 'm-' + 'f' * 32)


if __name__ == '__main__':
    unittest.main()
