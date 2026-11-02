// Presentation only. These inputs are copied observations, never admitted proof.
export const DECLARATION_FIELDS = Object.freeze([
  ['worker_id', 'Worker', 128], ['host_id', 'Host', 128],
  ['seat_id', 'Seat', 128], ['process_instance_id', 'Process instance', 128],
  ['profile_id', 'Profile', 128], ['workspace', 'Workspace', 512],
  ['project_id', 'Project', 128], ['adapter', 'Adapter', 128],
  ['adapter_version', 'Adapter version', 128],
  ['source_revision', 'Source revision (40 hex)', 40],
  ['wheel_sha256', 'Wheel SHA256 (64 hex)', 64],
].map(Object.freeze));

const STAGES = Object.freeze([
  ['identity', 'Identity preparation'], ['preflight', 'Adapter preflight'],
  ['connectivity', 'Station connectivity'], ['enrollment', 'Owner enrollment'],
  ['communications', 'Two-way communications'], ['containment', 'Native containment'],
  ['eligibility', 'Mission eligibility'], ['acceptance', 'Mission acceptance'],
]);
const UNBOUND = 'Seat, process, profile, workspace, source, wheel and current authority are not bound by these reports.';
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const record = value => value !== null && typeof value === 'object' &&
  !Array.isArray(value) && [Object.prototype, null].includes(Object.getPrototypeOf(value));
const keysOnly = (value, keys) => record(value) && Object.keys(value).every(key => keys.includes(key));
const text = (value, max = 128) => typeof value === 'string' && value.length > 0 &&
  value.length <= max && !/[\u0000-\u001f\u007f]/.test(value);
const time = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const digest = (value, size) => typeof value === 'string' && new RegExp('^[a-f0-9]{' + size + '}$', 'i').test(value);
const strings = value => Array.isArray(value) && value.length <= 64 && value.every(item => text(item));

function discoveryValid(value) {
  if (!keysOnly(value, ['supported', 'reason', 'version', 'config_sha256', 'containment', 'tool_policy'])) return false;
  if (value.supported === false) {
    return ['systemd_process_tree_containment_unavailable', 'openclaw_exec_probe_failed',
      'openclaw_exec_contract_incomplete', 'openclaw_version_mismatch'].includes(value.reason) &&
      (!own(value, 'version') || text(value.version, 1024)) &&
      !['config_sha256', 'containment', 'tool_policy'].some(key => own(value, key));
  }
  return value.supported === true && !own(value, 'reason') && text(value.version, 1024) &&
    digest(value.config_sha256, 64) && value.containment === 'systemd_transient_service' &&
    value.tool_policy === 'inference_only';
}

function preflightValid(value) {
  return keysOnly(value, ['status', 'adapter', 'project_id', 'worker_id']) &&
    value.status === 'PREFLIGHT_PASS' && text(value.project_id) && text(value.worker_id) &&
    discoveryValid(value.adapter) && value.adapter.supported === true;
}

function statusValid(value) {
  if (!keysOnly(value, ['schema', 'at', 'workers', 'message_count', 'oldest_message_age_s',
    'dead_letter_count', 'cursors', 'retention', 'limits', 'qualification']) ||
    value.schema !== 'residual.sc.mesh.status/1' || !time(value.at) ||
    value.qualification !== 'health_only_not_mesh_qualification' ||
    !Array.isArray(value.workers) || value.workers.length > 500) return false;
  const names = new Set();
  return value.workers.every(worker => {
    if (!keysOnly(worker, ['worker_id', 'host_id', 'adapter', 'adapter_version', 'state',
      'project_count', 'capabilities', 'last_seen', 'expires_at']) ||
      !['worker_id', 'host_id', 'adapter', 'adapter_version', 'state'].every(key => text(worker[key])) ||
      !Number.isSafeInteger(worker.project_count) || worker.project_count < 0 ||
      !strings(worker.capabilities) || !time(worker.last_seen) || !time(worker.expires_at) ||
      worker.last_seen > value.at || names.has(worker.worker_id)) return false;
    names.add(worker.worker_id);
    return true;
  });
}

/**
 * UI-only contract: {intended, preflight?, adapterDiscovery?, meshStatus?}.
 * Observations use existing mesh_cli/discover/status shapes. No new proof schema.
 * nowSeconds is an explicit display clock, not an authorization timestamp.
 * Plain JSON data only. Extra top-level/declaration/observation keys fail closed.
 */
