// Real Chromium DOM/storage; synthetic projections, no guest/provider workload.
const {chromium}=require('playwright');
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=http.createServer((req,res)=>{const file=path.resolve(root,'.'+req.url.split('?')[0]);if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return}if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Retention test</title>');return}try{res.setHeader('Content-Type','text/javascript');res.end(fs.readFileSync(file))}catch{res.writeHead(404).end()}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;
 try{browser=await chromium.launch({headless:true,args:['--no-sandbox']});const page=await browser.newPage();await page.goto(`http://127.0.0.1:${server.address().port}`);
 const result=await page.evaluate(async()=>{
  const {mountMissionControl,storeEvidence,clearLocalConversation}=await import('/demo/vm/mission-control-world.js');
  const id='c-'+'a'.repeat(32),mid='m-'+'b'.repeat(32),ek='residual.chat.evidence.v1.'+id,sk='residual.chat.session.v2.'+id;
  const frame=JSON.stringify({kind:'evidence',mission_id:mid,data:{seq:0,kind:'run_started',data:{goal:'PRIVATE_MARKER'}}});
  const payload=()=>({mission_id:mid,frames:[frame],trace_root:null,truncated:false});
  const checks=[];const check=(name,condition)=>{if(!condition)throw Error(name);checks.push(name)};
  check('persist',storeEvidence(id,payload()));check('exact frame roundtrip',JSON.parse(localStorage.getItem(ek)).frames[0]===frame);
  localStorage.setItem('residual.chat.current.v2',id);localStorage.setItem(sk,JSON.stringify({version:2,id,turns:[],revision:0}));localStorage.setItem('residual.chat.index.v2',JSON.stringify([{id,title:'test'}]));
  const ui=mountMissionControl({ready:()=>true,focus(){},run(){},mailbox(){}});
  check('restoration renders retained content',document.querySelector('#mc-events').textContent.includes('PRIVATE_MARKER'));
  check('separate consent defaults off',!document.querySelector('#mc-remember-evidence').checked);
  document.querySelector('#mc-clear-evidence').click();await new Promise(r=>setTimeout(r,20));
  check('clear removes storage and rendered evidence',!localStorage.getItem(ek)&&document.querySelector('#mc-events').textContent==='');
  check('clear preserves transcript',!!localStorage.getItem(sk));
  check('bounded truncation',storeEvidence(id,{...payload(),frames:[frame,'x'.repeat(300000)]})&&localStorage.getItem(ek).length<=300000&&JSON.parse(localStorage.getItem(ek)).truncated);
  const original=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw Error('quota')};check('quota failure reported',!storeEvidence(id,payload()));check('quota removes stale projection',!localStorage.getItem(ek));Storage.prototype.setItem=original;
  const remove=Storage.prototype.removeItem;Storage.prototype.removeItem=function(){throw Error('denied')};check('deletion failure reported',!clearLocalConversation(id));Storage.prototype.removeItem=remove;
  storeEvidence(id,payload());document.querySelector('#mc-delete-chat').click();check('conversation delete removes both keys',!localStorage.getItem(ek)&&!localStorage.getItem(sk));check('deleted chat absent from history',!localStorage.getItem('residual.chat.index.v2').includes(id));
  ui.destroy();return checks;
 });assert.equal(result.length,12);console.log(JSON.stringify({passed:result.length,checks:result}));
 }finally{if(browser)await browser.close();server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
