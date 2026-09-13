import dataclasses
import json
import random
import tempfile
import unittest
from pathlib import Path

from residual.config import build_harness, load_config
from residual.core import (Artifact, ContractError, Obligation, Registry, Task, Verdict,
                           canonical, digest, register_builtins, strict_json)
from residual.demo import make_case, register
from residual.engine import Harness, Limits
from residual.providers import CallableProvider, ProviderError, Reply, Usage
from residual.storage import Cache, verify_ledger


def registry():
    r = Registry()
    register_builtins(r)
    return r


def reply(updates=None, requests=None):
    return Reply(canonical({"updates": updates or {}, "requests": requests or []}), Usage(100, 20, 0, "reported"))


def task_two(private=False):
    source = Artifact("source", '{"a":1,"b":2}', not private)
    return Task("pair", "Extract two values.", {"source": source}, tuple(
        Obligation(n, f"Return {n}.", "json_value", ("source",), parameters={"artifact": "source", "pointer": "/" + n})
        for n in ("a", "b")))


class ContractTests(unittest.TestCase):
    def test_cycle_and_unknown_edges_rejected(self):
        for nodes in [(Obligation("a", "a", "json_value", depends_on=("b",)),),
                      (Obligation("a", "a", "json_value", depends_on=("b",)), Obligation("b", "b", "json_value", depends_on=("a",)))]:
            with self.assertRaises(ContractError):
                Task("test", "test", {}, nodes)

    def test_duplicate_and_nonfinite_json_rejected(self):
        for text in ['{"a":1,"a":2}', '{"v":NaN}', '{"v":Infinity}']:
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_artifact_path_escape_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "task").mkdir()
            (root / "secret.txt").write_text("secret")
            (root / "task" / "linked.txt").symlink_to(root / "secret.txt")
            for source in ("../secret.txt", "linked.txt"):
                path = root / "task" / "task.json"
                path.write_text(json.dumps({"id": "t", "goal": "g", "artifacts": [{"id": "x", "path": source}],
                                           "obligations": [{"id": "a", "instruction": "a", "check": "json_value"}]}))
                with self.assertRaises(ContractError):
                    Task.load(path)

    def test_invalid_limits_fail_before_work(self):
        for kwargs in ({"max_calls": True}, {"max_output_tokens": 0}, {"seed_lines": -1}, {"max_calls": 2.5}):
            with self.assertRaises(ContractError):
                Limits(**kwargs)

    def test_boolean_does_not_satisfy_integer_contract(self):
        h = Harness(registry(), CallableProvider("local", lambda p, m: reply({"a": True, "b": 2})), None,
                    Limits(local_rounds=1))
        result = h.run(task_two())
        self.assertFalse(result["success"])
        self.assertEqual(result["values"], {"b": 2})

    def test_duplicate_artifact_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps({"id": "t", "goal": "g", "artifacts": [{"id": "a", "text": "a"}] * 2,
                                       "obligations": [{"id": "o", "instruction": "o", "check": "json_value"}]}))
            with self.assertRaises(ContractError):
                Task.load(path)


