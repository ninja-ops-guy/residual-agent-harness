#!/usr/bin/env node
/**
 * RESIDUAL browser production-readiness runner.
 *
 * Fast, diagnostic-heavy browser qualification intended for a frozen RC.
 * It does not replace capable-runner M4, blank-VM, soak, physical-iPhone,
 * real-provider, or host-loss evidence. It rapidly catches browser/operator
 * regressions before those expensive gates are run.
 *
 * Usage:
 *   npm run test:readiness
 *   RESIDUAL_QA_URL=https://... npm run test:readiness
 *   RESIDUAL_QA_MODE=quick npm run test:readiness
 *
 * Outputs under runs/browser-readiness/<timestamp>/:
 *   report.json, summary.md, console.jsonl, network.jsonl, page-errors.jsonl,
 *   requests-failed.jsonl, snapshots/, screenshots/, traces/
 */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const out = process.env.RESIDUAL_QA_DIR || path.join(root, 'runs', 'browser-readiness', stamp);
const mode = process.env.RESIDUAL_QA_MODE || 'full';
const externalUrl = process.env.RESIDUAL_QA_URL || '';
const port = Number(process.env.RESIDUAL_QA_PORT || 8877);
const url = externalUrl || `http://127.0.0.1:${port}`;
const data = fs.mkdtempSync(path.join(os.tmpdir(), 'residual-readiness-'));
const started = Date.now();
fs.mkdirSync(out, {recursive:true});
for (const d of ['screenshots','snapshots','traces']) fs.mkdirSync(path.join(out,d), {recursive:true});

let server, browser, context, page;
const events = {console:[], pageErrors:[], requestsFailed:[], responses:[]};
const results = [];
const timings = {};
let stepStarted = 0;

