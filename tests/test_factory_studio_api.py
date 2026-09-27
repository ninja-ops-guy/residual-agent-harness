import json, tempfile, threading, urllib.request, unittest
from pathlib import Path
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.studio_api import StudioProjection, StudioHandler, ReadOnlyControl

class StudioAPITests(unittest.TestCase):
    def test_empty_snapshot_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            j=RuntimeJournal(Path(td)/"journal.sqlite",trace_id="studio-test")
            s=StudioProjection(j,model="test-model").snapshot()
            self.assertEqual(s["runId"],"studio-test");self.assertEqual(s["accepted"],0);self.assertEqual(s["workers"],[]);self.assertEqual(s["model"],"test-model")
    def test_read_only_control_fails_closed(self):
        with self.assertRaises(PermissionError): ReadOnlyControl().control("run",{"action":"run"})

if __name__=="__main__": unittest.main()
