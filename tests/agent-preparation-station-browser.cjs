// Real disposable Station, synthetic declarations; no providers or native agents.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {spawn,execFileSync}=require('node:child_process');
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const out=path.resolve('runs/agent-preparation-station');fs.mkdirSync(out,{recursive:true});
const report={head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),checks:[],requests:[],errors:[]};
const station=spawn(process.env.PYTHON || 'python',['-u','-c',`
import tempfile
from residual.station.service import Station
from residual.station.server import Server
with tempfile.TemporaryDirectory() as d:
 s=Server(('127.0.0.1',0),Station(d))
 print(s.server_port,flush=True)
 try: s.serve_forever()
 finally: s.server_close()
`]);
let browser;
async function check(name,fn){await fn();report.checks.push(name);}
(async()=>{
 const port=await new Promise((resolve,reject)=>{station.stdout.once('data',b=>resolve(Number(b.toString().trim())));station.once('exit',c=>reject(Error('Station exited '+c)));station.stderr.on('data',b=>process.stderr.write(b));});
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1280,height:1000}});
 page.on('pageerror',e=>report.errors.push(String(e)));
 page.on('request',r=>report.requests.push({method:r.method(),path:new URL(r.url()).pathname}));
 const url=`http://127.0.0.1:${port}`;
 await page.goto(url);await page.locator('[data-view="preparation"]').click();
 const rows=page.locator('[data-stage]');
 async function unknown(){await rows.first().waitFor();assert.equal(await rows.count(),8);for(const id of ['enrollment','eligibility','acceptance','connectivity'])assert.equal(await page.locator(`[data-stage="${id}"]`).getAttribute('data-state'),'UNKNOWN');}
 await check('normal navigation mounts eight stages without authority',unknown);
 await check('review declarations stays read-only',async()=>{await page.locator('[name="worker_id"]').fill('synthetic-worker');await page.getByRole('button',{name:'Review declarations'}).click();await unknown();assert.equal(await page.locator('[data-stage="identity"]').getAttribute('data-state'),'DECLARED');});
 await page.screenshot({path:path.join(out,'station-preparation.png'),fullPage:true});
 await check('leaving and reentering discards declarations',async()=>{await page.locator('[data-view="diagnostics"]').click();await page.locator('[data-view="preparation"]').click();await unknown();assert.equal(await page.locator('[name="worker_id"]').inputValue(),'');});
 await check('clear and reload retain no preparation state',async()=>{await page.locator('[name="worker_id"]').fill('temporary');await page.getByRole('button',{name:'Clear preparation'}).click();assert.equal(await page.locator('[name="worker_id"]').inputValue(),'');await page.reload();await unknown();assert.equal(await page.locator('[name="worker_id"]').inputValue(),'');assert.deepEqual(await page.evaluate(()=>Object.keys(localStorage)),[]);});
 await check('compact viewport supports normal interactions',async()=>{await page.setViewportSize({width:390,height:844});await page.locator('[name="worker_id"]').fill('compact');await page.getByRole('button',{name:'Review declarations'}).click();await unknown();await page.screenshot({path:path.join(out,'station-preparation-compact.png'),fullPage:true});});
 await check('no mutating requests or page errors',async()=>{assert(report.requests.every(r=>r.method==='GET'));assert.deepEqual(report.errors,[]);});
 report.passed=true;
})().catch(e=>{report.passed=false;report.failure=String(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();station.kill();fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));});
