/* Browser-independent control-logic tests. No real provider or browser proof. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../site/legal/provider-privacy.js', import.meta.url), 'utf8');
const walkthrough = readFileSync(new URL('../site/walkthrough-persist.js', import.meta.url), 'utf8');
function element(id) {
  return {id, checked:false, textContent:'', dataset:{}, listeners:{},
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); },
    dispatch(type, event={}) { for(const fn of this.listeners[type] || []) fn(event); },
    click() { this.dispatch('click', {isTrusted:false}); }};
}
function provider() {
  const elements = Object.fromEntries(['load','provider-privacy-withdraw','status'].map(id=>[id,element(id)]));
  const win = element('window'); let revoked=0, reloaded=0;
  const context = vm.createContext({document:{getElementById:id=>elements[id]},window:win,setTimeout});
  vm.runInContext(source.replace('export function','function') + '\nthis.install = installProviderPrivacy;',context);
  const control=context.install({onWithdraw:()=>revoked++,reload:()=>reloaded++});
  return {elements,win,control,revoked:()=>revoked,reloaded:()=>reloaded};
}
function walk(storage=new Map(), blocked=false) {
  const tab=element('walk');tab.dataset.tab='walk';const other=element('evidence');other.dataset.tab='evidence';
  const elements=Object.fromEntries(['step','run','reset','remember-walkthrough','remember-status'].map(id=>[id,element(id)]));
  const host={prepend(){}};elements.reset.closest=()=>host;
  const controls={querySelector:selector=>elements[selector.slice(1)]};const win=element('window');
  const localStorage={getItem:key=>{if(blocked)throw Error('blocked');return storage.get(key)??null;},
    setItem:(key,val)=>{if(blocked)throw Error('blocked');storage.set(key,val);},
    removeItem:key=>{if(blocked)throw Error('blocked');storage.delete(key);}};
  const document={readyState:'complete',getElementById:id=>elements[id],querySelectorAll:()=>[tab,other],createElement:()=>controls,querySelector:()=>host,body:host};
  vm.runInNewContext(walkthrough,{document,window:win,localStorage,setTimeout,Date,JSON,Number});
  return {elements,win,storage,choose(value){elements['remember-walkthrough'].checked=value;elements['remember-walkthrough'].dispatch('change');}};
}
const KEY='residual.walkthrough.v1', CONSENT='residual.walkthrough.consent.v1';

test('provider loading is off without a trusted feature-led choice',()=>{
 const p=provider();assert.equal(p.control.allowLoad(),false);p.elements.load.click();assert.equal(p.control.allowLoad(),false);
});
test('one real click authorizes only its immediate load',()=>{
 const p=provider();p.elements.load.dispatch('click',{isTrusted:true});assert.equal(p.control.allowLoad(),true);assert.equal(p.control.allowLoad(),false);
});
test('unused load authorization does not survive its event turn',async()=>{
 const p=provider();p.elements.load.dispatch('click',{isTrusted:true});await new Promise(resolve=>setTimeout(resolve,5));assert.equal(p.control.allowLoad(),false);
});
test('withdrawal revokes connection and reloads a previously loaded panel',()=>{
 const p=provider();p.elements.load.dispatch('click',{isTrusted:true});p.control.allowLoad();p.elements['provider-privacy-withdraw'].click();assert.equal(p.revoked(),1);assert.equal(p.reloaded(),1);assert.equal(p.control.allowLoad(),false);
});
test('back-forward restore revokes the earlier provider choice',()=>{
 const p=provider();p.elements.load.dispatch('click',{isTrusted:true});p.control.allowLoad();p.win.dispatch('pageshow',{persisted:true});assert.equal(p.revoked(),1);assert.equal(p.reloaded(),1);
});
test('walkthrough saves nothing optional until opt-in',()=>{
 const w=walk();w.elements.step.click();assert.equal(w.storage.size,0);w.choose(true);w.elements.step.click();assert.equal(JSON.parse(w.storage.get(KEY)).steps,2);assert.ok(w.storage.has(CONSENT));
});
test('remember preference restores, withdrawal removes only owned keys',()=>{
 const w=walk(new Map([['unrelated','keep']]));w.choose(true);w.elements.step.click();const restored=walk(w.storage);assert.equal(restored.elements['remember-walkthrough'].checked,true);restored.choose(false);assert.deepEqual([...w.storage],[['unrelated','keep']]);
});
test('legacy progress and expired choices are not restored',()=>{
 for (const storage of [new Map([[KEY,JSON.stringify({tab:'walk',steps:5,ran:false})]]),new Map([[CONSENT,JSON.stringify({version:1,expires:Date.now()-1})],[KEY,'{}']])]) {
  const w=walk(storage);assert.equal(w.elements['remember-walkthrough'].checked,false);assert.equal(storage.size,0);
 }
});
test('another tab withdrawing the choice prevents subsequent writes',()=>{
 const w=walk();w.choose(true);w.storage.delete(CONSENT);w.win.dispatch('storage',{key:CONSENT});w.elements.step.click();assert.equal(w.storage.has(KEY),false);assert.equal(w.elements['remember-walkthrough'].checked,false);
});
test('blocked storage leaves usable in-memory controls with accurate status',()=>{
 const w=walk(new Map(),true);w.choose(true);w.elements.step.click();w.elements.run.click();assert.equal(w.elements['remember-walkthrough'].checked,false);assert.match(w.elements['remember-status'].textContent,/Storage unavailable/);
});
