const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright');

const root=path.resolve(__dirname,'../..');
const data=fs.mkdtempSync(path.join(os.tmpdir(),'residual-adversarial-ui-'));
const out=process.env.STATION_QA_DIR||path.join(root,'runs','qualification-v1','adversarial-browser');
fs.mkdirSync(out,{recursive:true});
const stationPort=Number(process.env.STATION_QA_PORT||8891);
const providerPort=Number(process.env.TOXIC_PROVIDER_PORT||8892);
const stationUrl=`http://127.0.0.1:${stationPort}`;

const draft='# Generated qualification mission\n\nA real persisted planner result.\n\n```json\n'+JSON.stringify({
  schema_version:1,name:'Generated QA Mission',goal:'Exercise persisted asynchronous planning',
  tasks:[{id:'QA-1',title:'Write marker',instruction:'Write a marker file',files:['marker.txt'],context:[],depends_on:[],route:'local',checks:[{kind:'contains',path:'marker.txt',text:'ready'}]}]
},null,2)+'\n```';

function responseFor(body){
  const messages=body.messages||[];
  const system=messages.filter(m=>m.role==='system').map(m=>m.content||'').join('\n');
  if(system.includes('Write a Markdown implementation specification')) return draft;
  if(system.includes('Implement the assigned software specification')){
    let packet={};
    try{ packet=JSON.parse(messages.find(m=>m.role==='user')?.content||'{}'); }catch{}
    const id=packet?.task?.id||packet?.id;
    if(id==='OPS-101') return JSON.stringify({files:{'station/health.py':"def status(services):\n    return 'ready' if services and all(services.values()) else 'degraded'\n"}});
    return JSON.stringify({files:{'marker.txt':'ready\n'}});
  }
  if(system.toLowerCase().includes('review')) return JSON.stringify({approved:true,findings:[]});
  return 'Station online.';
}

const provider=http.createServer((req,res)=>{
  let raw='';req.on('data',b=>raw+=b);req.on('end',()=>{
    let body={};try{body=JSON.parse(raw||'{}')}catch{}
    if(!req.url.endsWith('/chat/completions')){res.writeHead(404);return res.end();}
    const payload=JSON.stringify({
      id:'qa-provider',model:body.model||'qa-model',
      choices:[{message:{role:'assistant',content:responseFor(body)},finish_reason:'stop'}],
      usage:{prompt_tokens:10,completion_tokens:10,total_tokens:20}
    });
    // A short delay makes the queued/active acknowledgement observable.
    setTimeout(()=>{res.writeHead(200,{'Content-Type':'application/json','Content-Length':Buffer.byteLength(payload)});res.end(payload);},250);
  });
});

const server=spawn(process.env.PYTHON||'python3',['-m','residual.station.server','--port',String(stationPort),'--data',data],{
  cwd:root,stdio:['ignore','pipe','pipe']
});

async function waitStation(){
  await new Promise((resolve,reject)=>{
    let text='';const timer=setTimeout(()=>reject(Error('Station startup timeout')),15000);
    server.stdout.on('data',b=>{text+=b;if(text.includes('Press Ctrl+C')){clearTimeout(timer);resolve();}});
    server.once('exit',code=>reject(Error('Station exited '+code)));
  });
}

async function api(page,pathName,body){
  return page.evaluate(async ({pathName,body})=>{
    const b=await fetch('/api/bootstrap').then(r=>r.json());
    const response=await fetch(pathName,{method:body===undefined?'GET':'POST',headers:{
      'X-Station-Token':b.token,...(body===undefined?{}:{'Content-Type':'application/json'})
    },...(body===undefined?{}:{body:JSON.stringify(body)})});
    const value=await response.json();
    if(!response.ok)throw Error(value.error||('HTTP '+response.status));
    return value;
  },{pathName,body});
}

async function waitJob(page,jobId){
  await page.waitForFunction(async jobId=>{
    const b=await fetch('/api/bootstrap').then(r=>r.json());
    const jobs=await fetch('/api/jobs',{headers:{'X-Station-Token':b.token}}).then(r=>r.json());
    const job=jobs.jobs.find(x=>x.id===jobId);
    return job&&['completed','failed','interrupted'].includes(job.state);
  },jobId,{timeout:30000});
  const jobs=await api(page,'/api/jobs');
  return jobs.jobs.find(x=>x.id===jobId);
}

async function waitTask(page,pid,tid,state){
  await page.waitForFunction(async ({pid,tid,state})=>{
    const b=await fetch('/api/bootstrap').then(r=>r.json());
    const value=await fetch('/api/projects/'+pid,{headers:{'X-Station-Token':b.token}}).then(r=>r.json());
    const task=value.project.tasks.find(x=>x.id===tid);
    return task&&task.state===state;
  },{pid,tid,state},{timeout:30000});
}

