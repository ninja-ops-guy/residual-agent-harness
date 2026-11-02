/* Synthetic sessionStorage only; validates real Chromium reloads and downloaded bytes. */
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const assert=require('node:assert/strict'),{createHash}=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const source=path.resolve(process.env.DIAGNOSTIC_SOURCE_ROOT||path.join(__dirname,'..'));
const out=path.resolve(process.env.DIAGNOSTIC_QA_DIR||path.join(source,'runs/browser/time-travel/diagnostic-restore'));
fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],external=[],downloads=[];let browser,page;
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function check(name,fn){try{fn();checks.push({name,passed:true});}catch(error){checks.push({name,passed:false,error:error.message});}}
// A local DOM-event run qualifies data paths only; default CI retains normal click checks.
async function inspectClick(locator){if(process.env.DIAGNOSTIC_DOM_EVENTS==='1')await locator.dispatchEvent('click');else await locator.click();}
const html=`<!doctype html><html><body><script type="module">
import {mountMissionControl,getDemoDiagnostics} from '/demo/vm/mission-control-diagnostics.js';
window.effects={run:0,mailbox:0,restart:0};
window.app=mountMissionControl({ready:()=>true,health:()=> 'ready',focus:()=>{},
  run(){effects.run++;throw Error('Unexpected execution')},mailbox(){effects.mailbox++;throw Error('Unexpected mailbox')},restart(){effects.restart++;throw Error('Unexpected restart')}});
window.diag=getDemoDiagnostics();window.ready=true;
</script></body></html>`;
const server=http.createServer((req,res)=>{
  if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end(html);return;}
  if(req.url==='/build-info.json'){res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify({commit:'synthetic-offline-review',webvm_commit:null}));return;}
  const filename=path.resolve(source,'.'+req.url.split('?')[0]);
  if(!filename.startsWith(path.join(source,'demo/vm')+path.sep)||!fs.existsSync(filename)||!fs.statSync(filename).isFile()){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':filename.endsWith('.webp')?'image/webp':filename.endsWith('.svg')?'image/svg+xml':'text/javascript'});fs.createReadStream(filename).pipe(res);
});
async function download(page,name){
  const [item]=await Promise.all([page.waitForEvent('download'),inspectClick(page.locator('#mc-diagnostics'))]);
  const filename=path.join(out,name+'.json');await item.saveAs(filename);
  const raw=fs.readFileSync(filename);downloads.push({file:path.basename(filename),bytes:raw.length,sha256:hash(raw)});
  return {raw:raw.toString('utf8'),json:JSON.parse(raw)};
}
async function ready(page){await page.waitForFunction(()=>window.ready&&diag.buffer.snapshot().some(e=>e.event_type==='environment.probed'));}
async function seedReload(page,sessionId,envelope){
  // Seed before the next document constructs diagnostics; old-page lifecycle writes cannot race it.
  await page.evaluate(seed=>{window.name='diagnostic-test-seed:'+JSON.stringify(seed);},{sessionId,envelope});
  await page.reload();await ready(page);
}
async function main(){
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}`;
  browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--disable-dev-shm-usage','--disable-gpu']});
  page=await browser.newPage({acceptDownloads:true,viewport:{width:1200,height:900}});
  page.setDefaultTimeout(15000);
  await page.addInitScript(()=>{
    const prefix='diagnostic-test-seed:';
    if(window.name.startsWith(prefix)){
      const seed=JSON.parse(window.name.slice(prefix.length));window.name='';
      sessionStorage.setItem('residual.demo.diagnostic.session.v1',seed.sessionId);
      sessionStorage.setItem('residual.demo.diagnostic.buffer.v1',JSON.stringify(seed.envelope));
    }
  });
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',route=>{if(!route.request().url().startsWith(origin+'/')){external.push(route.request().url());return route.abort();}return route.continue();});
  await page.goto(origin);await ready(page);
  const fixture=process.env.DIAGNOSTIC_FIXTURE_PATH?JSON.parse(fs.readFileSync(process.env.DIAGNOSTIC_FIXTURE_PATH,'utf8')):await page.evaluate(()=>{
    const mission='m-'+'a'.repeat(32),run=diag.startRun(mission,'audit');
    const valid=diag.emit('evidence.projected',{sequence:1,evidence_kind:'verification'},{mission_id:mission,run_id:run});
    const row=structuredClone(valid);
    row.prompt='EXCLUDED_TOP';row.trace_id='EXCLUDED_TRACE';row.component='EXCLUDED_COMPONENT';
    row.context={sequence:1,evidence_kind:'verification',prompt:'EXCLUDED_PROMPT',authorization:'Bearer EXCLUDED_CREDENTIAL',error_message:'漢'.repeat(2000),model:'漢'.repeat(1000)};
    row.release.private='EXCLUDED_RELEASE';row.diagnostic={failure_class:'EXCLUDED_CLASS',recoverable:true,raw:'EXCLUDED_DIAGNOSTIC'};
    const foreign={...structuredClone(valid),event_id:'evt_deadbeef',session_id:'ses_deadbeef',context:{status:'EXCLUDED_FOREIGN'}};
    const malformed={...structuredClone(valid),event_id:'evt_bad',event_type:'invalid type',context:{status:'EXCLUDED_MALFORMED'}};
    const envelope={session_id:diag.sessionId,events:[foreign,malformed,row]};
    return {envelope,valid};
  });
  fs.writeFileSync(path.join(out,'synthetic-storage-fixture.json'),JSON.stringify(fixture,null,2));
  await seedReload(page,fixture.envelope.session_id,fixture.envelope);
  const restored=await page.evaluate(()=>({events:diag.buffer.snapshot(),latest:diag.latestRunId,stored:sessionStorage.getItem('residual.demo.diagnostic.buffer.v1')}));
  fs.writeFileSync(path.join(out,'restored-observation.json'),JSON.stringify(restored,null,2));
  check('reload sanitizes restored fields and persistent copy',()=>{assert(!JSON.stringify(restored.events).includes('EXCLUDED_'));assert(!restored.stored.includes('EXCLUDED_'));});
  check('reload preserves valid historical identity without current execution grants',()=>{
    const event=restored.events.find(e=>e.event_id===fixture.valid.event_id);assert(event);
    for(const field of ['event_id','timestamp','run_id','mission_id'])assert.equal(event[field],fixture.valid[field]);
    assert.equal(restored.latest,fixture.valid.run_id);
  });
  check('foreign inner session and malformed records never enter restored history',()=>{assert(!restored.events.some(e=>['evt_deadbeef','evt_bad'].includes(e.event_id)));});
  check('restored string values retain existing limits',()=>{
    const event=restored.events.find(e=>e.event_id===fixture.valid.event_id);
    assert.equal(event.context.error_message.length,240);assert.equal(event.context.model.length,120);
  });
  await inspectClick(page.locator('#mc-timetravel'));await inspectClick(page.getByRole('button',{name:'REFRESH HISTORY',exact:true}));
  const panelText=await page.locator('#mc-timetravel-panel').innerText();
  check('actual browser details remain sanitized',()=>assert(!panelText.includes('EXCLUDED_')));
  await page.evaluate(()=>{
    const row=diag.buffer.events.find(e=>e.event_type==='evidence.projected');
    row.context.prompt='EXCLUDED_MEMORY';row.private='EXCLUDED_MEMORY_TOP';
    diag.environment.private='EXCLUDED_ENV';diag.release.private='EXCLUDED_MANIFEST';
  });
  const downloaded=await download(page,'current-session-download');
  check('actual downloaded bytes re-sanitize mutated memory and restored fields',()=>assert(!downloaded.raw.includes('EXCLUDED_')));
  check('download remains current-session scoped and explicitly non-authoritative',()=>{
    assert.equal(downloaded.json.manifest.session_id,fixture.envelope.session_id);
    assert.equal(downloaded.json.manifest.run_id,fixture.valid.run_id);
    assert.equal(downloaded.json.manifest.authoritative_execution_evidence,false);
    assert(downloaded.json.events.every(e=>e.session_id===fixture.envelope.session_id));
  });
  const bounds=await page.evaluate(()=>{
    const template=diag.buffer.events.find(e=>e.event_type==='evidence.projected');
    const keys=['browser','error_name','execution','failure_code','from','health','message_kind','mode','model','platform','run_status','stage','status','to','visibility'];
    const context=Object.fromEntries(keys.map(key=>[key,'漢'.repeat(120)]));context.error_message='漢'.repeat(240);
    diag.buffer.events=Array.from({length:600},(_,i)=>({...template,event_id:'evt_'+i.toString(16),context}));diag.persist();
    const raw=sessionStorage.getItem('residual.demo.diagnostic.buffer.v1');
    return {code_units:raw.length,utf8_bytes:new TextEncoder().encode(raw).length,events:JSON.parse(raw).events.length};
  });
  check('multibyte persistence obeys existing code-unit policy without claiming byte equivalence',()=>{assert(bounds.code_units<=1048576);assert(bounds.utf8_bytes>bounds.code_units);assert(bounds.events<600);});
  await seedReload(page,'ses_cccccccc',fixture.envelope);
  const switched=await download(page,'new-session-download');
  check('another browser session rejects the previous envelope and exported records',()=>{
    assert.equal(switched.json.manifest.session_id,'ses_cccccccc');assert.equal(switched.json.manifest.run_id,null);
    assert(!switched.raw.includes(fixture.valid.event_id));assert(!switched.raw.includes('EXCLUDED_'));
    assert(switched.json.events.every(e=>e.session_id==='ses_cccccccc'));
  });
  const effects=await page.evaluate(()=>effects);
  check('inspection performs no execution/mailbox/restart operations',()=>assert.deepEqual(effects,{run:0,mailbox:0,restart:0}));
  check('no page errors or external network requests',()=>{assert.deepEqual(errors,[]);assert.deepEqual(external,[]);});
  const sourceFiles=['demo/vm/mission-control-diagnostics.js','demo/vm/mission-control-timetravel.js','docs/TIME_TRAVEL_DEBUG.md'];
  const report={passed:checks.every(c=>c.passed),browser:browser.version(),source,
    interaction:process.env.DIAGNOSTIC_DOM_EVENTS==='1'?'DOM-dispatched inspection events; no rendered-click or screenshot qualification':'normal browser clicks',
    fixture_sha256:hash(fs.readFileSync(path.join(out,'synthetic-storage-fixture.json'))),
    source_hashes:Object.fromEntries(sourceFiles.map(file=>[file,hash(fs.readFileSync(path.join(source,file)))])),
    test_sha256:hash(fs.readFileSync(__filename)),checks,bounds,downloads,errors,external,effects,
    scope:'Real Chromium with synthetic local storage and actual download bytes; no live user profile, provider, native or execution-authority qualification'};
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));assert(report.passed,'diagnostic restore/export browser regression failed');
}
main().catch(async error=>{
  console.error(error);process.exitCode=1;
  if(page){try{await page.screenshot({path:path.join(out,'failure.png'),timeout:5000});}catch{}
    try{fs.writeFileSync(path.join(out,'failure-dom.json'),JSON.stringify(await page.evaluate(()=>({
      ready:window.ready,tab:document.querySelector('#mc-timetravel')?.outerHTML,
      bounds:document.querySelector('#mc-timetravel')?.getBoundingClientRect().toJSON(),body:document.body.innerText.slice(0,2000)})),null,2));}catch{}}
}).finally(async()=>{
  if(browser)await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);
  server.closeAllConnections();server.close();process.exit(process.exitCode||0);
});
