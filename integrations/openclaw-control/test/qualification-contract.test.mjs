import test from 'node:test';
import assert from 'node:assert/strict';
import { REQUIRED_TESTS,parseTapSummary,qualificationPass } from '../qualification-contract.mjs';

const summary=overrides=>({tests:REQUIRED_TESTS,pass:REQUIRED_TESTS,fail:0,skipped:0,cancelled:0,todo:0,...overrides});

test('complete TAP summary is parsed and exact mandatory coverage is accepted',()=>{
  const log=['# tests '+REQUIRED_TESTS,'# pass '+REQUIRED_TESTS,'# fail 0','# cancelled 0','# skipped 0','# todo 0'].join('\n');
  const counts=parseTapSummary(log);
  assert.deepEqual(counts,summary({}));
  assert.equal(qualificationPass({exitCode:0,counts,syntaxOk:true,sourceStable:true}),true);
});

test('missing TAP summary fields fail closed',()=>{
  const counts=parseTapSummary('# tests '+REQUIRED_TESTS+'\n# pass '+REQUIRED_TESTS+'\n# fail 0\n# cancelled 0\n# skipped 0');
  assert.equal(counts.todo,-1);
  assert.equal(qualificationPass({exitCode:0,counts,syntaxOk:true,sourceStable:true}),false);
});

test('skipped mandatory coverage cannot pass',()=>{
  assert.equal(qualificationPass({exitCode:0,counts:summary({pass:REQUIRED_TESTS-1,skipped:1}),syntaxOk:true,sourceStable:true}),false);
});

test('TODO mandatory coverage cannot pass',()=>{
  assert.equal(qualificationPass({exitCode:0,counts:summary({pass:REQUIRED_TESTS-1,todo:1}),syntaxOk:true,sourceStable:true}),false);
});

test('pass count mismatch or reduced test floor cannot pass',()=>{
  assert.equal(qualificationPass({exitCode:0,counts:summary({pass:REQUIRED_TESTS-1}),syntaxOk:true,sourceStable:true}),false);
  assert.equal(qualificationPass({exitCode:0,counts:summary({tests:REQUIRED_TESTS-1,pass:REQUIRED_TESTS-1}),syntaxOk:true,sourceStable:true}),false);
});
