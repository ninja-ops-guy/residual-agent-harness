// Reproducible software-component qualification. This NEVER grants release/live authority.
import { readdirSync,readFileSync,writeFileSync,mkdirSync,existsSync } from 'node:fs';
import { resolve,relative,join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { canonical,sha256 } from './protocol.mjs';
const root=fileURLToPath(new URL('.',import.meta.url));
const outFlag=process.argv.indexOf('--output');
const out=resolve(outFlag>=0?process.argv[outFlag+1]:'qualification-output');
if(existsSync(out)){console.error('OUTPUT_EXISTS: preserve previous generations');process.exit(2);}
mkdirSync(out,{recursive:true,mode:0o700});
function sources(){
  const result={};
  for(const dir of [root,join(root,'test')])for(const name of readdirSync(dir).sort()){
    if(!/\.(mjs|json|md)$/.test(name))continue;
    const path=join(dir,name);const bytes=readFileSync(path);
    result[relative(root,path).replaceAll('\\','/')]={bytes:bytes.length,sha256:sha256(bytes)};
  }
  return result;
}
const before=sources();
const syntax=[];
for(const file of Object.keys(before).filter(name=>name.endsWith('.mjs'))){
  const r=spawnSync(process.execPath,['--check',file],{cwd:root,encoding:'utf8',timeout:20000});
  syntax.push({file,exit_code:r.status});
}
// Reporter selection is a wire-format contract, not a runtime-dependent default.
const run=spawnSync(process.execPath,['--test','--test-reporter=tap','test/control.test.mjs','test/plugin.test.mjs','test/station-worker.test.mjs','test/lifecycle-contract.test.mjs'],{cwd:root,encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024});
const log=(run.stdout||'')+(run.stderr||'');writeFileSync(join(out,'tests.tap'),log,{mode:0o600});
const after=sources();
const counts=Object.fromEntries(['tests','pass','fail','skipped','cancelled'].map(key=>[key,Number(log.match(new RegExp('^# '+key+' (\\d+)','m'))?.[1]??-1)]));
const pass=run.status===0 && counts.tests>=56 && counts.fail===0 && counts.cancelled===0 &&
  syntax.every(row=>row.exit_code===0) && canonical(before)===canonical(after);
const receipt={schema:'residual.openclaw.software-qualification.v1',
  result:pass?'SOFTWARE_COMPONENT_PASS':'SOFTWARE_COMPONENT_FAIL',
  observed_at:new Date().toISOString(),environment:{node:process.version,platform:process.platform,arch:process.arch},
  base:{head:'8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2',tree:'7cd0d32be6fd61948f2fce753b122e5b6f0c6500'},
  scope:'Addition-only isolated package; not the RESIDUAL full suite or installed OpenClaw',
  source_files:before,source_set_sha256:sha256(Buffer.from(canonical(before))),syntax,
  tests:{...counts,exit_code:run.status,log_sha256:sha256(Buffer.from(log))},
  first_failure:pass?null:syntax.find(row=>row.exit_code!==0)?.file ||
    (Object.values(counts).some(n=>n<0)?'TEST_REPORT_FORMAT_INVALID':'TEST_OR_SOURCE_STABILITY_FAILURE'),
  native_openclaw:'NOT_EXECUTED',live_provider:'NOT_EXECUTED',station_integration:'NOT_IMPLEMENTED',
  external_restart:'NOT_IMPLEMENTED',native_cancel:'NOT_IMPLEMENTED',independent_review:'NOT_OBTAINED',
  release_admissible:false,release_result:'BLOCKED',promotion_authority:false};
writeFileSync(join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n',{mode:0o600});
console.log(JSON.stringify({result:receipt.result,tests:counts,release_result:'BLOCKED',receipt:join(out,'receipt.json')},null,2));
process.exitCode=!pass?1:process.argv.includes('--require-release')?3:0;
