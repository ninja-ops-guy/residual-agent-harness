import test from 'node:test';
import assert from 'node:assert/strict';
import {ProviderSession, PROTOCOL} from '../demo/vm/provider-session.js';

function withBrowserState(fn){
  const priorLocation=globalThis.location,priorChannel=globalThis.MessageChannel;
  class FakePort{constructor(){this.onmessage=null;this.closed=false;}postMessage(){}start(){}close(){this.closed=true;}}
  class FakeMessageChannel{constructor(){this.port1=new FakePort();this.port2=new FakePort();}}
  globalThis.location=new URL('https://example.test/demo/');
  globalThis.MessageChannel=FakeMessageChannel;
  return Promise.resolve(fn()).finally(()=>{
    if(priorLocation===undefined)delete globalThis.location;else globalThis.location=priorLocation;
    if(priorChannel===undefined)delete globalThis.MessageChannel;else globalThis.MessageChannel=priorChannel;
  });
}

test('guided setup transfers a private port into the embedded frame without opening a tab',()=>withBrowserState(()=>{
  const priorOpen=globalThis.open;let opened=false,handshake=null;
  globalThis.open=()=>{opened=true;};
  const frame={src:'',onload:null,contentWindow:{postMessage(message,origin,ports){handshake={message,origin,ports};}}};
  try{
    const states=[],session=new ProviderSession((...state)=>states.push(state));
    const url=new URL(session.open(frame));
    assert.equal(url.origin,'https://example.test');
    assert.equal(url.pathname,'/provider/');
    assert.equal(frame.src,url.href);
    frame.onload();
    assert.equal(handshake.message.protocol,PROTOCOL);
    assert.equal(handshake.message.kind,'connect');
    assert.equal(handshake.origin,'https://example.test');
    assert.equal(handshake.ports.length,1);
    assert.equal(opened,false);
    assert.equal(states.at(-1)[0],'connecting');
    session.close();
  }finally{if(priorOpen===undefined)delete globalThis.open;else globalThis.open=priorOpen;}
}));

test('closing embedded provider revokes the grant and clears liveness',()=>{
  const session=new ProviderSession();
  session.channel={postMessage(){},close(){}};
  session.connected=true;session.lastSeen=Date.now();
  session.grant={missionId:'m-'+'a'.repeat(32),calls:1,model:'gpt-5-nano',used:0,seen:new Set()};
  assert.equal(session.ready,true);
  session.close();
  assert.equal(session.connected,false);
  assert.equal(session.lastSeen,0);
  assert.equal(session.grant,null);
});
