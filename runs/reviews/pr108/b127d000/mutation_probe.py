"""Run one independent reversion attack, entirely in memory.

No reviewed source, protected test or ownership baseline is edited. Expected
exit 1 means pytest assertions caught the mutant; exit 2/error is NOT a kill.
Run from the exact checkout: python PATH/mutation_probe.py CASE XML_PATH.
"""
import dataclasses
import inspect
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import pytest
from residual.factory import m4_integrator, m4_safety, runtime, runtime_journal
from residual.factory.termination_provenance import ProcessControl

case, xml_path = sys.argv[1:]
adv = 'tests/test_sandbox_timing_adversarial.py::'
det = 'tests/test_sandbox_timing_determinism.py::'


def replace_method(owner, name, old, new, module):
    source = textwrap.dedent(inspect.getsource(getattr(owner, name)))
    assert source.count(old) == 1, (case, 'mutation point changed')
    scope = dict(vars(module))
    exec(compile(source.replace(old, new), '<lane2-mutant-' + case + '>', 'exec'), scope)
    setattr(owner, name, scope[name])


if case == 'B1_signed_payload_key':
    original = m4_integrator.VerificationResult.to_dict
    def changed(self):
        return dict(original(self), timed_out=self.timed_out)
    m4_integrator.VerificationResult.to_dict = changed
    selected = [adv + 'ReceiptSchemaStabilityTests']
elif case == 'B2_deadline_after_first_read':
    replace_method(runtime.FactoryRuntime, '_lease_denial',
                   'deadline = self._clock() + self.LEASE_UNKNOWN_DEADLINE_S\n'
                   '    read = self.journal.lease_read(contract, deadline=deadline, clock=self._clock)',
                   'read = self.journal.lease_read(contract)\n'
                   '    deadline = self._clock() + self.LEASE_UNKNOWN_DEADLINE_S', runtime)
    selected = [adv + 'LeaseUnknownDeadlineTests']
elif case == 'B3_stopped_before_reap':
    original = ProcessControl.kill
    def changed(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.stopped.set()
    ProcessControl.kill = changed
    selected = [adv + 'ReapTimeoutSemanticsTests']
elif case == 'B4_shared_diagnostic':
    original = runtime_journal.RuntimeJournal.lease_read
    class SharedDiagnostic:
        def __init__(self, state, journal):
            self.state, self.journal = state, journal
        @property
        def diag(self):
            return self.journal._review_shared_diag
    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        self._review_shared_diag = result.diag
        return SharedDiagnostic(result.state, self)
    runtime_journal.RuntimeJournal.lease_read = changed
    selected = [adv + 'LeaseDiagAttributionTests']
elif case == 'B5_signal_exit_for_timeout':
    original = m4_safety.run_trusted_fixture
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        return dataclasses.replace(result, returncode=-9) if result.timed_out else result
    m4_safety.run_trusted_fixture = changed
    selected = [adv + 'FixtureTimeoutContractTests']
elif case == 'CI_single_shot_reader':
    def changed(self, query, params=(), *, row_factory=None):
        with self._connect() as db:
            if row_factory is not None:
                db.row_factory = row_factory
            return db.execute(query, params).fetchall()
    runtime_journal.RuntimeJournal._read = changed
    selected = [det + 'JournalContentionReadTests::test_observations_retry_transient_lock_then_succeed']
elif case == 'H2_recompute_deadline':
    replace_method(runtime.FactoryRuntime, '_watch', 'memory_at = lease_at = 0.0',
                   'deadline = self._clock() + contract.wall_clock_budget_s\n'
                   '    memory_at = lease_at = 0.0', runtime)
    selected = [det + 'WatchdogDeadlineSnapshotTests']
elif case == 'M6_silent_reap_timeout':
    from residual.factory import termination_provenance
    replace_method(ProcessControl, 'kill', 'self.reap_timed_out.set()',
                   'return  # old silent timeout behavior', termination_provenance)
    selected = [det + 'ReapTimeoutProvenanceTests::test_reap_timeout_emits_typed_event_and_reason']
else:
    raise SystemExit('Unknown mutation case')

print('MUTATION', case, 'TESTS', selected, flush=True)
raise SystemExit(pytest.main([*selected, '-vv', '--tb=short', '--junitxml=' + xml_path]))