export function reducePreparation(input = {}, nowSeconds) {
  const stages = STAGES.map(([id, title]) => ({id, title, state: 'UNKNOWN', detail: 'No admissible evidence is supplied by this isolated view.'}));
  const result = {mode: 'read-only', integrated: false, valid: true, intended: {}, stages,
    notice: 'Not integrated. Not native-qualified. Declarations and copied reports do not authorize onboarding.',
    binding: UNBOUND};
  const set = (id, state, detail) => Object.assign(stages.find(stage => stage.id === id), {state, detail});
  const invalid = () => {
    result.valid = false;
    result.intended = {};
    for (const stage of stages) Object.assign(stage, {state: 'UNKNOWN', detail: 'Unsupported or malformed input; no report is accepted.'});
    return result;
  };
  if (!keysOnly(input, ['intended', 'preflight', 'adapterDiscovery', 'meshStatus']) || !time(nowSeconds)) return invalid();
  const intended = input.intended ?? {};
  if (!keysOnly(intended, [...DECLARATION_FIELDS.map(([key]) => key), 'capabilities'])) return invalid();
  for (const [key, , max] of DECLARATION_FIELDS) {
    if (!own(intended, key) || intended[key] === '') continue;
    if (!text(intended[key], max) ||
      (key === 'source_revision' && !digest(intended[key], 40)) ||
      (key === 'wheel_sha256' && !digest(intended[key], 64))) return invalid();
    result.intended[key] = intended[key];
  }
  if (own(intended, 'capabilities')) {
    if (!strings(intended.capabilities) || new Set(intended.capabilities).size !== intended.capabilities.length) return invalid();
    result.intended.capabilities = [...intended.capabilities];
  }
  if (Object.keys(result.intended).some(key => key !== 'capabilities')) {
    set('identity', 'DECLARED', 'Owner declarations only; identity is unverified. Missing declarations remain unspecified.');
  }
  set('preflight', 'UNKNOWN', 'No local adapter preflight report. A report cannot establish connection or current authority.');
  set('connectivity', 'UNKNOWN', 'No live connection is made. Copied health or preflight reports cannot prove present connectivity.');
  set('enrollment', 'UNKNOWN', 'No selected-worker enrollment observation. Current identity and project membership remain unverified.');
  set('communications', 'UNKNOWN', 'Counters, presence, READY and transport ACK do not establish a two-way scoped exchange.');
  set('containment', 'UNKNOWN', 'A reported containment mechanism is not native execution evidence.');
  set('eligibility', 'UNKNOWN', 'This view has no current authority, lease, generation or mission-admission evidence.');
  set('acceptance', 'UNKNOWN', 'Only ordinary Station verification and independent acceptance can establish mission acceptance.');

  if (input.preflight != null) {
    if (!preflightValid(input.preflight)) return invalid();
    const report = input.preflight;
    if (!intended.worker_id || !intended.project_id) {
      set('preflight', 'UNKNOWN', 'Select a declared worker and project before comparing the local report.');
    } else if (report.worker_id !== intended.worker_id || report.project_id !== intended.project_id) {
      set('preflight', 'MISMATCH', 'Local report names a different worker or project; it does not describe this preparation.');
    } else if (intended.adapter_version && report.adapter.version !== intended.adapter_version) {
      set('preflight', 'MISMATCH', 'Reported adapter version differs from the declaration.');
    } else {
      set('preflight', 'REPORTED', 'Local PREFLIGHT_PASS names this worker/project. Report time, host, workspace, source and wheel are unbound; freshness is unknown.');
    }
  }
  if (input.adapterDiscovery != null) {
    if (!discoveryValid(input.adapterDiscovery)) return invalid();
    if (input.adapterDiscovery.supported === false) {
      set('containment', 'UNSUPPORTED', 'Adapter discovery reports: ' + input.adapterDiscovery.reason + '. No native qualification.');
      if (input.preflight != null) set('preflight', 'MISMATCH', 'The supplied local reports conflict; no combined preflight conclusion.');
    } else if (input.preflight != null && ['version', 'config_sha256', 'containment', 'tool_policy'].some(
      key => input.adapterDiscovery[key] !== input.preflight.adapter[key])) {
      set('preflight', 'MISMATCH', 'The supplied local reports disagree on adapter configuration or version.');
    }
  }
  if (input.meshStatus != null) {
    const status = input.meshStatus;
    if (!statusValid(status)) return invalid();
    if (status.at > nowSeconds) {
      set('enrollment', 'UNKNOWN', 'Snapshot clock is ahead of the display clock; freshness is uncertain.');
      return result;
    }
    const worker = status.workers.find(row => row.worker_id === intended.worker_id);
    if (!worker || !intended.worker_id || !intended.host_id) return result;
    if (worker.host_id !== intended.host_id ||
      (intended.adapter && worker.adapter !== intended.adapter) ||
      (intended.adapter_version && worker.adapter_version !== intended.adapter_version)) {
      set('enrollment', 'MISMATCH', 'Selected-worker snapshot differs from declared host or adapter identity.');
    } else if (worker.expires_at <= nowSeconds) {
      set('enrollment', 'EXPIRED', 'The supplied enrollment snapshot has expired; no current enrollment claim.');
    } else if (worker.state === 'REVOKED') {
      set('enrollment', 'BLOCKED', 'Snapshot reports revoked enrollment. No authority is granted by this view.');
    } else if (!['ENROLLED', 'SYNCING', 'DISCONNECTED', 'READY'].includes(worker.state)) {
      set('enrollment', 'UNKNOWN', 'Snapshot state is unsupported or uncertain.');
    } else if ((intended.capabilities ?? []).some(capability => !worker.capabilities.includes(capability))) {
      set('enrollment', 'MISMATCH', 'Requested capability is absent from the supplied snapshot.');
    } else {
      set('enrollment', 'REPORTED', 'Snapshot reports ' + worker.state + ' for the declared worker/host. It is health-only and may be stale. project_count does not identify project membership.');
    }
  }
  return result;
}
