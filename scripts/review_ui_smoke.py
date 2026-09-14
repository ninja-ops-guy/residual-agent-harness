"""Browser smoke against a real local JWT-authenticated review server (fixture issuer)."""
import asyncio
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time

from aiohttp import web
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from playwright.async_api import async_playwright

from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
from residual.hitl.auth import OIDCAuthenticator
from residual.hitl.gateway import HITLEscalationGateway
from residual.hitl.server import create_app


async def main():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk={**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), 'kid':'browser-fixture', 'alg':'RS256'}
    issuer='https://identity.example.test/review'
    auth=OIDCAuthenticator(issuer=issuer,audience='residual-review',jwks={'keys':[jwk]})
    token=jwt.encode({'iss':issuer,'aud':'residual-review','sub':'test-operator','roles':['operator'],
        'scope':'residual:review','iat':int(time.time())-1,'exp':int(time.time())+180},key,algorithm='RS256',headers={'kid':'browser-fixture'})
    output=Path(os.environ.get('RESIDUAL_UI_EVIDENCE','evidence/review-ui')); output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        gateway=HITLEscalationGateway(b'f'*32,td,authenticate=auth)
        goal=GoalSpec('review','Review an isolated synthetic action',
            (SuccessCriterion('one',CheckType.MECHANICAL,'Check','host'),),1,100,30,AmendmentRule(('operator',)))
        challenge=gateway.generate_challenge('fixture-change',{'intent':'Restart the demo service',
            'untrusted':'<img src=x onerror="window.injected=true">'},'Operator approval required',goal)
        sock=socket.socket(); sock.bind(('127.0.0.1',0)); origin=f'http://127.0.0.1:{sock.getsockname()[1]}'
        runner=web.AppRunner(create_app(gateway,auth,origin=origin),access_log=None); await runner.setup()
        await web.SockSite(runner,sock).start()
        try:
            async with async_playwright() as playwright:
                browser=await playwright.chromium.launch(headless=True,
                    executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None,args=['--no-sandbox'])
                try:
                    page=await browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
                    errors=[]; page.on('pageerror',lambda error:errors.append(type(error).__name__))
                    await page.goto(origin); await page.locator('#credential').fill(token)
                    await page.get_by_role('button',name='Load challenges').click()
                    await page.get_by_role('button',name='Approve exact action').wait_for()
                    assert await page.locator('article img').count()==0
                    assert await page.evaluate('window.injected !== true')
                    assert await page.evaluate('Object.keys(localStorage).length===0 && Object.keys(sessionStorage).length===0')
                    assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    # Never put even fixture bearer credentials in screenshots or exported DOM.
                    await page.locator('#credential').fill('')
                    await page.screenshot(path=str(output/'review-mobile.png'),full_page=True)
                    await page.locator('#credential').fill(token)
                    page.on('dialog',lambda dialog:dialog.accept())
                    await page.get_by_role('button',name='Approve exact action').click()
                    await page.get_by_text('Status: approved',exact=True).wait_for()
                    assert gateway.get_challenge(challenge.challenge_id)['status']=='approved'
                    assert not errors,errors
                    await page.get_by_role('button',name='Clear credential').click()
                    assert await page.locator('#credential').input_value()==''
                    assert await page.locator('article').count()==0
                    (output/'result.json').write_text(json.dumps({'passed':True,'viewport':390,
                        'checks':['authenticated listing','literal untrusted text','no storage','mobile fit','exact approval','credential clear'],
                        'issuer':'local fixture; no deployed identity provider tested'}),encoding='utf-8')
                finally: await browser.close()
        finally: await runner.cleanup()
    print('Review browser smoke: PASS')


if __name__=='__main__': asyncio.run(main())
