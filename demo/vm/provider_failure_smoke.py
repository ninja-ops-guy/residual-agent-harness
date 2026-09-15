"""Browser regression for the real-user provider failure path.

The provider SDK remains an explicit test double. This proves Mission Control's
state/UX behavior, not paid inference or real Puter model availability.
"""
from __future__ import annotations

FAILURE_SDK = r'''
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
  ai: {
    listModels: async () => [{id:'openai/gpt-5-nano',aliases:['gpt-5-nano']}],
    chat: async () => {
      window.__providerFixture.calls++;
      throw {code:'403', message:'fixture secret body must not cross the bridge'};
    }
  }
};
'''


async def provider_failure_acceptance(page, context, args, report, stage):
    await page.locator('#mc-mission').click()
    await page.locator('#mc-new-chat').click()
    await page.get_by_text('Run controls', exact=True).click()
    await page.locator('#mc-mode').select_option('build')
    await page.locator('#mc-budget').select_option('1')
    await page.locator('#mc-files').fill('')
    await page.locator('#mc-required').fill('Calculator')
    prompt = 'Build a calculator from the real-provider failure regression'
    await page.locator('#mc-prompt').fill(prompt)
    await page.locator('#mc-consent').uncheck()

    # Send is the discovery path. It must open provider setup without losing or
    # submitting the prompt.
    users_before = await page.locator('#mc-chat .bubble.user').count()
    async with context.expect_page() as info:
        await page.locator('#mc-run').click()
    provider = await info.value
    await provider.wait_for_load_state('domcontentloaded')
    assert await page.locator('#mc-prompt').input_value() == prompt
    assert await page.locator('#mc-chat .bubble.user').count() == users_before
    assert 'prompt is still in the composer' in (await page.locator('#mc-chat').inner_text()).lower()
    assert 'provider setup opened' in (await page.locator('#mc-provider-gate-status').inner_text()).lower()
    report['workbench_guided_provider_discovery'] = 'PASS_PROMPT_PRESERVED_NO_INFERENCE'
    await stage('guided_provider_setup_preserves_unsent_prompt')

    await provider.route('https://js.puter.com/v2/**', lambda route: route.fulfill(
        status=200, content_type='text/javascript', body=FAILURE_SDK))
    await provider.locator('#load').click()
    await provider.locator('#signin').click()
    await page.wait_for_function("() => document.querySelector('#mc-connect').textContent === 'Provider connected'", timeout=20000)
    assert await provider.evaluate('window.__providerFixture.gesture')

    # Connectivity is not consent. The exact prompt still must not be sent.
    users_before = await page.locator('#mc-chat .bubble.user').count()
    await page.locator('#mc-run').click()
    assert await page.locator('#mc-prompt').input_value() == prompt
    assert await page.locator('#mc-chat .bubble.user').count() == users_before
    assert 'not authorized yet' in (await page.locator('#mc-provider-gate-status').inner_text()).lower()
    assert await provider.evaluate('window.__providerFixture.calls') == 0
    report['workbench_per_prompt_authorization_gate'] = 'PASS_CONNECTED_IS_NOT_CONSENT'
    await stage('per_prompt_authorization_blocks_unsent_prompt')

    await page.locator('#mc-consent').check()
    await page.locator('#mc-run').click()
    await page.wait_for_function("() => document.querySelector('#mc-verdict').textContent.startsWith('BLOCKED')", timeout=120000)
    chat = await page.locator('#mc-chat').inner_text()
    assert 'Build blocked — no artifact was accepted' in chat
    assert 'Build completed.' not in chat
    assert await page.locator('#mc-inline-preview-frame').count() == 0
    assert await page.locator('#mc-preview-frame').count() == 0
    assert 'No preview' in await page.locator('#mc-preview-status').inner_text()
    assert await page.locator('#mc-connect').inner_text() == 'Provider connected'
    assert await provider.evaluate('window.__providerFixture.calls') == 1
    assert 'fixture secret body' not in await page.locator('body').inner_text()

    await page.locator('button[data-tab="activity"]').click()
    engineer = await page.locator('#mc-engineer-timeline').inner_text()
    assert 'Build was not accepted' in engineer
    assert 'WHY' in engineer and 'NEXT' in engineer
    assert 'provider_authorization_failed' in engineer
    report['workbench_truthful_provider_failure'] = 'PASS_BLOCKED_NO_FALSE_SUCCESS_NO_PREVIEW'
    report['workbench_engineer_explanation'] = 'PASS_STAGE_WHY_NEXT_SAFE_ERROR_CODE'
    await page.screenshot(path=str(args.output / 'mission-provider-failure-explained.png'))
    await stage('provider_failure_is_blocked_explained_and_not_previewed')
    await provider.close()
