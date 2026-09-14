from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT/'benchmarks'/'factory'/'fb004'/'common.py'
spec=importlib.util.spec_from_file_location('fb004_common',COMMON)
fb=importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)

class FB004Tests(unittest.TestCase):
    def test_fixture_commits_are_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            inp,out=fb.create_fixture(Path(td)/'repo',known_good=True)
            self.assertEqual(inp,fb.INPUT_COMMIT); self.assertEqual(out,fb.EXPECTED_OUTPUT_COMMIT)
    def test_project_has_four_streams_and_sixteen_tasks(self):
        self.assertEqual(len(fb.REFERENCE),16); self.assertEqual(set(fb.SWARMS),{'architecture','backend','service','docs'})
        self.assertEqual(set().union(*(set(v) for v in fb.SWARMS.values())),set(fb.REFERENCE))
    def test_cross_stream_dependencies_exist(self):
        self.assertIn('scheduler',fb.DEPENDENCIES['api']); self.assertIn('api',fb.DEPENDENCIES['cli']); self.assertIn('health',fb.DEPENDENCIES['docs_readme'])
    def test_unsafe_candidate_is_rejected(self):
        self.assertFalse(fb.verify_candidate('ids','import os\ndef job_id(owner,payload):\n    return os.getcwd()\n'))
    def test_canonical_project_completion(self):
        accepted={task:source for task,(_path,source) in fb.REFERENCE.items()}
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo'; fb.create_fixture(repo)
            commit,passed,total=fb.finalize(repo,accepted)
            self.assertEqual(commit,fb.EXPECTED_OUTPUT_COMMIT); self.assertEqual(passed,total); self.assertEqual(total,4)

if __name__=='__main__': unittest.main()
