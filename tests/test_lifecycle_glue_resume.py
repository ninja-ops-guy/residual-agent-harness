"""Track E: deterministic resume after HITL escalation.

Proof strategy: the state hash is a pure function of (run_id, step, data).
A run is suspended (checkpoint + HITL challenge), approved by an
authenticated operator, and resumed. The resumed state's hash MUST equal the
hash recorded at suspension. Every non-approved path MUST fail closed.
"""
import tempfile
import unittest

from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
from residual.core import ContractError
from residual.hitl import HITLEscalationGateway, HITLStatus
from residual.lifecycle_glue import (
    CheckpointStore,
    DeterministicResumer,
    RunState,
    Suspension,
)

KEY = b"test_key_32_bytes_long___________"
RESPONSE = "authenticated-operator-response"


def goal_spec():
    return GoalSpec(
        goal_id="g1", objective="test deterministic resume",
        success_criteria=(SuccessCriterion("c1", CheckType.MECHANICAL, "d", "e"),),
        max_passes=5, token_budget=1000, wall_clock_budget_s=60.0,
        amendment_rule=AmendmentRule(authorized_roles=("operator",)),
    )


def make_stack(d, *, authenticate=lambda challenge, response, role: response == RESPONSE):
    hitl = HITLEscalationGateway(KEY, f"{d}/hitl", validity_window_s=60,
                                 authenticate=authenticate)
    checkpoints = CheckpointStore(f"{d}/checkpoints")
    return DeterministicResumer(hitl, checkpoints)


def run_state(**kw):
    values = dict(run_id="run-1", step=3,
                  data={"cursor": 3, "pending": ["a", "b"], "flags": {"safe": True}})
    return RunState(**{**values, **kw})


def suspend(resumer, state=None):
    state = state or run_state()
    return state, resumer.suspend(state, task_id="task-1",
                                  proposed_action={"action": "restart-service"},
                                  reason="production change", goal_spec=goal_spec())


def approve(resumer, suspension):
    return resumer._hitl.verify_approval(suspension.challenge_id, RESPONSE,
                                         "operator", ("operator",))


class TestDeterministicResume(unittest.TestCase):
    def test_state_hash_identical_before_and_after_resume(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            state, suspension = suspend(resumer)
            self.assertEqual(suspension.state_hash, state.state_hash)
            self.assertEqual(approve(resumer, suspension), HITLStatus.APPROVED)
            resumed = resumer.resume(suspension)
            # The determinism proof: bit-identical state across the suspension.
            self.assertEqual(resumed.state_hash, suspension.state_hash)
            self.assertEqual(resumed, state)

    def test_resume_is_reproducible_across_processes(self):
        """A second resumer instance over the same stores reproduces the state."""
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            state, suspension = suspend(resumer)
            approve(resumer, suspension)
            resumer2 = make_stack(d)  # fresh instance, same directories
            resumed = resumer2.resume(suspension)
            self.assertEqual(resumed.state_hash, state.state_hash)

    def test_resume_denied_before_approval(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            _state, suspension = suspend(resumer)
            self.assertEqual(resumer.challenge_status(suspension), HITLStatus.PENDING)
            with self.assertRaises(ContractError):
                resumer.resume(suspension)

    def test_resume_denied_after_operator_denial(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            _state, suspension = suspend(resumer)
            status = resumer._hitl.verify_approval(suspension.challenge_id, "wrong-response",
                                                   "operator", ("operator",))
            self.assertEqual(status, HITLStatus.DENIED)
            with self.assertRaises(ContractError):
                resumer.resume(suspension)

    def test_resume_denied_for_forged_challenge(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            state, suspension = suspend(resumer)
            forged = Suspension(run_id=state.run_id,
                                checkpoint_hash=suspension.checkpoint_hash,
                                challenge_id="00000000-0000-0000-0000-000000000000",
                                state_hash=suspension.state_hash)
            with self.assertRaises(ContractError):
                resumer.resume(forged)

    def test_resume_fails_on_tampered_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            _state, suspension = suspend(resumer)
            approve(resumer, suspension)
            # Tamper: point the suspension at a checkpoint for different state.
            other = resumer._checkpoints.save("run-1", 3, {"cursor": 999})
            tampered = Suspension(run_id="run-1",
                                  checkpoint_hash=other.checkpoint_hash,
                                  challenge_id=suspension.challenge_id,
                                  state_hash=suspension.state_hash)
            with self.assertRaises(ContractError):
                resumer.resume(tampered)

    def test_resume_fails_on_missing_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d)
            _state, suspension = suspend(resumer)
            approve(resumer, suspension)
            missing = Suspension(run_id="run-1", checkpoint_hash="f" * 64,
                                 challenge_id=suspension.challenge_id,
                                 state_hash=suspension.state_hash)
            with self.assertRaises(ContractError):
                resumer.resume(missing)

    def test_no_authenticator_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            resumer = make_stack(d, authenticate=None)
            _state, suspension = suspend(resumer)
            status = resumer._hitl.verify_approval(suspension.challenge_id, RESPONSE,
                                                   "operator", ("operator",))
            self.assertEqual(status, HITLStatus.DENIED)
            with self.assertRaises(ContractError):
                resumer.resume(suspension)

    def test_run_state_validation(self):
        with self.assertRaises(ContractError):
            RunState(run_id="run-1", step=0, data={"bad": object()})


if __name__ == "__main__":
    unittest.main()
