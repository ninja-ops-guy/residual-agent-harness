/* Dedicated synthetic preview; never starts Station or a native agent. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const out = path.resolve(process.env.PREPARATION_QA_DIR || path.join(root, 'runs', 'agent-preparation'));
fs.mkdirSync(out, {recursive: true});
const files = [
  'tests/fixtures/agent-preparation.html', 'tests/fixtures/agent-preparation-fixture.mjs',
  'tests/fixtures/agent-preparation-data.mjs', 'residual/station/static/agent-preparation-model.mjs',
  'residual/station/static/agent-preparation-view.mjs', 'residual/station/static/agent-preparation.css',
];
const allowed = new Set(files.map(file => '/' + file));
const mime = {'.html': 'text/html', '.mjs': 'text/javascript', '.css': 'text/css'};
const requests = [], violations = [], checks = [], pageErrors = [], observations = [];
const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');
const git = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8'}).trim();
let browser, page, origin, failure;
const server = http.createServer((request, response) => {
  const url = new URL(request.url, 'http://127.0.0.1');
  requests.push({method: request.method, path: url.pathname});
  if (request.method !== 'GET' || !allowed.has(url.pathname)) {
    violations.push({method: request.method, path: url.pathname});
    response.writeHead(403); response.end(); return;
  }
  response.writeHead(200, {'Content-Type': mime[path.extname(url.pathname)], 'Cache-Control': 'no-store'});
  response.end(fs.readFileSync(path.join(root, url.pathname.slice(1))));
});
const state = id => page.locator('[data-stage="' + id + '"]').getAttribute('data-state');
async function unknownAuthority() {
  for (const id of ['connectivity', 'communications', 'eligibility', 'acceptance']) assert.equal(await state(id), 'UNKNOWN');
}
async function check(name, body) {
  try {
    await body();
    observations.push({name, stages: await page.locator('[data-stage]').evaluateAll(rows =>
      rows.map(row => ({stage: row.dataset.stage, state: row.dataset.state}))),
    side_effects: await page.evaluate(() => window.preparationEffects)});
    checks.push({name, passed: true});
  }
  catch (error) { checks.push({name, passed: false, error: String(error)}); throw error; }
}
async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = 'http://127.0.0.1:' + server.address().port;
  browser = await chromium.launch({headless: true});
  const context = await browser.newContext({viewport: {width: 1280, height: 1000}});
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || route.request().method() !== 'GET' || !allowed.has(url.pathname)) {
      violations.push({method: route.request().method(), path: url.pathname, origin: url.origin});
      return route.abort();
    }
    return route.continue();
  });
  await context.addInitScript(() => {
    window.preparationEffects = [];
    const block = name => () => { window.preparationEffects.push(name); throw new Error('Unexpected side effect: ' + name); };
    window.fetch = block('fetch');
    XMLHttpRequest.prototype.open = block('xhr');
    window.WebSocket = block('websocket');
    window.EventSource = block('eventsource');
    navigator.sendBeacon = block('beacon');
    Storage.prototype.setItem = block('storage');
    indexedDB.open = block('indexeddb');
  });
  page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => pageErrors.push(String(error)));
  await page.goto(origin + '/tests/fixtures/agent-preparation.html');
  await page.getByRole('heading', {name: 'Agent preparation', exact: true}).waitFor();
  await check('initial state is empty, unintegrated and unknown', async () => {
    assert.equal(await page.locator('[data-state="UNKNOWN"]').count(), 8);
    assert.match(await page.locator('.preparation-notice').innerText(), /not integrated and not native-qualified/);
    assert.equal(await page.getByLabel('Host', {exact: true}).inputValue(), '');
  });
  await check('normal click loads reports without granting authority or project membership', async () => {
    await page.getByRole('button', {name: 'Load reported snapshot', exact: true}).click();
    assert.equal(await state('identity'), 'DECLARED');
    assert.equal(await state('preflight'), 'REPORTED');
    assert.equal(await state('enrollment'), 'REPORTED');
    assert.match(await page.locator('[data-stage="enrollment"]').innerText(), /project_count does not identify project membership/);
    await unknownAuthority();
    await page.screenshot({path: path.join(out, 'reported.png'), fullPage: true});
  });
  await check('editing project and reviewing with normal click does not inherit preflight', async () => {
    await page.getByLabel('Project', {exact: true}).fill('another-project');
    await page.getByRole('button', {name: 'Review declarations', exact: true}).click();
    assert.equal(await state('preflight'), 'MISMATCH');
    await unknownAuthority();
  });
  await check('different adapter cannot corroborate local preflight without a mesh snapshot', async () => {
    await page.getByRole('button', {name: 'Load local preflight only', exact: true}).click();
    assert.equal(await state('enrollment'), 'UNKNOWN');
    await page.getByLabel('Adapter', {exact: true}).fill('hermes');
    await page.getByRole('button', {name: 'Review declarations', exact: true}).click();
    assert.equal(await state('preflight'), 'MISMATCH');
    assert.equal(await state('enrollment'), 'UNKNOWN');
    assert.match(await page.locator('[data-stage="preflight"]').innerText(), /OpenClaw-only/);
    await unknownAuthority();
    await page.screenshot({path: path.join(out, 'adapter-mismatch.png'), fullPage: true});
  });
  await check('missing adapter keeps local preflight unknown without a mesh snapshot', async () => {
    await page.getByLabel('Adapter', {exact: true}).fill('');
    await page.getByRole('button', {name: 'Review declarations', exact: true}).click();
    assert.equal(await state('preflight'), 'UNKNOWN');
    assert.equal(await state('enrollment'), 'UNKNOWN');
    await unknownAuthority();
    await page.screenshot({path: path.join(out, 'adapter-missing.png'), fullPage: true});
  });
  await check('corrected adapter reports only local preflight without granting authority', async () => {
    await page.getByLabel('Adapter', {exact: true}).fill('openclaw-exec');
    await page.getByRole('button', {name: 'Review declarations', exact: true}).click();
    assert.equal(await state('preflight'), 'REPORTED');
    assert.equal(await state('enrollment'), 'UNKNOWN');
    assert.equal(await state('containment'), 'UNKNOWN');
    await unknownAuthority();
    await page.screenshot({path: path.join(out, 'adapter-corrected.png'), fullPage: true});
  });
  for (const [button, id, expected] of [
    ['Load expired snapshot', 'enrollment', 'EXPIRED'],
    ['Load other project', 'preflight', 'MISMATCH'],
    ['Load other host', 'enrollment', 'MISMATCH'],
    ['Load revoked snapshot', 'enrollment', 'BLOCKED'],
    ['Load uncertain snapshot', 'enrollment', 'UNKNOWN'],
    ['Load unsupported adapter', 'containment', 'UNSUPPORTED'],
  ]) await check(button + ' cannot promote another stage', async () => {
    await page.getByRole('button', {name: button, exact: true}).click();
    assert.equal(await state(id), expected);
    await unknownAuthority();
  });
  await check('hostile declaration renders as inert text with no resource or script execution', async () => {
    await page.getByRole('button', {name: 'Load hostile declaration', exact: true}).click();
    await page.getByRole('button', {name: 'Review declarations', exact: true}).click();
    assert.match(await page.locator('.preparation-declarations').innerText(), /<img src=/);
    assert.equal(await page.locator('#preparation img').count(), 0);
    assert.equal(await page.evaluate(() => window.preparationAttack), undefined);
    await unknownAuthority();
    await page.screenshot({path: path.join(out, 'hostile-inert.png'), fullPage: true});
  });
  await check('unsupported credential field is rejected without rendering its contents', async () => {
    await page.getByRole('button', {name: 'Load invalid credential field', exact: true}).click();
    assert.equal(await page.locator('[data-state="UNKNOWN"]').count(), 8);
    assert(!(await page.locator('body').innerText()).includes('SYNTHETIC-SECRET-MUST-NOT-RENDER'));
    assert.equal(await page.getByLabel('Host', {exact: true}).inputValue(), '');
  });
  await check('normal clear removes observations and declarations', async () => {
    await page.getByRole('button', {name: 'Load reported snapshot', exact: true}).click();
    await page.getByRole('button', {name: 'Clear preparation', exact: true}).click();
    assert.equal(await page.locator('[data-state="UNKNOWN"]').count(), 8);
    assert.equal(await page.getByLabel('Worker', {exact: true}).inputValue(), '');
  });
  await check('reload does not restore previous identity or project state', async () => {
    await page.getByRole('button', {name: 'Load reported snapshot', exact: true}).click();
    assert.deepEqual(await page.evaluate(() => window.preparationEffects), []);
    assert.deepEqual(await page.evaluate(() => [localStorage.length, sessionStorage.length]), [0, 0]);
    await page.reload();
    await page.getByRole('heading', {name: 'Agent preparation', exact: true}).waitFor();
    assert.equal(await page.locator('[data-state="UNKNOWN"]').count(), 8);
    assert.equal(await page.getByLabel('Project', {exact: true}).inputValue(), '');
    await page.screenshot({path: path.join(out, 'reloaded-empty.png'), fullPage: true});
  });
  await check('all interactions stay local with zero persistence or network side effects', async () => {
    assert.deepEqual(violations, []);
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(await page.evaluate(() => window.preparationEffects), []);
    assert.deepEqual(await context.cookies(), []);
    assert.deepEqual(await page.evaluate(() => [localStorage.length, sessionStorage.length]), [0, 0]);
  });
  assert.equal(checks.length, 17);
}
main().catch(async error => {
  failure = String(error.stack || error);
  process.exitCode = 1;
  if (page) await page.screenshot({path: path.join(out, 'failure.png'), fullPage: true}).catch(() => {});
}).finally(async () => {
  const summary = {
    head: git('rev-parse', 'HEAD'), tree: git('rev-parse', 'HEAD^{tree}'),
    tracked_changes: git('diff', '--name-only', 'HEAD'), untracked_files: git('ls-files', '--others', '--exclude-standard'),
    run_id: process.env.GITHUB_RUN_ID || null, attempt: process.env.GITHUB_RUN_ATTEMPT || null,
    node: process.version, platform: process.platform, browser: browser ? browser.version() : null,
    interaction: 'normal Playwright click/fill; no force, DOM-dispatch or input injection',
    scope: 'synthetic standalone; not integrated; not native-qualified',
    checks, observations, passed: !failure && checks.length === 17, failure: failure || null, requests, violations, pageErrors,
    source_hashes: Object.fromEntries([...files, 'tests/agent-preparation.test.mjs', 'tests/agent-preparation-browser.cjs'].map(file => [file, hash(fs.readFileSync(path.join(root, file)))])),
    artifacts: Object.fromEntries(fs.readdirSync(out).filter(file => file.endsWith('.png')).map(file => [file, hash(fs.readFileSync(path.join(out, file)))])),
  };
  fs.writeFileSync(path.join(out, 'result.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(JSON.stringify(summary, null, 2));
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
});
