import copy
import itertools
import random
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from residual.cic import (consistent, elimination_certificate, feasibility, interaction_graph,
                          min_fill, prepare, validate_model, verify_certificate)
from residual.config import load_config
from residual.core import Artifact, Context, ContractError, Obligation, Registry, Task, Verdict, canonical
from residual.engine import Harness, Limits
from residual.extensions import VerifierRevision
from residual.providers import Provider, Reply, Usage
from residual.receipts import validate_receipt_graph
from residual.storage import Cache, verify_ledger
from residual.study import make_protocol, run_study, write_json
from residual.study_tasks import StudyFixtureProvider, assignment_valid, register


ROOT = Path(__file__).resolve().parents[1]
MODEL = {"domains": {"a": [1, 2], "b": [1]}, "different": [["a", "b"]]}


def registry(modern=False):
    result = Registry()
    register(result)
    if modern:
        identity = VerifierRevision.from_artifact(__file__, configuration={}, policy={})
        result.identities.update({k: (identity, "mechanical") for k in result.checks})
    return result


def task(model=None, dependent=True, private=False):
    model = copy.deepcopy(MODEL if model is None else model)
    obligations = tuple(Obligation(k, "Choose a jointly valid integer for " + k,
        "study_compatible" if dependent and k == "b" else "study_choice", ("model",),
        ("a",) if dependent and k == "b" else (),
        {"choices": v, **({"dependency": "a"} if dependent and k == "b" else {})}) for k, v in model["domains"].items())
    return Task("cic-test", "Satisfy all constraints", {"model": Artifact("model", canonical(model), not private)}, obligations, "model")


class Answers(Provider):
    def __init__(self, answers, placement="local"):
        self.answers, self.placement, self.packets = answers, placement, []

    def generate(self, packet, max_output_tokens):
        self.packets.append(copy.deepcopy(packet))
        answer = self.answers[min(len(self.packets) - 1, len(self.answers) - 1)]
        updates = {o["id"]: answer for o in packet["obligations"]}
        return Reply(canonical({"updates": updates, "requests": []}), Usage(source="simulation"))


