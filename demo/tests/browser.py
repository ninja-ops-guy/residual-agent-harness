"""Real browser QA at root + GitHub Pages project paths; no backend required."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    checks = 0
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / 'root'
        shutil.copytree(args.site, root)
        shutil.copytree(args.site, root / 'residual-agent-harness')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                kwargs = {'headless': True}
                if os.environ.get('DEMO_CHROMIUM'):
                    kwargs['executable_path'] = os.environ['DEMO_CHROMIUM']
                browser = p.chromium.launch(**kwargs)
                for width, height in [(1440, 1060), (390, 844), (360, 800)]:
                    for prefix in ['/', '/residual-agent-harness/']:
                        context = browser.new_context(viewport={'width': width, 'height': height},
                            is_mobile=width < 500, has_touch=width < 500, reduced_motion='reduce', accept_downloads=True)
                        page = context.new_page()
                        errors, requests, bad_responses = [], [], []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.on('request', lambda request: requests.append(request.url))
                        page.on('response', lambda response: bad_responses.append(response.url) if response.status >= 400 else None)
                        page.goto(origin + prefix)
                        expect(page.locator('#run')).to_be_enabled()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'
                        checks += 1
                        for scenario, outcome in [('clean', 'ACCEPTED'), ('rejected', 'BLOCKED'), ('unknown', 'BLOCKED'), ('conflict', 'CONFLICT')]:
                            page.select_option('#scenario', scenario)
                            page.click('#run')
                            expect(page.locator('#run-state')).to_have_text(outcome)
                            expect(page.locator('#events li')).to_have_count(6)
                            if scenario == 'unknown':
                                expect(page.locator('.worker .badge').filter(has_text='UNKNOWN')).to_have_count(1)
                            if scenario == 'conflict':
                                expect(page.locator('#passed-count')).to_have_text('3 / 3')
                            with page.expect_download() as download:
                                page.click('#download')
                            payload = json.loads(Path(download.value.path()).read_text())
                            assert payload['simulation'] is True and payload['signed'] is False
                            assert payload['source_revision'] == page.locator('body').get_attribute('data-source-revision')
                            assert payload['integration']['status'] == outcome
                            assert payload['schema'] == 'residual.pages-simulation.v1'
                            if outcome != 'ACCEPTED':
                                assert payload['integration']['artifacts'] == []
                            checks += 1
                        if args.screenshots and prefix != '/':
                            page.select_option('#scenario', 'clean')
                            page.click('#run')
                            expect(page.locator('#run-state')).to_have_text('ACCEPTED')
                            page.screenshot(path=str(args.screenshots / f'demo-{width}.png'), full_page=True)
                        page.click('#reset')
                        expect(page.locator('#run-state')).to_have_text('READY')
                        expect(page.locator('#download')).to_be_disabled()
                        checks += 1
                        assert not errors, errors
                        assert not bad_responses, bad_responses
                        assert all(urlsplit(url).netloc == urlsplit(origin).netloc for url in requests), requests
                        assert all('/api/' not in url and 'localhost:8765' not in url for url in requests), requests
                        if prefix != '/':
                            assert all(urlsplit(url).path.startswith(prefix) for url in requests), requests
                        checks += 1
                        # Exercise cancellation while timers are pending, not just reduced-motion instant completion.
                        page.emulate_media(reduced_motion='no-preference')
                        page.select_option('#scenario', 'clean')
                        page.click('#run')
                        page.select_option('#scenario', 'unknown')
                        page.wait_for_timeout(1600)
                        expect(page.locator('#run-state')).to_have_text('READY')
                        expect(page.locator('#download')).to_be_disabled()
                        page.click('#run')
                        expect(page.locator('#run-state')).to_have_text('BLOCKED')
                        page.click('#run')
                        page.click('#reset')
                        page.wait_for_timeout(1600)
                        expect(page.locator('#run-state')).to_have_text('READY')
                        checks += 1
                        # Explicitly prove CSP denies a connection. This deliberate violation is expected.
                        denied = page.evaluate("async () => { try { await fetch('./backend-probe'); return false; } catch { return true; } }")
                        assert denied, 'connect-src none was not enforced'
                        checks += 1
                        context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    print(f'{checks} browser checks passed: desktop + 390px + 360px, root + project path; four scenarios each.')


if __name__ == '__main__':
    main()