function jsonl(name, row) {
  fs.appendFileSync(path.join(out, name), JSON.stringify({...row, at:new Date().toISOString()})+'\n');
}
function record(name, status, detail={}, ms=Date.now()-stepStarted) {
  const row={name,status,ms,...detail}; results.push(row); console.log(`[${status}] ${name} (${ms}ms)`);
  return row;
}
async function evidence(slug) {
  if (!page) return;
  try {
    await page.screenshot({path:path.join(out,'screenshots',slug+'.png'),fullPage:true});
    fs.writeFileSync(path.join(out,'snapshots',slug+'.html'), await page.content());
  } catch {}
}
async function gate(name, fn, {soft=false}={}) {
  stepStarted=Date.now();
  try { const detail=(await fn())||{}; return record(name,'PASS',detail); }
  catch (e) {
    await evidence('FAIL-'+name.toLowerCase().replace(/[^a-z0-9]+/g,'-'));
    const detail={error:e.message,stack:e.stack};
    record(name,soft?'WARN':'FAIL',detail);
    if (!soft) throw e;
  }
}
async function startStation() {
  if (externalUrl) return;
  server=spawn(process.env.PYTHON||'python3',['-m','residual.station.server','--port',String(port),'--data',data],
    {cwd:root,stdio:['ignore','pipe','pipe']});
  let stderr='';
  server.stderr.on('data',b=>{stderr+=b; jsonl('server-stderr.jsonl',{text:String(b)});});
  await new Promise((resolve,reject)=>{
    let text='';
    const timer=setTimeout(()=>reject(Error('Station startup timeout; stderr='+stderr.slice(-2000))),20000);
    server.stdout.on('data',b=>{text+=b;jsonl('server-stdout.jsonl',{text:String(b)});if(text.includes('Press Ctrl+C')){clearTimeout(timer);resolve();}});
    server.once('exit',code=>reject(Error('Station exited during startup: '+code)));
  });
}
function attachDiagnostics(p) {
  p.on('console',m=>{const row={type:m.type(),text:m.text(),url:p.url()};events.console.push(row);jsonl('console.jsonl',row);});
  p.on('pageerror',e=>{const row={message:e.message,stack:e.stack,url:p.url()};events.pageErrors.push(row);jsonl('page-errors.jsonl',row);});
  p.on('requestfailed',r=>{const row={url:r.url(),method:r.method(),failure:r.failure()};events.requestsFailed.push(row);jsonl('requests-failed.jsonl',row);});
  p.on('response',r=>{if(r.status()>=400){const row={url:r.url(),status:r.status(),method:r.request().method()};events.responses.push(row);jsonl('network.jsonl',row);}});
}
async function bootBrowser(viewport={width:1440,height:1040}) {
  browser=await chromium.launch({headless:process.env.HEADED!=='1',args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  context=await browser.newContext({viewport,recordVideo:process.env.RESIDUAL_QA_VIDEO==='1'?{dir:path.join(out,'traces')}:undefined});
  await context.tracing.start({screenshots:true,snapshots:true,sources:true});
  page=await context.newPage(); attachDiagnostics(page);
}
async function bootstrap() {
  const res=await page.request.get(url+'/api/bootstrap'); assert.equal(res.ok(),true,'/api/bootstrap not OK'); return res.json();
}
async function projects(token) {
  const res=await page.request.get(url+'/api/projects',{headers:{'X-Station-Token':token}}); assert.equal(res.ok(),true,'/api/projects not OK'); return res.json();
}
async function waitIntegrated(token) {
  await page.waitForFunction(async({base,token})=>{
    const r=await fetch(base+'/api/projects',{headers:{'X-Station-Token':token}}); if(!r.ok)return false;
    const b=await r.json(); return !!b.projects?.[0]?.tasks?.length && b.projects[0].tasks.every(t=>t.state==='integrated');
  },{base:url,token},{timeout:45000});
}
async function run() {
  await gate('station-startup',startStation);
  await gate('browser-startup',()=>bootBrowser());

  await gate('landing-render',async()=>{
    await page.goto(url,{waitUntil:'domcontentloaded'}); await page.getByRole('heading',{name:'Welcome to the night shift.'}).waitFor({timeout:15000});
    await evidence('01-landing'); return {url:page.url(),title:await page.title()};
  });

  const boot=await bootstrap();
  await gate('bootstrap-contract',async()=>{
    assert(boot.token,'bootstrap token absent');
    const p=await projects(boot.token); assert(Array.isArray(p.projects),'projects missing'); return {projects:p.projects.length};
  });

  await gate('training-mission-e2e',async()=>{
    await page.getByRole('button',{name:'▶ Run training mission',exact:true}).click();
    await waitIntegrated(boot.token); await page.locator('#main').click({position:{x:5,y:5}}); await page.waitForTimeout(800);
    return {state:'integrated'};
  });

  await gate('receipt-and-evidence-discoverability',async()=>{
    await page.locator('[data-view="board"]').click();
    await page.getByRole('button',{name:'Open run receipt',exact:true}).click();
    const body=page.locator('#dialog-body'); await body.waitFor();
    assert((await body.innerText()).includes('"outcome": "success"'),'success receipt absent');
    await page.getByRole('button',{name:'Close dialog',exact:true}).click();
    await page.locator('.task-card').first().click(); await page.locator('.receipt-hash').waitFor();
    assert((await page.locator('#dialog-body').innerText()).includes('Bound verification receipt'));
    await page.getByRole('button',{name:'Close dialog',exact:true}).click();
  });

  await gate('verified-release-export',async()=>{
    const download=page.waitForEvent('download'); await page.getByRole('button',{name:'Export verified release',exact:true}).click();
    const d=await download; assert(d.suggestedFilename().endsWith('.zip')); return {filename:d.suggestedFilename()};
  });

  await gate('xss-operator-note',async()=>{
    await page.locator('[data-view="comms"]').click(); const payload='<img src=x onerror=alert(1)> readiness';
    await page.locator('#note-message').fill(payload); await page.getByRole('button',{name:'Post ↗',exact:true}).click();
    await page.getByText(payload,{exact:true}).waitFor(); assert.equal(await page.locator('.message img').count(),0);
  });

  await gate('provider-secret-redaction',async()=>{
    await page.locator('[data-view="models"]').click(); await page.locator('#cloud-kind').selectOption('anthropic');
    await page.locator('#cloud-key').fill('READINESS-PRIVATE-KEY'); await page.getByRole('button',{name:'Save model routes',exact:true}).click();
    await page.reload(); await page.locator('#cloud-kind').waitFor(); assert.equal(await page.locator('#cloud-key').inputValue(),'');
    const raw=await page.evaluate(()=>fetch('/api/bootstrap').then(r=>r.text())); assert(!raw.includes('READINESS-PRIVATE-KEY'));
  });

  await gate('diagnostics-and-trace',async()=>{
    await page.locator('[data-view="diagnostics"]').click(); await page.getByRole('button',{name:'↻ Inspect',exact:true}).click();
    await page.getByText('SQLite WAL',{exact:true}).waitFor(); await page.getByRole('button',{name:'Inspect trace',exact:true}).click();
    await page.locator('#observation-summary').filter({hasText:'CHAIN VERIFIED'}).waitFor(); assert(await page.locator('.observation-row').count()>0);
    const download=page.waitForEvent('download'); await page.getByRole('button',{name:'Download JSONL',exact:true}).click();
    assert.equal((await download).suggestedFilename(),'observations.jsonl');
  });

  await gate('mobile-390-no-overflow',async()=>{
    await page.setViewportSize({width:390,height:844}); await page.goto(url+'/#overview'); await page.getByRole('heading',{name:'Welcome to the night shift.'}).waitFor();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'overview horizontal overflow');
    await page.locator('[data-view="board"]').click(); assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'board horizontal overflow');
    await evidence('02-mobile');
  });

  if (mode!=='quick') {
    await gate('reload-state-continuity',async()=>{
      await page.setViewportSize({width:1440,height:1040}); await page.reload({waitUntil:'domcontentloaded'});
      await page.getByRole('heading',{name:'Welcome to the night shift.'}).waitFor();
      await page.locator('[data-view="board"]').click(); assert(await page.locator('.task-card').count()>0);
    });
    await gate('ui-repair-actions-are-actionable',async()=>{
      // Production-readiness audit: visible controls must not be disabled/no-op anchors.
      const bad=await page.evaluate(()=>[...document.querySelectorAll('button,a')].filter(el=>{
        const t=(el.textContent||'').trim().toLowerCase();
        const repair=/repair|retry|restart|recover|resume|triage|fix/.test(t);
        return repair && (el.disabled || el.getAttribute('aria-disabled')==='true' || (el.tagName==='A' && !el.getAttribute('href')));
      }).map(el=>(el.textContent||'').trim()));
      assert.deepEqual(bad,[], 'non-actionable repair controls: '+bad.join(', ')); return {inspected:true};
    });
  }

  await gate('browser-error-budget',async()=>{
    const consoleErrors=events.console.filter(x=>x.type==='error' && !x.text.includes('400 (Bad Request)'));
    assert.deepEqual(events.pageErrors,[],'page errors present');
    assert.deepEqual(consoleErrors,[],'console errors present');
    assert.deepEqual(events.requestsFailed,[],'failed requests present');
    return {consoleErrors:0,pageErrors:0,requestFailures:0,http4xx5xx:events.responses.length};
  });

  await evidence('03-final');
}
async function finalize(error) {
  try { if(context) await context.tracing.stop({path:path.join(out,'traces','playwright-trace.zip')}); } catch {}
  try { if(browser) await browser.close(); } catch {}
  try { if(server) server.kill('SIGTERM'); } catch {}
  try { fs.rmSync(data,{recursive:true,force:true}); } catch {}
  const failed=results.filter(r=>r.status==='FAIL');
  const report={
    schema:'residual.browser-readiness.v1', passed:!error && failed.length===0, mode, target:url,
    revision:process.env.RESIDUAL_QA_REVISION||process.env.GITHUB_SHA||'UNKNOWN',
    started_at:new Date(started).toISOString(), elapsed_ms:Date.now()-started,
    gates:results, diagnostics:{console:events.console.length,page_errors:events.pageErrors.length,request_failures:events.requestsFailed.length,http_errors:events.responses.length},
    limitations:[
      'Does not replace capable-runner M4 qualification.',
      'Does not replace true blank-VM install/reinstall/upgrade evidence.',
      'Does not replace elapsed soak or host-loss/recovery evidence.',
      'Does not prove physical iPhone/Safari behavior from Chromium.',
      'Does not prove paid/live provider semantic success without a real-account run.'
    ],
    error:error?{message:error.message,stack:error.stack}:null
  };
  fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));
  const lines=['# RESIDUAL Browser Readiness','',`Target: ${url}`,`Revision: ${report.revision}`,`Mode: ${mode}`,`Result: **${report.passed?'PASS':'FAIL'}**`,'','| Gate | Result | ms |','|---|---:|---:|',
    ...results.map(r=>`| ${r.name} | ${r.status} | ${r.ms} |`),'','## Diagnostics',`- Console events: ${events.console.length}`,`- Page errors: ${events.pageErrors.length}`,`- Failed requests: ${events.requestsFailed.length}`,`- HTTP >=400 responses: ${events.responses.length}`,'','## Non-claims',...report.limitations.map(x=>'- '+x)];
  fs.writeFileSync(path.join(out,'summary.md'),lines.join('\n')+'\n');
  console.log('\nEvidence: '+out); console.log('Result: '+(report.passed?'PASS':'FAIL'));
  if (!report.passed) process.exitCode=1;
}
run().then(()=>finalize()).catch(async e=>{console.error(e);await finalize(e);});
