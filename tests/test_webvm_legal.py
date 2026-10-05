"""Bounded legal-publication tests; fake owner facts are NEVER production approval."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publish_legal', ROOT / 'demo/vm/publish_legal.py')
legal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legal)
# Synthetic fixtures only. No claim that this mailbox or business exists.
APPROVED_FIXTURE = dict(schema_version=1, operator_name='Fixture operator',
    privacy_email='privacy@residual-fixture.org', effective_date='2026-10-04',
    runtime_disclosure='Synthetic runtime inventory for isolated testing only.',
    international_processing='Synthetic transfer notice for isolated testing only.',
    owner_review_complete=True)
COMMIT = 'a' * 40


def fixture(site: Path) -> None:
    for route in legal.ROUTES:
        path = site / route; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fixture</title></head><body><main>Fixture only</main></body></html>')
    (site / 'provider/index.html').write_text((ROOT / 'demo/vm/provider.html').read_text())
    (site / 'walkthrough/persist.js').write_text((ROOT / 'site/walkthrough-persist.js').read_text())
    (site / 'provider/provider.js').write_text("""
let channel, sdk, grant = null, busy = false, modelCatalog = null, sdkLoadPromise = null, loadGeneration = 0;
const send = value => { window.fixtureLastState = value; };
window.fixtureSdkLoads = 0;
function loadSdk(restoring = false) {
  window.fixtureSdkLoads++;
  return Promise.resolve();
}
const load = document.getElementById('load');
load.disabled = false;
load.addEventListener('click', () => loadSdk().catch(() => {}));
""")


class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links = []; self.ids = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if 'id' in values: self.ids.append(values['id'])
        if tag in ('a', 'link', 'script'): self.links.append(values.get('href') or values.get('src') or '')


class LegalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.site = Path(self.tmp.name)
        fixture(self.site)
    def tearDown(self): self.tmp.cleanup()
    def publish(self, config=None):
        return legal.publish_legal(self.site, commit=COMMIT, config=config or APPROVED_FIXTURE)
    def test_unreviewed_checked_in_config_blocks_before_writes(self):
        before = (self.site / 'index.html').read_bytes()
        with self.assertRaisesRegex(ValueError, 'LEGAL_PUBLICATION_HOLD'):
            legal.publish_legal(self.site, commit=COMMIT)
        self.assertEqual(before, (self.site / 'index.html').read_bytes())
        self.assertFalse((self.site / 'legal').exists())
    def test_missing_owner_fields_and_placeholder_emails_block(self):
        for key in ('privacy_email', 'runtime_disclosure', 'international_processing', 'effective_date'):
            cfg = copy.deepcopy(APPROVED_FIXTURE); cfg[key] = None
            with self.subTest(key=key), self.assertRaises(ValueError): self.publish(cfg)
        for email in ('privacy@example.org', 'privacy@x.invalid', 'bad', 'x@y.test'):
            cfg = dict(APPROVED_FIXTURE, privacy_email=email)
            with self.subTest(email=email), self.assertRaises(ValueError): self.publish(cfg)
    def test_escaping_owner_values(self):
        self.publish(dict(APPROVED_FIXTURE, operator_name='<script>bad</script>'))
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;', (self.site/'legal/privacy.html').read_text())
        self.assertNotIn('<script>bad', (self.site/'legal/privacy.html').read_text())
    def test_exact_commit_required(self):
        with self.assertRaises(ValueError): legal.publish_legal(self.site, commit='main', config=APPROVED_FIXTURE)
    def test_publication_idempotent(self):
        first = self.publish(); second = self.publish()
        self.assertEqual(first, second)
        for route in legal.ROUTES:
            self.assertEqual(1, (self.site/route).read_text().count(legal.BEGIN))
    def test_all_active_routes_have_visible_static_links(self):
        self.publish()
        for route in legal.ROUTES:
            text = (self.site/route).read_text()
            self.assertIn('<footer', text)
            for name in legal.PAGES: self.assertIn(name, text)
    def test_legal_assets_and_fragment_targets_exist_under_project_path(self):
        self.publish()
        for file in (self.site/'legal').glob('*.html'):
            parser = Links(); parser.feed(file.read_text())
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            for link in parser.links:
                if not link or link.startswith(('https:', 'mailto:')): continue
                target, _, fragment = link.partition('#')
                path = (file.parent / target).resolve() if target else file
                if path.is_dir(): path = path/'index.html'
                self.assertTrue(path.is_file(), (file, link))
                if fragment:
                    destination = Links(); destination.feed(path.read_text())
                    self.assertIn(fragment, destination.ids)
    def test_provider_guard_before_any_sdk_load(self):
        self.publish(); js = (self.site/'provider/provider.js').read_text()
        self.assertLess(js.index('if (!providerPrivacy.allowLoad())'), js.index('window.fixtureSdkLoads++;'))
        self.assertIn("import {installProviderPrivacy}", js)
    def test_changed_provider_anchor_fails_without_partial_publication(self):
        (self.site/'provider/provider.js').write_text('changed upstream')
        with self.assertRaises(ValueError): self.publish()
        self.assertFalse((self.site/'legal').exists())
        self.assertNotIn(legal.BEGIN, (self.site/'index.html').read_text())
    def test_provider_referrer_origin_and_disclosed_load_action_preserved(self):
        self.publish(); text=(self.site/'provider/index.html').read_text()
        self.assertIn('name="referrer" content="origin"',text)
        self.assertIn('aria-describedby="provider-privacy-choice"',text)
        self.assertNotIn('checked',text)
    def test_hashed_artifact_includes_final_pages_scripts_and_persistence(self):
        manifest=self.publish()
        self.assertEqual(COMMIT,manifest['source_commit'])
        self.assertIn('walkthrough/persist.js',manifest['sha256'])
        for path,digest in manifest['sha256'].items():
            self.assertEqual(hashlib.sha256((self.site/path).read_bytes()).hexdigest(),digest)
    def test_existing_identity_records_after_publication(self):
        text=(ROOT/'demo/vm/pages_contract.py').read_text()
        self.assertLess(text.index('publish_legal(args.demo_dir.parent'),text.index('identity = {'))
    def test_new_legal_pages_no_external_subresources(self):
        self.publish()
        for file in (self.site/'legal').glob('*.html'):
            text=file.read_text()
            self.assertNotRegex(text,r'<(?:script|iframe|img)[^>]+src="https?://')
            self.assertNotIn('{{',text)

if __name__ == '__main__': unittest.main()
