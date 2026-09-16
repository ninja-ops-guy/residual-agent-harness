"""Rejections that prevent misleading economics evidence."""
import subprocess
from unittest.mock import patch

import pytest

from residual.core import ContractError
from residual.eval_frozen.economics import fixture_observations, build_swarm5_evidence
from residual.observability.reliability import (
    CostAccounting, ReliabilityObservation, TimingBreakdown,
    build_reliability_report, pareto_inputs,
)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_measurements_are_refused_at_construction(value):
    with pytest.raises(ContractError):
        TimingBreakdown(worker_execution_ms=value, wall_clock_ms=value)
    with pytest.raises(ContractError):
        CostAccounting(api_cost_usd=value)


def test_missing_observation_hash_cannot_disable_integrity_check():
    raw = fixture_observations('1' * 40, '2' * 40)[0].payload()
    raw.pop('observation_sha256')
    raw['accepted'] = False
    with pytest.raises(ContractError, match='hash'):
        ReliabilityObservation.from_dict(raw)


def test_pareto_refuses_report_changed_after_hashing():
    report = build_reliability_report(fixture_observations('1' * 40, '2' * 40))
    report['aggregates'][0]['assr'] = 0.123
    with pytest.raises(ContractError, match='hash'):
        pareto_inputs(report)


def test_service_time_does_not_claim_observed_throughput():
    report = build_reliability_report(fixture_observations('1' * 40, '2' * 40))
    assert report['schema_version'] == 'residual.reliability-report.v2'
    assert report['overall']['throughput_runs_per_sec'] is None
    assert report['overall']['throughput_unavailable_reason'] == 'no_retained_measurement_window'
    assert report['overall']['serial_service_rate_runs_per_sec'] > 0
    assert all(row['accepted_throughput'] is None for row in pareto_inputs(report)['points'])


def test_generator_refuses_unrelated_tree_and_dirty_source(tmp_path):
    from scripts import swarm5_evidence as generator
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-b', 'main')
    git('config', 'user.email', 'fixture@example.invalid')
    git('config', 'user.name', 'Fixture')
    source = tmp_path / 'source.py'
    source.write_text('version = 1\n')
    git('add', 'source.py'); git('commit', '-m', 'parent')
    parent = git('rev-parse', 'HEAD')
    source.write_text('version = 2\n')
    git('commit', '-am', 'successor')
    with patch.object(generator, 'ROOT', tmp_path), patch.object(generator, 'build_swarm5_evidence') as build:
        build.return_value = build_swarm5_evidence('1' * 40, '2' * 40)
        with pytest.raises(ValueError, match='tree differs'):
            generator.main(['--commit', parent, '--output', str(tmp_path / 'output')])
        source.write_text('version = 3\n')
        with pytest.raises(ValueError, match='source changed'):
            generator.main(['--output', str(tmp_path / 'output')])
        build.assert_not_called()
        assert not (tmp_path / 'output').exists()
