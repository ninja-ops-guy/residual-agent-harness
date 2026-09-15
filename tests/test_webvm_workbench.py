"""Real Harness tests; the mailbox's remote SDK responses are explicit test doubles."""
import dataclasses
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from residual.core import ContractError, Context, canonical
from residual.workbench.runner import (execute, make_task, source_snapshot, verify_run,
                                       check_answer, WorkbenchDeadline, ObservedHarness)


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / 'residual').mkdir()
        (self.root / 'README.md').write_text('Evidence matters.\nRead the source.\n')
        (self.root / 'residual/code.py').write_text('def first():\n    return 1\n# TODO add tests\n')
        self.out = self.root / 'runs'; self.mail = self.root / 'mail'; self.mail.mkdir()
        self.req = {'id': 'm-' + 'a' * 32, 'prompt': 'Explain this source', 'files': ['README.md'], 'mode': 'audit'}

    def execute(self, request=None, observer=None):
        return execute(request or self.req, root=self.root, output_root=self.out, mailbox=self.mail, observer=observer)

    def test_audit_uses_real_source_and_harness(self):
        events = []; result = self.execute(observer=events.append)
        self.assertTrue(result['verification']['result_bound']); self.assertFalse(result['simulation'])
        self.assertEqual(result['result']['metrics']['calls'], 0)
        self.assertEqual(result['result']['metrics']['deterministic_accepts'], 1)
        self.assertEqual(result['result']['values']['inventory']['files'][0]['lines'], 2)
        projected = [e['data'] for e in events if e['kind'] == 'evidence']
        retained = [json.loads(s) for s in (Path(result['output']) / 'trace.jsonl').read_text().splitlines()]
        self.assertEqual(projected, retained)

    def test_source_changes_change_actual_audit(self):
        first = self.execute(); (self.root / 'README.md').write_text('Changed\nTODO now\n')
        second = self.execute({**self.req, 'id': 'm-' + 'b' * 32})
        self.assertNotEqual(first['result']['values'], second['result']['values'])
        self.assertEqual(second['result']['values']['inventory']['files'][0]['todo_lines'], [2])

    def test_python_audit_parses_symbols(self):
        result = self.execute({**self.req, 'files': ['residual/code.py']})
        item = result['result']['values']['inventory']['files'][0]
        self.assertEqual(item['syntax'], 'PASS'); self.assertEqual(item['symbols'], ['first'])

    def test_bad_python_recorded_not_executed(self):
        (self.root / 'residual/code.py').write_text('def invalid(:\n')
        result = self.execute({**self.req, 'files': ['residual/code.py']})
        self.assertEqual(result['result']['values']['inventory']['files'][0]['syntax'], 'FAIL')

    def test_source_scope(self):
        for name in ['../README.md', '/etc/passwd', '.env', 'residual/../README.md', 'residual/.hidden', 'unknown', 'residual\\code.py']:
            with self.subTest(name=name), self.assertRaises((ContractError, OSError)):
                source_snapshot(self.root, [name])

    def test_source_symlink_rejected(self):
        (self.root / 'residual/link.py').symlink_to(self.root / 'README.md')
        with self.assertRaises(ContractError): source_snapshot(self.root, ['residual/link.py'])

    def test_source_size_and_binary_rejected(self):
        for raw in [b'x' * 24001, b'\x00bad']:
            (self.root / 'README.md').write_bytes(raw)
            with self.assertRaises(ContractError): source_snapshot(self.root, ['README.md'])

    def test_duplicate_and_empty_sources_rejected(self):
        for names in [[], ['README.md'] * 2]:
            with self.assertRaises(ContractError): source_snapshot(self.root, names)

    def test_prompt_is_data_not_code(self):
        result = self.execute({**self.req, 'prompt': '$(touch OWNED); `bad`\n<script>alert(1)</script>'})
        self.assertFalse((self.root / 'OWNED').exists())
        self.assertIn('$(touch', result['task']['goal'])

    def test_request_shape_and_budget(self):
        changes = [{'prompt': ''}, {'prompt': 'x' * 4001}, {'max_calls': 4}, {'max_calls': True},
                   {'max_output_tokens': 2000}, {'model': 'x";bad'}, {'mode': 'fake'},
                   {'id': '../escape'}, {'cloud_consent': 'yes'}, {'required_text': [True]}, {'unknown': 1}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ContractError): make_task({**self.req, **change}, self.root)

    def test_parallel_lock_not_removed(self):
        self.out.mkdir(); lock = self.out / '.active'; lock.write_text('other run')
        with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(lock.read_text(), 'other run')

    def test_duplicate_run_never_overwrites(self):
        self.execute(); before = (self.out / self.req['id'] / 'trace.jsonl').read_bytes()
        with self.assertRaises(FileExistsError): self.execute()
        self.assertEqual(before, (self.out / self.req['id'] / 'trace.jsonl').read_bytes())

    def test_live_requires_consent_no_fallback(self):
        with self.assertRaises(ContractError): self.execute({**self.req, 'mode': 'live'})
        self.assertFalse((self.out / self.req['id'] / 'result.json').exists())

    def test_demo_config_rejected(self):
        with self.assertRaises(ContractError):
            execute({**self.req, 'mode': 'live'}, root=self.root, output_root=self.out, config={'local': {'kind': 'demo'}})

    def live(self, fail_first=False, mutate=False):
        events = []; calls = []
        def observer(event):
            events.append(event)
            if event['kind'] != 'inference_requested': return
            req = event['data']; calls.append(req)
            value = {'text': 'Review checklist: inspect the evidence.', 'citations': [
                {'artifact_id': 'source-0', 'start_line': 1, 'end_line': 1, 'quote': 'Evidence matters.'}]}
            if fail_first and len(calls) == 1: value['citations'][0]['quote'] = 'Invented'
            if mutate: (self.root / 'README.md').write_text('tampered after snapshot')
            reply = {'request_id': req['request_id'], 'ok': True, 'text': canonical({'updates': {'answer': value}, 'requests': []})}
            (self.mail / f"{event['mission_id']}-{req['request_id']}.json").write_text(canonical(reply))
        result = self.execute({**self.req, 'mode': 'live', 'cloud_consent': True, 'required_text': ['Review checklist']}, observer)
        return result, calls, events

    def test_live_harness_mailbox_contract_test_double(self):
        result, calls, _ = self.live()
        self.assertTrue(result['result']['success']); self.assertEqual(len(calls), 1)
        self.assertEqual(result['semantic_verification'], 'UNKNOWN')
        self.assertIsNone(result['result']['metrics']['remote_cost_usd'])
        self.assertIn('Review checklist', (Path(result['output']) / 'answer.md').read_text())

    def test_real_harness_rejects_and_retries_test_double(self):
        result, calls, _ = self.live(fail_first=True)
        self.assertTrue(result['result']['success']); self.assertEqual(len(calls), 2)
        self.assertEqual(result['result']['metrics']['candidate_rejections'], 1)
        packet = json.loads(calls[1]['messages'][-1]['content'])
        self.assertTrue(packet['counterexamples'])

    def test_answer_is_bound_to_frozen_sources(self):
        result, _, _ = self.live(mutate=True)
        self.assertEqual(result['task']['artifacts'][0]['text'], 'Evidence matters.\nRead the source.\n')
        self.assertTrue(result['verification']['result_bound'])

    def test_result_tampering_detected(self):
        result = self.execute(); folder = Path(result['output']); path = folder / 'result.json'
        raw = json.loads(path.read_text()); raw['success'] = False; path.write_text(canonical(raw))
        with self.assertRaises(ContractError): verify_run(folder)

    def test_trace_tampering_detected(self):
        result = self.execute(); folder = Path(result['output']); path = folder / 'trace.jsonl'
        path.write_text(path.read_text().replace('run_started', 'bad_started'))
        with self.assertRaises(ContractError): verify_run(folder)

    def test_cancelled_mission_never_calls_provider(self):
        (self.mail / f"{self.req['id']}-cancel.json").write_text('{}')
        events = []; result = self.execute({**self.req, 'mode': 'live', 'cloud_consent': True}, events.append)
        self.assertFalse(result['result']['success'])
        self.assertFalse(any(e['kind'] == 'inference_requested' for e in events))

    def test_answer_check_unknown_not_conflated_with_pass(self):
        task, *_ = make_task({**self.req, 'mode': 'live'}, self.root)
        ctx = Context(task.obligations[0], task.artifacts, {})
        for value in [{}, {'text': 'answer', 'citations': []}, {'text': '', 'citations': []}]:
            self.assertEqual(check_answer(value, ctx).status, 'fail')

    def test_deadline_escapes_generic_provider_exception_handling(self):
        self.assertFalse(issubclass(WorkbenchDeadline, Exception))


if __name__ == '__main__': unittest.main()
