"""Browser workbench acceptance. Remote SDK is a TEST DOUBLE, never paid inference.

Runs against a real Linux guest. The SDK substitution is Playwright routing in
this test process only; the shipped app has no fixture or fallback switch.
"""
import re
import secrets
import shlex

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
    const packet = JSON.parse(messages[messages.length-1].content), obligation = packet.obligations[0], e = packet.evidence[0];
    let updates;
    if (obligation.id === 'build') {
      const revision = packet.evidence.some(item => String(item.artifact_id||'').startsWith('prior-'));
      updates = {build: revision ? {summary:'Calculator v2 dark mode refinement.',files:[
        {path:'index.html',content:'<!doctype html><title>Calculator</title><body data-revision="2" style="background:#111;color:#eee"><main><h1>Calculator</h1><label>A <input id="a" type="number"></label><label>B <input id="b" type="number"></label><button id="go">Add</button><output id="result">0</output></main><script>go.onclick=()=>result.textContent=String(Number(a.value)+Number(b.value));</script></body>'},
        {path:'README.md',content:'Calculator v2\n\nDark mode refinement. Generated review artifact.'}
      ]}:{summary:'Calculator deliverable generated for review.',files:[
        {path:'index.html',content:'<!doctype html><title>Calculator</title><main><h1>Calculator</h1><label>A <input id="a" type="number"></label><label>B <input id="b" type="number"></label><button id="go">Add</button><output id="result">0</output></main><script>go.onclick=()=>result.textContent=String(Number(a.value)+Number(b.value));</script>'},
        {path:'README.md',content:'Calculator\n\nGenerated review artifact. Not executed by RESIDUAL.'}
      ]}};
    } else {
      const answer = {text:'Transport contract fixture for: '+packet.goal,
        citations:[{artifact_id:e.artifact_id,start_line:e.start_line,end_line:e.start_line,quote:e.text.split('\n')[0]}]};
      updates = {answer};
    }
    return {message:{content:JSON.stringify({updates,requests:[]})},usage:{input_tokens:10,output_tokens:10}};
  }}
};
'''


async def workbench_acceptance(page, context, args, report, command_proof, stage):
    report['workbench_provider_evidence'] = 'REAL_GUEST_WITH_TEST_DOUBLE_SDK_NOT_PAID_INFERENCE'
    report['provider_auth_evidence'] = 'USER_GESTURE_AND_POPUP_CONTRACT_TEST_DOUBLE_NOT_REAL_PUTER_LOGIN'
    await page.locator('#mc-mission').click()
    assert await page.locator('#mc-mission').inner_text() == 'Chat'
    assert await page.locator('button[data-tab="activity"]').count() == 1
    assert await page.locator('button[data-tab="evidence"]').count() == 1
    assert await page.locator('button[data-tab="files"]').count() == 1
    assert await page.locator('#mc-new-chat').count() == 1
    assert await page.locator('#mc-history').count() == 1
    await page.get_by_text('Run controls', exact=True).click()
    await page.locator('#mc-mode').select_option('audit')
    await page.locator('#mc-prompt').fill('Inspect these actual repository sources ' + secrets.token_hex(4))
    await page.locator('#mc-files').fill('residual/cli.py\nresidual/engine.py')
    await page.locator('#mc-run').click()
    await page.wait_for_function("() => document.querySelector('#mc-verdict').textContent.startsWith('PASSED') && !document.querySelector('#mc-result').hidden", timeout=120000)
    assert 'deterministic source inventory' in await page.locator('#mc-verdict').inner_text()
    assert int(await page.locator('#mc-count').inner_text()) > 0
    assert 'main' in await page.locator('#mc-answer').inner_text()
    assert 'Inspect these actual repository sources' in await page.locator('#mc-chat').inner_text()
    report['workbench_audit'] = 'PASS'
    report['workbench_chat_ui'] = 'PASS_WITH_BACKGROUND_TABS'
    await stage('workbench_real_repository_audit_passed')
    await page.screenshot(path=str(args.output / 'mission-chat-audit.png'))
    assert not report['optional_requests'], 'provider network initialized before opt-in'

    # Prove Mission Control has exactly one live worker after its first mission.
    # The PID snapshot uses Bash builtins only and does not start another Python.
    await page.locator('#mc-terminal').click()
    await command_proof('read -r residual_worker_pid < /tmp/residual-workbench.pid && kill -0 "$residual_worker_pid" && printf "%s\\n" "$residual_worker_pid" > /tmp/residual-worker-first.pid')
    await page.locator('#mc-mission').click()

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
    await command_proof('read -r residual_worker_pid < /tmp/residual-workbench.pid && read -r residual_worker_first < /tmp/residual-worker-first.pid && test "$residual_worker_pid" = "$residual_worker_first" && kill -0 "$residual_worker_pid"')
    await stage('cloud_network_failure_preserves_guest')

    await provider.unroute('https://js.puter.com/v2/**')
    await provider.route('https://js.puter.com/v2/**', lambda route: route.fulfill(status=200, content_type='text/javascript', body=SDK_FIXTURE))
    await provider.locator('#load').click()
    await provider.locator('#signin').click()
    await page.wait_for_function("() => document.querySelector('#mc-connect').textContent === 'Provider connected'", timeout=20000)
    assert await provider.evaluate('window.__providerFixture.gesture'), 'sign-in lost user gesture'

    await page.locator('#mc-mission').click()
    await page.get_by_text('Run controls', exact=True).click()
    await page.locator('#mc-mode').select_option('build')
    await page.locator('#mc-prompt').fill('Build a calculator')
    await page.locator('#mc-files').fill('')
    await page.locator('#mc-required').fill('Calculator')
    await page.locator('#mc-consent').check()
    conversation_id = await page.evaluate("localStorage.getItem('residual.chat.current.v2')")
    assert re.fullmatch(r'c-[a-f0-9]{32}', conversation_id)
    await page.locator('#mc-run').click()
    assert await page.locator('#mc-new-chat').is_disabled()
    assert await page.locator('#mc-history').is_disabled()
    await page.wait_for_function("() => document.querySelector('#mc-verdict').textContent.includes('CODE CORRECTNESS: UNKNOWN') && !document.querySelector('#mc-result').hidden", timeout=120000)
    await page.wait_for_function("() => !document.querySelector('#mc-new-chat').disabled && !document.querySelector('#mc-history').disabled", timeout=20000)
    assert not await page.locator('#mc-new-chat').is_disabled()
    assert not await page.locator('#mc-history').is_disabled()
    assert 'PASSED' in await page.locator('#mc-verdict').inner_text()
    assert 'index.html' in await page.locator('#mc-artifact-list').inner_text()
    assert 'Calculator deliverable' in await page.locator('#mc-answer').inner_text()
    await page.locator('#mc-inline-preview-frame').wait_for(timeout=20000)
    frame = page.frame_locator('#mc-inline-preview-frame')
    await frame.locator('#a').fill('2'); await frame.locator('#b').fill('3'); await frame.locator('#go').click()
    assert await frame.locator('#result').inner_text() == '5'
    assert await page.locator('#mc-inline-preview-frame').get_attribute('sandbox') == 'allow-scripts'
    build_path = re.search(r'/opt/residual/runs/missions/m-[a-f0-9]{32}', await page.locator('#mc-path').inner_text()).group()
    first_mid = build_path.rsplit('/', 1)[-1]
    await page.screenshot(path=str(args.output / 'mission-chat-build-preview.png'))
    await page.locator('#mc-terminal').click()
    await command_proof(f'test -s {build_path}/artifacts/index.html && grep -q Calculator {build_path}/artifacts/index.html && grep -q "\\\"executed\\\":false" {build_path}/artifacts/manifest.json && read -r residual_worker_pid < /tmp/residual-workbench.pid && read -r residual_worker_first < /tmp/residual-worker-first.pid && test "$residual_worker_pid" = "$residual_worker_first" && kill -0 "$residual_worker_pid"')
    report['workbench_build_artifacts'] = 'PASS_WITH_SDK_TEST_DOUBLE_NOT_EXECUTED'
    report['workbench_interactive_preview'] = 'PASS_SANDBOXED_CALCULATOR_INTERACTION_WITH_TEST_DOUBLE_ARTIFACT'
    await stage('workbench_generated_artifacts_saved_previewed_and_verified')

    await page.locator('#mc-mission').click()
    await page.locator('#mc-prompt').fill('Make the calculator dark mode while preserving addition')
    await page.locator('#mc-run').click()
    assert await page.locator('#mc-new-chat').is_disabled()
    assert await page.locator('#mc-history').is_disabled()
    assert await page.locator('#mc-detach').is_disabled()
    await page.wait_for_function("() => document.querySelector('#mc-session').textContent.includes('REV 2') && document.querySelector('#mc-answer').textContent.includes('dark mode')", timeout=120000)
    await page.wait_for_function("() => !document.querySelector('#mc-new-chat').disabled && !document.querySelector('#mc-history').disabled && !document.querySelector('#mc-detach').disabled", timeout=20000)
    assert not await page.locator('#mc-new-chat').is_disabled()
    assert not await page.locator('#mc-history').is_disabled()
    assert not await page.locator('#mc-detach').is_disabled()
    assert await page.locator('#mc-inline-preview-frame-r1').count() == 1
    refined = page.frame_locator('#mc-inline-preview-frame')
    assert await refined.locator('body').get_attribute('data-revision') == '2'
    await refined.locator('#a').fill('4'); await refined.locator('#b').fill('6'); await refined.locator('#go').click()
    assert await refined.locator('#result').inner_text() == '10'
    second_path = re.search(r'/opt/residual/runs/missions/m-[a-f0-9]{32}', await page.locator('#mc-path').inner_text()).group()
    assert second_path != build_path
    await page.locator('button[data-tab="files"]').click()
    await page.wait_for_function("() => document.querySelector('#mc-preview-status').textContent.includes('RUNTIME SMOKE: PASS')", timeout=20000)
    await page.locator('#mc-terminal').click()
    await command_proof(f'grep -q "\\\"conversation_id\\\":\\\"{conversation_id}\\\"" {second_path}/summary.json && grep -q "\\\"parent_mission_id\\\":\\\"{first_mid}\\\"" {second_path}/summary.json && grep -q "\\\"revision\\\":2" {second_path}/summary.json && read -r residual_worker_pid < /tmp/residual-workbench.pid && read -r residual_worker_first < /tmp/residual-worker-first.pid && test "$residual_worker_pid" = "$residual_worker_first" && kill -0 "$residual_worker_pid"')
    report['workbench_conversation_continuity'] = 'PASS_SAME_SESSION_PARENT_BUNDLE_FROZEN_AND_REVISION_BOUND'
    report['workbench_preview_runtime_smoke'] = 'PASS_NO_STARTUP_JS_ERRORS_SEMANTIC_CORRECTNESS_UNKNOWN'
    report['workbench_active_mission_navigation_lock'] = 'PASS'
    await stage('workbench_followup_revision_and_runtime_smoke_passed')

    await page.locator('#mc-mission').click()
    await page.get_by_text('Run controls', exact=True).click()
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
    assert 'README.md:1-1' in await page.locator('#mc-citations').text_content()
    assert await provider.evaluate('window.__providerFixture.calls') == 3
    path = re.search(r'/opt/residual/runs/missions/m-[a-f0-9]{32}', await page.locator('#mc-path').inner_text()).group()
    await page.screenshot(path=str(args.output / 'mission-chat-provider-contract.png'))
    await page.locator('#mc-terminal').click()
    await command_proof(f'test -s {path}/answer.md && read -r residual_worker_pid < /tmp/residual-workbench.pid && read -r residual_worker_first < /tmp/residual-worker-first.pid && test "$residual_worker_pid" = "$residual_worker_first" && kill -0 "$residual_worker_pid"')
    report['workbench_provider_contract'] = 'PASS_WITH_SDK_TEST_DOUBLE'
    report['workbench_persistent_worker'] = 'PASS_SAME_PID_ACROSS_AUDIT_BUILD_FOLLOWUP_LIVE'
    await stage('workbench_real_guest_provider_transport_contract_passed')

    # Shut down the persistent worker cleanly before exercising the standalone
    # CLI. This proves the two interfaces independently and avoids concurrent
    # CPython interpreters in the WebVM guest during qualification.
    await command_proof('read -r residual_worker_pid < /tmp/residual-workbench.pid && ( set -C; umask 077; printf "shutdown\\n" > /tmp/residual-workbench.control ) && wait "$residual_worker_pid" && test ! -e /tmp/residual-workbench.pid && test ! -e /tmp/residual-workbench.control')
    # Preserve the original independent evidence-chain acceptance coverage while
    # avoiding one fresh interpreter per mission: verify build, follow-up, and
    # live-provider outputs together in one post-worker Python process.
    verify_code = (
        'from pathlib import Path; from residual.workbench.runner import verify_run; '
        f'verify_run(Path({build_path!r})); '
        f'verify_run(Path({second_path!r})); '
        f'verify_run(Path({path!r}))'
    )
    await command_proof('python3 -c ' + shlex.quote(verify_code))
    report['workbench_external_trace_verification'] = 'PASS_BUILD_FOLLOWUP_LIVE_AFTER_WORKER_SHUTDOWN'
    await command_proof('python3 -m residual.workbench audit --stream --files residual/cli.py')
    await page.locator('#mc-mission').click()
    assert 'deterministic source inventory' in await page.locator('#mc-verdict').inner_text()
    assert path not in await page.locator('#mc-path').inner_text()
    await stage('workbench_cli_to_ui_projection_passed')
    await provider.close()
    await page.reload(wait_until='domcontentloaded')
    await page.locator('#mc-terminal').click()
    await page.wait_for_function("() => document.body.innerText.replace(/\\s/g,'').includes('residual@demo:~/residual-agent-harness$')", timeout=120000)
    await command_proof(
        f'test -s {path}/answer.md && '
        f'test -s {build_path}/artifacts/index.html && '
        f'test -s {second_path}/artifacts/index.html && '
        'python3 -c ' + shlex.quote(verify_code)
    )
    await page.locator('#mc-mission').click()
    chat_text = await page.locator('#mc-chat').inner_text()
    assert 'Build a calculator' in chat_text
    assert 'Make the calculator dark mode while preserving addition' in chat_text
    assert 'Session transcript restored from this browser' in chat_text
    assert 'Restored browser-local preview cache' in chat_text
    assert await page.locator('#mc-restored-preview-frame').count() == 1
    report['workbench_conversation_reload'] = 'PASS_SANITIZED_BROWSER_CACHE_WITH_AUTHORITY_LABEL'
    await stage('workbench_saved_conversation_survives_reload')