class StructuralAlgorithms(unittest.TestCase):
    def test_model_rejects_unsupported_and_unbounded_inputs(self):
        bad = [{}, {"domains": {}}, {"domains": {"a": [True]}}, {"domains": {"a": [1, 1]}},
               {"domains": {"a": []}}, {"domains": {"a": [10**7]}}, {"domains": {"a": [1]}, "clauses": []},
               {"domains": {"a": [1]}, "different": [["a", "missing"]]},
               {"domains": {"a": [1]}, "sums": [{"keys": ["a", "a"], "equals": 2}]},
               {"domains": {"a": [1]}, "sums": [{"keys": ["a"], "equals": True}]},
               {"domains": {"a": list(range(65))}}, {"domains": {f"x{i}": [0] for i in range(33)}},
               {"domains": {"a": [1]}, "different": [["a", "a"]] * 129}]
        for model in bad:
            with self.subTest(model=model), self.assertRaises(ContractError):
                validate_model(model)

    def test_graph_uses_constraint_scopes_and_sum_cliques(self):
        graph = interaction_graph({"domains": {k: [0, 1] for k in "abcd"}, "sums": [{"keys": list("abc"), "equals": 1}]})
        self.assertEqual(graph, {"a": {"b", "c"}, "b": {"a", "c"}, "c": {"a", "b"}, "d": set()})

    def test_certificate_known_graphs_and_determinism(self):
        for graph, width in [({}, 0), ({"a": set()}, 0),
                ({"a": {"b"}, "b": {"a", "c"}, "c": {"b"}}, 1),
                ({k: set("abcd") - {k} for k in "abcd"}, 3),
                ({"a": {"b", "d"}, "b": {"a", "c"}, "c": {"b", "d"}, "d": {"a", "c"}}, 2)]:
            before = copy.deepcopy(graph)
            cert = min_fill(graph)
            self.assertEqual(cert["width_upper_bound"], width)
            self.assertTrue(verify_certificate(graph, cert))
            self.assertEqual(cert, min_fill(dict(reversed(list(graph.items())))))
            self.assertEqual(graph, before)

    def test_certificate_rejects_missing_duplicate_and_tampered_steps(self):
        graph = interaction_graph(MODEL)
        for ordering in [["a"], ["a", "a"], ["a", "z"], ["a", True]]:
            with self.assertRaises(ContractError):
                elimination_certificate(graph, ordering)
        cert = min_fill(graph)
        for key, value in [("width_upper_bound", 0), ("width_upper_bound", True), ("steps", [])]:
            bad = {**cert, key: value}
            self.assertFalse(verify_certificate(graph, bad))

    def test_invalid_graphs_rejected(self):
        for graph in [{"a": {"a"}}, {"a": {"b"}}, {"a": {"b"}, "b": set()}, {"a": []}]:
            with self.assertRaises(ContractError):
                min_fill(graph)

    def test_search_matches_independent_exhaustive_oracle(self):
        rng = random.Random(781)
        for _ in range(150):
            keys = list("abcd")[:rng.randint(1, 4)]
            model = {"domains": {k: rng.sample([-1, 0, 1, 2], rng.randint(1, 4)) for k in keys},
                "different": [list(p) for p in itertools.combinations(keys, 2) if rng.random() < .3],
                "less_than": [list(p) for p in itertools.combinations(keys, 2) if rng.random() < .2],
                "sums": [{"keys": keys, "equals": rng.randint(-3, 6)}] if rng.random() < .6 else []}
            solutions = [dict(zip(keys, vals)) for vals in itertools.product(*(model["domains"][k] for k in keys))
                         if assignment_valid(dict(zip(keys, vals)), model)]
            result = feasibility(model, min_fill(interaction_graph(model))["ordering"], 10000)
            self.assertEqual(result.status, "SAT" if solutions else "UNSAT")
            if solutions:
                self.assertIn(result.assignment, solutions)

    def test_exhaustion_is_unknown_and_never_exceeds_budget(self):
        for bound in [0, 1]:
            result = feasibility(MODEL, ["a", "b"], bound)
            self.assertEqual(result.status, "UNKNOWN")
            self.assertIsNone(result.assignment)
            self.assertLessEqual(result.nodes, bound)
        for bound in [-1, True, 1_000_001]:
            with self.assertRaises(ContractError):
                feasibility(MODEL, ["a", "b"], bound)

    def test_self_constraint_is_unsat(self):
        model = {"domains": {"a": [0]}, "different": [["a", "a"]]}
        self.assertEqual(feasibility(model, ["a"], 1).status, "UNSAT")

    def test_partial_consistency_does_not_accept_complete_missing_or_bool(self):
        self.assertTrue(consistent(MODEL, {"a": 2}))
        self.assertFalse(consistent(MODEL, {"a": 2}, complete=True))
        self.assertFalse(consistent(MODEL, {"a": True, "b": 1}, complete=True))


