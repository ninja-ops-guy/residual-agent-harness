import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validInference,
  validProtocolEnvelope,
  protocolReply,
} from '../../demo/vm/provider-session.js';

let state=0x5eed1234;
function rand(){state=(Math.imul(state,1664525)+1013904223)>>>0;return state/0x100000000;}
function pick(values){return values[Math.floor(rand()*values.length)];}
function text(max=80){
  const alphabet='abcXYZ019_-/.:;[]{}"\\\n\t🙂';
  let out='';const n=Math.floor(rand()*max);
  for(let i=0;i<n;i++)out+=alphabet[Math.floor(rand()*alphabet.length)];
  return out;
}
function value(depth=0){
  if(depth>3)return pick([null,true,false,Math.floor(rand()*1000),text()]);
  switch(Math.floor(rand()*7)){
    case 0:return null;
    case 1:return rand()<.5;
    case 2:return Math.floor(rand()*1e7);
    case 3:return text(180);
    case 4:return Array.from({length:Math.floor(rand()*6)},()=>value(depth+1));
    default:{
      const out={};const count=Math.floor(rand()*7);
      for(let i=0;i<count;i++)out[text(20)||('k'+i)]=value(depth+1);
      return out;
    }
  }
}

test('browser provider validators are total over a deterministic malformed corpus',()=>{
  state=0x5eed1234;
  for(let i=0;i<3000;i++){
    const candidate=value();
    assert.doesNotThrow(()=>validInference(candidate));
    assert.equal(typeof validInference(candidate),'boolean');
    assert.doesNotThrow(()=>validProtocolEnvelope(candidate));
    assert.equal(typeof validProtocolEnvelope(candidate),'boolean');
  }
});

test('any protocolReply success is itself a valid RESIDUAL protocol envelope',()=>{
  state=0x9e3779b9;
  let accepted=0,rejected=0;
  for(let i=0;i<2500;i++){
    const candidate=value();
    try{
      const raw=protocolReply(candidate);
      const parsed=JSON.parse(raw);
      assert.equal(validProtocolEnvelope(parsed),true);
      accepted++;
    }catch(error){
      rejected++;
      assert.equal(error?.code,'provider_protocol_invalid',`unexpected exception type for corpus item ${i}: ${error}`);
      assert.ok(!String(error).includes('SECRET_CANARY_VALUE'));
    }
  }
  assert.ok(rejected>0);
  // The corpus is intentionally mostly malformed. If accepted entries exist they
  // have already been checked against the exact envelope validator above.
  assert.ok(accepted>=0);
});

test('adversarial response content never bypasses exact envelope validation',()=>{
  const payloads=[
    'SECRET_CANARY_VALUE',
    '{"updates":{"answer":{"text":"ok","citations":[]}}}',
    '{"updates":{"answer":{"text":"ok","citations":[]}},"requests":[],"extra":true}',
    '```json\n{"updates":{"answer":{"text":"ok","citations":[]}},"requests":[]}\n``` trailing',
    '{"updates":{"answer":{"text":"ok","citations":[]},"__proto__":{"polluted":true}},"requests":[]}',
    '[{"updates":{},"requests":[]}]',
    '{"updates":null,"requests":[]}',
  ];
  for(const content of payloads){
    try{
      const raw=protocolReply({message:{content}});
      assert.equal(validProtocolEnvelope(JSON.parse(raw)),true);
    }catch(error){
      assert.equal(error?.code,'provider_protocol_invalid');
    }
  }
  assert.equal({}.polluted,undefined);
});