async function main(){
  provider.listen(providerPort,'127.0.0.1');
  await new Promise(resolve=>provider.once('listening',resolve));
  await waitStation();
  const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('400 (Bad Request)'))errors.push(m.text());});
  try{
    await page.goto(stationUrl+'/#models');
    await page.getByRole('heading',{name:'Your model workshop.'}).waitFor();
    await api(page,'/api/settings',{local:{kind:'openai_compatible',model:'qa-model',base_url:`http://127.0.0.1:${providerPort}/v1`,output_token_field:'max_tokens'},local_credentials:{api_key:'QA-SECRET'}});

    // Q-UX-CHAT-003: real async model message, immediate acknowledgement, durable completion.
    await page.reload();await page.getByRole('heading',{name:'Your model workshop.'}).waitFor();
    await page.locator('#playground-prompt').fill('Acknowledge this qualification message');
    await page.getByRole('button',{name:'Send message ↗',exact:true}).click();
    await page.getByText('Operation queued. Progress appears at the bottom of the station.').waitFor();
    await page.locator('#playground-result').filter({hasText:'Station online.'}).waitFor({timeout:30000});
    const jobsAfterChat=await api(page,'/api/jobs');
    const chatJob=jobsAfterChat.jobs.find(j=>j.kind==='playground');
    assert(chatJob&&chatJob.state==='completed'&&chatJob.result?.text==='Station online.');
    await page.reload();await page.locator('[data-view="diagnostics"]').click();
    await page.getByRole('heading',{name:'Follow the evidence.'}).waitFor();
    await page.getByRole('cell',{name:'playground',exact:true}).waitFor();

    // Q-UX-JOBS-002: generate a real planner job, then prove the completed draft survives reload.
    await page.locator('[data-view="overview"]').click();
    await page.getByRole('button',{name:'+ New mission',exact:true}).last().click();
    await page.getByRole('button',{name:'Draft with a model',exact:true}).click();
    await page.locator('#draft-goal').fill('Build a persisted qualification marker');
    await page.getByRole('button',{name:'Generate draft',exact:true}).click();
    await page.getByText('Operation queued. Progress appears at the bottom of the station.').waitFor();
    await page.locator('#project-spec').waitFor({timeout:30000});
    assert((await page.locator('#project-spec').inputValue()).includes('Generated QA Mission'));
    await page.getByRole('button',{name:'Close dialog',exact:true}).click();
    await page.reload();
    const draftCard=page.getByRole('button',{name:/DRAFT SPEC.*Open generated draft/});
    await draftCard.waitFor({timeout:10000});await draftCard.click();
    assert((await page.locator('#project-spec').inputValue()).includes('Generated QA Mission'));
    await page.getByRole('button',{name:'Close dialog',exact:true}).click();

    // Q-UX-REPAIR-001: create a live mission, force a real failed candidate through the
    // remote-worker API, then repair/review/integrate through the actual browser controls.
    const bootstrap=await page.evaluate(()=>fetch('/api/bootstrap').then(r=>r.json()));
    const created=await api(page,'/api/projects',{markdown:bootstrap.demo_spec,source:'',allow_cloud:false,commands:true});
    const pid=created.project_id;
    const triage=await api(page,`/api/projects/${pid}/triage`,{});
    assert.equal((await waitJob(page,triage.job_id)).state,'completed');
    const access=await api(page,'/api/workers/access',{enabled:true,rotate:true});
    const claim=await page.evaluate(async ({pid,key})=>{
      const response=await fetch('/api/worker/claim',{method:'POST',headers:{'Authorization':'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({project_id:pid,name:'qa-runner',task_id:'OPS-101'})});
      return response.json();
    },{pid,key:access.token});
    assert(claim.work?.lease);
    const bad=await page.evaluate(async ({work,key})=>{
      const response=await fetch('/api/worker/result',{method:'POST',headers:{'Authorization':'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({
        project_id:work.project_id,task_id:work.task_id,lease:work.lease,submission_id:'qa-bad-1',
        response:{files:{'station/health.py':"def status(services):\n    return 'ready'\n"}}
      })});return {status:response.status,body:await response.json()};
    },{work:claim.work,key:access.token});
    assert.equal(bad.status,200);
    await waitTask(page,pid,'OPS-101','repair_required');

    await page.evaluate(pid=>localStorage.setItem('residual-project',pid),pid);
    await page.goto(stationUrl+'/#board');await page.getByRole('heading',{name:'Mission board',exact:true}).waitFor();
    const card=page.locator('.task-card').filter({hasText:'OPS-101'});await card.waitFor();await card.click();
    await page.getByText('repair required',{exact:true}).waitFor();
    await page.getByRole('button',{name:'▶ Run task',exact:true}).click();
    await waitTask(page,pid,'OPS-101','review_ready');
    await card.click();await page.getByRole('button',{name:'Review candidate',exact:true}).click();
    await waitTask(page,pid,'OPS-101','approved');
    await card.click();await page.getByRole('button',{name:'Integrate verified change',exact:true}).click();
    await waitTask(page,pid,'OPS-101','integrated');
    await page.reload();await page.locator('.task-card').filter({hasText:'OPS-101'}).waitFor();
    assert((await page.locator('.task-card').filter({hasText:'OPS-101'}).innerText()).includes('integrated'));

    assert.deepEqual(errors,[]);
    const result={passed:true,checks:[
      'Q-UX-CHAT-003 async message acknowledged and durably completed',
      'Q-UX-JOBS-002 real generated draft persisted across reload',
      'Q-UX-REPAIR-001 failed candidate exposed repair action and recovered through integration'
    ],errors};
    fs.writeFileSync(path.join(out,'adversarial-browser-results.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  }finally{
    await browser.close();
  }
}

main().catch(error=>{
  console.error(error);
  fs.writeFileSync(path.join(out,'adversarial-browser-results.json'),JSON.stringify({passed:false,error:error.message},null,2));
  process.exitCode=1;
}).finally(()=>{
  provider.close();
  server.kill('SIGTERM');
  try{fs.rmSync(data,{recursive:true,force:true});}catch{}
});
