import contextlib
import dataclasses
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from residual.config import build_harness, load_config
from residual.core import Artifact, ContractError, Obligation, Registry, Task, Verdict, canonical
from residual.engine import Harness, Limits
from residual.providers import CallableProvider, Prices, ProviderError, Reply, Usage
from residual.storage import Cache
from residual.study import (MeteredProvider, StudyBudget, load_suite, main, make_protocol,
                            paired_intervals, read_jsonl, report_study, run_study,
                            schedule, summarize_rows, write_json)
from residual.study_tasks import StudyFixtureProvider, expression, grade, register


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "examples/study-fixture.toml")


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "examples/study", self.root / "suite")
        self.suite = self.root / "suite/suite.json"

    def protocol(self, **changes):
        args = dict(suite_path=self.suite, config=CONFIG, modes=["cascade", "residual"],
                    repeats=2, seed=17, max_calls=1000, max_remote_bytes=1_000_000)
        args.update(changes)
        return make_protocol(**args)

    def lock(self, **changes):
        path = self.root / "lock.json"
        write_json(path, {"suite": "suite/suite.json", "protocol": self.protocol(**changes)})
        return path

    def mutate_suite(self, change):
        data = json.loads(self.suite.read_text())
        change(data)
        write_json(self.suite, data)

    def test_schedule_pairs_every_case_repeat_mode_once(self):
        p = self.protocol()
        rows = schedule(p)
        self.assertEqual(rows, schedule(p))
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({(r['case_id'], r['repeat'], r['mode']) for r in rows}), 24)
        self.assertNotEqual(rows, schedule(self.protocol(seed=18)))
        self.assertNotIn("affine-dev", {r["case_id"] for r in rows})

    def test_family_overlap_rejected(self):
        self.mutate_suite(lambda d: d["cases"][1].update(family="affine"))
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_duplicate_case_rejected(self):
        self.mutate_suite(lambda d: d["cases"].append(dict(d["cases"][0])))
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_duplicate_task_under_another_case_rejected(self):
        self.mutate_suite(lambda d: d["cases"][1].update(task=d["cases"][0]["task"]))
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_renamed_identical_task_rejected(self):
        duplicate = json.loads((self.root / "suite/affine-dev/task.json").read_text())
        duplicate["id"] = "new-name"
        write_json(self.root / "suite/quadratic/task.json", duplicate)
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_path_escape_rejected(self):
        self.mutate_suite(lambda d: d["cases"][0].update(grader="../outside.json"))
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside.json"
        shutil.copy(self.root / "suite/quadratic/grader.json", outside)
        target = self.root / "suite/quadratic/grader.json"
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_grader_cannot_be_task_artifact(self):
        path = self.root / "suite/quadratic/task.json"
        data = json.loads(path.read_text())
        data["artifacts"] = [{"id": "requirements", "path": "grader.json", "cloud": True}]
        write_json(path, data)
        with self.assertRaises(ContractError):
            load_suite(self.suite)

    def test_grader_target_and_kind_validated_before_dispatch(self):
        for value in ({"kind": "exact", "values": {"missing": 1}}, {"kind": "python", "source": "pass"}):
            write_json(self.root / "suite/quadratic/grader.json", value)
            with self.assertRaises(ContractError):
                self.protocol()

    def test_invalid_limits_modes_and_secrets_rejected(self):
        for change in ({"repeats": 0}, {"seed": True}, {"max_calls": 0}, {"local_cost_per_hour": float("nan")},
                       {"modes": ["residual", "residual"]}, {"modes": ["imaginary"]},
                       {"config": {**CONFIG, "local": {"kind": "ollama", "api_key": "never-store-this"}}}):
            with self.subTest(change=change), self.assertRaises(ContractError):
                self.protocol(**change)

    def test_freeze_does_not_make_provider_calls(self):
        with patch("residual.study.build_harness", side_effect=AssertionError("provider construction")):
            self.lock()

    def test_changed_grader_refuses_before_dispatch(self):
        lock = self.lock()
        write_json(self.root / "suite/quadratic/grader.json", {"kind": "exact", "values": {"expression": "changed"}})
        with patch("residual.study.build_harness") as build, self.assertRaises(ContractError):
            run_study(lock, self.root / "out")
        build.assert_not_called()

    def test_changed_code_refuses_before_dispatch(self):
        lock = self.lock()
        with patch("residual.study.sources", return_value={"changed": "code"}), self.assertRaises(ContractError):
            run_study(lock, self.root / "out")

    def test_lock_tamper_rejected(self):
        path = self.lock()
        data = json.loads(path.read_text())
        data["protocol"]["repeats"] += 1
        write_json(path, data)
        with self.assertRaises(ContractError):
            run_study(path, self.root / "out")

    def test_end_to_end_separates_acceptance_and_success(self):
        out = self.root / "out"
        report = run_study(self.lock(), out)
        self.assertTrue(report["simulation"])
        self.assertEqual(report["scheduled_runs"], 24)
        self.assertEqual(report["recorded_runs"], 24)
        weak = [r for r in report["runs"] if r["case_id"] == "weak-composition"]
        self.assertTrue(all(r["controller_success"] and not r["success"] for r in weak))
        dead = [r for r in report["runs"] if r["case_id"] == "frozen-dead-end"]
        self.assertTrue(all(not r["controller_success"] for r in dead))
        joint = [r for r in report["runs"] if r["case_id"] == "joint-choice"]
        self.assertTrue(all(r["success"] for r in joint))
        self.assertTrue(all(s["total_cost_usd"] is None for s in report["summary"]))
        self.assertEqual(report, report_study(out))

    def test_private_grader_is_never_in_model_packet_or_feedback(self):
        path = self.root / "suite/quadratic/grader.json"
        secret = "PRIVATE_GRADER_SENTINEL_71ee"
        write_json(path, {"kind": "exact", "values": {"expression": secret}})
        packets = []
        original = StudyFixtureProvider.generate

        def record(provider, packet, maximum):
            packets.append(canonical(packet))
            return original(provider, packet, maximum)

        with patch.object(StudyFixtureProvider, "generate", record):
            run_study(self.lock(), self.root / "out")
        self.assertTrue(packets)
        self.assertNotIn(secret, "\n".join(packets))

    def test_budget_exhaustion_retains_every_scheduled_denominator(self):
        report = run_study(self.lock(max_calls=1), self.root / "out")
        self.assertEqual(report["reserved_calls"], 1)
        self.assertEqual(len(report["runs"]), 24)
        self.assertTrue(any(r["status"] == "not_run_budget" for r in report["runs"]))
        self.assertTrue(all(not s["complete"] and s["total_cost_usd"] is None for s in report["summary"]))

    def test_missing_run_is_reported_as_incomplete(self):
        out = self.root / "out"
        run_study(self.lock(), out)
        lines = (out / "runs.jsonl").read_text().splitlines()
        (out / "runs.jsonl").write_text("\n".join(lines[:-1]) + "\n")
        report = report_study(out)
        self.assertEqual(report["recorded_runs"], 23)
        self.assertEqual(report["scheduled_runs"], 24)
        self.assertTrue(any(r["status"] == "not_recorded" for r in report["runs"]))

    def test_missing_call_completion_preserves_unknown_cost(self):
        out = self.root / "out"
        run_study(self.lock(), out)
        events = read_jsonl(out / "calls.jsonl")
        drop = next(e for e in events if e["event"] == "finished")
        (out / "calls.jsonl").write_text("\n".join(canonical(e) for e in events if e is not drop) + "\n")
        report = report_study(out)
        self.assertEqual(report["missing_call_completions"], 1)
        self.assertTrue(any(s["calls_without_usage"] for s in report["summary"]))

    def test_duplicate_run_receipt_rejected(self):
        out = self.root / "out"
        run_study(self.lock(), out)
        path = out / "runs.jsonl"
        path.write_text(path.read_text() + path.read_text().splitlines()[0] + "\n")
        with self.assertRaises(ContractError):
            report_study(out)

    def test_call_reservation_mismatch_rejected(self):
        out = self.root / "out"
        run_study(self.lock(), out)
        events = read_jsonl(out / "calls.jsonl")
        next(e for e in events if e["event"] == "finished")["request_bytes"] += 1
        (out / "calls.jsonl").write_text("\n".join(map(canonical, events)) + "\n")
        with self.assertRaises(ContractError):
            report_study(out)

    def test_deleted_call_journal_cannot_turn_inference_into_free_work(self):
        out = self.root / "out"
        run_study(self.lock(), out)
        (out / "calls.jsonl").unlink()
        with self.assertRaises(ContractError):
            report_study(out)

    def test_changed_result_or_trace_cannot_be_reused_as_evidence(self):
        out = self.root / "out"
        report = run_study(self.lock(), out)
        run_id = report["runs"][0]["run_id"]
        path = out / run_id / "result.json"
        value = json.loads(path.read_text())
        value["success"] = not value["success"]
        write_json(path, value)
        with self.assertRaises(ContractError):
            report_study(out)

    def test_output_directory_cannot_be_overwritten(self):
        out = self.root / "out"
        lock = self.lock()
        run_study(lock, out)
        with self.assertRaises(FileExistsError):
            run_study(lock, out)

    def test_cli_freeze_run_and_report(self):
        lock, out = self.root / "cli.json", self.root / "cli-out"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["freeze", "--suite", str(self.suite), "--config", str(ROOT / "examples/study-fixture.toml"),
                "--output", str(lock), "--repeats", "1", "--modes", "residual"]), 0)
            self.assertEqual(main(["run", "--lock", str(lock), "--output", str(out)]), 0)
            self.assertEqual(main(["report", str(out)]), 0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["freeze", "--suite", str(self.suite), "--config", str(ROOT / "examples/study-fixture.toml"),
                "--output", str(lock)]), 1)

    def test_cluster_bootstrap_uses_families_not_repeat_count(self):
        p = self.protocol(repeats=20)
        rows = [{**j, "success": j["mode"] == "residual"} for j in schedule(p)]
        comparison = paired_intervals(rows, p)[0]
        self.assertEqual(comparison["families"], 6)
        self.assertEqual(comparison["pairs"], 120)
        self.assertEqual(comparison["family_bootstrap_95_interval"], [1, 1])


class StudyAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = Path(self.tmp.name) / "calls.jsonl"

    def test_reserve_before_transport_and_do_not_refund_failures(self):
        budget = StudyBudget(1, 10000, self.journal)

        def fail(packet, maximum):
            self.assertEqual(read_jsonl(self.journal)[0]["event"], "reserved")
            raise RuntimeError("PRIVATE_EXCEPTION_BODY")

        provider = MeteredProvider(CallableProvider("failing", fail, "remote"), budget, "r", "expert")
        with self.assertRaises(RuntimeError):
            provider.generate({}, 10)
        with self.assertRaises(ProviderError):
            provider.generate({}, 10)
        self.assertEqual(budget.calls, 1)
        self.assertNotIn("PRIVATE_EXCEPTION_BODY", self.journal.read_text())
        self.assertIsNone(provider.records[0]["cost_usd"])

    def test_remote_byte_limit_blocks_before_transport(self):
        budget = StudyBudget(10, 1, self.journal)
        with patch.object(StudyFixtureProvider, "generate") as transport:
            provider = MeteredProvider(StudyFixtureProvider("expert"), budget, "r", "expert")
            with self.assertRaises(ProviderError):
                provider.generate({}, 10)
            transport.assert_not_called()
        self.assertEqual(budget.calls, 0)

    def rows(self):
        return [{"run_id": "a", "mode": "residual", "status": "completed", "controller_success": True,
                 "success": True, "elapsed_ms": 3600000},
                {"run_id": "b", "mode": "residual", "status": "completed", "controller_success": False,
                 "success": False, "elapsed_ms": 3600000}]

    def test_failed_runs_costs_are_in_success_denominator(self):
        calls = [{"run_id": rid, "cost_usd": cost, "usage": {"source": "reported", "input_tokens": 1, "output_tokens": 2},
                  "placement": "remote", "request_bytes": 100} for rid, cost in (("a", 2), ("b", 4))]
        p = {"modes": ["residual"], "local_cost_per_hour_usd": 1}
        s = summarize_rows(self.rows(), calls, p)[0]
        self.assertEqual(s["total_cost_per_success_usd"], 8)
        self.assertEqual(s["success_rate"], .5)

    def test_unknown_usage_cost_and_local_rate_stay_unknown(self):
        call = {"run_id": "b", "cost_usd": None, "usage": None, "placement": "remote", "request_bytes": 100}
        s = summarize_rows(self.rows(), [call], {"modes": ["residual"], "local_cost_per_hour_usd": None})[0]
        self.assertIsNone(s["total_cost_per_success_usd"])
        self.assertFalse(s["usage_complete"])
        self.assertEqual(s["calls_without_usage"], 1)

    def test_all_failure_has_no_cost_per_success(self):
        rows = self.rows()
        rows[0]["success"] = False
        s = summarize_rows(rows, [], {"modes": ["residual"], "local_cost_per_hour_usd": 1})[0]
        self.assertIsNone(s["total_cost_per_success_usd"])

    def test_priced_receipt_uses_provider_reported_usage(self):
        p = CallableProvider("priced", lambda p, m: Reply("{}", Usage(100, 10, 40, "reported")), "remote", Prices(2, 4, .5))
        meter = MeteredProvider(p, StudyBudget(1, 10000, self.journal), "r", "expert")
        meter.generate({}, 100)
        self.assertAlmostEqual(meter.records[0]["cost_usd"], .00018)


