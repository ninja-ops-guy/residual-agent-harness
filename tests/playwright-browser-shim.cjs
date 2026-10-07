/* Adapter for tests/browser.cjs so the same user journey can qualify Chromium,
 * Firefox, and WebKit without changing the production UI harness.
 *
 * WebKit's Playwright screenshot implementation injects a temporary inline
 * stylesheet. Command Station correctly rejects that stylesheet under its
 * `style-src 'self'` CSP, which WebKit reports as a page console error. The
 * application itself is not generating that inline style. We suppress only
 * that exact Playwright-instrumentation message while screenshot() is active;
 * identical CSP errors at any other time remain fatal to browser.cjs.
 */
const playwright = require('playwright');
const name = process.env.PLAYWRIGHT_BROWSER || 'chromium';
if (!['chromium', 'firefox', 'webkit'].includes(name)) {
  throw new Error(`Unsupported PLAYWRIGHT_BROWSER=${name}`);
}
const selected = playwright[name];
const screenshotCsp = "Refused to apply a stylesheet because its hash, its nonce, or 'unsafe-inline' does not appear in the style-src directive of the Content Security Policy.";

function instrumentWebKitPage(page) {
  if (name !== 'webkit' || page.__residualQualificationWrapped) return page;
  page.__residualQualificationWrapped = true;
  let screenshotActive = false;
  let suppressed = 0;

  const originalOn = page.on.bind(page);
  page.on = (event, listener) => {
    if (event !== 'console') return originalOn(event, listener);
    return originalOn(event, message => {
      if (screenshotActive && message.type() === 'error' && message.text() === screenshotCsp) {
        suppressed += 1;
        return;
      }
      return listener(message);
    });
  };

  const originalScreenshot = page.screenshot.bind(page);
  page.screenshot = async options => {
    screenshotActive = true;
    try {
      const result = await originalScreenshot(options);
      await page.waitForTimeout(25);
      return result;
    } finally {
      screenshotActive = false;
      if (suppressed) {
        console.log(`RESIDUAL_QA_WEBKIT_SCREENSHOT_CSP suppressed=${suppressed}`);
        suppressed = 0;
      }
    }
  };
  return page;
}

async function wrapBrowser(browser) {
  if (name !== 'webkit') return browser;
  const originalNewContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await originalNewContext(options);
    const originalNewPage = context.newPage.bind(context);
    context.newPage = async () => instrumentWebKitPage(await originalNewPage());
    return context;
  };
  return browser;
}

module.exports = {
  chromium: {
    async launch(options = {}) {
      if (name === 'chromium') return selected.launch(options);
      const { executablePath, args, ...portable } = options;
      return wrapBrowser(await selected.launch(portable));
    },
  },
};
