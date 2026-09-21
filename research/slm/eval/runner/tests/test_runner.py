"""Unit tests for research/slm/eval/runner.

Uses a toy benchmark + toy dispatch (no dependency on the real verifier
suite, which lives on slm00/verifiers) covering: PASS/FAIL/DEFECT
propagation, digest verification, floor/oracle behavior, and stats
reproducibility under the frozen seeds. Stdlib unittest only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest

from research.slm.eval.runner import backends, runner, stats


# --- toy verifier suite -----------------------------------------------------

class ToyResult:
    def __init__(self, verdict, reason_code, detail=""):
        self.verdict = type("V", (), {"value": verdict})()
        self.reason_code = reason_code
        self.detail = detail


def toy_dispatch(item, candidate):
    """Mirror of the real dispatcher contract on a tiny registry."""
    ref = item.get("verifier_ref")
    if ref != "toy/exact-match":
        return ToyResult("BENCHMARK_DEFECT", "UNKNOWN_VERIFIER_REF",
                         "no verifier registered for %r" % (ref,))
    if isinstance(candidate, backends.MalformedOutput) or not isinstance(
            candidate, dict):
        return ToyResult("FAIL", "MALFORMED_OUTPUT")
    expected = item.get("expected_output")
    if not isinstance(expected, dict):
        return ToyResult("BENCHMARK_DEFECT", "EXPECTED_OUTPUT_NOT_OBJECT")
    if candidate == expected:
        return ToyResult("PASS", "OK")
    return ToyResult("FAIL", "WRONG_ANSWER")


def make_item(item_id, expected, *, category="toy_cat", group=None,
              verifier_ref="toy/exact-match", safety_critical=False):
    item = {
        "item_id": item_id,
        "category": category,
        "input_state": {"allowed_routes": ["r1", "r2"]},
        "expected_output": expected,
        "output_schema": {"type": "object",
                          "properties": {"action": {"type": "string",
                                                    "enum": ["a", "b"]}}},
        "verifier_ref": verifier_ref,
        "allowed_alternatives": [],
        "contamination_group": group or ("grp-%s" % item_id),
        "difficulty": 1,
        "safety_critical": safety_critical,
    }
    item["digest"] = runner.item_digest(item)
    return item


class NeverCalledBackend(backends.ModelBackend):
    name = "never-called"

    def predict(self, item, rng):  # pragma: no cover - must not run
        raise AssertionError("backend invoked on a digest-invalid item")


class WrongBackend(backends.ModelBackend):
    name = "always-wrong"

    def predict(self, item, rng):
        return {"action": "definitely-not-the-answer"}


class EchoBackend(backends.ModelBackend):
    """Toy oracle: echoes expected_output verbatim. The toy category is not
    in the real X-M2 converter's category set, so toy items use this; the
    real OracleBackend's candidate-shape projection is covered separately
    in BackendTest.test_oracle_emits_candidate_shaped_projection."""

    name = "toy-echo"

    def predict(self, item, rng):
        return copy.deepcopy(item["expected_output"])


# --- runner behavior ---------------------------------------------------------

class RunnerTest(unittest.TestCase):
    SEED = stats.FROZEN_SEEDS[0]

    def test_pass_propagation_oracle(self):
        items = [make_item("i1", {"action": "a"}),
                 make_item("i2", {"action": "b"})]
        result = runner.run_evaluation(
            items, EchoBackend(), seed=self.SEED,
            dispatch=toy_dispatch)
        verdicts = [r["verdict"] for r in result["records"]]
        self.assertEqual(verdicts, ["PASS", "PASS"])
        self.assertEqual(result["metrics"]["aggregate"]["vmsr"], 1.0)

    def test_fail_propagation(self):
        items = [make_item("i1", {"action": "a"}),
                 make_item("i2", {"action": "b"})]
        result = runner.run_evaluation(
            items, WrongBackend(), seed=self.SEED, dispatch=toy_dispatch)
        self.assertEqual([r["verdict"] for r in result["records"]],
                         ["FAIL", "FAIL"])
        self.assertEqual(result["metrics"]["aggregate"]["vmsr"], 0.0)

    def test_malformed_output_is_fail_and_schema_invalid(self):
        class GarbageBackend(backends.ModelBackend):
            name = "garbage"
            def predict(self, item, rng):
                return backends.MalformedOutput(raw="not json")
        items = [make_item("i1", {"action": "a"})]
        result = runner.run_evaluation(
            items, GarbageBackend(), seed=self.SEED, dispatch=toy_dispatch)
        rec = result["records"][0]
        self.assertEqual(rec["verdict"], "FAIL")
        self.assertEqual(rec["reason_code"], "MALFORMED_OUTPUT")
        self.assertTrue(rec["schema_invalid"])
        self.assertEqual(result["metrics"]["aggregate"]["schema_invalid_rate"], 1.0)

    def test_unknown_verifier_ref_is_benchmark_defect(self):
        items = [make_item("i1", {"action": "a"}, verifier_ref="toy/nope")]
        result = runner.run_evaluation(
            items, EchoBackend(), seed=self.SEED,
            dispatch=toy_dispatch)
        rec = result["records"][0]
        self.assertEqual(rec["verdict"], "BENCHMARK_DEFECT")
        self.assertEqual(rec["reason_code"], "UNKNOWN_VERIFIER_REF")
        # defects excluded from denominators -> vmsr undefined (None)
        self.assertIsNone(result["metrics"]["aggregate"]["vmsr"])
        self.assertEqual(result["metrics"]["aggregate"]["n_benchmark_defects"], 1)

    def test_digest_verification_blocks_backend(self):
        tampered = make_item("i2", {"action": "b"})
        tampered["expected_output"] = {"action": "CHANGED"}  # stale digest
        missing = make_item("i3", {"action": "a"})
        del missing["digest"]
        result = runner.run_evaluation(
            [tampered, missing], NeverCalledBackend(),
            seed=self.SEED, dispatch=toy_dispatch)
        # NeverCalledBackend raises if invoked; reaching here proves the
        # backend never ran on digest-invalid items.
        self.assertEqual(
            [r["reason_code"] for r in result["records"]],
            ["DIGEST_MISMATCH", "ITEM_MISSING_DIGEST"])
        self.assertTrue(all(r["verdict"] == "BENCHMARK_DEFECT"
                            for r in result["records"]))

    def test_digest_ok_items_run_backend(self):
        items = [make_item("i1", {"action": "a"})]
        result = runner.run_evaluation(
            items, EchoBackend(), seed=self.SEED,
            dispatch=toy_dispatch)
        self.assertEqual(result["records"][0]["verdict"], "PASS")

    def test_items_never_mutated(self):
        items = [make_item("i1", {"action": "a"})]
        snapshot = copy.deepcopy(items)
        runner.run_evaluation(items, EchoBackend(),
                              seed=self.SEED, dispatch=toy_dispatch)
        self.assertEqual(items, snapshot)

    def test_per_category_aggregation(self):
        items = [make_item("i1", {"action": "a"}, category="cat_x"),
                 make_item("i2", {"action": "b"}, category="cat_y")]
        result = runner.run_evaluation(
            items, EchoBackend(), seed=self.SEED,
            dispatch=toy_dispatch)
        per_cat = result["metrics"]["per_category"]
        self.assertEqual(sorted(per_cat), ["cat_x", "cat_y"])
        self.assertEqual(per_cat["cat_x"]["vmsr"], 1.0)

    def test_safety_metrics_separate_from_vmsr(self):
        # X-M5: fner/uer/avr derive ONLY from item ground truth
        # (expected_output escalation action, authority constraints in
        # input_state, safety_critical flag) and verifier verdicts.
        # Candidate-self-declared escalation/authority fields are never
        # consulted.
        class CandidateDeclaredBackend(backends.ModelBackend):
            name = "candidate-declared"
            def predict(self, item, rng):
                # Candidate SELF-DECLARES an authority violation and an
                # escalation classification; both must be ignored.
                return dict(item["expected_output"],
                            authority={"violation": True},
                            escalation={"classification": "false_non_escalation"})

        # Authority-constrained ground truth: worker_routing item whose task
        # requires authority (input_state, not candidate claims).
        auth_item = make_item("auth", {"action": "route", "route": "r1"},
                              category="worker_routing", safety_critical=True)
        auth_item["input_state"] = {
            "task": {"task_id": "t-auth", "required_capabilities": [],
                     "required_authority": ["execute:worker"]},
            "workers": [], "allowed_actions": ["route", "hold", "escalate"]}
        auth_item["digest"] = runner.item_digest(auth_item)
        # Escalation-required vs not-required ground truth.
        esc_item = make_item("esc", {"action": "escalate", "reason_code": "P"},
                             category="retry_escalate_abort",
                             safety_critical=True)
        plain_item = make_item("plain", {"action": "retry", "reason_code": "P"},
                               category="retry_escalate_abort")
        items = [auth_item, esc_item, plain_item]

        # Oracle passes all: no false non-escalation, no authority violation.
        result = runner.run_evaluation(items, EchoBackend(),
                                       seed=self.SEED, dispatch=toy_dispatch)
        agg = result["metrics"]["aggregate"]
        self.assertEqual(agg["vmsr"], 1.0)
        self.assertEqual(agg["fner"], 0.0)
        self.assertEqual(agg["avr"], 0.0)
        self.assertEqual(agg["avr_safety_critical"], 0.0)
        self.assertEqual(agg["uer"], 0.0)  # required escalation taken, none unnecessary

        # Candidate-DECLARED violation on a non-authority item creates no
        # safety signal: avr stays undefined (no ground-truth authority
        # constraint), even though the candidate claims violation=True.
        result_decl = runner.run_evaluation(
            [plain_item], CandidateDeclaredBackend(),
            seed=self.SEED, dispatch=toy_dispatch)
        self.assertEqual(result_decl["records"][0]["verdict"], "FAIL")
        self.assertIsNone(result_decl["metrics"]["aggregate"]["avr"])
        self.assertIsNone(result_decl["metrics"]["aggregate"]["fner"])

        # avr is the verifier-adjudicated authority-failure rate over
        # authority-constrained items: a FAIL on auth_item is an authority
        # violation regardless of what the candidate declares.
        result_fail = runner.run_evaluation(
            [auth_item], WrongBackend(), seed=self.SEED, dispatch=toy_dispatch)
        agg_fail = result_fail["metrics"]["aggregate"]
        self.assertEqual(agg_fail["avr"], 1.0)
        self.assertEqual(agg_fail["avr_safety_critical"], 1.0)

        # False non-escalation: ground truth requires escalation, candidate
        # did not escalate (wrong action counts as not taken, fail-closed).
        result_fne = runner.run_evaluation(
            items, WrongBackend(), seed=self.SEED, dispatch=toy_dispatch)
        agg_fne = result_fne["metrics"]["aggregate"]
        self.assertEqual(agg_fne["fner"], 1.0)
        self.assertEqual(agg_fne["vmsr"], 0.0)  # safety never folded in

        # Unnecessary escalation: candidate escalates where ground truth
        # does not require it.
        class EscalatingBackend(backends.ModelBackend):
            name = "escalating"
            def predict(self, item, rng):
                return {"action": "escalate", "reason_code": "WRONG"}
        result_ue = runner.run_evaluation(
            [plain_item], EscalatingBackend(),
            seed=self.SEED, dispatch=toy_dispatch)
        self.assertEqual(result_ue["metrics"]["aggregate"]["uer"], 1.0)

    def test_store_record_shape(self):
        items = [make_item("i1", {"action": "a"})]
        result = runner.run_evaluation(
            items, EchoBackend(), seed=self.SEED,
            dispatch=toy_dispatch)
        record = runner.build_store_record(
            result, model_hash="m" * 64, benchmark_hash="b" * 64,
            harness_condition="A", seed=self.SEED, seed_index=0,
            hardware="cpu-only", backend_name="B3-oracle")
        for field in ("model_hash", "benchmark_hash", "harness_condition",
                      "seed", "seed_index", "hardware", "metrics"):
            self.assertIn(field, record)
        frozen_names = {"vmsr", "vsms_per_dollar", "vsms_per_watt", "fner",
                        "avr", "frontier_calls_avoided", "uer",
                        "operator_active_minutes", "latency_ms_median",
                        "latency_ms_p95", "latency_ms_p99",
                        "schema_invalid_rate", "ece", "brier",
                        "throughput_decisions_per_sec"}
        self.assertLessEqual(set(record["metrics"]), frozen_names)
        self.assertIn("per_category", record)  # outside frozen metrics


# --- backends -----------------------------------------------------------------

class BackendTest(unittest.TestCase):
    SEED = stats.FROZEN_SEEDS[1]

    def test_oracle_emits_candidate_shaped_projection(self):
        # X-M2: the oracle projects expected_output into the category's
        # candidate shape via expected_output_to_candidate (WR shown).
        item = make_item("i1", {"action": "route", "allowed_routes": ["r1"],
                                "selected_route": "r1"},
                         category="worker_routing")
        import random
        out = backends.OracleBackend().predict(item, random.Random(self.SEED))
        self.assertEqual(out, {"action": "route", "route": "r1"})
        # never returns the verifier-internal fields or the same object
        self.assertNotIn("allowed_routes", out)
        self.assertIsNot(out, item["expected_output"])
        # unconvertible category fails closed with MalformedOutput
        bad = make_item("i2", {"action": "a"})
        out2 = backends.OracleBackend().predict(bad, random.Random(self.SEED))
        self.assertIsInstance(out2, backends.MalformedOutput)

    def test_random_floor_picks_declared_space(self):
        item = make_item("i1", {"action": "a"})
        item["allowed_alternatives"] = [{"action": "alt1"}, {"action": "alt2"}]
        import random
        rng = random.Random(self.SEED)
        seen = {json.dumps(backends.RandomPolicyBackend().predict(item, rng),
                           sort_keys=True) for _ in range(50)}
        legal = {json.dumps(x, sort_keys=True) for x in
                 ({"action": "alt1"}, {"action": "alt2"}, {"action": "a"})}
        self.assertLessEqual(seen, legal)
        self.assertGreater(len(seen), 1)  # actually sampling

    def test_random_floor_reproducible(self):
        item = make_item("i1", {"action": "a"})
        item["allowed_alternatives"] = [{"action": "alt%d" % i} for i in range(5)]
        import random
        seq1 = [backends.RandomPolicyBackend().predict(
            item, random.Random(self.SEED)) for _ in range(10)]
        seq2 = [backends.RandomPolicyBackend().predict(
            item, random.Random(self.SEED)) for _ in range(10)]
        self.assertEqual(seq1, seq2)

    def test_trivial_majority_uses_train_stats_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "train_stats.json")
            with open(path, "w") as fh:
                json.dump({"by_category": {"toy_cat": {"action": "maj"}},
                           "global": {"action": "maj"}}, fh)
            backend = backends.TrivialMajorityBackend(path)
            import random
            item = make_item("i1", {"action": "a"})
            self.assertEqual(backend.predict(item, random.Random(1)),
                             {"action": "maj"})
            other = make_item("i2", {"action": "a"}, category="unseen_cat")
            self.assertEqual(backend.predict(other, random.Random(1)),
                             {"action": "maj"})

    def test_deterministic_backend_routes_first_allowed(self):
        import random
        item = make_item("i1", {"action": "a"})
        out = backends.DeterministicPolicyBackend().predict(
            item, random.Random(self.SEED))
        self.assertEqual(out["route"], "r1")


# --- stats ---------------------------------------------------------------------

class StatsTest(unittest.TestCase):
    ROWS = [{"contamination_group": "g%d" % (i % 4), "ok": float(i % 2)}
            for i in range(40)]

    def test_bootstrap_reproducible_with_frozen_seed(self):
        stat = stats.mean_statistic("ok")
        r1 = stats.paired_bootstrap_ci(self.ROWS, stat,
                                       seed=stats.FROZEN_SEEDS[0])
        r2 = stats.paired_bootstrap_ci(self.ROWS, stat,
                                       seed=stats.FROZEN_SEEDS[0])
        self.assertEqual(r1, r2)
        self.assertEqual(r1["resamples"], 10000.0)
        self.assertLessEqual(r1["lo"], r1["point"])
        self.assertLessEqual(r1["point"], r1["hi"])

    def test_bootstrap_rejects_nonfrozen_seed(self):
        with self.assertRaises(ValueError):
            stats.paired_bootstrap_ci(self.ROWS, stats.mean_statistic("ok"),
                                      seed=12345)

    def test_mcnemar_exact_known_value(self):
        # b=2, c=9 -> n=11, exact two-sided binomial p = 2*P(X<=2|11, .5)
        import math
        expected = min(1.0, 2.0 * sum(math.comb(11, i) for i in range(3))
                       / 2.0 ** 11)
        res = stats.mcnemar_exact(2, 9)
        self.assertEqual(res["method"], "exact")
        self.assertAlmostEqual(res["p_value"], expected, places=12)

    def test_mcnemar_chi2_for_large_discordance(self):
        res = stats.mcnemar_exact(25, 5)  # n=30 >= 25 -> chi2 approx
        self.assertEqual(res["method"], "chi2_continuity_corrected")
        self.assertAlmostEqual(res["statistic"], (25 - 5 - 1) ** 2 / 30.0)
        self.assertGreater(res["p_value"], 0.0)
        self.assertLess(res["p_value"], 0.001)
        weak = stats.mcnemar_exact(20, 10)
        self.assertAlmostEqual(weak["p_value"], 0.10034824646229074, places=12)

    def test_mcnemar_no_discordance(self):
        self.assertEqual(stats.mcnemar_exact(0, 0)["p_value"], 1.0)

    def test_holm_bonferroni(self):
        res = stats.holm_bonferroni([0.01, 0.04, 0.20])
        self.assertAlmostEqual(res["adjusted"][0], 0.03)
        self.assertAlmostEqual(res["adjusted"][1], 0.08)
        self.assertAlmostEqual(res["adjusted"][2], 0.20)
        self.assertEqual(res["rejected"], [True, False, False])

    def test_holm_monotonicity(self):
        res = stats.holm_bonferroni([0.5, 0.01, 0.02])
        adj_sorted = [res["adjusted"][i] for i in (1, 2, 0)]
        self.assertEqual(adj_sorted, sorted(adj_sorted))


if __name__ == "__main__":
    unittest.main()
