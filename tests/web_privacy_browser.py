#!/usr/bin/env python3
"""Real Chromium checks against synthetic Pages fixtures, not a real VM/provider.

Run: python tests/web_privacy_browser.py [--evidence-dir /tmp/legal-browser-proof]
Requires Playwright and Chromium; CHROMIUM_EXECUTABLE may identify a system browser.
"""
from __future__ import annotations
import argparse
import functools
import http.server
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_webvm_legal import ROOT, APPROVED_FIXTURE, COMMIT, fixture, legal


def run(evidence: Path | None = None) -> dict:
    checks: list[str] = []
    def check(name: str, condition: bool) -> None:
        if not condition: raise AssertionError(name)
        checks.append(name)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); site = root/'residual-agent-harness'; fixture(site)
        (site/'walkthrough/index.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Walkthrough fixture</title></head><body><main><h1>Walkthrough fixture</h1><button data-tab="walk">Walk</button><button data-tab="evidence">Evidence</button><button id="step">Step</button><button id="run">Run failure scenario</button><button id="reset">Reset</button></main><script src="./persist.js"></script></body></html>''')
        (site/'demo/index.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mission Control fixture</title></head><body><script>setTimeout(() => { const section=document.createElement('section');section.id='mission-control';section.style.cssText='position:fixed;inset:0;display:flex;flex-direction:column;background:#030603;color:#d8ffe0';section.innerHTML='<main style="flex:1;min-height:0"><h1>Mission Control fixture</h1></main>';document.body.append(section); }, 30);</script></body></html>''')
        legal.publish_legal(site, commit=COMMIT, config=APPROVED_FIXTURE)
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_address[1]}/residual-agent-harness'
        try:
            with sync_playwright() as pw:
                executable=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium')
                browser=pw.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
                context=browser.new_context(viewport={'width':1280,'height':900})
                page=context.new_page(); errors=[]; requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                context.on('request',lambda request:requests.append(request.url))
                page.goto(base+'/walkthrough/');page.wait_for_selector('#remember-walkthrough')
                key='residual.walkthrough.v1';consent='residual.walkthrough.consent.v1'
                check('remember is off by default',not page.locator('#remember-walkthrough').is_checked())
                page.locator('#step').click()
                check('no optional progress before opt-in',page.evaluate('(k)=>localStorage.getItem(k)',key) is None)
                page.locator('#remember-walkthrough').check();page.locator('#step').click()
                check('opt-in stores bounded progress',json.loads(page.evaluate('(k)=>localStorage.getItem(k)',key))['steps']==2)
                page.reload();page.wait_for_selector('#remember-walkthrough')
                check('explicit preference restores',page.locator('#remember-walkthrough').is_checked())
                page.locator('#remember-walkthrough').uncheck()
                check('withdraw deletes both owned keys',page.evaluate('(ks)=>ks.every(k=>localStorage.getItem(k)===null)',[key,consent]))
                page.evaluate('(k)=>localStorage.setItem(k,JSON.stringify({tab:"walk",steps:10,ran:false}))',key)
                page.reload();page.wait_for_selector('#remember-walkthrough')
                check('legacy progress without consent discarded',page.evaluate('(k)=>localStorage.getItem(k)',key) is None)
                page.locator('#remember-walkthrough').check()
                page.evaluate('(k)=>localStorage.setItem(k,JSON.stringify({version:1,expires:Date.now()-1}))',consent)
                page.reload();page.wait_for_selector('#remember-walkthrough')
                check('expired preference not restored',not page.locator('#remember-walkthrough').is_checked())
                page.locator('#remember-walkthrough').check()
                other=context.new_page();other.goto(base+'/legal/cookies.html')
                other.evaluate('localStorage.setItem("unrelated.project","keep")')
                other.locator('#forget-walkthrough').click()
                page.wait_for_function('!document.getElementById("remember-walkthrough").checked')
                page.locator('#step').click()
                check('withdrawal in another tab prevents rewrites',page.evaluate('(k)=>localStorage.getItem(k)',key) is None)
                check('unrelated origin storage preserved',other.evaluate('localStorage.getItem("unrelated.project")')=='keep')
                other.close()
                page.goto(base+'/provider/');page.wait_for_function('window.fixtureSdkLoads===0')
                page.evaluate('document.getElementById("load").click()')
                check('programmatic provider load blocked without user choice',page.evaluate('window.fixtureSdkLoads')==0)
                page.locator('#load').click()
                check('provider load permitted after choice',page.evaluate('window.fixtureSdkLoads')==1)
                page.locator('#provider-privacy-withdraw').click();page.wait_for_load_state()
                page.wait_for_function('window.fixtureSdkLoads===0')
                check('provider withdrawal reloads without SDK',page.evaluate('window.fixtureSdkLoads')==0)
                page.goto(base+'/legal/privacy.html')
                page.keyboard.press('Tab')
                check('keyboard skip link available',page.evaluate('document.activeElement.textContent')=='Skip to content')
                page.keyboard.press('Enter')
                check('skip link reaches main',page.evaluate('document.activeElement.id')=='main')
                for width in (1280,375,320):
                    page.set_viewport_size({'width':width,'height':812})
                    page.goto(base+'/legal/privacy.html')
                    check(f'privacy page fits {width}px viewport',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                if evidence:
                    evidence.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(evidence/'privacy-narrow.png'),full_page=True)
                page.set_viewport_size({'width':375,'height':812});page.goto(base+'/demo/')
                page.wait_for_selector('#mission-control > [data-residual-legal]')
                box=page.locator('[data-residual-legal]').bounding_box()
                check('legal links visible inside full-screen layout',bool(box and box['y']>=0 and box['y']+box['height']<=812))
                check('demo links preserve session with new tab',page.locator('[data-residual-legal] a').first.get_attribute('target')=='_blank')
                check('new pages and controls request only same-origin resources',all(url.startswith(base.rsplit('/residual-agent-harness',1)[0]) for url in requests))
                check('no page JavaScript errors in normal fixtures',not errors)
                blocked=browser.new_context()
                blocked.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
                limited=blocked.new_page();limited.goto(base+'/walkthrough/')
                limited.locator('#remember-walkthrough').check()
                check('storage failure leaves remembering off',not limited.locator('#remember-walkthrough').is_checked())
                check('storage failure explains in-memory fallback','Storage unavailable' in limited.locator('#remember-status').inner_text())
                limited.locator('#step').click();limited.locator('#run').click()
                blocked.close();context.close();browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    report={'scope':'synthetic browser fixtures; NOT real WebVM, provider login, legal approval or live deployment',
            'passed':len(checks),'checks':checks}
    if evidence:(evidence/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-dir',type=Path)
    args=parser.parse_args();print(json.dumps(run(args.evidence_dir),indent=2))
