import test from 'node:test';
import assert from 'node:assert/strict';
import {reducePreparation} from '../residual/station/static/agent-preparation-model.mjs';
import {fixture, DISPLAY_TIME} from './fixtures/agent-preparation-data.mjs';

const reduce = input => reducePreparation(input, DISPLAY_TIME);
const stage = (output, id) => output.stages.find(item => item.id === id);
const authorityUnknown = output => {
  for (const id of ['connectivity', 'communications', 'eligibility', 'acceptance']) assert.equal(stage(output, id).state, 'UNKNOWN');
  assert.equal(output.integrated, false);
  assert.equal(output.mode, 'read-only');
};
const allUnknown = output => {
  assert(output.stages.every(item => item.state === 'UNKNOWN'));
  authorityUnknown(output);
};

test('empty input leaves all eight independent stages unknown', () => {
  const output = reduce({});
  assert.equal(output.stages.length, 8);
  allUnknown(output);
});
test('declarations and local/health reports never confer authority', () => {
  const output = reduce(fixture());
  assert.equal(stage(output, 'identity').state, 'DECLARED');
  assert.equal(stage(output, 'preflight').state, 'REPORTED');
  assert.equal(stage(output, 'enrollment').state, 'REPORTED');
  assert.equal(stage(output, 'containment').state, 'UNKNOWN');
  assert.match(stage(output, 'preflight').detail, /freshness is unknown/);
  assert.match(stage(output, 'enrollment').detail, /project_count does not identify project membership/);
  authorityUnknown(output);
});
test('preflight without mesh status cannot supply enrollment or connectivity', () => {
  const input = fixture(); delete input.meshStatus;
  const output = reduce(input);
  assert.equal(stage(output, 'enrollment').state, 'UNKNOWN');
  authorityUnknown(output);
});
for (const [name, id, state] of [
  ['expired', 'enrollment', 'EXPIRED'], ['wrong-host', 'enrollment', 'MISMATCH'],
  ['wrong-project', 'preflight', 'MISMATCH'], ['revoked', 'enrollment', 'BLOCKED'],
  ['uncertain', 'enrollment', 'UNKNOWN'], ['future', 'enrollment', 'UNKNOWN'],
  ['unsupported', 'containment', 'UNSUPPORTED'],
]) test(name + ' observation stays bounded to its stage', () => {
  const output = reduce(fixture(name));
  assert.equal(stage(output, id).state, state);
  authorityUnknown(output);
});
test('unsupported discovery conflicts with a passing local report', () => {
  assert.equal(stage(reduce(fixture('unsupported')), 'preflight').state, 'MISMATCH');
});
test('different successful discovery config/version cannot reconcile preflight', () => {
  for (const field of ['version', 'config_sha256']) {
    const input = fixture();
    input.adapterDiscovery = {...input.preflight.adapter};
    input.adapterDiscovery[field] = field === 'version' ? 'different-v2' : 'd'.repeat(64);
    const output = reduce(input);
    assert.equal(stage(output, 'preflight').state, 'MISMATCH');
    authorityUnknown(output);
  }
});
test('project count, foreign cursors and message counters cannot prove selected membership', () => {
  const input = fixture();
  input.meshStatus.workers[0].project_count = 900;
  input.meshStatus.message_count = 900;
  const output = reduce(input);
  assert.match(stage(output, 'enrollment').detail, /does not identify project membership/);
  authorityUnknown(output);
});
test('missing declared host or worker cannot match enrollment', () => {
  for (const field of ['worker_id', 'host_id']) {
    const input = fixture(); delete input.intended[field];
    assert.equal(stage(reduce(input), 'enrollment').state, 'UNKNOWN');
  }
});
test('missing declared project cannot match preflight', () => {
  const input = fixture(); delete input.intended.project_id;
  assert.equal(stage(reduce(input), 'preflight').state, 'UNKNOWN');
});
test('changed worker cannot reuse observations for another worker', () => {
  const input = fixture(); input.intended.worker_id = 'other-worker';
  const output = reduce(input);
  assert.equal(stage(output, 'preflight').state, 'MISMATCH');
  assert.equal(stage(output, 'enrollment').state, 'UNKNOWN');
});
test('changed adapter or missing requested capability is a mismatch', () => {
  for (const change of [
    input => input.intended.adapter = 'hermes',
    input => input.intended.adapter_version = 'different-v2',
    input => input.intended.capabilities.push('tool.execute'),
  ]) {
    const input = fixture(); change(input);
    const output = reduce(input);
    assert.equal(stage(output, 'enrollment').state, 'MISMATCH');
    authorityUnknown(output);
  }
});
test('seat/process/profile/workspace/source/wheel cannot become bound by matching labels', () => {
  for (const field of ['seat_id', 'process_instance_id', 'profile_id', 'workspace', 'source_revision', 'wheel_sha256']) {
    const input = fixture();
    input.intended[field] = field === 'source_revision' ? 'd'.repeat(40) : field === 'wheel_sha256' ? 'e'.repeat(64) : 'different';
    const output = reduce(input);
    assert.match(output.binding, /not bound/);
    authorityUnknown(output);
    assert.equal(stage(output, 'containment').state, 'UNKNOWN');
  }
});
test('untyped ACK, accepted and generation claims are unsupported, never new proof', () => {
  for (const extra of [{ACK: true}, {accepted: true}, {generation: 2}, {proof: {eligible: true}}]) {
    const output = reduce({...fixture(), ...extra});
    assert.equal(output.valid, false);
    allUnknown(output);
  }
});
test('credential/config/profile contents and unknown fields are not retained', () => {
  for (const key of ['token', 'provider_key', 'config', 'profile']) {
    const input = fixture(); input.intended[key] = 'SYNTHETIC-SECRET';
    const output = reduce(input);
    assert.equal(output.valid, false);
    assert(!JSON.stringify(output).includes('SYNTHETIC-SECRET'));
    allUnknown(output);
  }
});
test('hostile text stays a bounded declaration, not markup or an instruction', () => {
  const input = fixture('hostile'); const output = reduce(input);
  assert.equal(output.intended.workspace, input.intended.workspace);
  authorityUnknown(output);
});
test('oversized, multiline and object declarations fail closed without echo', () => {
  for (const value of ['x'.repeat(513), 'line\nbreak', {token: 'secret'}]) {
    const input = fixture(); input.intended.workspace = value;
    const output = reduce(input);
    assert.equal(output.valid, false);
    assert.deepEqual(output.intended, {});
    allUnknown(output);
  }
});
test('unsupported snapshot qualification, duplicate IDs and impossible timestamps fail closed', () => {
  for (const change of [
    input => input.meshStatus.qualification = 'MESH_QUALIFIED',
    input => input.meshStatus.workers.push({...input.meshStatus.workers[0]}),
    input => input.meshStatus.workers[0].last_seen = input.meshStatus.at + 1,
    input => input.meshStatus.workers[0].expires_at = '2100',
    input => input.meshStatus.workers[0].project_ids = ['synthetic-project'],
    input => input.meshStatus.token = 'secret',
    input => input.preflight.adapter.supported = 'true',
  ]) {
    const input = fixture(); change(input);
    const output = reduce(input);
    assert.equal(output.valid, false);
    allUnknown(output);
  }
});
test('unknown preflight statuses cannot turn reports into acceptance', () => {
  for (const status of ['READY', 'ACK', 'PASS', 'MESH_QUALIFIED', 'ACCEPTED', 'UNKNOWN']) {
    const input = fixture(); input.preflight.status = status;
    allUnknown(reduce(input));
  }
});
test('invalid display clock cannot establish temporal status', () => {
  for (const clock of [undefined, NaN, Infinity, -1, '2000']) allUnknown(reducePreparation(fixture(), clock));
});
test('pure reducer is deterministic, does not mutate input or reuse old project data', () => {
  const input = fixture(); const original = structuredClone(input);
  const first = reduce(input);
  assert.deepEqual(input, original);
  assert.deepEqual(first, reduce(input));
  const next = reduce({intended: {project_id: 'new-project'}});
  assert.equal(stage(next, 'identity').state, 'DECLARED');
  for (const item of next.stages.filter(item => item.id !== 'identity')) assert.equal(item.state, 'UNKNOWN');
  assert(!JSON.stringify(next).includes('synthetic-worker'));
});
