"""Fail-closed R0-R5 launch preparation; no live driver is enabled here."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


class LaunchError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS='1', LC_ALL='C')
    result = subprocess.run(['git', '-C', str(repo), *args], env=env,
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise LaunchError(f'Git inspection failed: {args[0]}')
    return result.stdout.strip()


def inspect_checkout(repo: Path, expected_sha: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', expected_sha):
        raise LaunchError('merged-main SHA must be a full lowercase object ID')
    if Path(_git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo.resolve():
        raise LaunchError('repository root required')
    sha = _git(repo, 'rev-parse', 'HEAD')
    if sha != expected_sha:
        raise LaunchError('HEAD differs from supplied merged-main SHA')
    if _git(repo, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise LaunchError('dirty checkout: tracked or untracked changes')
    # Index flags can hide working-tree mutations from ordinary git status.
    flagged = _git(repo, 'ls-files', '-v').splitlines()
    if any(line and (line[0].islower() or line[0] == 'S') for line in flagged):
        raise LaunchError('assume-unchanged/skip-worktree index flags are forbidden')
    if _git(repo, 'ls-files', '--stage').startswith('160000 ') or any(
        line.startswith('160000 ') for line in _git(repo, 'ls-files', '--stage').splitlines()
    ):
        raise LaunchError('submodule qualification is unsupported')
    return {'commit': sha, 'tree': _git(repo, 'rev-parse', 'HEAD^{tree}'),
            'git_version': _git(repo, '--version'),
            'clean': True, 'merged_main_verified': False}


def checked_file(repo: Path, relative: str, expected: str) -> tuple[bytes, str]:
    if not isinstance(relative, str) or not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise LaunchError('file binding requires relative path and SHA256')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise LaunchError('file binding escapes repository')
    current = repo
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise LaunchError('symlinked inputs are forbidden')
    if not current.is_file() or current.stat().st_size > 16 * 1024 * 1024:
        raise LaunchError('missing or oversized input')
    blob = current.read_bytes()
    actual = hashlib.sha256(blob).hexdigest()
    if actual != expected:
        raise LaunchError(f'file hash mismatch: {relative}')
    return blob, actual


def namespace_probe(repo: Path) -> dict:
    """Run #81's actual M4 capability probe in a fresh process, without key env."""
    if platform.system() != 'Linux':
        return {'status': 'UNKNOWN', 'reason': 'platform_not_linux'}
    if not (repo / 'residual/factory/m4_sandbox.py').is_file():
        return {'status': 'UNKNOWN', 'reason': 'm4_probe_not_in_checkout'}
    code = ('import sys,json;sys.path.insert(0,sys.argv[1]);'
            'from residual.factory.m4_sandbox import probe_isolation;'
            'ok,reason=probe_isolation();'
            'print(json.dumps({"status":"PASS" if ok else "UNKNOWN","reason":reason}))')
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(repo)],
                                    cwd=repo, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, timeout=30,
                                    env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
            stdout.seek(0)
            raw = stdout.read(65537)
            if result.returncode or len(raw) > 65536:
                return {'status': 'ERROR', 'reason': 'm4_probe_process_failed'}
            probe = json.loads(raw)
            if probe.get('status') not in {'PASS', 'UNKNOWN'} or not isinstance(probe.get('reason'), str):
                raise ValueError('invalid probe response')
            return probe
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return {'status': 'ERROR', 'reason': 'm4_probe_unavailable'}


def qualification_claim(blob: bytes | None, checkout: dict) -> dict:
    """Validate retained evidence shape; local JSON is not remote attestation."""
    if blob is None:
        return {'status': 'UNKNOWN', 'reason': 'qualification_evidence_missing'}
    try:
        evidence = json.loads(blob)
        valid = (evidence['schema_version'] == 'residual.m4-qualification.v1'
                 and evidence['main_sha'] == checkout['commit']
                 and evidence['main_tree'] == checkout['tree']
                 and evidence['pr81_merged'] is True
                 and evidence['issue63_closed'] is True
                 and evidence['independent_audit'] == 'PASS'
                 and evidence['checks']
                 and all(check['conclusion'] == 'success' and check['run_id']
                         and check['head_sha'] == checkout['commit']
                         for check in evidence['checks']))
    except (KeyError, TypeError, ValueError):
        valid = False
    return {'status': 'RECORDED_UNAUTHENTICATED' if valid else 'UNKNOWN',
            'reason': 'external_provenance_review_required' if valid else 'invalid_qualification_evidence',
            'sha256': hashlib.sha256(blob).hexdigest()}


