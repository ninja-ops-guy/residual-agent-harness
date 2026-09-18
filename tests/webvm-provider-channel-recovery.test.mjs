import test from 'node:test';
import assert from 'node:assert/strict';
import {ProviderSession, PROTOCOL, PROVIDER_CHANNEL_TOKEN_KEY} from '../demo/vm/provider-session.js';

const token='a'.repeat(64);

function withBrowserState(fn){
  const priorStorage=globalThis.sessionStorage,priorChannel=globalThis.BroadcastChannel;
  const priorLocation=globalThis.location;
  const data=new Map();
  class FakeStorage{getItem(key){return data.has(key)?data.get(key):null;}setItem(key,value){data.set(key,String(value));}removeItem(key){data.delete(key);}}
  class FakeChannel{static instances=[];constructor(name){this.name=name;this.closed=false;this.onmessage=null;FakeChannel.instances.push(this);}postMessage(){}close(){this.closed=true;}}
  globalThis.sessionStorage=new FakeStorage();globalThis.BroadcastChannel=FakeChannel;
  globalThis.location=new URL('https://example.test/demo/');
  return Promise.resolve(fn({data,FakeChannel})).finally(()=>{
    if(priorStorage===undefined)delete globalThis.sessionStorage;else globalThis.sessionStorage=priorStorage;
    if(priorChannel===undefined)delete globalThis.BroadcastChannel;else globalThis.BroadcastChannel=priorChannel;
    if(priorLocation===undefined)delete globalThis.location;else globalThis.location=priorLocation;
  });
}

test('Mission Control restores the private embedded-provider channel',()=>withBrowserState(({data,FakeChannel})=>{
  data.set(PROVIDER_CHANNEL_TOKEN_KEY,token);
  const states=[],session=new ProviderSession((...state)=>states.push(state));
  assert.equal(session.token,token);
  assert.equal(FakeChannel.instances[0].name,`${PROTOCOL}:${token}`);
  FakeChannel.instances[0].onmessage({data:{protocol:PROTOCOL,kind:'state',connected:true}});
  assert.equal(session.ready,true);
  assert.equal(states.at(-1)[0],'connected');
  session.close();
  assert.equal(data.has(PROVIDER_CHANNEL_TOKEN_KEY),false);
}));

test('guided setup returns an embeddable URL without opening a tab',()=>withBrowserState(({FakeChannel})=>{
  const priorOpen=globalThis.open;let opened=false;globalThis.open=()=>{opened=true;};
  try{
    const session=new ProviderSession();
    const url=new URL(session.open());
    assert.equal(url.origin,'https://example.test');
    assert.equal(url.pathname,'/provider/');
    assert.match(url.hash,/^#[a-f0-9]{64}$/);
    assert.equal(FakeChannel.instances.length,1);
    assert.equal(opened,false);
    session.close();
  }finally{if(priorOpen===undefined)delete globalThis.open;else globalThis.open=priorOpen;}
}));
