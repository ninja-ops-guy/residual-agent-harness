/* Adapter for tests/browser.cjs so the same user journey can qualify Chromium,
 * Firefox, and WebKit without changing the production UI harness.
 *
 * AUD-1 removes operator authority from /api/bootstrap. The production server
 * gives the browser an HttpOnly session cookie through a one-time launch URL.
 * Qualification runs use an isolated temporary Station data directory; this
 * shim reads that exact test-only session token from the newest residual-ui-*
 * SQLite database and installs the equivalent HttpOnly cookie before the first
 * navigation. This is test harness code only and is not imported by production.
 *
 * WebKit's Playwright screenshot implementation injects a temporary inline
 * stylesheet. Command Station correctly rejects that stylesheet under its
 * `style-src 'self'` CSP, which WebKit reports as a page console error. The
 * application itself is not generating that inline style. We suppress only
 * that exact Playwright-instrumentation message while screenshot() is active;
 * identical CSP errors at any other time remain fatal to browser.cjs.
 */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const playwright = require('playwright');
const name = process.env.PLAYWRIGHT_BROWSER || 'chromium';
if (!['chromium', 'firefox', 'webkit'].includes(name)) {
  throw new Error(`Unsupported PLAYWRIGHT_BROWSER=${name}`);
}
const selected = playwright[name];
const screenshotCsp = "Refused to apply a stylesheet because its hash, its nonce, or 'unsafe-inline' does not appear in the style-src directive of the Content Security Policy.";

function newestStationDb() {
  const dirs = fs.readdirSync(os.tmpdir(), {withFileTypes: true})
    .filter(entry => entry.isDirectory() && entry.name.startsWith('residual-ui-'))
    .map(entry => path.join(os.tmpdir(), entry.name))
    .filter(dir => fs.existsSync(path.join(dir, 'station.sqlite3')))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!dirs.length) throw new Error('Isolated browser Station database was not found');
  return path.join(dirs[0], 'station.sqlite3');
}

function testSessionToken() {
  const script = [
    'import json, sqlite3, sys',
    'c=sqlite3.connect(sys.argv[1])',
    "r=c.execute(\"select value from settings where id='session_token'\").fetchone()",
    "assert r, 'session token missing'",
    'print(json.loads(r[0]))',
  ].join(';');
  return execFileSync(process.env.PYTHON || 'python3', ['-c', script, newestStationDb()], {encoding: 'utf8'}).trim();
}

async function authenticateContext(context, target) {
  if (context.__residualAuthenticated) return;
  const origin = new URL(String(target)).origin;
  await context.addCookies([{
    name: 'residual_session',
    value: testSessionToken(),
    url: origin,
    httpOnly: true,
    sameSite: 'Strict',
  }]);
  context.__residualAuthenticated = true;
}

function instrumentPage(page, context) {
  if (page.__residualQualificationWrapped) return page;
  page.__residualQualificationWrapped = true;
  let screenshotActive = false;
  let suppressed = 0;

  const originalGoto = page.goto.bind(page);
  page.goto = async (target, options) => {
    await authenticateContext(context, target);
    return originalGoto(target, options);
  };

  const originalOn = page.on.bind(page);
  page.on = (event, listener) => {
    if (event !== 'console') return originalOn(event, listener);
    return originalOn(event, message => {
      if (name === 'webkit' && screenshotActive && message.type() === 'error' && message.text() === screenshotCsp) {
        suppressed += 1;
        return;
      }
      return listener(message);
    });
  };

  if (name === 'webkit') {
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
  }
  return page;
}

async function wrapBrowser(browser) {
  const originalNewContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await originalNewContext(options);
    const originalNewPage = context.newPage.bind(context);
    context.newPage = async () => instrumentPage(await originalNewPage(), context);
    return context;
  };
  return browser;
}

module.exports = {
  chromium: {
    async launch(options = {}) {
      if (name === 'chromium') return wrapBrowser(await selected.launch(options));
      const { executablePath, args, ...portable } = options;
      return wrapBrowser(await selected.launch(portable));
    },
  },
};
