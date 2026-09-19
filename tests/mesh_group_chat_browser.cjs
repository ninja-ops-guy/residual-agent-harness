/* Focused browser onboarding qualification for setup + Shared Comms. */
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const data=fs.mkdtempSync(path.join(os.tmpdir(),'residual-onboarding-'));
const out=process.env.STATION_QA_DIR||path.join(root,'runs','browser');fs.mkdirSync(out,{recursive:true});
const port=Number(process.env.STATION_ONBOARDING_PORT||8877),url='http://127.0.0.1:'+port;
const server=spawn(process.env.PYTHON||'python3',['-m','residual.station.server','--port',String(port),'--data',data],{cwd:root,stdio:['ignore','pipe','pipe']});
const checks=[],errors=[];let browser;
async function waitServer(){await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(Error('Server startup timeout')),15000);server.stdout.on('data',b=>{text+=b;if(text.includes('Press Ctrl+C')){clearTimeout(timer);resolve();}});server.once('exit',code=>reject(Error('Server exited '+code)));});}
async function main(){
  await waitServer();
  browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']});
  const context=await browser.newContext({viewport:{width:1280,height:900}}),page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('400 (Bad Request)'))errors.push(m.text());});
  const pagesBefore=context.pages().length;
  await page.goto(url);
  await page.getByRole('heading',{name:'Welcome to the night shift.'}).waitFor();
  assert.equal(context.pages().length,pagesBefore);
  checks.push('Fresh station boots without popup onboarding');

  await page.getByRole('button',{name:'Open setup checklist',exact:true}).click();
  await page.getByRole('heading',{name:'Ready for your first shift?'}).waitFor();
  assert.equal(await page.locator('.setup-step').count(),4);
  for(const text of ['Test the workflow','Power up a local model','Connect cloud support','Import your specification']) assert((await page.locator('#dialog-body').innerText()).includes(text));
  assert.equal(context.pages().length,pagesBefore);
  checks.push('Setup checklist presents all four onboarding steps in-place');
  await page.screenshot({path:path.join(out,'mesh-onboarding-01-checklist.png'),fullPage:true});

  await page.getByRole('button',{name:'Run training',exact:true}).click();
  await page.waitForFunction(async()=>{const b=await fetch('/api/bootstrap').then(r=>r.json());const p=await fetch('/api/projects',{headers:{'X-Station-Token':b.token}}).then(r=>r.json());return p.projects[0]?.tasks?.every(t=>t.state==='integrated');},{},{timeout:45000});
  await page.waitForTimeout(800);
  checks.push('Training mission launches from onboarding and reaches integrated state');

  await page.locator('[data-view="comms"]').click();
  await page.getByRole('heading',{name:'Keep everyone in sync.'}).waitFor();
  const commsText=await page.locator('#main').innerText();
  assert(commsText.includes('SHARED EVENT LOG'));
  assert(commsText.includes('The chat displays recorded activity'));
  assert(commsText.includes('Agents receive task-specific context and report deltas'));
  checks.push('Shared Comms truthfully presents event-log/scoped-delivery semantics');

  const note='<img src=x onerror=alert(1)> onboarding hello';
  await page.locator('#note-message').fill(note);
  await page.getByRole('button',{name:'Post ↗',exact:true}).click();
  await page.getByText(note,{exact:true}).waitFor();
  assert.equal(await page.locator('.message img').count(),0);
  checks.push('First operator message is acknowledged, persisted and rendered as inert text');
  await page.screenshot({path:path.join(out,'mesh-onboarding-02-shared-comms.png'),fullPage:true});

  await page.reload();
  await page.locator('[data-view="comms"]').click();
  await page.getByText(note,{exact:true}).waitFor();
  assert.equal(await page.locator('.message img').count(),0);
  checks.push('Shared Comms survives reload with operator message intact');

  assert.deepEqual(errors,[]);
  const result={passed:true,checks,errors,separation_note:'Shared Comms is a Station event log; residual.mesh is separately qualified by Python onboarding tests.'};
  fs.writeFileSync(path.join(out,'mesh-onboarding-results.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result,null,2));
}
main().catch(e=>{console.error(e);fs.writeFileSync(path.join(out,'mesh-onboarding-results.json'),JSON.stringify({passed:false,checks,error:e.message,errors},null,2));process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();server.kill('SIGTERM');try{fs.rmSync(data,{recursive:true,force:true});}catch{}});
