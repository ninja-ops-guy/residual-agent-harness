"""Preparation tests use tiny disposable Git repositories and never call providers."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from residual.eval import launch

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'docs/evaluation/r0-r5.protocol.json'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


@pytest.fixture
def checkout(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.email', 'test@example.invalid')
    git(repo, 'config', 'user.name', 'Fixture')
    for name in (PROTOCOL, 'docs/evaluation/r0-r5.fixture-workload.json'):
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'fixture')
    return repo


def options(repo):
    return dict(merged_main_sha=git(repo, 'rev-parse', 'HEAD'),
                protocol_path=PROTOCOL,
                protocol_sha256=hashlib.sha256((repo / PROTOCOL).read_bytes()).hexdigest())


def test_preparation_records_full_schedule_without_results(checkout):
    report = launch.prepare(checkout, **options(checkout))
    protocol = json.loads((checkout / PROTOCOL).read_bytes())
    assert report['results'] is None
    assert report['live_execution_enabled'] is False
    assert report['namespace_probe']['status'] == 'UNKNOWN'
    assert report['qualification']['status'] == 'UNKNOWN'
    assert report['checkout']['merged_main_verified'] is False
    assert report['scheduled_denominator'] == 6 * protocol['repetitions'] * len(protocol['task_population'])
    assert all(item['status'] == 'NOT_RUN' for item in report['schedule'])
    assert len({(i['task_id'], i['configuration'], i['repeat']) for i in report['schedule']}) == report['scheduled_denominator']
    assert report['schedule'] == launch.prepare(checkout, **options(checkout))['schedule']


@pytest.mark.parametrize('mutation', ['tracked', 'untracked', 'hidden_index'])
def test_dirty_and_hidden_changes_refused(checkout, mutation):
    args = options(checkout)
    if mutation == 'untracked':
        (checkout / 'extra.txt').write_text('dirty')
    else:
        if mutation == 'hidden_index':
            git(checkout, 'update-index', '--assume-unchanged', PROTOCOL)
        with (checkout / PROTOCOL).open('a') as stream:
            stream.write(' ')
    with pytest.raises(launch.LaunchError, match='dirty|index flags'):
        launch.prepare(checkout, **args)


def test_exact_head_and_hash_required(checkout):
    args = options(checkout)
    with pytest.raises(launch.LaunchError, match='HEAD differs'):
        launch.prepare(checkout, **(args | {'merged_main_sha': 'a' * 40}))
    with pytest.raises(launch.LaunchError, match='full lowercase'):
        launch.prepare(checkout, **(args | {'merged_main_sha': args['merged_main_sha'][:7]}))
    with pytest.raises(launch.LaunchError, match='hash mismatch'):
        launch.prepare(checkout, **(args | {'protocol_sha256': 'a' * 64}))


@pytest.mark.parametrize('relative', ['../external.json', '/tmp/external.json'])
def test_paths_cannot_escape(checkout, relative):
    with pytest.raises(launch.LaunchError, match='escapes'):
        launch.checked_file(checkout, relative, 'a' * 64)


def test_symlink_inputs_refused(checkout):
    source = checkout / PROTOCOL
    other = checkout / 'copy.json'
    other.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(other)
    with pytest.raises(launch.LaunchError, match='symlinked'):
        launch.checked_file(checkout, PROTOCOL, hashlib.sha256(other.read_bytes()).hexdigest())


def test_self_asserted_qualification_cannot_enable_live(checkout, monkeypatch):
    args = options(checkout)
    identity = launch.inspect_checkout(checkout, args['merged_main_sha'])
    claim = json.dumps({'schema_version': 'residual.m4-qualification.v1',
                       'main_sha': identity['commit'], 'main_tree': identity['tree'],
                       'pr81_merged': True, 'issue63_closed': True,
                       'independent_audit': 'PASS',
                       'checks': [{'head_sha': identity['commit'], 'run_id': 1,
                                   'conclusion': 'success'}]}).encode()
    monkeypatch.setattr(launch, 'namespace_probe', lambda repo: {'status': 'PASS', 'reason': 'fixture'})
    report = launch.prepare(checkout, qualification=claim, **args)
    assert report['qualification']['status'] == 'RECORDED_UNAUTHENTICATED'
    assert report['live_execution_enabled'] is False
    assert 'remote_qualification_not_authenticated' in report['blockers']
    bad = json.loads(claim)
    bad['checks'][0]['conclusion'] = 'skipped'
    assert launch.qualification_claim(json.dumps(bad).encode(), identity)['status'] == 'UNKNOWN'
    bad['checks'][0]['conclusion'] = 'success'
    bad['main_tree'] = 'a' * 40
    assert launch.qualification_claim(json.dumps(bad).encode(), identity)['status'] == 'UNKNOWN'


def test_live_switch_always_rejected_before_preparation(tmp_path, monkeypatch):
    monkeypatch.setattr(launch, 'prepare', lambda *a, **kw: pytest.fail('live reached preparation'))
    assert launch.main(['--mode', 'live', '--merged-main-sha', 'a' * 40,
                        '--protocol', 'unused', '--protocol-sha256', 'b' * 64,
                        '--output', str(tmp_path / 'output.json')]) == 2
    assert not (tmp_path / 'output.json').exists()


def test_cli_output_is_exclusive_and_outside_checkout(checkout, tmp_path):
    args = options(checkout)
    output = tmp_path / 'preparation.json'
    command = ['--repo', str(checkout), '--merged-main-sha', args['merged_main_sha'],
               '--protocol', PROTOCOL, '--protocol-sha256', args['protocol_sha256'],
               '--output', str(output)]
    assert launch.main(command) == 0
    content = output.read_bytes()
    assert launch.main(command) == 2
    assert output.read_bytes() == content
    assert launch.main(command[:-1] + [str(checkout / 'output.json')]) == 2


def test_namespace_failure_stays_unknown(checkout, monkeypatch):
    monkeypatch.setattr(launch.platform, 'system', lambda: 'Darwin')
    assert launch.namespace_probe(checkout) == {'status': 'UNKNOWN', 'reason': 'platform_not_linux'}


def test_frozen_flag_is_not_a_live_authorization(checkout):
    protocol = json.loads((checkout / PROTOCOL).read_text())
    protocol['frozen'] = True
    (checkout / PROTOCOL).write_text(json.dumps(protocol))
    git(checkout, 'add', '.')
    git(checkout, 'commit', '-qm', 'invalid freeze')
    with pytest.raises(ValueError, match='cannot qualify live'):
        launch.prepare(checkout, **options(checkout))
