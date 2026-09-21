"""Regression tests for red-team finding G2-B1 (gold-label leak in B1).

G2-B1: RandomPolicyBackend built its sampling set as
``allowed_alternatives + [expected_output]``; with the frozen bench's
``allowed_alternatives == []`` the choice set degenerated to exactly the gold
label, so B1 deterministically emitted expected_output verbatim (measured
VMSR 0.873, 100% in 6/8 categories). Root cause enabler: the runner passed
the full item to backends under a shallow MappingProxyType.

These tests pin the remediation:
* the runner hands non-oracle backends ONLY a whitelisted candidate payload
  (gold fields absent; reading them fails loudly with KeyError);
* B1 samples uniformly over the schema-valid decision space declared by
  output_schema / input_state, never from expected_output;
* on the real 1,000-item frozen bench (regenerated from its frozen
  generator), B1 sits at the random floor, far below the 0.80 qualification
  threshold, and almost never reproduces the gold label;
* the B3 oracle -- the single documented gold-receiving backend -- still
  reaches the VMSR 1.0 ceiling.

Bench-dependent tests skip cleanly when the bench generator
(slm00/control-bench) or verifier suite (slm00/verifiers) is not present in
the checkout; the whitelist/KeyError tests are self-contained.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import tempfile
import unittest

from research.slm.eval.runner import backends, runner, stats


# --- locating the frozen bench generator / verifier suite -------------------

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_GENERATOR_PATH = os.path.join(
    _REPO_ROOT, "research", "slm", "bench", "generate_bench.py")
_SEED_DIR = os.path.join(_REPO_ROOT, "research", "slm", "bench", "seed")

HAS_GENERATOR = os.path.isfile(_GENERATOR_PATH) and os.path.isdir(_SEED_DIR)
try:
    import research.slm.verifiers  # noqa: F401
    HAS_VERIFIERS = True
except Exception:
    HAS_VERIFIERS = False


def _generate_bench(tmpdir):
    """Regenerate the frozen 1,000-item bench via its frozen generator."""
    spec = importlib.util.spec_from_file_location("generate_bench",
                                                  _GENERATOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = os.path.join(tmpdir, "bench.jsonl")
    manifest = os.path.join(tmpdir, "manifest.json")
    argv = ["generate_bench.py", "--seed-dir", _SEED_DIR,
            "--out", out, "--manifest", manifest]
    import sys
    saved = sys.argv
    try:
        sys.argv = argv
        rc = mod.main()
    finally:
        sys.argv = saved
    if rc not in (None, 0):
        raise AssertionError("bench generator exited with %r" % (rc,))
    return runner.load_benchmark(out)


def _exact_match_dispatch(item, candidate):
    """Conservative fallback scoring: exact equality with expected_output.

    Used only when the real verifier suite is not importable. It
    UNDERSTATES B1's floor (verifiers accept any legal route etc.), so a
    floor assertion that holds under exact-match holds a fortiori under the
    real suite.
    """
    if isinstance(candidate, backends.MalformedOutput) or not isinstance(
            candidate, dict):
        verdict, reason = "FAIL", "MALFORMED_OUTPUT"
    elif candidate == item.get("expected_output"):
        verdict, reason = "PASS", "OK"
    else:
        verdict, reason = "FAIL", "WRONG_ANSWER"
    return {"verdict": verdict, "reason_code": reason, "detail": ""}


def _dispatch(item, candidate):
    if HAS_VERIFIERS:
        return runner.default_dispatch(item, candidate)
    return _exact_match_dispatch(item, candidate)


# --- fixtures -----------------------------------------------------------------

def make_gold_laden_item():
    """Item carrying every gold/metadata field that must never leak."""
    item = {
        "item_id": "g2b1-1",
        "category": "worker_routing",
        "input_state": {
            "task": {"task_id": "t1", "required_capabilities": [],
                     "required_authority": []},
            "workers": [{"worker_id": "w1", "capabilities": [],
                         "authority": [], "available": True}],
            "allowed_actions": ["route", "hold", "escalate"],
        },
        "output_schema": {
            "type": "object", "required": ["action", "route"],
            "properties": {
                "action": {"enum": ["route", "hold", "escalate"]},
                "route": {"type": ["string", "null"]}}},
        "expected_output": {"action": "escalate", "allowed_routes": [],
                            "selected_route": None},
        "expected_escalation": True,
        "rationale": "gold rationale text",
        "verifier_ref": "slm00.verifier.worker_routing",
        "contamination_group": "grp-g2b1",
        "source_provenance": {"source": "synthetic"},
        "synthetic": True,
        "bench_version": "control-bench-v0",
        "safety_critical": True,
        "difficulty": {"branching_factor": 3},
        "allowed_alternatives": [],
    }
    item["digest"] = runner.item_digest(item)
    return item


# --- whitelist / structural control -------------------------------------------

class CandidatePayloadTest(unittest.TestCase):

    def test_payload_contains_only_live_model_fields(self):
        payload = backends.candidate_payload(make_gold_laden_item())
        self.assertLessEqual(
            set(payload), set(backends.CANDIDATE_PAYLOAD_FIELDS))
        for field in ("item_id", "category", "input_state", "output_schema"):
            self.assertIn(field, payload)

    def test_gold_and_metadata_fields_absent_and_fail_loudly(self):
        payload = backends.candidate_payload(make_gold_laden_item())
        for field in backends.GOLD_OR_METADATA_FIELDS:
            self.assertNotIn(field, payload)
            with self.assertRaises(KeyError, msg=field):
                payload[field]
        # .get() must not silently succeed either
        self.assertIsNone(payload.get("expected_output"))

    def test_payload_is_fresh_deep_copy_per_call(self):
        item = make_gold_laden_item()
        p1 = backends.candidate_payload(item)
        p2 = backends.candidate_payload(item)
        self.assertIsNot(p1, p2)
        self.assertIsNot(p1["input_state"], p2["input_state"])
        # mutating a payload can never reach the frozen item
        p1["input_state"]["workers"].clear()
        self.assertEqual(len(item["input_state"]["workers"]), 1)
        self.assertEqual(len(p2["input_state"]["workers"]), 1)

    def test_runner_never_hands_gold_to_non_oracle_backends(self):
        """End-to-end through run_evaluation: a probing backend records the
        exact mapping it receives; gold keys must be absent and KeyError on
        access; the B3 oracle is the single declared exception."""
        received = []

        class ProbeBackend(backends.ModelBackend):
            name = "probe"
            def predict(self, item, rng):
                received.append(item)
                with self_.assertRaises(KeyError):
                    item["expected_output"]
                return {"action": "hold", "route": None}

        self_ = self
        item = make_gold_laden_item()
        runner.run_evaluation([item], ProbeBackend(),
                              seed=stats.FROZEN_SEEDS[0], dispatch=_dispatch)
        self.assertEqual(len(received), 1)
        self.assertLessEqual(set(received[0]),
                             set(backends.CANDIDATE_PAYLOAD_FIELDS))
        for field in backends.GOLD_OR_METADATA_FIELDS:
            self.assertNotIn(field, received[0])

        oracle_seen = []

        class ProbeOracle(backends.ModelBackend):
            name = "probe-oracle"
            requires_gold = True  # documented B3-style exception
            def predict(self, item, rng):
                oracle_seen.append(item)
                return {"action": "hold", "route": None}

        runner.run_evaluation([item], ProbeOracle(),
                              seed=stats.FROZEN_SEEDS[0], dispatch=_dispatch)
        self.assertIn("expected_output", oracle_seen[0])  # oracle path kept

    def test_only_oracle_backend_declares_requires_gold(self):
        gold = {name for name, cls in backends.BACKENDS.items()
                if getattr(cls, "requires_gold", False)}
        self.assertEqual(gold, {"B3-oracle"})


# --- B1 behavior ----------------------------------------------------------------

class RandomFloorUnitTest(unittest.TestCase):
    SEED = stats.FROZEN_SEEDS[0]

    def test_b1_samples_declared_schema_space_without_gold(self):
        item = make_gold_laden_item()
        payload = backends.candidate_payload(item)
        rng = random.Random(self.SEED)
        b1 = backends.RandomPolicyBackend()
        seen = {json.dumps(b1.predict(payload, rng), sort_keys=True)
                for _ in range(200)}
        # actions drawn uniformly from the declared enum; routes from the
        # input_state-declared worker ids (or None)
        legal = {json.dumps({"action": a, "route": r}, sort_keys=True)
                 for a in ("route", "hold", "escalate")
                 for r in ("w1", None)}
        self.assertLessEqual(seen, legal)
        self.assertGreater(len(seen), 1)  # actually sampling, not echoing
        # gold label {action: escalate, route: null-ish} is at most one draw
        # of many -- never the deterministic output
        gold_like = {json.dumps({"action": "escalate"}, sort_keys=True)}
        self.assertNotEqual(seen, gold_like)

    def test_b1_ignores_expected_output_even_if_smuggled(self):
        """Defense in depth: even if expected_output were somehow present,
        B1's sampling space must not include it (regression for the original
        allowed_alternatives + [expected_output] defect)."""
        item = make_gold_laden_item()
        # shrink the schema space to force repeated draws; gold is a value
        # OUTSIDE the declared enum to make any leak visible
        item["output_schema"]["properties"]["action"] = {"enum": ["x", "y"]}
        item["expected_output"] = {"action": "GOLD", "route": None}
        rng = random.Random(self.SEED)
        b1 = backends.RandomPolicyBackend()
        seen = {json.dumps(b1.predict(item, rng), sort_keys=True)
                for _ in range(50)}
        self.assertLessEqual(
            seen, {json.dumps({"action": a, "route": "w1"}, sort_keys=True)
                   for a in ("x", "y")} |
                  {json.dumps({"action": a, "route": None}, sort_keys=True)
                   for a in ("x", "y")})
        self.assertNotIn(json.dumps({"action": "GOLD", "route": None},
                                    sort_keys=True), seen)

    def test_b1_deterministic_per_frozen_seed(self):
        item = backends.candidate_payload(make_gold_laden_item())
        b1 = backends.RandomPolicyBackend()
        seq1 = [b1.predict(item, random.Random(self.SEED)) for _ in range(20)]
        seq2 = [b1.predict(item, random.Random(self.SEED)) for _ in range(20)]
        self.assertEqual(seq1, seq2)


# --- bench-level floor / ceiling -------------------------------------------------

@unittest.skipUnless(HAS_GENERATOR,
                     "bench generator (slm00/control-bench) not in checkout")
class FrozenBenchFloorTest(unittest.TestCase):
    SEED = stats.FROZEN_SEEDS[0]

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.items = _generate_bench(cls._tmp.name)
        assert len(cls.items) == 1000, len(cls.items)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_b1_random_floor_far_below_qualification_threshold(self):
        result = runner.run_evaluation(
            self.items, backends.RandomPolicyBackend(),
            seed=self.SEED, dispatch=_dispatch)
        agg = result["metrics"]["aggregate"]
        self.assertEqual(agg["n_scored"], 1000)
        self.assertEqual(agg["n_benchmark_defects"], 0)
        vmsr = agg["vmsr"]
        self.assertIsNotNone(vmsr)
        # Random floor: must be FAR below the 0.80 qualification threshold
        # (the leaked-gold B1 measured 0.873). A healthy random policy on a
        # non-trivial bench scores orders of magnitude lower.
        self.assertLess(vmsr, 0.50,
                        "B1 VMSR %.3f suspiciously high -- label leak or "
                        "trivially passable bench?" % vmsr)
        for cat, block in result["metrics"]["per_category"].items():
            self.assertLess(
                block["vmsr"] or 0.0, 0.80,
                "B1 category %s VMSR %r at/above qualification threshold"
                % (cat, block["vmsr"]))

    def test_b1_output_almost_never_equals_gold(self):
        """Replay the exact runner RNG stream and compare raw B1 predictions
        against expected_output: the overwhelming majority must differ."""
        b1 = backends.RandomPolicyBackend()
        rng = random.Random(self.SEED)
        equal = 0
        for item in self.items:
            pred = b1.predict(backends.candidate_payload(item), rng)
            if pred == item["expected_output"]:
                equal += 1
        self.assertLess(equal / len(self.items), 0.05,
                        "%d/1000 B1 outputs equal the gold label" % equal)

    def test_b1_floor_reproducible(self):
        r1 = runner.run_evaluation(self.items, backends.RandomPolicyBackend(),
                                   seed=self.SEED, dispatch=_dispatch)
        r2 = runner.run_evaluation(self.items, backends.RandomPolicyBackend(),
                                   seed=self.SEED, dispatch=_dispatch)
        self.assertEqual(r1["metrics"]["aggregate"]["vmsr"],
                         r2["metrics"]["aggregate"]["vmsr"])

    @unittest.skipUnless(HAS_VERIFIERS,
                         "verifier suite (slm00/verifiers) not in checkout")
    def test_b3_oracle_ceiling_is_one(self):
        """B3 legitimately receives gold (documented path) and must still
        define the ceiling at VMSR 1.0 on the frozen bench."""
        result = runner.run_evaluation(
            self.items, backends.OracleBackend(),
            seed=self.SEED, dispatch=runner.default_dispatch)
        agg = result["metrics"]["aggregate"]
        self.assertEqual(agg["n_scored"], 1000)
        self.assertEqual(agg["vmsr"], 1.0)


if __name__ == "__main__":
    unittest.main()
