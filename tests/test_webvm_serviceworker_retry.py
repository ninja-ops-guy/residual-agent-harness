from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from demo.vm.harden_serviceworker import harden


PATCHED_UPSTREAM = '''async function handleFetch(request) {
\t// Perform the original fetch request and store the result in order to modify the response.
\ttry {
\t\tvar r = await fetch(request);
\t}
\tcatch (e) {
\t\tconsole.warn("Serviceworker fetch failed:", request.url, e);
\t\treturn Response.error();
\t}
\tif (r.status === 0) {
\t\treturn r;
\t}
\treturn r;
}
'''


class ServiceWorkerRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'serviceWorker.js'

    def test_injects_retry_before_handle_fetch_and_replaces_only_fetch_anchor(self):
        self.path.write_text(PATCHED_UPSTREAM, encoding='utf-8')
        harden(self.path)
        text = self.path.read_text(encoding='utf-8')
        self.assertIn('function residualIsImmutableDiskChunk(request)', text)
        self.assertIn('async function residualFetchWithRetry(request)', text)
        self.assertIn('/residual-demo-[0-9a-f]{64}\\.ext2\\.c[0-9a-f]+\\.txt$', text)
        self.assertIn('var r = await residualFetchWithRetry(request);', text)
        self.assertNotIn('var r = await fetch(request);', text)
        self.assertIn('return Response.error();', text)
        self.assertLess(text.index('function residualIsImmutableDiskChunk'), text.index('async function handleFetch'))

    def test_duplicate_hardening_fails_closed(self):
        self.path.write_text(PATCHED_UPSTREAM, encoding='utf-8')
        harden(self.path)
        with self.assertRaises(SystemExit):
            harden(self.path)

    def test_moved_upstream_fetch_anchor_fails_closed(self):
        self.path.write_text(PATCHED_UPSTREAM.replace('var r = await fetch(request);', 'var r = await fetch(request.url);'), encoding='utf-8')
        with self.assertRaises(SystemExit):
            harden(self.path)


if __name__ == '__main__':
    unittest.main()
