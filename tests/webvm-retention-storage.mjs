import test from 'node:test';
import assert from 'node:assert/strict';
import {storeEvidence,loadEvidence,clearLocalConversation} from '../demo/vm/mission-control-world.js';
const id='c-'+'a'.repeat(32),mid='m-'+'b'.repeat(32),ev='residual.chat.evidence.v1.'+id,session='residual.chat.session.v2.'+id;
function setup(){const map=new Map();globalThis.localStorage={getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v),removeItem:k=>map.delete(k)};return map}
const payload=()=>({mission_id:mid,frames:['exact canonical frame'],trace_root:'root',truncated:false});
test('persistence roundtrips exact projection bytes and binding',()=>{setup();assert.equal(storeEvidence(id,payload()),true);assert.deepEqual(loadEvidence(id),payload())});
test('clear evidence preserves transcript and unrelated origin data',()=>{const m=setup();m.set(session,'chat');m.set('other','keep');storeEvidence(id,payload());assert.ok(clearLocalConversation(id,{evidenceOnly:true}));assert.equal(loadEvidence(id),null);assert.equal(m.get(session),'chat');assert.equal(m.get('other'),'keep')});
test('conversation deletion clears session evidence index and current',()=>{const m=setup();m.set(session,'chat');m.set('residual.chat.current.v2',id);m.set('residual.chat.index.v2',JSON.stringify([{id}]));storeEvidence(id,payload());assert.ok(clearLocalConversation(id));assert.equal(m.has(session),false);assert.equal(m.has(ev),false);assert.equal(m.has('residual.chat.current.v2'),false);assert.equal(m.get('residual.chat.index.v2'),'[]')});
test('storage truncation preserves prefix and marks incomplete',()=>{setup();assert.ok(storeEvidence(id,{...payload(),frames:['first','x'.repeat(300000)]}));assert.deepEqual(loadEvidence(id).frames,['first']);assert.equal(loadEvidence(id).truncated,true)});
test('quota failure removes stale projection and reports failure',()=>{const m=setup();m.set(ev,'stale');localStorage.setItem=()=>{throw Error('quota')};assert.equal(storeEvidence(id,payload()),false);assert.equal(m.has(ev),false)});
test('denied deletion reports failure and does not overwrite',()=>{const m=setup();m.set(ev,'stale');localStorage.removeItem=()=>{throw Error('denied')};assert.equal(storeEvidence(id,payload()),false);assert.equal(clearLocalConversation(id),false);assert.equal(m.get(ev),'stale')});
test('restoration rejects malformed oversized and excessive-frame storage',()=>{const m=setup();for(const value of ['{','x'.repeat(300001),JSON.stringify({...payload(),frames:Array(301).fill('x')})]){m.set(ev,value);assert.equal(loadEvidence(id),null)}});
test('unavailable storage restores no evidence',()=>{setup();localStorage.getItem=()=>{throw Error('denied')};assert.equal(loadEvidence(id),null)});
