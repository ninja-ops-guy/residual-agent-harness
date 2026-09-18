import test from 'node:test';
import assert from 'node:assert/strict';
import {ProviderSession} from '../demo/vm/provider-session.js';

test('inline provider session starts inert without cross-tab state',()=>{
  const session=new ProviderSession();
  assert.equal(session.channel,null);
  assert.equal(session.sdk,null);
  assert.equal(session.sdkLoad,null);
  assert.equal(session.ready,false);
  session.close();
});

test('closing inline provider revokes the grant and clears liveness',()=>{
  const session=new ProviderSession();
  session.connected=true;
  session.lastSeen=Date.now();
  session.grant={missionId:'m-'+'a'.repeat(32),calls:1,model:'gpt-5-nano',used:0,seen:new Set()};
  assert.equal(session.ready,true);
  session.close();
  assert.equal(session.connected,false);
  assert.equal(session.lastSeen,0);
  assert.equal(session.grant,null);
});

test('inline provider retry replaces a failed SDK script',async()=>{
  const priorDocument=globalThis.document;
  const priorWindow=globalThis.window;
  let current=null,appends=0,removals=0;
  globalThis.window={};
  globalThis.document={
    querySelector:()=>current,
    createElement:()=>({dataset:{},remove(){removals++;current=null;}}),
    head:{append(script){current=script;appends++;queueMicrotask(()=>{
      if(appends===1)script.onerror();
      else{
        globalThis.window.puter={auth:{isSignedIn:()=>false},ai:{}};
        script.onload();
      }
    });}},
  };
  try{
    const session=new ProviderSession();
    await assert.rejects(session.open(),/sdk_load_failed/);
    assert.equal(removals,1);
    assert.equal(await session.open(),false);
    assert.equal(appends,2);
  }finally{
    globalThis.document=priorDocument;
    globalThis.window=priorWindow;
  }
});