class StudyControlTests(unittest.TestCase):
    def task(self):
        return Task("counterexample-test", "Produce 2", {}, (Obligation("answer", "Produce 2", "two"),))

    def registry(self):
        r = Registry()
        r.check("two", lambda v, c: Verdict.passed() if v == 2 else Verdict.fail("wrong", "Try 2"), "1")
        return r

    def test_no_feedback_ablates_feedback_without_accepting_wrong_output(self):
        def local(p, m):
            return Reply(canonical({"updates": {"answer": 1}, "requests": []}))

        def expert(p, m):
            value = 2 if "answer" in p["counterexamples"] else 1
            return Reply(canonical({"updates": {"answer": value}, "requests": []}))

        for mode, expected in (("residual", True), ("no_feedback", False)):
            h = Harness(self.registry(), CallableProvider("local", local), CallableProvider("expert", expert, "remote"),
                        Limits(local_rounds=1, expert_rounds=1), mode=mode)
            self.assertEqual(h.run(self.task())["success"], expected)

    def test_no_solvers_ablates_tools_without_changing_check(self):
        registry = self.registry()
        registry.solver("solve", lambda c: 2)
        task = dataclasses.replace(self.task(), obligations=(dataclasses.replace(self.task().obligations[0], solver="solve"),))
        bad = CallableProvider("bad", lambda p, m: Reply(canonical({"updates": {"answer": 1}, "requests": []})))
        self.assertTrue(Harness(registry, bad, None).run(task)["success"])
        self.assertFalse(Harness(registry, bad, None, mode="no_solvers").run(task)["success"])

    def test_partial_reported_usage_remains_unknown_without_crashing(self):
        provider = CallableProvider("partial", lambda p, m: Reply(canonical({"updates": {"answer": 2}, "requests": []}),
                                                               Usage(None, 2, source="reported")), "remote")
        result = Harness(self.registry(), None, provider).run(self.task())
        self.assertTrue(result["success"])
        self.assertFalse(result["metrics"]["remote_usage_complete"])

    def test_expression_interpreter_rejects_execution_and_resource_abuse(self):
        for source in ("__import__('os').system('echo unsafe')", "x.__class__", "2**999999", "[x]*1000", "True", "1/2", "9"*500):
            with self.subTest(source=source), self.assertRaises((ContractError, SyntaxError)):
                expression(source, 2)
        self.assertEqual(expression("(x*x+1)//2", -3), 5)
        self.assertFalse(grade({"e": "x//0"}, {"kind": "expression", "obligation": "e", "examples": [[1, 0]]})["pass"])

    def test_hidden_tests_catch_visible_example_overfit(self):
        self.assertTrue(grade({"e": "x"}, {"kind": "expression", "obligation": "e", "examples": [[0, 0], [1, 1]]})["pass"])
        self.assertFalse(grade({"e": "x"}, {"kind": "expression", "obligation": "e", "examples": [[7, 49]]})["pass"])

    def test_new_host_contract_repairs_dead_end_and_reuses_independent_work(self):
        registry = Registry()
        register(registry)
        registry.check("constant", lambda v, c: Verdict.passed() if v == 9 else Verdict.fail("bad"), "1")
        task = Task.load(ROOT / "examples/study/frozen-dead-end/task.json")
        task = dataclasses.replace(task, obligations=(*task.obligations, Obligation("independent", "Return 9", "constant")))

        def worker(packet, maximum):
            choices = json.loads(packet["evidence"][0]["text"])["choices"] if packet["evidence"] else {}
            return Reply(canonical({"updates": {o["id"]: 9 if o["id"] == "independent" else choices[o["id"]][0] for o in packet["obligations"]}, "requests": []}))

        provider = CallableProvider("worker", worker)
        with tempfile.TemporaryDirectory() as tmp:
            cache = Cache(Path(tmp) / "cache.db")
            self.addCleanup(cache.close)
            old = Harness(registry, provider, None, cache=cache).run(task)
            self.assertFalse(old["success"])
            self.assertEqual(old["values"]["a"], 1)
            # Explicit host-authored new snapshot; the model cannot mutate accepted a.
            data = json.loads(task.artifacts["requirements"].text)
            data["choices"]["a"] = [2]
            revised = dataclasses.replace(task, artifacts={"requirements": Artifact("requirements", canonical(data), True)},
                obligations=(dataclasses.replace(task.obligations[0], parameters={"choices": [2]}), *task.obligations[1:]))
            new = Harness(registry, provider, None, cache=cache).run(revised)
            self.assertTrue(new["success"])
            self.assertEqual(new["values"]["a"], 2)
            self.assertEqual(new["metrics"]["cache_hits"], 1)
            self.assertNotEqual(old["receipts"]["a"], new["receipts"]["a"])
            self.assertEqual(old["receipts"]["independent"], new["receipts"]["independent"])


if __name__ == "__main__":
    unittest.main()
