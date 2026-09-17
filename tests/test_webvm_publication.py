"""Fast publication-contract tests; no claims about VM execution."""
from pathlib import Path
import unittest
from demo.vm.pages_contract import validate_entry_html, validate_pages_config


VALID = '<html><head></head><body><script>import("./_app/immutable/entry/start.js")</script></body></html>'


class WebVMPublicationTests(unittest.TestCase):
    def test_workflow_source_allowed(self):
        validate_pages_config({"build_type": "workflow"})

    def test_legacy_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "GitHub Actions"):
            validate_pages_config({"build_type": "legacy", "source": {"branch": "main", "path": "/"}})

    def test_unknown_source_rejected(self):
        for value in ({}, {"build_type": None}, {"build_type": "future"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_pages_config(value)

    def test_generated_entry_allowed(self):
        validate_entry_html(VALID)

    def test_self_redirect_rejected(self):
        for fragment in ('<meta http-equiv="refresh" content="0;url=../demo/">', '<script>location.replace("../demo/")</script>', '<script>location.assign("./")</script>'):
            with self.subTest(fragment=fragment), self.assertRaisesRegex(ValueError, "redirect"):
                validate_entry_html(VALID.replace("<head>", "<head>" + fragment))

    def test_case_insensitive_meta_refresh_rejected(self):
        with self.assertRaisesRegex(ValueError, "redirect"):
            validate_entry_html(VALID + '<META HTTP-EQUIV="REFRESH" CONTENT="0;url=./">')

    def test_optional_boot_dependencies_rejected(self):
        for url in ('https://js.puter.com/v2/', 'https://plausible.leaningtech.com/js/script.js'):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "eagerly"):
                validate_entry_html(VALID + f'<script defer src="{url}"></script>')

    def test_plain_html_is_not_vm(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_entry_html('<html><body>VM READY</body></html>')

    def test_repository_fallback_does_not_loop(self):
        html = (Path(__file__).resolve().parents[1] / "demo/index.html").read_text()
        self.assertNotIn('http-equiv="refresh"', html.lower())
        self.assertNotIn("location.replace", html)
        self.assertIn("GitHub Actions", html)

    def test_provider_helper_bypasses_cross_origin_isolation_headers(self):
        worker = (Path(__file__).resolve().parents[1] / "site/coi-serviceworker.js").read_text()
        provider_scope = 'new URL("provider/", self.registration.scope).pathname'
        bypass = 'requestUrl.origin === self.location.origin && requestUrl.pathname.startsWith(providerScopePath)'
        raw_fetch = 'event.respondWith(fetch(r));'
        coep_header = 'newHeaders.set("Cross-Origin-Embedder-Policy"'
        self.assertIn(provider_scope, worker)
        self.assertIn(bypass, worker)
        self.assertIn(raw_fetch, worker)
        self.assertLess(worker.index(bypass), worker.index(coep_header))


if __name__ == '__main__':
    unittest.main()