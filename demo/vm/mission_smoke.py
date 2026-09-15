"""Browser workbench acceptance. Remote SDK is a TEST DOUBLE, never paid inference.

Runs against a real Linux guest. The SDK substitution is Playwright routing in
this test process only; the shipped app has no fixture or fallback switch.
"""
import re
import secrets

SDK_FIXTURE = r'''
window.__providerFixture = {signedIn:false, calls:0, gesture:false};
window.puter = {
  auth: {
    isSignedIn: () => window.__providerFixture.signedIn,
    signIn: () => {
      window.__providerFixture.gesture = navigator.userActivation.isActive;
      if (!window.__providerFixture.gesture) return Promise.reject({error:'popup_blocked'});
      const popup = window.open('about:blank', '_blank');
      if (!popup) return Promise.reject({error:'popup_blocked'});
      popup.close(); window.__providerFixture.signedIn = true; return Promise.resolve({});
    }
  },
  ai: {chat: async (messages, options) => {
    window.__providerFixture.calls++;
    const packet = JSON.parse(messages[messages.length-1].content), e = packet.evidence[0];
    const answer = {text:'Transport contract fixture for: '+packet.goal,
      citations:[{artifact_id:e.artifact_id,start_line:e.start_line,end_line:e.start_line,quote:e.text.split('\n')[0]}]};
    return {message:{content:JSON.stringify({updates:{answer},requests:[]})},usage:{input_tokens:10,output_tokens:10}};
  }}
};
'''


async def workbench_acceptance(page, context, args, report, command_proof, stage):
    report['workbench_provider_evidence'] = 'REAL_GUEST_WITH_TEST_DOUBLE_SDK_NOT_PAID_INFERENCE'
    report['provider_auth_evidence'] = 'USER_GESTURE_AND_POPUP_CONTRACT_TEST_DOUBLE_NOT_REAL_PUTER_LOGIN'
    await page.locator('#mc-mission').click()
    await page.locator('#mc-mode').select_option('audit')
    await page.locator('#mc-prompt').fill('Inspect these actual repository sources ' + secrets.token_hex(4))
    await page.get_by_text('Sources and acceptance checks', exact=True).click()
    await page.locator('#mc-files').fill('residual/cli.py')
    await page.locator('#mc-run').click()
    await page.wait_for_function("() => document.querySelector('#mc-verdict').textContent.startsWith('PASSED') && !document.querySelector('#mc-result').hidden", timeout=120000)
    assert 'deterministic source inventory' in await page.locator('#mc-verdict').inner_text()
    assert int(await page.locator('#mc-count').inner_text()) > 0
    assert 'main' in await page.locator('#mc-answer').inner_text()
    report['workbench_audit'] = 'PASS'
    await stage('workbench_real_repository_audit_passed')
    await page.screenshot(path=str(args.output / 'mission-audit.png'))
    assert not report['optional_requests'], 'provider network initialized before opt-in'

    async with context.expect_page() as info:
        await page.locator('#mc-connect').click()
    provider = await info.value
    await provider.wait_for_load_state('domcontentloaded')
    await provider.locator('#load').wait_for()
    assert await provider.evaluate('!window.crossOriginIsolated'), 'provider helper must be outside isolated VM context'
    assert await page.evaluate('!window.puter'), 'Puter SDK leaked into isolated VM host'
    assert not report['optional_requests'], 'helper initialized SDK without its load consent'
    await provider.route('https://js.puter.com/v2/**', lambda route: route.abort('internetdisconnected'))
    await provider.locator('#load').click()
    await provider.wait_for_function("() => document.querySelector('#status').textContent.includes('could not load')")
    assert report['optional_requests'], 'explicit SDK load did not attempt a network request'
    await page.locator('#mc-terminal').click()
    await command_proof('true')
    await stage('cloud_network_failure_preserves_guest')

    # Deterministic contract test, not a claim of real authentication or model output.
    await provider.unroute('https://js.puter.com/v2/**')
    await provider.route('https://js.puter.com/v2/**', lambda route: route.fulfill(status=200, content_type='text/javascript', body=SDK_FIXTURE))
    await provider.locator('#load').click()
    await provider.locator('#signin').click()
    await page.wait_for_function("() => document.querySelector('#mc-connect').textContent === 'Provider connected'", timeout=20000)
    assert await provider.evaluate('window.__providerFixture.gesture'), 'sign-in lost user gesture'
    await page.locator('#mc-mission').click()
    await page.locator('#mc-mode').select_option('live')
    nonce = 'mission-proof-' + secrets.token_hex(4)
    await page.locator('#mc-prompt').fill('Explain the selected source. Include ' + nonce)
    await page.locator('#mc-files').fill('README.md')
    await page.locator('#mc-required').fill(nonce)
    await page.locator('#mc-consent').check()
    await page.locator('#mc-run').click()
    await page.wait_for_function("() => document.querySelector('#mc-verdict').textContent.includes('SEMANTIC CORRECTNESS: UNKNOWN') && !document.querySelector('#mc-result').hidden", timeout=120000)
    assert 'PASSED' in await page.locator('#mc-verdict').inner_text()
    assert nonce in await page.locator('#mc-answer').inner_text()
    assert await provider.evaluate('window.__providerFixture.calls') == 1
    path = re.search(r'/opt/residual/runs/missions/m-[a-f0-9]{32}', await page.locator('#mc-path').inner_text()).group()
    await page.screenshot(path=str(args.output / 'mission-provider-contract.png'))
    await page.locator('#mc-terminal').click()
    await command_proof(f'test -s {path}/answer.md && python3 -m residual verify-trace {path}/trace.jsonl --result {path}/result.json')
    report['workbench_provider_contract'] = 'PASS_WITH_SDK_TEST_DOUBLE'
    await stage('workbench_real_guest_provider_transport_contract_passed')

    # CLI-launched work projects the real ledger back into Mission Control.
    await command_proof('python3 -m residual.workbench audit --stream --files residual/cli.py')
    await page.locator('#mc-mission').click()
    assert 'deterministic source inventory' in await page.locator('#mc-verdict').inner_text()
    assert path not in await page.locator('#mc-path').inner_text()
    await stage('workbench_cli_to_ui_projection_passed')
    await provider.close()
    await page.reload(wait_until='domcontentloaded')
    await page.locator('#mc-terminal').click()
    await page.wait_for_function("() => document.body.innerText.replace(/\\s/g,'').includes('residual@demo:~/residual-agent-harness$')", timeout=120000)
    await command_proof(f'test -s {path}/answer.md && python3 -m residual verify-trace {path}/trace.jsonl --result {path}/result.json')
    await stage('workbench_saved_mission_survives_reload')
