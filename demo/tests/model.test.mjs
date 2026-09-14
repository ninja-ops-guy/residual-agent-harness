import test from 'node:test';
import assert from 'node:assert/strict';
import {SCENARIOS, TASKS, canonical, fixture, verify, integrate, runScenario} from '../site/model.mjs';

for (const [name, expected] of Object.entries({clean: 'ACCEPTED', rejected: 'BLOCKED', unknown: 'BLOCKED', conflict: 'CONFLICT'})) {
  test(`${name}: intended outcome, explicit simulation and unsigned provenance`, () => {
    const result = runScenario(name, 'a'.repeat(40));
    assert.equal(result.integration.status, expected);
    assert.equal(result.simulation, true);
    assert.equal(result.signed, false);
    assert.equal(result.schema, 'residual.pages-simulation.v1');
    assert.equal(result.source_revision, 'a'.repeat(40));
    assert.equal(result.events.length, 6);
    assert.deepEqual(result.events.map(event => event.sequence), [1, 2, 3, 4, 5, 6]);
    if (expected !== 'ACCEPTED') assert.deepEqual(result.integration.artifacts, []);
  });
}
test('faulty candidate fails without erasing other passing checks', () => {
  assert.deepEqual(runScenario('rejected').checks.map(c => c.status), ['FAIL', 'PASS', 'PASS']);
});
test('missing evidence remains UNKNOWN', () => {
  assert.deepEqual(runScenario('unknown').checks.map(c => c.status), ['PASS', 'UNKNOWN', 'PASS']);
});
test('conflict is detected from different verified bytes, not assigned from worker count', () => {
  const result = runScenario('conflict');
  assert.ok(result.checks.every(c => c.status === 'PASS'));
  assert.deepEqual(result.integration.conflicts, ['config/shared.json']);
});
test('integration recomputes checks rather than trusting a forged PASS field', () => {
  const candidates = fixture('rejected');
  candidates[0].status = 'PASS';
  assert.equal(integrate(candidates).status, 'BLOCKED');
});
test('all permutations produce byte-identical accepted artifacts', () => {
  const candidates = fixture('clean');
  const expected = canonical(integrate(candidates));
  for (const a of [0, 1, 2]) for (const b of [0, 1, 2]) for (const c of [0, 1, 2]) {
    if (new Set([a, b, c]).size === 3) assert.equal(canonical(integrate([candidates[a], candidates[b], candidates[c]])), expected);
  }
});
test('identical shared content deduplicates instead of inventing a conflict', () => {
  const candidates = fixture('conflict');
  candidates[1].content = candidates[2].content = {timeout_ms: 2000, log_format: 'json'};
  assert.equal(integrate(candidates).status, 'ACCEPTED');
  assert.equal(integrate(candidates).artifacts.length, 2);
});
test('missing and duplicated required tasks fail closed', () => {
  const candidates = fixture('clean');
  assert.equal(integrate(candidates.slice(1)).status, 'BLOCKED');
  assert.equal(integrate([candidates[0], candidates[0], candidates[1]]).status, 'BLOCKED');
});
test('out-of-scope artifact paths are blocked', () => {
  for (const path of ['../secret', '/tmp/result', 'config/../../key', 'https://example.com/code', 'config/file.py']) {
    const candidates = fixture('clean');
    candidates[0].path = path;
    assert.equal(integrate(candidates).status, 'BLOCKED');
  }
});
test('verifier rejects unknown tasks and invalid integer values', () => {
  assert.equal(verify({task: 'unknown', content: {}}).status, 'FAIL');
  for (const value of [0, -1, 1.5, '3', null, true, 12, Infinity, NaN]) {
    assert.equal(verify({task: 'retry', content: {max_attempts: value}}).status, 'FAIL');
  }
});
test('scenario names cannot resolve inherited object properties', () => {
  for (const name of ['constructor', '__proto__', 'missing']) assert.throws(() => fixture(name), /Unknown demo scenario/);
});
test('reruns are deterministic and fixtures are not shared mutable state', () => {
  const first = runScenario('clean');
  fixture('clean')[0].content.max_attempts = 999;
  assert.deepEqual(runScenario('clean'), first);
  assert.ok(Object.isFrozen(TASKS));
  assert.ok(Object.isFrozen(SCENARIOS));
});
test('canonical serialization ignores object insertion order', () => {
  assert.equal(canonical({b: 2, a: {y: 1, x: 0}}), canonical({a: {x: 0, y: 1}, b: 2}));
});
