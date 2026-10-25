"""In-process mesh bridge to durable provider continuity.

The caller supplies an authenticated enrollment and the original claimed work.
This does not qualify an OpenClaw remote runner or renew any authority. Whole-plan
execution admission is a different accounting contract and must not be reused here.
"""
from residual.core import ContractError, digest
from .mesh_state import MeshState
from .models import model_call


def mesh_model_call(store, worker, work, system, schema=None, *, extensions=None):
    mesh = MeshState(store)
    pid, tid = work['project_id'], work['task_id']
    placement = 'remote' if work['route'] == 'cloud' else 'local'

    def authority():
        current, project = mesh.authorize(worker, pid)
        task = store.validate_lease(pid, tid, work['lease_id'], work['fencing_token'])
        if (project.get('generation', 1) != work['generation']
                or task['attempt'] != work['attempt']
                or task['owner'] != 'mesh:' + current['worker_id']
                or task['route'] != work['route']):
            raise ContractError('authority_rescinded')
        capability = 'model.remote' if placement == 'remote' else 'model.local'
        if capability not in current['capabilities']:
            raise ContractError('authority_rescinded')
        if task.get('mesh_execution_budget') is not None:
            raise ContractError('Whole-plan admission cannot be reused for per-call continuity')

    def reserve(provider, request, meta):
        authority()
        store.reserve_mesh_attempt(pid, tid, work['lease_id'], work['fencing_token'],
                                   placement, meta['request_bytes'])

    authority()
    identity = digest({'project': pid, 'task': tid, 'attempt': work['attempt'],
                       'generation': work['generation'], 'fence': work['fencing_token'],
                       'worker': worker['worker_id'], 'packet': work['packet'],
                       'system': system, 'schema': schema})
    return model_call(store, pid, 'runner', work['packet'], system, schema,
                      work['route'], tid, invocation_id=identity,
                      authority_check=authority, reserve_attempt=reserve,
                      durable=True, extensions=extensions)
