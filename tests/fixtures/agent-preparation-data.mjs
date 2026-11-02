// Synthetic only. Shapes are copied from #559 mesh_cli/discover/status contracts.
export const DISPLAY_TIME = 2000;
export function fixture(name = 'reported') {
  const adapter = {supported: true, version: 'synthetic-v1', config_sha256: 'a'.repeat(64),
    containment: 'systemd_transient_service', tool_policy: 'inference_only'};
  const input = {
    intended: {worker_id: 'synthetic-worker', host_id: 'synthetic-host', seat_id: 'synthetic-seat',
      process_instance_id: 'synthetic-process', profile_id: 'synthetic-profile',
      workspace: '/synthetic/workspace', project_id: 'synthetic-project', adapter: 'openclaw-exec',
      adapter_version: 'synthetic-v1', source_revision: 'b'.repeat(40), wheel_sha256: 'c'.repeat(64),
      capabilities: ['comms.read']},
    preflight: {status: 'PREFLIGHT_PASS', adapter, project_id: 'synthetic-project', worker_id: 'synthetic-worker'},
    meshStatus: {schema: 'residual.sc.mesh.status/1', at: 1990,
      workers: [{worker_id: 'synthetic-worker', host_id: 'synthetic-host', adapter: 'openclaw-exec',
        adapter_version: 'synthetic-v1', state: 'READY', project_count: 1, capabilities: ['comms.read'],
        last_seen: 1980, expires_at: 2100}],
      message_count: 4, oldest_message_age_s: 20, dead_letter_count: 0,
      cursors: [{worker_id: 'synthetic-worker', project: 'other-project', seq: 4, updated_at: 1980}],
      retention: [], limits: {project_messages: 5000, bulk_messages: 200, dead_letters: 1000, replay_age_s: 86400},
      qualification: 'health_only_not_mesh_qualification'},
  };
  if (name === 'empty') return {};
  if (name === 'expired') input.meshStatus.workers[0].expires_at = DISPLAY_TIME;
  if (name === 'wrong-project') input.preflight.project_id = 'foreign-project';
  if (name === 'wrong-host') input.meshStatus.workers[0].host_id = 'foreign-host';
  if (name === 'revoked') input.meshStatus.workers[0].state = 'REVOKED';
  if (name === 'uncertain') input.meshStatus.workers[0].state = 'UNKNOWN';
  if (name === 'unsupported') input.adapterDiscovery = {supported: false, reason: 'systemd_process_tree_containment_unavailable'};
  if (name === 'hostile') input.intended.workspace = '<img src="/unexpected" onerror="window.preparationAttack=1">';
  if (name === 'credential-extra') input.intended.token = 'SYNTHETIC-SECRET-MUST-NOT-RENDER';
  if (name === 'future') input.meshStatus.at = DISPLAY_TIME + 1;
  return input;
}
