import test from 'node:test';
import assert from 'node:assert/strict';
import {ProviderSession, PROTOCOL, PROVIDER_CHANNEL_TOKEN_KEY} from '../demo/vm/provider-session.js';

const token='a'.repeat(64);

function withBrowserState(fn){
  const priorStorage=globalThis.sessionStorage;
  const priorChannel=globalThis.BroadcastChannel;
  const data=new Map();
  class FakeStorage{
    getItem(key){return data.has(key)?data.get(key):null;}
    setItem(key,value){data.set(key,String(value));}
    removeItem(key){data.delete(key);}
  }
  class FakeChannel{
    static instances=[];
    constructor(name){this.name=name;this.closed=false;this.onmessage=null;FakeChannel.instances.push(this);}
    postMessage(){}
    close(){this.closed=true;}
  }
  globalThis.sessionStorage=new FakeStorage();
  globalThis.BroadcastChannel=FakeChannel;
  return Promise.resolve(fn({data,FakeChannel})).finally(()=>{
    if(priorStorage===undefined)delete globalThis.sessionStorage;else globalThis.sessionStorage=priorStorage;
    if(priorChannel===undefined)delete globalThis.BroadcastChannel;else globalThis.BroadcastChannel=priorChannel;
  });
}

test('Mission Control restores the same private provider channel after reload',()=>withBrowserState(({data,FakeChannel})=>{
  data.set(PROVIDER_CHANNEL_TOKEN_KEY,token);
  const states=[];
  const session=new ProviderSession((...state)=>states.push(state));
  assert.equal(session.token,token);
  assert.equal(FakeChannel.instances.length,1);
  assert.equal(FakeChannel.instances[0].name,`${PROTOCOL}:${token}`);
  FakeChannel.instances[0].onmessage({data:{protocol:PROTOCOL,kind:'state',connected:true}});
  assert.equal(session.ready,true);
  assert.equal(states.at(-1)[0],'connected');
  session.close();
  assert.equal(data.has(PROVIDER_CHANNEL_TOKEN_KEY),false);
}));

test('invalid persisted channel material is ignored fail-closed',()=>withBrowserState(({data,FakeChannel})=>{
  data.set(PROVIDER_CHANNEL_TOKEN_KEY,'not-a-token');
  const session=new ProviderSession();
  assert.equal(session.token,'');
  assert.equal(session.channel,null);
  assert.equal(FakeChannel.instances.length,0);
  session.close();
}));