class StructuralHarness(unittest.TestCase):
    def run_case(self, candidate, **options):
        source = options.pop("task", task())
        provider = Answers([candidate])
        harness = Harness(options.pop("registry", registry()), provider, None, mode=options.pop("mode", "cic"),
                          limits=options.pop("limits", Limits(local_rounds=1)), **options)
        result = harness.run(source)
        return harness, result, provider

    def test_atomic_group_avoids_frozen_dead_end(self):
        for mode in ["structural", "cic"]:
            h = Harness(registry(), StudyFixtureProvider(), StudyFixtureProvider("expert"), mode=mode)
            result = h.run(task())
            self.assertTrue(result["success"])
            self.assertEqual(result["original_values"], {"a": 2, "b": 1})
            self.assertEqual(len(result["receipts"]), 1)
            self.assertGreater(result["metrics"]["candidate_rejections"], 0)
            self.assertEqual(len([e for e in h.ledger.events if e["kind"] == "obligation_accepted"]), 1)
        baseline = Harness(registry(), StudyFixtureProvider(), StudyFixtureProvider("expert")).run(task())
        self.assertFalse(baseline["success"])
        self.assertEqual(baseline["values"], {"a": 1})

    def test_partial_invalid_and_extra_group_values_never_accept(self):
        for candidate in [{"a": 2}, {"a": 1, "b": 1}, {"a": 2, "b": 1, "extra": 0}, 2]:
            h, result, _ = self.run_case(candidate)
            self.assertEqual(result["original_values"], {})
            self.assertEqual(result["receipts"], {})
            self.assertFalse(result["success"])

    def test_sat_preflight_does_not_bypass_original_verifier(self):
        r = registry()
        r.checks["study_choice"] = ("reject", lambda v, ctx: Verdict.fail("additional_contract"))
        _, result, _ = self.run_case({"a": 2, "b": 1}, registry=r)
        self.assertEqual(next(iter(result["structural"]["feasibility"].values()))["status"], "SAT")
        self.assertFalse(result["success"])

    def test_unknown_and_throwing_original_verifiers_never_pass(self):
        def broken(value, ctx):
            raise RuntimeError("private checker details")
        for check in [lambda v, ctx: Verdict("unknown", "missing_evidence"), broken, lambda v, ctx: True]:
            r = registry()
            r.checks["study_choice"] = ("test", check)
            _, result, _ = self.run_case({"a": 2, "b": 1}, registry=r)
            self.assertFalse(result["success"])
            self.assertNotIn("private checker details", canonical(result))

    def test_unsat_skips_transport_and_cannot_accept_cache(self):
        impossible = task({"domains": {"a": [1], "b": [1]}, "different": [["a", "b"]]})
        class PoisonCache:
            def get(self, key):
                raise AssertionError("UNSAT must bypass cache")
        _, result, provider = self.run_case({"a": 1, "b": 1}, task=impossible, cache=PoisonCache())
        self.assertEqual(provider.packets, [])
        self.assertEqual(result["metrics"]["structural_unsat_groups"], 1)
        self.assertFalse(result["success"])

    def test_unknown_search_still_checks_complete_candidate(self):
        _, result, _ = self.run_case({"a": 2, "b": 1}, limits=Limits(max_structural_nodes=0))
        self.assertEqual(next(iter(result["structural"]["feasibility"].values()))["status"], "UNKNOWN")
        self.assertTrue(result["success"])

    def test_search_budget_shared_across_components(self):
        source = task({"domains": {"a": [0], "b": [1], "c": [2]}}, dependent=False)
        _, result, _ = self.run_case({}, task=source, limits=Limits(max_structural_nodes=1))
        self.assertEqual(result["metrics"]["structural_search_nodes"], 1)
        self.assertEqual(sorted(s["status"] for s in result["structural"]["feasibility"].values()), ["SAT", "UNKNOWN", "UNKNOWN"])

    def test_unsat_component_does_not_block_unrelated_component(self):
        source = task({"domains": {"a": [1], "b": [1], "c": [2]}, "different": [["a", "b"]]}, dependent=False)
        _, result, provider = self.run_case({"c": 2}, task=source)
        self.assertEqual(result["original_values"], {"c": 2})
        self.assertEqual(len(provider.packets), 1)
        self.assertEqual(result["metrics"]["structural_unsat_groups"], 1)

    def test_forged_legacy_cache_candidate_is_rechecked(self):
        class ForgedCache:
            def get(self, key):
                return True, {"a": 1, "b": 1}
            def put(self, key, value):
                pass
        _, result, _ = self.run_case({"a": 1, "b": 1}, cache=ForgedCache())
        self.assertFalse(result["success"])
        self.assertEqual(result["receipts"], {})
        self.assertEqual(result["metrics"]["cache_hits"], 0)

    def test_configuration_enforces_search_limit(self):
        for limit in [-1, True, 1_000_001]:
            with self.assertRaises(ContractError):
                Limits(max_structural_nodes=limit)

    def test_component_context_boundary_and_member_parameters_hidden(self):
        source = task({"domains": {"a": [1], "b": [2]}}, dependent=False)
        _, _, provider = self.run_case({}, task=source)
        self.assertEqual(len(provider.packets), 2)
        for packet in provider.packets:
            self.assertEqual(len(packet["obligations"]), 1)
            member = packet["obligations"][0]["members"][0]
            self.assertNotIn("parameters", member)
            self.assertNotIn("check", member)
            self.assertNotIn("certificate", packet)

    def test_private_member_and_downstream_group_never_exported(self):
        source = task(private=True)
        source = replace(source, obligations=(*source.obligations, Obligation("c", "Count", "study_choice", depends_on=("a",), parameters={"choices": [1]})))
        remote = Answers([{"a": 2, "b": 1}], "remote")
        result = Harness(registry(), None, remote, mode="cic").run(source)
        self.assertEqual(remote.packets, [])
        self.assertFalse(result["success"])

    def test_external_dependency_projection_and_station_receipt_parents(self):
        source = task()
        source = replace(source, obligations=(*source.obligations, Obligation("c", "Use a", "use_a", depends_on=("a",))))
        r = registry(modern=True)
        identity = next(iter(r.identities.values()))[0]
        r.check("use_a", lambda v, ctx: Verdict.passed() if ctx.dependency("a") == v else Verdict.fail("wrong"), "1", identity=identity)
        provider = Answers([{"a": 2, "b": 1}, {"c": 2}])
        harness = Harness(r, provider, None, mode="cic", limits=Limits(local_rounds=1))
        result = harness.run(source)
        self.assertTrue(result["success"])
        self.assertEqual(result["original_values"], {"a": 2, "b": 1, "c": 2})
        self.assertEqual(len(result["station_receipts"]), 2)
        self.assertEqual(sum(len(r["payload"]["parent_receipts"]) for r in result["station_receipts"].values()), 1)
        validate_receipt_graph(harness.station_receipts, {o.id: o.depends_on for o in harness.task.obligations})

    def test_original_context_cannot_read_other_members_undeclared_evidence(self):
        source = task()
        source = replace(source, artifacts={**source.artifacts, "secret": Artifact("secret", "PRIVATE", False)},
            obligations=(source.obligations[0], replace(source.obligations[1], evidence=("model", "secret"))))
        r = registry()
        r.checks["study_choice"] = ("test", lambda v, ctx: (ctx.evidence("secret"), Verdict.passed())[1])
        _, result, _ = self.run_case({"a": 2, "b": 1}, task=source, registry=r)
        self.assertFalse(result["success"])

    def test_cache_rechecks_joint_and_member_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Cache(Path(folder) / "cache.db")
            self.addCleanup(cache.close)
            h, first, _ = self.run_case({"a": 2, "b": 1}, cache=cache, registry=registry(modern=True))
            self.assertTrue(first["success"])
            second = h.run(task())
            self.assertEqual(second["metrics"]["cache_hits"], 1)
            self.assertEqual(second["metrics"]["calls"], 0)
            self.assertEqual(first["receipts"], second["receipts"])
            changed = task({"domains": {"a": [2, 3], "b": [1]}, "different": [["a", "b"]]})
            third = h.run(changed)
            self.assertEqual(third["metrics"]["cache_hits"], 0)
            self.assertNotEqual(first["receipts"], third["receipts"])

    def test_original_verifier_identity_change_invalidates_group_cache(self):
        h, first, _ = self.run_case({"a": 2, "b": 1}, registry=registry(modern=True), cache=Cache())
        self.addCleanup(h.cache.close)
        original, check_type = h.source_registry.identities["study_choice"]
        h.source_registry.identities["study_choice"] = (replace(original, policy_hash="f" * 64), check_type)
        second = h.run(task())
        self.assertEqual(second["metrics"]["cache_hits"], 0)
        self.assertNotEqual(first["receipts"], second["receipts"])

    def test_legacy_members_do_not_gain_modern_receipts(self):
        _, result, _ = self.run_case({"a": 2, "b": 1})
        self.assertEqual(result["station_receipts"], {})

    def test_no_structure_falls_back_without_wrapping_values(self):
        source = replace(task(), structure=None)
        r = Harness(registry(), StudyFixtureProvider(), None, mode="cic").run(source)
        self.assertFalse(r["structural"]["applicable"])
        self.assertNotIn("original_values", r)
        self.assertEqual(r["values"], {"a": 1})

    def test_invalid_opt_in_fails_before_transport(self):
        source = task()
        invalid = [replace(source, obligations=(replace(source.obligations[0], evidence=()), source.obligations[1])),
                   replace(source, artifacts={"model": Artifact("model", '{"domains":{"unknown":[1]}}')}),
                   replace(source, artifacts={"model": Artifact("model", '{"domains":{"a":[]}}')})]
        for source in invalid:
            provider = Answers([{}])
            with self.assertRaises(ContractError):
                Harness(registry(), provider, None, mode="cic").run(source)
            self.assertEqual(provider.packets, [])

    def test_quotient_cycle_is_rejected(self):
        source = task({"domains": {"a": [1], "c": [2]}, "different": [["a", "c"]]}, dependent=False)
        source = replace(source, obligations=(source.obligations[0],
            Obligation("b", "Use a", "study_choice", depends_on=("a",), parameters={"choices": [1]}),
            replace(source.obligations[1], depends_on=("b",))))
        with self.assertRaisesRegex(ContractError, "cycle"):
            prepare(source, registry(), "cic", 100)

    def test_all_member_solvers_remain_checked(self):
        source = task()
        r = registry()
        r.solver("choose", lambda ctx: 2 if ctx.obligation.id == "a" else 1)
        source = replace(source, obligations=tuple(replace(o, solver="choose") for o in source.obligations))
        result = Harness(r, None, None, mode="cic").run(source)
        self.assertTrue(result["success"])
        self.assertEqual(result["metrics"]["deterministic_accepts"], 1)

    def test_trace_binds_projection_and_analysis(self):
        h, result, _ = self.run_case({"a": 2, "b": 1})
        from residual.core import digest
        self.assertEqual(h.ledger.events[-1]["data"]["result_sha256"], digest({k: v for k, v in result.items() if k != "trace_root"}))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            h.ledger.write(path)
            self.assertEqual(verify_ledger(path)["root"], result["trace_root"])

    def test_three_arm_study_retains_failures_overhead_and_unknown_cost(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            suite = ROOT / "examples/cic/suite.json"
            protocol = make_protocol(suite, load_config(ROOT / "examples/study-fixture.toml"),
                ["residual", "structural", "cic"], 1, 42, 1000, 1_000_000)
            lock = folder / "lock.json"
            write_json(lock, {"suite": str(suite), "protocol": protocol})
            report = run_study(lock, folder / "study")
            self.assertTrue(report["comparison_complete"])
            self.assertEqual(report["scheduled_runs"], 18)
            rows = {s["mode"]: s for s in report["summary"]}
            self.assertEqual(rows["residual"]["false_acceptances"], 4)
            for mode in ["structural", "cic"]:
                self.assertEqual(rows[mode]["successful"], 4)
                self.assertEqual(rows[mode]["false_acceptances"], 0)
                self.assertGreater(rows[mode]["structural_elapsed_ms"], 0)
                self.assertIsNone(rows[mode]["total_cost_per_success_usd"])
            self.assertEqual(rows["cic"]["structural_unsat_groups"], 1)
            self.assertLess(rows["cic"]["calls"], rows["structural"]["calls"])


if __name__ == "__main__":
    unittest.main()
