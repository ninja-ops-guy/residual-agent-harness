/** Browser-only teaching fixture. This is NOT the Python Factory runtime. */
export const SCENARIOS = Object.freeze({
  clean: {title: 'Verified acceptance', description: 'Three scripted workers propose bounded policy changes. All required checks pass; disjoint artifacts are composed in a stable order.'},
  rejected: {title: 'Faulty candidate', description: 'The retry worker proposes twelve attempts against a maximum of three. Its check fails. Other passing work stays visible; the complete output is withheld.'},
  unknown: {title: 'Missing evidence', description: 'The timeout worker omits the required value. UNKNOWN is not a weaker PASS. The complete output stays blocked pending new evidence.'},
  conflict: {title: 'Integration conflict', description: 'Two individually passing workers propose different bytes for one shared file. The demo stops at the integration boundary instead of silently choosing a winner.'},
});
export const TASKS = Object.freeze([
  Object.freeze({id: 'retry', label: 'Bound retries', worker: 'W-01', check: 'Integer max_attempts between 1 and 3', key: 'max_attempts'}),
  Object.freeze({id: 'timeout', label: 'Set timeout', worker: 'W-02', check: 'Integer timeout_ms between 1 and 3000', key: 'timeout_ms'}),
  Object.freeze({id: 'logging', label: 'Structure logs', worker: 'W-03', check: 'log_format equals json', key: 'log_format'}),
]);

export function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
}

export function fixture(name) {
  if (!Object.hasOwn(SCENARIOS, name)) throw new Error('Unknown demo scenario');
  const candidates = [
    {task: 'retry', path: 'config/retry.json', content: {max_attempts: name === 'rejected' ? 12 : 3}},
    {task: 'timeout', path: 'config/timeout.json', content: name === 'unknown' ? {} : {timeout_ms: 2500}},
    {task: 'logging', path: 'config/logging.json', content: {log_format: 'json'}},
  ];
  if (name === 'conflict') {
    candidates[1] = {task: 'timeout', path: 'config/shared.json', content: {timeout_ms: 2500, log_format: 'text'}};
    candidates[2] = {task: 'logging', path: 'config/shared.json', content: {timeout_ms: 1500, log_format: 'json'}};
  }
  return candidates;
}

export function verify(candidate) {
  const task = TASKS.find(item => item.id === candidate.task);
  if (!task) return {status: 'FAIL', reason: 'Task is outside the demo contract.'};
  if (!candidate.content || !Object.hasOwn(candidate.content, task.key)) {
    return {status: 'UNKNOWN', reason: `Required evidence ${task.key} is absent.`};
  }
  const value = candidate.content[task.key];
  const pass = task.id === 'logging' ? value === 'json'
    : Number.isInteger(value) && value >= 1 && value <= (task.id === 'retry' ? 3 : 3000);
  return {status: pass ? 'PASS' : 'FAIL', reason: pass ? task.check : `Candidate violates: ${task.check}.`};
}

export function integrate(candidates) {
  // Recheck at the boundary. Never accept a caller-supplied "PASS" label.
  if (candidates.length !== TASKS.length || new Set(candidates.map(c => c.task)).size !== TASKS.length
      || candidates.some(candidate => verify(candidate).status !== 'PASS')) {
    return {status: 'BLOCKED', artifacts: [], conflicts: [], reason: 'Every required task must independently pass.'};
  }
  const paths = new Map();
  const conflicts = new Set();
  for (const candidate of candidates) {
    if (!/^config\/[a-z]+\.json$/.test(candidate.path)) {
      return {status: 'BLOCKED', artifacts: [], conflicts: [], reason: 'Artifact path is outside the demo contract.'};
    }
    const bytes = canonical(candidate.content);
    if (paths.has(candidate.path) && paths.get(candidate.path) !== bytes) conflicts.add(candidate.path);
    paths.set(candidate.path, bytes);
  }
  if (conflicts.size) return {status: 'CONFLICT', artifacts: [], conflicts: [...conflicts].sort(), reason: 'Different verified bytes target the same file. Human resolution is required outside this demo.'};
  return {status: 'ACCEPTED', artifacts: [...paths].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([path, content]) => ({path, content})), conflicts: [], reason: 'All required checks pass and there are no unresolved byte conflicts.'};
}

export function runScenario(name, sourceRevision = 'local-unversioned') {
  const candidates = fixture(name);
  const checks = candidates.map(candidate => ({task: candidate.task, ...verify(candidate)}));
  const integration = integrate(candidates);
  return {
    schema: 'residual.pages-simulation.v1', simulation: true, signed: false,
    runtime: 'standalone-javascript-teaching-fixture', source_revision: sourceRevision,
    scenario: name, candidates, checks, integration,
    events: [
      {sequence: 1, kind: 'demo_plan_frozen', detail: 'Three required policy checks; writes restricted to config/*.json.'},
      {sequence: 2, kind: 'scripted_candidates', detail: 'Three local fixture values. No model, sandbox, network, or worker process was invoked.'},
      ...checks.map((check, index) => ({sequence: index + 3, kind: `check_${check.status.toLowerCase()}`, detail: `${check.task}: ${check.reason}`})),
      {sequence: 6, kind: `integration_${integration.status.toLowerCase()}`, detail: integration.reason},
    ],
    limitations: ['Not a Station receipt or signature.', 'Not execution of M2/M3/M4.', 'No model-quality, speedup, cost, or reliability benchmark claim.'],
  };
}
