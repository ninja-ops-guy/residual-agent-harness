"""Generated-artifact workbench tests. Provider replies are explicit test doubles."""
import json
from pathlib import Path
import tempfile
import unittest

from residual.core import ContractError, canonical
from residual.workbench.build import (execute_build, make_build_task, safe_artifact_path,
                                      validate_bundle, MAX_BUILD_FILE_BYTES)


class BuildWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root / 'residual').mkdir()
        (self.root / 'README.md').write_text('Reference source.\n')
        self.out = self.root / 'runs'; self.mail = self.root / 'mail'; self.mail.mkdir()
        self.req = {'id': 'm-' + 'd' * 32, 'mode': 'build', 'prompt': 'Build a calculator',
                    'files': [], 'model': 'gpt-5-nano', 'max_calls': 2,
                    'max_output_tokens': 1536, 'cloud_consent': True,
                    'required_text': ['Calculator']}

    def reply_observer(self, value):
        def observer(event):
            if event['kind'] != 'inference_requested': return
            req = event['data']
            reply = {'request_id': req['request_id'], 'ok': True,
                     'text': canonical({'updates': {'build': value}, 'requests': []})}
            (self.mail / f"{event['mission_id']}-{req['request_id']}.json").write_text(canonical(reply))
        return observer

    def test_build_without_reference_sources_writes_only_artifact_directory(self):
        value = {'summary': 'Calculator deliverable.', 'files': [
            {'path': 'index.html', 'content': '<h1>Calculator</h1>'},
            {'path': 'app.js', 'content': 'const add=(a,b)=>a+b;'}]}
        result = execute_build(self.req, root=self.root, output_root=self.out, mailbox=self.mail,
                               observer=self.reply_observer(value))
        folder = Path(result['output'])
        self.assertTrue(result['result']['success']); self.assertTrue(result['verification']['result_bound'])
        self.assertEqual(result['semantic_verification'], 'UNKNOWN')
        self.assertEqual((folder / 'artifacts/index.html').read_text(), '<h1>Calculator</h1>')
        manifest = json.loads((folder / 'artifacts/manifest.json').read_text())
        self.assertFalse(manifest['executed']); self.assertEqual(len(manifest['files']), 2)
        self.assertFalse((self.root / 'index.html').exists())

    def test_build_instruction_requires_directly_previewable_static_browser_bundle(self):
        task, _, _, _ = make_build_task(self.req, self.root)
        instruction = task.obligations[0].description
        self.assertIn('directly previewable static bundle', instruction)
        self.assertIn('index.html', instruction)
        self.assertIn('do not require npm, a build step, a dev server, CDN assets, or remote network access', instruction)

    def test_generated_code_is_never_executed(self):
        value = {'summary': 'Calculator', 'files': [
            {'path': 'app.py', 'content': "from pathlib import Path\nPath('OWNED').write_text('bad')\n# Calculator"}]}
        result = execute_build(self.req, root=self.root, output_root=self.out, mailbox=self.mail,
                               observer=self.reply_observer(value))
        self.assertTrue(result['result']['success']); self.assertFalse((self.root / 'OWNED').exists())

    def test_optional_reference_sources_are_frozen(self):
        request = {**self.req, 'files': ['README.md'], 'id': 'm-' + 'e' * 32}
        value = {'summary': 'Calculator', 'files': [{'path': 'README.txt', 'content': 'Calculator'}]}
        result = execute_build(request, root=self.root, output_root=self.out, mailbox=self.mail,
                               observer=self.reply_observer(value))
        self.assertEqual(result['task']['artifacts'][0]['text'], 'Reference source.\n')

    def test_bundle_contract_rejects_unsafe_paths_and_duplicates(self):
        base = {'summary': 'Calculator', 'files': [{'path': 'index.html', 'content': 'Calculator'}]}
        self.assertIsNone(validate_bundle(base, ['Calculator']))
        bad = ['../x', '/etc/passwd', '.hidden', 'dir/.hidden', 'a\\b', 'a//b']
        for path in bad:
            with self.subTest(path=path):
                value = {'summary': 'Calculator', 'files': [{'path': path, 'content': 'x'}]}
                self.assertEqual(validate_bundle(value), 'build_file_path')
                with self.assertRaises(ContractError): safe_artifact_path(path)
        duplicate = {'summary': 'Calculator', 'files': [
            {'path': 'a.txt', 'content': 'a'}, {'path': 'a.txt', 'content': 'b'}]}
        self.assertEqual(validate_bundle(duplicate), 'build_duplicate_path')

    def test_bundle_contract_limits_files_bytes_and_required_text(self):
        self.assertEqual(validate_bundle({'summary': 'x', 'files': []}), 'build_file_count')
        self.assertEqual(validate_bundle({'summary': 'x', 'files': [
            {'path': 'a.txt', 'content': 'x' * (MAX_BUILD_FILE_BYTES + 1)}]}), 'build_file_size')
        self.assertEqual(validate_bundle({'summary': 'x', 'files': [
            {'path': 'a.txt', 'content': 'y'}]}, ['Calculator']), 'required_text_missing')

    def test_invalid_bundle_fails_closed_and_writes_no_generated_files(self):
        value = {'summary': 'Calculator', 'files': [{'path': '../escape', 'content': 'Calculator'}]}
        result = execute_build({**self.req, 'max_calls': 1}, root=self.root, output_root=self.out, mailbox=self.mail,
                               observer=self.reply_observer(value))
        self.assertFalse(result['result']['success']); self.assertNotIn('build', result['result']['values'])
        self.assertFalse((Path(result['output']) / 'artifacts').exists())

    def test_build_task_rejects_unknown_fields_and_requires_consent_at_execution(self):
        with self.assertRaises(ContractError): make_build_task({**self.req, 'extra': 1}, self.root)
        with self.assertRaises(ContractError):
            execute_build({**self.req, 'cloud_consent': False}, root=self.root, output_root=self.out, mailbox=self.mail)


if __name__ == '__main__':
    unittest.main()
