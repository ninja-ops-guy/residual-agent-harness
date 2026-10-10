/* Real Mission Control + local Python Harness audit; no remote provider or WASM claim. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),http=require('node:http');
const assert=require('node:assert/strict');const {spawnSync}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),out=process.env.TIMETRAVEL_QA_DIR||path.join(root,'runs/browser/time-travel');
fs.mkdirSync(out,{recursive:true});const temp=fs.mkdtempSync(path.join(os.tmpdir(),'residual-tt-'));
const checks=[],errors=[],external=[];let browser;const calls={run:0,mailbox:0,restart:0};
const python=`import sys,json,base64\nfrom pathlib import Path\nfrom residual.workbench.runner import execute\nr=json.load(sys.stdin)\nframes=[]\nresult=execute(r,root=Path(sys.argv[1]),output_root=Path(sys.argv[2]),observer=frames.append)\nassert result['verification']['result_bound'] and not result['simulation']\nassert result['result']['metrics']['calls']==0\nstream=''.join('\\x1b]777;RESIDUAL;'+base64.b64encode(json.dumps(f).encode()).decode()+'\\x07' for f in frames)\nprint(json.dumps({'stream':stream,'status':result['status'],'evidence_count':len([f for f in frames if f['kind']=='evidence']),'result_bound':True}))`;
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><script type="module">
import {mountMissionControl,getDemoDiagnostics} from '/demo/vm/mission-control-diagnostics.js';
window.hostCalls={run:0,mailbox:0,restart:0};
window.app=mountMissionControl({ready:()=>true,health:()=> 'ready',focus:()=>{},restart:()=>{hostCalls.restart++},mailbox:()=>{hostCalls.mailbox++;throw Error('Unexpected provider call')},run:async request=>{hostCalls.run++;const response=await fetch('/audit',{method:'POST',body:JSON.stringify(request)});if(!response.ok)throw Error(await response.text());const result=await response.json();window.audit=result;for(let i=0;i<result.stream.length;i+=17)app.onOutput(result.stream.slice(i,i+17));return {status:result.status}}});window.diag=getDemoDiagnostics();window.ready=true;
</script></body></html>`;
const server=http.createServer((req,res)=>{
  if(req.url==='/audit'&&req.method==='POST'){let body='';req.on('data',b=>body+=b);req.on('end',()=>{calls.run++;const result=spawnSync(process.env.PYTHON||'python3',['-c',python,root,temp],{cwd:root,input:body,encoding:'utf8'});res.writeHead(result.status===0?200:500,{'Content-Type':'application/json'});res.end(result.status===0?result.stdout:result.stderr)});return;}
  if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end(html);return;}
  if(req.url==='/build-info.json'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({commit:'local-qualification',webvm_commit:null}));return;}
  const filename=path.resolve(root,'.'+req.url.split('?')[0]);
  if(!filename.startsWith(path.join(root,'demo/vm')+path.sep)||!fs.existsSync(filename)){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':filename.endsWith('.webp')?'image/webp':'text/javascript'});fs.createReadStream(filename).pipe(res);
});
async function main(){
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url=`http://127.0.0.1:${server.address().port}`;
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  const page=await browser.newPage({viewport:{width:1536,height:1100}});page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{if(!route.request().url().startsWith(url)){external.push(route.request().url());return route.abort()}return route.continue()});
  await page.goto(url);await page.waitForFunction(()=>window.ready);
  await page.getByRole('button',{name:'🚗 Time Travel',exact:true}).click();
  await page.getByRole('button',{name:'Chat',exact:true}).click();
  await page.getByText('Run controls',{exact:true}).click();await page.locator('#mc-mode').selectOption('audit');await page.locator('#mc-prompt').fill('Time travel qualification: inventory README');
  await page.locator('#mc-run').click();await page.waitForFunction(()=>window.audit&&window.diag.buffer.events.some(e=>e.event_type==='mission.host_run_completed'));
  assert.equal(await page.evaluate(()=>audit.result_bound),true);
  await page.getByRole('button',{name:'🚗 Time Travel',exact:true}).click();
  const run=await page.evaluate(()=>diag.latestRunId);await page.getByLabel('Time travel scope').selectOption(run);
  const position=page.locator('.tt-position');const snapshot=page.locator('.tt-side .tt-card').first();
  assert.match(await snapshot.innerText(),/passed/);
  const evidenceCount=await page.evaluate(()=>audit.evidence_count);assert(evidenceCount>0);assert.match(await snapshot.innerText(),new RegExp('Evidence\\s+'+evidenceCount));
  checks.push('Real Python Harness audit: bound result, zero provider calls, chunked output projected into Mission Control and debugger');
  await page.getByRole('button',{name:'|◀ FIRST',exact:true}).click();assert.match(await position.innerText(),/EVENT 1 \/ /);assert.match(await snapshot.innerText(),/submitted/);
  await page.getByRole('button',{name:'STEP ▶',exact:true}).click();assert.match(await position.innerText(),/EVENT 2 \/ /);await page.getByRole('button',{name:'◀ STEP',exact:true}).click();assert.match(await position.innerText(),/EVENT 1 \/ /);
  const slider=page.getByLabel('Historical event position');await slider.focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('Tab');assert.match(await position.innerText(),/EVENT 2 \/ /);
  await page.getByRole('button',{name:'◆ JUMP TO EVIDENCE',exact:true}).click();assert.match(await snapshot.innerText(),/evidence.projected/);
  await page.getByRole('button',{name:'LAST ▶|',exact:true}).click();await page.locator('.tt-log button').first().click();assert.match(await position.innerText(),/EVENT 1 \/ /);
  checks.push('First/last/step, keyboard scrubber, evidence jump and event log select real recorded events');
  const before=await page.evaluate(()=>JSON.stringify(diag.buffer.snapshot()));const effects=await page.evaluate(()=>JSON.stringify(hostCalls));
  await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();assert.match(await position.innerText(),/EVENT 1 \/ /);
  assert.equal(await page.evaluate(()=>JSON.stringify(diag.buffer.snapshot())),before);assert.equal(await page.evaluate(()=>JSON.stringify(hostCalls)),effects);
  assert(await page.getByRole('button',{name:'FORK HERE · UNAVAILABLE',exact:true}).isDisabled());checks.push('Inspection and refresh preserve retained diagnostics and cause zero execution/mailbox/restart side effects');
  await page.getByRole('button',{name:'Chat',exact:true}).click();await page.getByText('Run controls',{exact:true}).click();await page.locator('#mc-files').fill('unknown');await page.locator('#mc-prompt').fill('Expected invalid-source failure');await page.locator('#mc-run').click();await page.waitForFunction(()=>diag.buffer.events.some(e=>e.event_type==='mission.host_run_failed'));
  await page.locator('#mc-timetravel').click();await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();await page.getByLabel('Time travel scope').selectOption(await page.evaluate(()=>diag.latestRunId));await page.getByRole('button',{name:'⚠ JUMP TO FAILURE',exact:true}).click();assert.match(await snapshot.innerText(),/mission.host_run_failed/);assert.match(await snapshot.innerText(),/failed/);
  checks.push('Real rejected source request produces inspectable failed host run without false completion');
  await page.evaluate(()=>{window.secondMission='m-'+'b'.repeat(32);const rid=diag.startRun(secondMission,'audit');diag.emit('evidence.projected',{evidence_kind:'counterexample',sequence:1},{run_id:rid,mission_id:secondMission});diag.emit('mission.finished',{status:'failed',failure_code:'schema_failure'},{run_id:rid,mission_id:secondMission,severity:'warn'});});
  const second=await page.evaluate(()=>diag.latestRunId);await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();await page.getByLabel('Time travel scope').selectOption(second);
  await page.getByRole('button',{name:'⚠ JUMP TO FAILURE',exact:true}).click();assert.match(await snapshot.innerText(),/evidence.projected/);
  await page.getByLabel('Time travel scope').selectOption('');await page.getByRole('button',{name:'LAST ▶|',exact:true}).click();assert.match(await snapshot.innerText(),/schema_failure/);
  await page.getByLabel('Time travel scope').selectOption(run);await page.getByRole('button',{name:'LAST ▶|',exact:true}).click();assert.match(await snapshot.innerText(),/passed/);assert.doesNotMatch(await snapshot.innerText(),/schema_failure/);
  checks.push('Explicit negative fixture: counterexample jump and independent run/session scope isolation');
  for(const name of ['Chat','Activity','Evidence','Files','Terminal']){await page.locator(`[data-tab="${{Chat:'chat',Activity:'activity',Evidence:'evidence',Files:'files',Terminal:'terminal'}[name]}"]`).click();assert(await page.locator('#mc-timetravel-panel').isHidden());await page.locator('#mc-timetravel').click();assert(await page.locator('#mc-timetravel-panel').isVisible())}
  checks.push('All Mission Control tabs remain symmetric with debugger navigation');
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  for(const width of [768,390]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert(await page.locator('#mc-timetravel-panel').evaluate(el=>el.scrollWidth<=el.clientWidth));await page.screenshot({path:path.join(out,`width-${width}.png`),fullPage:true})}
  checks.push('Desktop/tablet/mobile render without horizontal overflow');
  await page.setViewportSize({width:1536,height:1100});
  await page.getByLabel('Time travel scope').selectOption('');
  await page.evaluate(()=>{window.xssExecuted=false;diag.emit('ui.state_changed',{stage:'test',status:'<img src=x onerror=window.xssExecuted=true>',prompt:'PRIVATE_PROMPT_DO_NOT_SHOW'});});
  await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();await page.getByRole('button',{name:'LAST ▶|',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.xssExecuted),false);assert.equal(await page.locator('#mc-timetravel-panel img').count(),1);assert.doesNotMatch(await page.locator('#mc-timetravel-panel').innerText(),/PRIVATE_PROMPT_DO_NOT_SHOW/);
  checks.push('Untrusted event text stays inert and disallowed prompt content never reaches the view');
  await page.evaluate(()=>{const sample=diag.buffer.snapshot()[0];diag.buffer.events=Array.from({length:5000},(_,i)=>({...sample,event_id:'evt_'+i,event_type:'evidence.projected',run_id:null,timestamp:new Date(1700000000000+i).toISOString(),monotonic_ms:i,context:{sequence:i,evidence_kind:'verification'}}))});
  const start=Date.now();await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();assert.equal(await page.locator('.tt-log button').count(),5000);assert(Date.now()-start<10000,'5000 event render exceeded 10 seconds');
  await page.getByRole('button',{name:'|◀ FIRST',exact:true}).click();await page.evaluate(()=>diag.emit('session.started',{status:'new'}));await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();assert.match(await position.innerText(),/EVENT 5000 \/ 5000/);
  checks.push('Bounded 5000-event history renders; eviction recovers selection without out-of-range state');
  await page.evaluate(()=>{diag.buffer.events=[]});await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();await page.getByLabel('Time travel scope').selectOption('');assert(await page.getByLabel('Historical event position').isDisabled());assert.match(await page.locator('.tt-empty').innerText(),/No sanitized/);
  await page.evaluate(()=>diag.startRun('m-'+'c'.repeat(32),'audit'));await page.getByRole('button',{name:'REFRESH HISTORY',exact:true}).click();assert.match(await position.innerText(),/EVENT 1 \/ 1/);
  await page.evaluate(()=>app.destroy());assert.equal(await page.locator('#mission-control').count(),0);checks.push('Empty/evicted history can recover and full Mission Control teardown removes debugger');
  assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(calls.run,2);
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:true,browser:await browser.version(),checks,errors,external,scope:'native local Harness + browser; no WASM runtime or paid provider qualification'},null,2));console.log(JSON.stringify({passed:true,checks},null,2));
}
main().catch(e=>{console.error(e);fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:false,checks,errors,error:e.stack},null,2));process.exitCode=1}).finally(async()=>{await browser?.close();server.close();fs.rmSync(temp,{recursive:true,force:true})});
