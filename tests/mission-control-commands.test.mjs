import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const source=readFileSync(new URL('../demo/vm/mission-control-commands.js',import.meta.url),'utf8');
const mod=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const {executeMissionCommand,missionCommandHelp}=mod;

function api(overrides={}){
  const calls=[];
  const base={
    status:async()=>({guest:'ready',mission_active:false}),
    tab:async value=>calls.push(['tab',value]),
    mode:async value=>(calls.push(['mode',value]),value),
    budget:async value=>calls.push(['budget',value]),
    model:async value=>calls.push(['model',value]),
    outputTokens:async value=>(calls.push(['tokens',value]),Math.min(value,1536)),
    busy:async()=>false,
    newChat:async()=>calls.push(['new']),
    detach:async()=>(calls.push(['detach']),true),
    history:async()=>[{id:'c-1',title:'One'}],
    clear:async()=>calls.push(['clear']),
    stop:async()=>(calls.push(['stop']),true),
    restart:async()=>(calls.push(['restart']),true),
    connect:async()=>calls.push(['connect']),
    meshStatus:async()=>({attached:false,browser_lab:'isolated'}),
    workerStatus:async()=>({available:true,ready:true,poisoned:false})
  };
  return {api:{...base,...overrides},calls};
}

test('non-command and escaped slash are not intercepted',async()=>{
  for(const value of ['Build a calculator','//literal slash']){
    const {api:a}=api();
    assert.deepEqual(await executeMissionCommand(value,a),{handled:false});
  }
});

test('help exposes bounded console surface',async()=>{
  const {api:a}=api();
  const result=await executeMissionCommand('/help',a);
  assert.equal(result.handled,true);
  assert.match(result.text,/\/status/);
  assert.match(result.text,/\/mesh status/);
  assert.doesNotMatch(result.text,/shell|exec|sudo/i);
  assert.equal(missionCommandHelp(),result.text);
});

test('tab mode budget model and tokens are typed',async()=>{
  const x=api();
  assert.match((await executeMissionCommand('/tab evidence',x.api)).text,/evidence/);
  assert.match((await executeMissionCommand('/mode audit',x.api)).text,/audit/);
  assert.match((await executeMissionCommand('/budget 3',x.api)).text,/3/);
  assert.match((await executeMissionCommand('/model openai\/gpt-5.4-nano',x.api)).text,/gpt-5.4-nano/);
  const tokens=await executeMissionCommand('/tokens 8192',x.api);
  assert.match(tokens.text,/1536/);
  assert.deepEqual(x.calls,[
    ['tab','evidence'],['mode','audit'],['budget',3],
    ['model','openai/gpt-5.4-nano'],['tokens',8192]
  ]);
});

test('invalid control values fail without invoking adapter',async()=>{
  const x=api();
  for(const value of ['/tab nope','/mode root','/budget 99','/model x;rm','/tokens 9']){
    const result=await executeMissionCommand(value,x.api);
    assert.match(result.text,/Usage:/);
  }
  assert.deepEqual(x.calls,[]);
});

test('active mission blocks lineage-destructive commands',async()=>{
  const x=api({busy:async()=>true});
  assert.match((await executeMissionCommand('/new',x.api)).text,/active/);
  assert.match((await executeMissionCommand('/detach',x.api)).text,/active/);
  assert.match((await executeMissionCommand('/clear',x.api)).text,/active/);
  assert.deepEqual(x.calls,[]);
});

test('conversation commands are explicit and non-destructive to guest evidence',async()=>{
  const x=api();
  assert.match((await executeMissionCommand('/history',x.api)).text,/c-1/);
  assert.match((await executeMissionCommand('/new',x.api)).text,/Guest evidence.*unchanged/);
  assert.match((await executeMissionCommand('/detach',x.api)).text,/fresh artifact lineage/);
  assert.match((await executeMissionCommand('/clear',x.api)).text,/Guest traces.*not deleted/);
  assert.deepEqual(x.calls,[['new'],['detach'],['clear']]);
});

test('direct tab aliases, cancel and worker status remain typed controls',async()=>{
  const x=api();
  await executeMissionCommand('/activity',x.api);
  await executeMissionCommand('/evidence',x.api);
  await executeMissionCommand('/files',x.api);
  await executeMissionCommand('/chat',x.api);
  const worker=await executeMissionCommand('/worker status',x.api);
  assert.match(worker.text,/"ready": true/);
  await executeMissionCommand('/cancel',x.api);
  assert.deepEqual(x.calls,[
    ['tab','activity'],['tab','evidence'],['tab','files'],['tab','chat'],['stop']
  ]);
});

test('stop restart connect and terminal call only explicit adapter methods',async()=>{
  const x=api();
  await executeMissionCommand('/stop',x.api);
  await executeMissionCommand('/restart',x.api);
  await executeMissionCommand('/connect',x.api);
  await executeMissionCommand('/terminal',x.api);
  assert.deepEqual(x.calls,[['stop'],['restart'],['connect'],['tab','terminal']]);
});

test('mesh and experiment commands preserve browser isolation boundary',async()=>{
  const x=api();
  const mesh=await executeMissionCommand('/mesh status',x.api);
  assert.match(mesh.text,/isolated/);
  const dist=await executeMissionCommand('/experiment distributed',x.api);
  assert.match(dist.text,/residual experiment distributed/);
  const proto=await executeMissionCommand('/experiment mesh',x.api);
  assert.match(proto.text,/residual experiment mesh/);
  const pipeline=await executeMissionCommand('/experiment pipeline',x.api);
  assert.match(pipeline.text,/residual experiment pipeline/);
  const recovery=await executeMissionCommand('/experiment recovery',x.api);
  assert.match(recovery.text,/residual experiment recovery/);
  const matrix=await executeMissionCommand('/experiment matrix',x.api);
  assert.match(matrix.text,/residual experiment matrix/);
  const bridge=await executeMissionCommand('/experiment bridge',x.api);
  assert.match(bridge.text,/residual experiment bridge/);
});

test('unknown command is inert and returns help',async()=>{
  const x=api();
  const result=await executeMissionCommand('/rm -rf /',x.api);
  assert.match(result.text,/Unknown command/);
  assert.deepEqual(x.calls,[]);
});

test('Mission Control world intercepts slash commands before mission submission',()=>{
  const world=readFileSync(new URL('../demo/vm/mission-control-world.js',import.meta.url),'utf8');
  const install=readFileSync(new URL('../demo/vm/install_workbench.py',import.meta.url),'utf8');
  assert.match(world,/executeMissionCommand/);
  assert.match(world,/stopImmediatePropagation\(\)/);
  assert.match(world,/value\.startsWith\('\/'\)/);
  assert.match(world,/host\.meshStatus/);
  assert.match(install,/mission-control-commands\.js/);
  assert.match(install,/workerStatus:/);
});
