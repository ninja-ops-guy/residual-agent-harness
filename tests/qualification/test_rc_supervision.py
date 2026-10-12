"""Injected observations only: no OS process truth, watchdog, kill or workload."""
from dataclasses import asdict, replace
import copy
import hashlib
import unittest

from scripts import qualification_rc_supervision as sup


PAYLOAD = {"fixture_operation": "completed"}
DIGEST = hashlib.sha256(sup.canonical(PAYLOAD)).hexdigest()


class Clock:
    def __init__(self): self.value = 0
    def __call__(self): return self.value


class Process:
    def __init__(self, identity):
        self.observation = {"identity": asdict(identity), "state": "alive"}
        self.calls = 0
        self.effect = None
    def poll(self):
        self.calls += 1
        if self.effect: self.effect(self)
        return self.observation


class Driver(Process):
    def __init__(self, identity):
        super().__init__(identity)
        self.observation["outcome"] = None
    def poll(self, task): return super().poll()


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.identities = [sup.ProcessIdentity("synthetic-host", i+1, "birth-"+str(i), str(i+1)*64) for i in range(3)]
        self.tasks = tuple(sup.Task("task-"+str(i), "attempt-1", "nonce-"+str(i), i, 3+i*3, DIGEST) for i in range(2))
        self.requirements = sup.Requirements("synthetic-run", *self.identities, 0, 1, 2, 0.25, self.tasks)
        self.observer, self.target = Process(self.identities[0]), Process(self.identities[1])
        self.driver = Driver(self.identities[2])
        self.controller = self.make()

    def make(self, **kwargs):
        return sup.Supervisor(self.requirements, clock=self.clock, observer=self.observer,
                              target=self.target, driver=self.driver, **kwargs)

    def outcome(self, task=0, **changes):
        selected = self.tasks[task]
        result = {"task_id": selected.task_id, "attempt_id": selected.attempt_id,
                  "nonce": selected.nonce, "sequence": selected.sequence, "result_id": "result-"+str(task),
                  "status": "succeeded", "payload": copy.deepcopy(PAYLOAD),
                  "target": asdict(self.identities[1]), "driver": asdict(self.identities[2])}
        result.update(changes)
        self.driver.observation["outcome"] = result
        return result

    def failure(self, report, reason):
        self.assertEqual(report["state"], "failed")
        self.assertEqual(report["first_failure"]["reason"], reason)
        self.assertFalse(report["rc_qualified"])

    def test_valid_correlated_results_count_acceptances_not_driver_claims(self):
        self.outcome(); first = self.controller.tick()
        self.assertEqual(first["accepted_result_count"], 1)
        self.assertEqual(first["state"], "pending")
        self.clock.value = 1; self.outcome(1)
        final = self.controller.tick()
        self.assertEqual(final["state"], "observed_complete")
        self.assertEqual(final["accepted_result_count"], 2)
        self.assertFalse(final["rc_qualified"])
        self.assertIn("external_watchdog_unverified", final["missing_capabilities"])
        self.assertIn("adapter_poll_preemption_unverified", final["missing_capabilities"])

    def test_pending_never_returning_worker_reaches_deadline_without_calling_worker(self):
        # The worker is separate in the protocol. Poll remains controllably nonblocking.
        def forbidden_workload(): raise AssertionError("workload must never be invoked here")
        self.driver.worker = forbidden_workload
        for now in (0, 1, 2):
            self.clock.value = now
            self.assertEqual(self.controller.tick()["state"], "pending")
        self.clock.value = 3
        self.failure(self.controller.tick(), "task_deadline_missed")

    def test_poll_returning_late_and_pending_missing_deadline_fail(self):
        self.driver.effect = lambda _: setattr(self.clock, "value", self.clock.value+1)
        self.failure(self.controller.tick(), "adapter_poll_budget_exceeded")
        # This fake advances a clock; it does not prove preemption of a blocked poll.

    def test_result_arriving_at_external_deadline_is_not_accepted(self):
        self.requirements = replace(self.requirements, start_at=2.8)
        self.controller = self.make(); self.clock.value = 2.8
        self.outcome()
        self.driver.effect = lambda _: setattr(self.clock, "value", 3.0)
        report = self.controller.tick()
        self.failure(report, "task_deadline_missed")
        self.assertEqual(report["accepted_result_count"], 0)

    def test_invalid_and_regressing_clock(self):
        for value in (float("nan"), float("inf"), -1, True, "0", 10**1000):
            with self.subTest(value=value):
                self.setUp(); self.clock.value = value
                self.failure(self.controller.tick(), "invalid_monotonic_time")
        self.setUp(); self.controller.tick(); self.clock.value = 1; self.controller.tick()
        self.clock.value = 0.5
        self.failure(self.controller.tick(), "monotonic_regression")

    def test_cadence_gaps_and_no_old_time_credit(self):
        self.controller.tick(); self.clock.value = 0.5
        self.failure(self.controller.tick(), "cadence_violation")
        self.setUp(); self.clock.value = 2.5
        self.failure(self.controller.tick(), "observation_gap")
        for kwargs in ({"resume_state": {}}, {"resume_state": self.controller.report()},
                       {"prior_elapsed": 1}, {"prior_elapsed": True}, {"prior_elapsed": float("nan")}):
            with self.assertRaisesRegex(ValueError, "resume_or_time_accumulation_forbidden"):
                self.make(**kwargs)

    def test_target_exit_absence_failure_cancellation_and_replacement(self):
        for state in ("exited", "absent", "failed", "cancelled"):
            with self.subTest(state=state):
                self.setUp(); self.target.observation["state"] = state
                if state == "absent": self.target.observation["identity"] = None
                self.failure(self.controller.tick(), "target_"+state)
        self.setUp(); self.target.observation["identity"]["birth_token"] = "new-generation-same-pid"
        self.failure(self.controller.tick(), "target_replaced")

    def test_role_coverage_exact_boundary_and_just_over(self):
        for delay, failed in ((0.25, False), (0.250001, True)):
            with self.subTest(delay=delay):
                self.setUp()
                self.requirements = replace(self.requirements, poll_budget=0.5)
                self.controller = self.make()
                self.controller.tick()
                self.clock.value = 1.75
                self.target.effect = lambda _: setattr(self.clock, "value", self.clock.value+delay)
                report = self.controller.tick()
                if failed:
                    self.failure(report, "observation_gap")
                    self.assertEqual(self.controller._last_observation["target"], 0)
                else:
                    self.assertEqual(report["state"], "pending")
                    self.assertEqual(self.controller._last_observation["target"], 2)
                self.assertEqual(report["accepted_result_count"], 0)

    def test_cumulative_poll_time_cannot_reset_each_roles_history(self):
        for role, start, delays in (
                ("observer", 2, (0.25, 0.25, 0)),
                ("target", 1.75, (0.25, 0.25, 0)),
                ("driver", 1.5, (0.25, 0.25, 0.25))):
            with self.subTest(role=role):
                self.setUp(); self.controller.tick(); self.outcome()
                self.clock.value = start
                for handle, delay in zip((self.observer, self.target, self.driver), delays):
                    handle.effect = lambda _, delay=delay: setattr(self.clock, "value", self.clock.value+delay)
                report = self.controller.tick()
                self.failure(report, "observation_gap")
                self.assertEqual(self.controller._last_observation[role], 0)
                self.assertEqual(report["accepted_result_count"], 0)
                self.assertEqual(self.controller._index, 0)

    def test_tick_interval_is_not_role_coverage_or_poll_budget(self):
        # Three individually legal polls can span more than one poll budget.
        for handle in (self.observer, self.target, self.driver):
            handle.effect = lambda _: setattr(self.clock, "value", self.clock.value+0.25)
        self.assertEqual(self.controller.tick()["state"], "pending")
        self.assertEqual(self.controller._last_observation,
                         {"observer": 0.25, "target": 0.5, "driver": 0.75})
        self.clock.value = 2
        self.assertEqual(self.controller.tick()["state"], "pending")
        self.assertEqual(self.controller._last_observation,
                         {"observer": 2.25, "target": 2.5, "driver": 2.75})

    def test_failed_identity_does_not_refresh_successful_observation(self):
        self.controller.tick(); self.clock.value = 1
        self.target.observation["state"] = "exited"
        self.failure(self.controller.tick(), "target_exited")
        self.assertEqual(self.controller._last_observation["target"], 0)

    def test_cancel_and_interrupt_inside_each_poll_preserve_first_failure(self):
        for action, reason in (("cancel", "cancelled_by_caller"), ("interrupt", "observer_interrupted")):
            for role in ("observer", "target", "driver"):
                for boundary in (1, 2):
                    for prior in (0, 1):
                        with self.subTest(action=action, role=role, boundary=boundary, prior=prior):
                            self.setUp()
                            if prior:
                                self.outcome(); self.controller.tick(); self.clock.value = 1
                            shared = self.outcome(prior)
                            handle = getattr(self, role)
                            trigger = handle.calls+boundary
                            latched = []
                            def fail_inside(h):
                                if h.calls == trigger:
                                    latched.append(getattr(self.controller, action)())
                                    # Returned dictionaries remain shared and mutable after cancellation.
                                    shared["payload"]["fixture_operation"] = "changed-after-failure"
                                    self.controller.interrupt(); self.controller.cancel()
                            handle.effect = fail_inside
                            report = self.controller.tick()
                            self.failure(report, reason)
                            self.assertEqual(report, latched[0])
                            self.assertEqual(report["accepted_result_count"], prior)
                            self.assertEqual(self.controller._index, prior)
                            self.assertEqual(len(self.controller._seen_results), prior)
                            calls = (self.observer.calls, self.target.calls, self.driver.calls)
                            # No subsequent role callback runs after the latch.
                            offset = prior*2+boundary-1
                            expected = tuple(offset+(i <= ("observer", "target", "driver").index(role))
                                             for i in range(3))
                            self.assertEqual(calls, expected)
                            self.assertEqual(self.controller.tick(), report)

    def test_cancel_and_interrupt_inside_every_clock_callback(self):
        for action, reason in (("cancel", "cancelled_by_caller"), ("interrupt", "observer_interrupted")):
            for trigger in range(1, 14):
                with self.subTest(action=action, clock_call=trigger):
                    self.setUp(); self.outcome()
                    calls = 0
                    def clock():
                        nonlocal calls
                        calls += 1
                        if calls == trigger: getattr(self.controller, action)()
                        return self.clock.value
                    self.controller._clock = clock
                    report = self.controller.tick()
                    self.failure(report, reason)
                    self.assertEqual(calls, trigger)
                    self.assertEqual(report["accepted_result_count"], 0)
                    self.assertEqual(self.controller._index, 0)

    def test_callback_failure_then_exception_preserves_latch(self):
        self.outcome()
        def fail_then_raise(_):
            self.controller.cancel()
            raise RuntimeError("untrusted callback failure")
        self.driver.effect = fail_then_raise
        report = self.controller.tick()
        self.failure(report, "cancelled_by_caller")
        self.assertEqual(report["accepted_result_count"], 0)
        self.assertEqual(self.controller._index, 0)

    def test_healthy_observer_does_not_mask_target_exit_at_completion_boundary(self):
        self.outcome()
        def exit_on_second(handle):
            if handle.calls == 2: handle.observation["state"] = "exited"
        self.target.effect = exit_on_second
        report = self.controller.tick()
        self.failure(report, "target_exited")
        self.assertEqual(report["accepted_result_count"], 0)

    def test_driver_absence_replacement_and_boundary_exit(self):
        self.driver.observation["state"] = "absent"
        self.failure(self.controller.tick(), "driver_absent")
        self.setUp(); self.driver.observation["identity"]["birth_token"] = "new"
        self.failure(self.controller.tick(), "driver_replaced")
        self.setUp(); self.outcome()
        self.driver.effect = lambda h: h.observation.update(state="exited") if h.calls == 2 else None
        self.failure(self.controller.tick(), "driver_exited")

    def test_observer_restart_interruption_and_first_failure_preserved(self):
        self.observer.observation["identity"]["birth_token"] = "restarted"
        first = self.controller.tick()
        self.failure(first, "observer_replaced")
        self.controller.cancel(); self.controller.interrupt(); self.clock.value = 100
        self.assertEqual(self.controller.tick()["first_failure"], first["first_failure"])
        self.setUp()
        self.observer.effect = lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
        self.failure(self.controller.tick(), "observer_interrupted")

    def test_cancellation_never_claims_process_termination(self):
        report = self.controller.cancel()
        self.failure(report, "cancelled_by_caller")
        self.assertEqual(self.target.calls, 0)
        self.assertEqual(self.driver.calls, 0)
        self.assertEqual(self.controller.tick(), report)

    def test_stale_duplicate_wrong_attempt_and_process_correlations(self):
        for changes in ({"task_id": "wrong"}, {"attempt_id": "attempt-0"}, {"nonce": "stale"},
                        {"sequence": True}, {"sequence": 1}):
            with self.subTest(changes=changes):
                self.setUp(); self.outcome(**changes)
                self.failure(self.controller.tick(), "stale_or_wrong_attempt_result")
        self.setUp(); self.outcome(); self.controller.tick(); self.clock.value = 1
        self.outcome(1, result_id="result-0")
        self.failure(self.controller.tick(), "duplicate_result")
        self.setUp(); wrong = asdict(self.identities[1]); wrong["birth_token"] = "replaced"
        self.outcome(target=wrong)
        self.failure(self.controller.tick(), "result_process_identity_mismatch")

    def test_failed_missing_fabricated_count_and_wrong_payload_claims(self):
        for state in ("failed", "cancelled", "missing", "unknown"):
            with self.subTest(state=state):
                self.setUp(); self.outcome(status=state)
                self.failure(self.controller.tick(), "task_result_not_successful")
        self.setUp(); self.outcome(completed_count=1000)
        self.failure(self.controller.tick(), "invalid_clock_or_adapter_observation")
        self.setUp(); self.outcome(payload={"fabricated": 1})
        self.failure(self.controller.tick(), "result_payload_mismatch")
        self.setUp(); self.driver.observation.pop("outcome")
        self.failure(self.controller.tick(), "invalid_clock_or_adapter_observation")

    def test_snapshots_do_not_retain_untrusted_aliases(self):
        outcome = self.outcome(); report = self.controller.tick()
        outcome["result_id"] = "mutated"; outcome["payload"]["fixture_operation"] = "changed"
        report["accepted"].clear()
        current = self.controller.report()
        self.assertEqual(current["accepted_result_count"], 1)
        self.assertEqual(current["accepted"][0]["result_id"], "result-0")
        self.assertEqual(current["accepted"][0]["payload_sha256"], DIGEST)

    def test_boundary_result_mutation_rejected(self):
        self.outcome()
        def change(handle):
            if handle.calls == 2: handle.observation["outcome"]["result_id"] = "changed"
        self.driver.effect = change
        self.failure(self.controller.tick(), "driver_result_changed")

    def test_selection_requires_finite_explicit_time_and_generation_identity(self):
        for changes in ({"cadence": 0}, {"maximum_gap": float("inf")}, {"poll_budget": -1},
                        {"target": self.identities[0]}, {"tasks": []}, {"start_at": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.requirements, **changes)
        with self.assertRaises(ValueError): replace(self.identities[1], birth_token="")
        with self.assertRaises(ValueError): replace(self.identities[1], pid=True)
        with self.assertRaises(ValueError):
            replace(self.requirements, target=replace(self.identities[0], birth_token="different-birth-same-pid"))
        with self.assertRaises(ValueError): replace(self.requirements, tasks=(self.tasks[0], self.tasks[0]))

    def test_adapter_exceptions_are_sanitized(self):
        self.driver.effect = lambda _: (_ for _ in ()).throw(RuntimeError("SECRET https://signed.invalid"))
        report = self.controller.tick()
        self.failure(report, "invalid_clock_or_adapter_observation")
        self.assertNotIn("SECRET", str(report))
        self.assertNotIn("https:", str(report))


if __name__ == "__main__":
    unittest.main()