class RoutingTests(unittest.TestCase):
    def test_cloud_receives_only_failed_independent_obligation(self):
        seen = []
        def expert(packet, maximum):
            seen.append(packet)
            return reply({"b": 2})
        h = Harness(registry(), CallableProvider("local", lambda p, m: reply({"a": 1, "b": 9})),
                    CallableProvider("expert", expert, "remote"), Limits(local_rounds=1))
        result = h.run(task_two())
        self.assertTrue(result["success"])
        self.assertEqual([o["id"] for o in seen[0]["obligations"]], ["b"])
        self.assertEqual(seen[0]["accepted_dependencies"], {})
        self.assertEqual(set(seen[0]["counterexamples"]), {"b"})

    def test_cloud_cannot_overwrite_accepted_result(self):
        responses = iter([reply({"a": 999, "b": 2}), reply({"b": 2})])
        h = Harness(registry(), CallableProvider("local", lambda p, m: reply({"a": 1})),
                    CallableProvider("expert", lambda p, m: next(responses), "remote"), Limits(local_rounds=1))
        result = h.run(task_two())
        self.assertEqual(result["values"], {"a": 1, "b": 2})
        self.assertEqual(result["metrics"]["expert_calls"], 2)

    def test_absent_verifier_is_not_implicitly_accepted(self):
        r = registry()
        r.check("bad", lambda v, c: True, "1")
        task = Task("t", "g", {}, (Obligation("a", "a", "bad"),))
        result = Harness(r, CallableProvider("local", lambda p, m: reply({"a": 1})), None, Limits(local_rounds=1)).run(task)
        self.assertFalse(result["success"])
        self.assertEqual(result["unresolved"]["a"]["code"], "invalid_verifier_result")

    def test_evidence_pull_recovers_starved_context(self):
        h = build_harness(load_config())
        result = h.run(make_case())
        self.assertTrue(result["success"])
        self.assertTrue(any(e["kind"] == "evidence_requested" for e in h.ledger.events))
        self.assertLess(result["metrics"]["remote_request_bytes"], 10000)

    def test_ablation_without_pull_fails_relevant_cases(self):
        result = build_harness(load_config(), "no_pull").run(make_case())
        self.assertFalse(result["success"])
        self.assertNotIn("cause", result["values"])
        self.assertEqual(result["unresolved"]["action"]["code"], "dependency_blocked")

    def test_small_capsule_planner_avoids_unnecessary_roundtrip(self):
        task = make_case(noise_lines=4)
        adaptive = build_harness(load_config()).run(task)
        fixed = build_harness(load_config(), "residual_fixed").run(task)
        self.assertTrue(adaptive["success"] and fixed["success"])
        self.assertEqual(adaptive["metrics"]["expert_calls"], 1)
        self.assertEqual(fixed["metrics"]["expert_calls"], 2)
        self.assertLess(adaptive["metrics"]["remote_request_bytes"], fixed["metrics"]["remote_request_bytes"])

    def test_private_artifacts_never_reach_remote_provider(self):
        seen = []
        expert = CallableProvider("expert", lambda p, m: (seen.append(p), reply())[1], "remote")
        result = Harness(registry(), None, expert).run(task_two(private=True))
        self.assertEqual(seen, [])
        self.assertEqual(result["metrics"]["remote_calls"], 0)

    def test_private_data_propagates_through_dependencies(self):
        r = registry()
        r.check("child", lambda v, c: Verdict.passed() if v == c.dependency("a") else Verdict.fail("wrong"), "1")
        base = task_two(private=True)
        a = dataclasses.replace(base.obligations[0], solver="json_value")
        b = Obligation("child", "Return dependency.", "child", depends_on=("a",))
        task = Task("t", "g", base.artifacts, (a, b))
        seen = []
        result = Harness(r, None, CallableProvider("expert", lambda p, m: (seen.append(p), reply())[1], "remote")).run(task)
        self.assertEqual(result["values"], {"a": 1})
        self.assertEqual(seen, [])
        self.assertEqual(result["unresolved"]["child"]["code"], "local_only")

    def test_private_artifact_names_not_in_unrelated_remote_packet(self):
        base = task_two()
        task = dataclasses.replace(base, artifacts={**base.artifacts, "private_vault": Artifact("private_vault", "SECRET", False)})
        seen = []
        for mode in ("residual", "cascade", "full_cloud"):
            h = Harness(registry(), None, CallableProvider("expert", lambda p, m: (seen.append(p), reply({"a": 1, "b": 2}))[1], "remote"), mode=mode)
            self.assertTrue(h.run(task)["success"])
        self.assertNotIn("private_vault", canonical(seen))
        self.assertNotIn("SECRET", canonical(seen))

    def test_unrequested_evidence_and_oversized_windows_denied(self):
        for artifact, end in (("not_declared", 1), ("source", 1000)):
            response = reply(requests=[{"obligation_id": "a", "artifact_id": artifact, "start_line": 1, "end_line": end}])
            h = Harness(registry(), None, CallableProvider("expert", lambda p, m: response, "remote"), Limits(expert_rounds=1))
            result = h.run(task_two())
            self.assertFalse(result["success"])
            self.assertTrue(any(e["kind"] == "evidence_denied" for e in h.ledger.events))

    def test_local_worker_cannot_mix_private_and_exportable_frontiers(self):
        task = Task("isolation", "Extract values.",
                    {"public": Artifact("public", '"PUBLIC"', True), "private": Artifact("private", '"SECRET"', False)},
                    (Obligation("a", "public", "json_value", ("public",), parameters={"artifact": "public"}),
                     Obligation("b", "private", "json_value", ("private",), parameters={"artifact": "private"})))
        for mode in ("residual", "cascade", "full_cloud"):
            seen = []
            def worker(packet, maximum):
                seen.append(packet)
                return reply({o["id"]: ("PUBLIC" if o["id"] == "a" else "SECRET") for o in packet["obligations"]})
            h = Harness(registry(), CallableProvider("local", worker), CallableProvider("expert", worker),
                        Limits(local_rounds=1), mode=mode)
            self.assertTrue(h.run(task)["success"])
            for packet in seen:
                if any(o["id"] == "a" for o in packet["obligations"]):
                    self.assertNotIn("SECRET", canonical(packet))
                    self.assertNotIn('"artifact_id":"private"', canonical(packet))

    def test_budget_is_checked_before_network_call(self):
        seen = []
        h = Harness(registry(), None, CallableProvider("expert", lambda p, m: (seen.append(p), reply())[1], "remote"),
                    Limits(max_remote_input_bytes=1))
        result = h.run(task_two())
        self.assertEqual(seen, [])
        self.assertEqual(result["metrics"]["calls"], 0)
        self.assertEqual(result["unresolved"]["a"]["code"], "budget_exhausted")

    def test_failed_transport_consumes_reservation_and_usage_is_unknown(self):
        def failure(packet, max_tokens):
            raise ProviderError("http_429")
        h = Harness(registry(), None, CallableProvider("expert", failure, "remote"), Limits(max_expert_calls=1))
        result = h.run(task_two())
        self.assertEqual(result["metrics"]["remote_calls"], 1)
        self.assertGreater(result["metrics"]["remote_request_bytes"], 0)
        self.assertFalse(result["metrics"]["remote_usage_complete"])
        self.assertIsNone(result["metrics"]["remote_cost_usd"])

    def test_custom_exception_text_does_not_leak(self):
        def failure(packet, maximum):
            raise RuntimeError("Bearer VERY_SECRET_KEY")
        h = Harness(registry(), None, CallableProvider("expert", failure, "remote"), Limits(expert_rounds=1))
        result = h.run(task_two())
        self.assertNotIn("VERY_SECRET", canonical(result) + canonical(h.ledger.events))

    def test_duplicate_keys_and_truncated_outputs_never_pass(self):
        for raw, reason in [('{"updates":{"a":1},"updates":{"b":2},"requests":[]}', None),
                            (canonical({"updates": {"a": 1, "b": 2}, "requests": []}), "length")]:
            h = Harness(registry(), CallableProvider("local", lambda p, m: Reply(raw, finish_reason=reason)), None,
                        Limits(local_rounds=1))
            self.assertFalse(h.run(task_two())["success"])

    def test_independent_branches_continue_after_one_branch_fails(self):
        r = registry()
        r.check("child", lambda v, c: Verdict.passed() if v == c.dependency("b") + 1 else Verdict.fail("wrong"), "1")
        task = task_two()
        task = dataclasses.replace(task, obligations=(*task.obligations, Obligation("c", "b+1", "child", depends_on=("b",))))
        def solve(packet, maximum):
            return reply({o["id"]: {"a": 0, "b": 2, "c": 3}[o["id"]] for o in packet["obligations"]})
        result = Harness(r, CallableProvider("local", solve), None, Limits(local_rounds=1)).run(task)
        self.assertEqual(result["values"], {"b": 2, "c": 3})

    def test_generated_dags_never_execute_children_before_dependencies(self):
        rng = random.Random(81)
        for _ in range(20):
            r = Registry()
            r.check("sum", lambda v, c: Verdict.passed() if v == sum(c.dependency(d) for d in c.obligation.depends_on) + 1 else Verdict.fail("wrong"), "1")
            nodes = tuple(Obligation(f"n{i}", "sum dependencies + 1", "sum", depends_on=tuple(f"n{j}" for j in range(i) if rng.random() < 0.3)) for i in range(8))
            def worker(packet, maximum):
                deps = packet["accepted_dependencies"]
                return reply({o["id"]: sum(deps[d]["value"] for d in o["depends_on"]) + 1 for o in packet["obligations"]})
            result = Harness(r, CallableProvider("local", worker), None).run(Task("dag", "sum graph", {}, nodes))
            self.assertTrue(result["success"])


