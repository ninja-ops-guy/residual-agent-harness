#!/usr/bin/env python3
"""Offline browser regressions for the Pages host; does NOT verify the real VM.

Install: python -m pip install playwright==1.57.0
         python -m playwright install --with-deps chromium
Run: python scripts/check_live_demo_browser.py --html site/live-demo.html
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, default=Path('site/live-demo.html'))
    parser.add_argument('--evidence', type=Path, default=Path('artifacts/pages-browser'))
    args = parser.parse_args()
    html = args.html.read_text(encoding='utf-8')
    # Catch truncated HTML/scripts even when the HTML parser treats EOF as text.
    assert html.rstrip().endswith('</html>'), 'HTML is truncated: missing closing html tag'
    assert len(re.findall(r'<script\b', html)) == html.count('</script>'), 'Unclosed script'
    for script in re.findall(r'<script\b[^>]*>(.*?)</script>', html, re.S):
        subprocess.run(['node', '--check'], input=script, text=True, check=True)
    assert not re.search(r'<script(?![^>]*\b(?:defer|async)\b)[^>]*src=["\']https://', html), 'Remote parser-blocking script'
    args.evidence.mkdir(parents=True, exist_ok=True)
    results = ['HTML complete; inline JavaScript parses; remote SDK is nonblocking']
    base = 'http://localhost:18741'
    headers = {'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp'}
    with sync_playwright() as pw:
        launch_options = {'headless': True}
        if executable := os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
            launch_options['executable_path'] = executable
        browser = pw.chromium.launch(**launch_options)
        try:
            def open_page(mobile=False):
                context = browser.new_context(viewport={'width': 390 if mobile else 1365, 'height': 844 if mobile else 900}, is_mobile=mobile, has_touch=mobile)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.clock.install()
                def route_request(route):
                    url = route.request.url
                    if url.startswith(base + '/demo/'):
                        route.fulfill(status=200, content_type='text/html', headers=headers, body=html)
                    elif url.startswith(base + '/vm/'):
                        route.fulfill(status=200, content_type='text/html', headers=headers, body='<!doctype html><body style="background:black;color:#39ff68"><p>MOCK FRAME: no real Linux guest</p><textarea class="xterm-helper-textarea"></textarea></body>')
                    elif url.startswith('https://js.puter.com/'):
                        # Deliberately leave the optional SDK request pending.
                        # A synchronous script would prevent even h1 from parsing.
                        return
                    else:
                        route.abort()
                page.route('**/*', route_request)
                page.goto(base + '/demo/', wait_until='commit')
                expect(page.locator('h1')).to_be_visible()
                page.wait_for_function("document.querySelector('#vm').contentDocument?.querySelector('textarea')")
                return context, page, errors

            def vm_message(page, message):
                frame = next(frame for frame in page.frames if '/vm/' in frame.url)
                frame.evaluate('(data) => parent.postMessage(data, location.origin)', message)
                page.wait_for_timeout(50)

            def overlay_shown(page):
                expect(page.locator('#loading')).not_to_have_class(re.compile(r'\bhidden\b'))
                expect(page.locator('#status')).not_to_contain_text('READY')

            context, page, errors = open_page()
            page.clock.fast_forward(1000)
            overlay_shown(page)
            assert not errors, errors
            results.append('Stalled SDK does not block rendering; iframe load does not mark guest ready')
            vm_message(page, {'type':'residual-vm-state', 'state':'runtime-loading', 'isolated':True, 'sab':True})
            vm_message(page, {'type':'residual-vm-state', 'state':'console-attached'})
            vm_message(page, {'type':'residual-vm-state', 'state':'guest-starting'})
            overlay_shown(page)
            results.append('Runtime loading, console attach, and guest-starting remain unconfirmed')
            page.evaluate("setCloudReady({username:'<img src=x onerror=alert(1)>'})")
            overlay_shown(page)
            expect(page.locator('#cloudBadge img')).to_have_count(0)
            results.append('Cloud auth cannot mark VM ready; account label is text, not HTML')
            page.evaluate("dispatchEvent(new MessageEvent('message',{source:window,origin:location.origin,data:{type:'residual-vm-output',data:'forged'}}))")
            page.evaluate("dispatchEvent(new MessageEvent('message',{source:document.querySelector('#vm').contentWindow,origin:'https://untrusted.invalid',data:{type:'residual-vm-output',data:'forged'}}))")
            vm_message(page, {'type':'residual-vm-output', 'data':''})
            vm_message(page, {'type':'residual-vm-output', 'data':123})
            overlay_shown(page)
            results.append('Wrong source/origin and empty/non-text output cannot mark VM ready')
            vm_message(page, {'type':'residual-vm-output', 'data':'RESIDUAL BOOT: guest process attached\n'})
            expect(page.locator('#loading')).to_have_class(re.compile(r'\bhidden\b'))
            expect(page.locator('#status')).to_have_text('VM READY · GUEST ATTACHED')
            results.append('Guest-output event, not navigation, marks guest attached (mock contract test)')
            # Verify the existing inference bridge still responds and clamps tokens.
            page.evaluate("window.puter={ai:{chat:async (messages,options)=>{window.capturedOptions=options;return {message:{content:'test response'},usage:{prompt_tokens:7,completion_tokens:3}}}}}")
            frame = next(frame for frame in page.frames if '/vm/' in frame.url)
            frame.evaluate("window.responses=[];addEventListener('message',e=>window.responses.push(e.data))")
            import base64
            request = base64.urlsafe_b64encode(json.dumps({'messages':[{'role':'user','content':'offline mock test'}],'max_output_tokens':9999}).encode()).decode().rstrip('=')
            vm_message(page, {'type':'residual-vm-output','data':f'__RESIDUAL_BROWSER_REQUEST__:ab12:{request}\n'})
            page.wait_for_function('window.capturedOptions?.max_tokens === 512')
            frame.wait_for_function('window.responses.length === 1')
            response = frame.evaluate('window.responses[0]')
            encoded = response['data'].strip().split(':')[-1]
            payload = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
            assert payload['ok'] is True and payload['text'] == 'test response', payload
            assert payload['usage'] == {'input_tokens':7,'output_tokens':3}, payload
            results.append('Mock cloud bridge round-trip preserves response, usage, and output-token cap')
            page.locator('#reset').click()
            page.wait_for_function("document.querySelector('#vm').contentDocument?.querySelector('textarea')")
            overlay_shown(page)
            page.clock.fast_forward(31000)
            overlay_shown(page)
            expect(page.locator('#status')).to_have_text('VM STARTUP UNCONFIRMED')
            expect(page.locator('#loading a')).to_be_visible()
            results.append('Reset rearms watchdog; timeout stays unconfirmed with visible recovery')
            vm_message(page, {'type':'residual-vm-state', 'state':'runtime-error', 'error':'WebAssembly module could not load'})
            page.clock.fast_forward(40000)
            overlay_shown(page)
            expect(page.locator('#bootDetail')).to_contain_text('WebAssembly module could not load')
            results.append('Runtime error stays visible; no later timer hides or overwrites it')
            assert not errors, errors
            page.screenshot(path=str(args.evidence / 'desktop-error.png'), full_page=True)
            context.close()
            context, page, errors = open_page(mobile=True)
            expect(page.locator('#typeBtn')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
            vm_message(page, {'type':'residual-vm-state', 'state':'runtime-loading', 'isolated':False, 'sab':False})
            overlay_shown(page)
            expect(page.locator('#bootDetail')).to_contain_text('cross-origin isolation')
            page.screenshot(path=str(args.evidence / 'mobile-blocked.png'), full_page=True)
            assert not errors, errors
            results.append('390px touch viewport renders; missing isolation shows actionable error')
            context.close()
        finally:
            browser.close()
    report = {'passed':len(results), 'scope':'Chromium host UI with mocked VM and SDK; NOT live WebVM, Safari, or cloud inference validation', 'checks':results}
    (args.evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
