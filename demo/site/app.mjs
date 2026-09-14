import {SCENARIOS, TASKS, runScenario} from './model.mjs';

const $ = id => document.getElementById(id);
const select = $('scenario');
let result = null;
let generation = 0;
let timer;
const revision = document.body.dataset.sourceRevision;

function text(tag, content, className = '') {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}
function badge(node, value) {
  node.textContent = value;
  node.className = `badge ${value.toLowerCase()}`;
}
function stage(index) {
  document.querySelectorAll('[data-stage]').forEach(node => node.classList.toggle('active', Number(node.dataset.stage) <= index));
}
function workers(record = null, revealChecks = false) {
  $('workers').replaceChildren(...TASKS.map(task => {
    const card = text('article', '', 'worker');
    const header = text('div', '', 'worker-header');
    const check = record?.checks.find(item => item.task === task.id);
    const mark = text('span', '');
    badge(mark, revealChecks && check ? check.status : record ? 'PROPOSED' : 'PENDING');
    header.append(text('span', task.worker, 'label'), mark);
    const candidate = record?.candidates.find(item => item.task === task.id);
    card.append(header, text('h4', task.label), text('p', task.check),
      text('pre', candidate ? JSON.stringify(candidate.content, null, 2) : 'Awaiting proposal'));
    return card;
  }));
}
function events(record, count) {
  $('events').replaceChildren(...record.events.slice(0, count).map(event => {
    const item = text('li', '');
    const content = text('div', '');
    content.append(text('span', event.kind, 'event-kind'), text('span', event.detail));
    item.append(text('span', String(event.sequence).padStart(2, '0'), 'sequence'), content);
    return item;
  }));
}
function reset() {
  generation += 1;
  clearTimeout(timer);
  result = null;
  $('run').disabled = false;
  $('reset').disabled = false;
  $('download').disabled = true;
  badge($('run-state'), 'READY');
  $('scenario-description').textContent = SCENARIOS[select.value].description;
  $('gate-title').textContent = 'No output accepted yet.';
  $('gate-detail').textContent = 'Run a scenario to inspect the checks and the integration decision.';
  $('passed-count').textContent = '—';
  $('result-preview').textContent = 'No simulation result.';
  $('events').replaceChildren(text('li', 'The demo records each step here. Nothing has run yet.', 'empty'));
  workers();
  stage(-1);
}
function finish(record) {
  result = record;
  stage(3);
  workers(record, true);
  events(record, 6);
  badge($('run-state'), record.integration.status);
  const titles = {ACCEPTED: 'Checked artifacts accepted.', BLOCKED: 'Final output withheld.', CONFLICT: 'Conflict stops the handoff.'};
  $('gate-title').textContent = titles[record.integration.status];
  $('gate-detail').textContent = record.integration.reason;
  $('passed-count').textContent = `${record.checks.filter(check => check.status === 'PASS').length} / 3`;
  $('result-preview').textContent = JSON.stringify({schema: record.schema, simulation: true, signed: false,
    outcome: record.integration.status, artifacts: record.integration.artifacts.map(item => item.path),
    conflicts: record.integration.conflicts}, null, 2);
  $('download').disabled = false;
  $('run').disabled = false;
}
function run() {
  reset();
  const ticket = generation;
  const record = runScenario(select.value, revision);
  $('run').disabled = true;
  badge($('run-state'), 'RUNNING');
  const steps = [
    () => {stage(0); events(record, 1);},
    () => {stage(1); workers(record); events(record, 2);},
    () => {stage(2); workers(record, true); events(record, 5);},
    () => finish(record),
  ];
  let current = 0;
  const delay = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 450;
  function advance() {
    if (ticket !== generation) return;
    steps[current++]();
    if (current < steps.length) timer = setTimeout(advance, delay);
  }
  advance();
}
$('run').addEventListener('click', run);
$('reset').addEventListener('click', reset);
select.addEventListener('change', reset);
$('download').addEventListener('click', () => {
  if (!result) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2) + '\n'], {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = `residual-simulation-${result.scenario}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
reset();