class CacheAndTraceTests(unittest.TestCase):
    def test_cache_revalidates_and_invalidates_changed_evidence(self):
        calls = []
        def worker(packet, maximum):
            calls.append(packet)
            source = strict_json(packet["evidence"][0]["text"])
            return reply({o["id"]: source[o["id"]] for o in packet["obligations"]})
        cache = Cache()
        h = Harness(registry(), CallableProvider("local", worker), None, cache=cache)
        first = h.run(task_two())
        second = h.run(task_two())
        self.assertTrue(first["success"] and second["success"])
        self.assertEqual(second["metrics"]["cache_hits"], 2)
        self.assertEqual(len(calls), 1)
        changed = dataclasses.replace(task_two(), artifacts={"source": Artifact("source", '{"a":3,"b":4}', True)})
        third = h.run(changed)
        self.assertEqual(third["values"], {"a": 3, "b": 4})
        self.assertEqual(third["metrics"]["cache_hits"], 0)
        cache.close()

    def test_tampered_cache_value_must_pass_live_verifier(self):
        cache = Cache()
        h = Harness(registry(), CallableProvider("local", lambda p, m: reply({"a": 1, "b": 2})), None, cache=cache)
        h.run(task_two())
        cache.db.execute("UPDATE results SET value='999'")
        cache.db.commit()
        result = h.run(task_two())
        self.assertEqual(result["values"], {"a": 1, "b": 2})
        self.assertEqual(result["metrics"]["cache_hits"], 0)
        cache.close()

    def test_null_is_a_real_cache_hit(self):
        task = Task("t", "g", {"s": Artifact("s", "null")}, (Obligation("a", "null", "json_value", ("s",), parameters={"artifact": "s"}),))
        cache = Cache()
        h = Harness(registry(), CallableProvider("local", lambda p, m: reply({"a": None})), None, cache=cache)
        h.run(task)
        self.assertEqual(h.run(task)["metrics"]["cache_hits"], 1)
        cache.close()

    def test_verifier_revision_changes_cache_key(self):
        cache = Cache()
        r = registry()
        h = Harness(r, CallableProvider("local", lambda p, m: reply({"a": 1, "b": 2})), None, cache=cache)
        h.run(task_two())
        revision, check = r.checks["json_value"]
        r.checks["json_value"] = ("2", check)
        self.assertEqual(h.run(task_two())["metrics"]["cache_hits"], 0)
        cache.close()

    def test_trace_rejects_tampering_truncation_and_wrong_root(self):
        h = build_harness(load_config())
        result = h.run(make_case())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            h.ledger.write(path)
            self.assertEqual(verify_ledger(path, result["trace_root"])["root"], result["trace_root"])
            with self.assertRaises(ContractError):
                verify_ledger(path, "0" * 64)
            original = path.read_text()
            path.write_text("\n".join(original.splitlines()[:-1]))
            with self.assertRaises(ContractError):
                verify_ledger(path)
            path.write_text(original.replace('"mode":"residual"', '"mode":"cascade"', 1))
            with self.assertRaises(ContractError):
                verify_ledger(path)

    def test_traces_contain_hashes_not_raw_evidence(self):
        h = build_harness(load_config())
        h.run(make_case())
        text = canonical(h.ledger.events)
        self.assertNotIn("NXDOMAIN", text)
        self.assertNotIn("background sensor", text)


if __name__ == "__main__":
    unittest.main()