def prepare(repo: Path, *, merged_main_sha: str, protocol_path: str,
            protocol_sha256: str, qualification: bytes | None = None) -> dict:
    repo = repo.resolve()
    checkout = inspect_checkout(repo, merged_main_sha)
    raw, protocol_hash = checked_file(repo, protocol_path, protocol_sha256)
    from .protocol import validate_protocol
    protocol = validate_protocol(repo / protocol_path, repo, expected_sha256=protocol_hash)
    if protocol.get('schema_version') != 'residual.r0-r5.protocol.v1':
        raise LaunchError('unsupported R0-R5 protocol schema')
    configurations = protocol.get('configurations', [])
    if [config.get('id') for config in configurations] != [f'R{i}' for i in range(6)]:
        raise LaunchError('protocol must enumerate R0-R5 exactly in order')
    bindings = {}
    for name in ('workload', 'config'):
        binding = protocol.get(name)
        if binding is None and name == 'config':
            continue  # Embedded model/settings are covered by the protocol file hash.
        if not isinstance(binding, dict):
            raise LaunchError(f'missing {name} file binding')
        blob, digest = checked_file(repo, binding.get('path'), binding.get('sha256'))
        bindings[name] = {'path': binding['path'], 'sha256': digest}
        if name == 'workload':
            from .workload import FrozenWorkload
            workload = FrozenWorkload.from_json(blob.decode('utf-8'))
            if workload.manifest_hash != binding.get('manifest_hash'):
                raise LaunchError('workload manifest binding mismatch')
            bindings[name]['manifest_hash'] = workload.manifest_hash
            bindings[name]['task_count'] = len(workload.tasks)
    probe = namespace_probe(repo)
    claim = qualification_claim(qualification, checkout)
    if inspect_checkout(repo, merged_main_sha) != checkout:
        raise LaunchError('checkout changed during preparation')
    blockers = ['live_adapter_not_implemented', 'remote_qualification_not_authenticated',
                *protocol.get('blockers', [])]
    if protocol.get('frozen') is not True:
        blockers.append('protocol_not_frozen')
    if probe['status'] != 'PASS':
        blockers.append('linux_m4_namespace_probe_not_pass')
    if claim['status'] == 'UNKNOWN':
        blockers.append(claim['reason'])
    schedule = []
    for repeat, seed in enumerate(protocol['seeds']):
        block = [(task, config['id']) for task in protocol['task_population']
                 for config in configurations]
        random.Random(seed).shuffle(block)
        schedule.extend({'task_id': task, 'configuration': config,
                         'repeat': repeat, 'schedule_seed': seed, 'status': 'NOT_RUN'}
                        for task, config in block)
    return {
        'schema_version': 'residual.r0-r5.launch-preparation.v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'evidence_level': 'preparation_only', 'live_execution_enabled': False,
        'checkout': checkout, 'protocol_sha256': protocol_hash,
        'bindings': bindings, 'model': protocol.get('model'),
        'environment': {'python': sys.version, 'executable': sys.executable,
                        'platform': platform.platform(), 'machine': platform.machine()},
        'namespace_probe': probe, 'qualification': claim, 'blockers': blockers,
        'configuration_readiness': [{'id': c['id'], 'status': 'NOT_RUN',
                                     'adapter': c.get('adapter')} for c in configurations],
        'schedule': schedule, 'scheduled_denominator': len(schedule),
        'results': None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--merged-main-sha', required=True)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--protocol-sha256', required=True)
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('prepare', 'live'), default='prepare')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'live':
            raise LaunchError('live execution disabled: requires merged-main M4 qualification and reviewed R0-R5 adapters')
        if args.output.resolve().is_relative_to(args.repo.resolve()):
            raise LaunchError('write preparation evidence outside the checkout')
        evidence = prepare(args.repo, merged_main_sha=args.merged_main_sha,
                           protocol_path=args.protocol, protocol_sha256=args.protocol_sha256,
                           qualification=args.qualification.read_bytes() if args.qualification else None)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(evidence, output, indent=2, sort_keys=True)
            output.write('\n')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'launch blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
