"""Synthetic clocks, wheels and observations only; no installed/long soak proof."""
import copy
import json
import importlib
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from scripts import qualification_rc_soak as soak


def policy(**overrides):
    values = dict(duration=10, interval=5, max_gap=6, max_rss=10000,
                  max_fds=100, workload=("submit", "complete"))
    values.update(overrides)
    return soak.Policy(**values)


def sample(t=0, **overrides):
    values = dict(monotonic=t, wall=1000+t, rss=100, fds=5, identity={"id": "frozen"},
                  origins={"residual": {"path": "synthetic/residual/__init__.py", "sha256": "a"*64}},
                  epoch={"run": "one", "pid": 1}, alive=True,
                  counts={"submit": int(t)+1, "complete": int(t)+1})
    values.update(overrides)
    return values


def write_selected_fixture(root, wheel, configuration, *, profile_policy=None):
    """Generate a caller's SYNTHETIC test requirements, not production defaults."""
    if profile_policy is None:
        profile_policy = policy()
    config_bytes = configuration.read_bytes()
    profile_doc = {"schema": "residual.rc-soak.profile.v1", "id": "synthetic",
                   "configuration_sha256": soak.digest(config_bytes),
                   "policy": soak.policy_requirements(profile_policy)}
    profile_path = root / "profile.json"
    profile_path.write_bytes(soak.canonical(profile_doc))
    with zipfile.ZipFile(wheel) as archive:
        adapter_hash = soak.digest(archive.read("residual/adapter.py"))
    source = {"head": "a"*40, "tree": "b"*40}
    facts = {"schema": "residual.rc-soak.manifest.v1", "source": source,
             "artifacts": [{"id": "synthetic-wheel", "kind": "wheel", "path": wheel.name,
                            "sha256": soak.digest(wheel.read_bytes()), "source": source}],
             "candidate_artifact": "synthetic-wheel",
             "configuration": {"path": configuration.name, "sha256": soak.digest(config_bytes),
                               "canonical_sha256": soak.digest(soak.canonical(json.loads(config_bytes)))},
             "profile": {"path": "profile.json", "id": "synthetic", "sha256": soak.digest(profile_path.read_bytes())},
             "runner": {"sha256": soak.digest(Path(soak.__file__).read_bytes())},
             "adapter": {"module": "residual.adapter", "sha256": adapter_hash, "artifact_id": "synthetic-wheel"},
             "environment": {"os": "synthetic", "architecture": "synthetic",
                             "python": {"implementation": "synthetic", "version": "0.test", "executable_sha256": "e"*64},
                             "dependencies": [{"name": "synthetic-dependency", "version": "0.test", "artifact_sha256": "f"*64}]}}
    path = root / "manifest.json"
    path.write_bytes(soak.canonical(facts))
    return path, soak.digest(soak.canonical(facts))


class MonitorTests(unittest.TestCase):
    def monitor(self):
        return soak.Continuity(policy(), sample()["identity"], sample()["epoch"])

    def test_full_observation_requires_both_clocks_and_three_samples(self):
        m = self.monitor()
        self.assertTrue(m.add(sample()))
        self.assertFalse(m.complete())
        self.assertTrue(m.add(sample(5)))
        self.assertFalse(m.complete())
        self.assertTrue(m.add(sample(10)))
        self.assertTrue(m.complete())

    def test_gap_reset_drift_interruption_and_resources_fail_sticky(self):
        for bad, reason in [
            (sample(7), "observation_gap"),
            (sample(5, wall=1009), "observation_gap"),
            (sample(0), "clock_reset"),
            (sample(5, wall=999), "clock_reset"),
            (sample(5, epoch={"run": "two", "pid": 1}), "identity_drift"),
            (sample(5, identity={"id": "other"}), "identity_drift"),
            (sample(5, alive=False), "interruption"),
            (sample(5, rss=10001), "resource_limit"),
            (sample(5, fds=101), "resource_limit"),
            (sample(5, counts={"submit": 1, "complete": 1}), "workload_stalled_or_reset"),
            (sample(5, counts={"submit": 0, "complete": 0}), "workload_stalled_or_reset"),
        ]:
            with self.subTest(reason=reason, bad=bad):
                m = self.monitor(); m.add(sample())
                self.assertFalse(m.add(bad))
                first = copy.deepcopy(m.first_failure)
                self.assertEqual(first["reason"], reason)
                self.assertFalse(m.add(sample(10)))
                self.assertEqual(m.first_failure, first)
                self.assertFalse(m.complete())

    def test_nonfinite_boolean_missing_and_unexpected_observations(self):
        for key in ("monotonic", "wall", "rss", "fds"):
            for value in (float("nan"), float("inf"), -1, True, "0"):
                with self.subTest(key=key, value=value):
                    self.assertFalse(self.monitor().add(sample(**{key: value})))
        for counts in ({}, {"submit": True, "complete": 1}, {"submit": 1, "complete": 1, "SECRET": 1}):
            self.assertFalse(self.monitor().add(sample(counts=counts)))

    def test_numeric_policy_validation(self):
        for key in ("duration", "interval", "max_gap", "max_rss", "max_fds"):
            for value in (float("nan"), float("inf"), -1, 0, True, 10**1000):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    policy(**{key: value})
        for values in ({"interval": 7}, {"duration": 6}, {"workload": ()},
                       {"workload": ("submit", "submit")}, {"workload": ("SECRET\n",)}):
            with self.assertRaises(ValueError):
                policy(**values)

    def test_reused_counts_and_mutation_after_acceptance_are_snapshotted(self):
        m = self.monitor()
        counts = {"submit": 1, "complete": 1}
        first = sample(counts=counts)
        self.assertTrue(m.add(first))
        counts.update(submit=2, complete=2)
        first["identity"]["id"] = "mutated"
        self.assertEqual(m.previous["counts"], {"submit": 1, "complete": 1})
        self.assertEqual(m.previous["identity"], {"id": "frozen"})
        self.assertTrue(m.add(sample(5, counts=counts)))
        counts.update(submit=3, complete=3)
        self.assertEqual(m.previous["counts"]["complete"], 2)
        self.assertTrue(m.add(sample(10, counts=counts)))
        self.assertTrue(m.complete())


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.installed = self.root / "installed"
        (self.installed / "residual").mkdir(parents=True)
        self.source = b"# synthetic candidate\n"
        (self.installed / "residual/__init__.py").write_bytes(self.source)
        self.wheel = self.root / "candidate.whl"
        with zipfile.ZipFile(self.wheel, "w") as z:
            z.writestr("residual/__init__.py", self.source)
        self.config = self.root / "config.json"
        self.config.write_text('{"mode":"offline"}')
        self.modules = {"residual": SimpleNamespace(__file__=str(self.installed / "residual/__init__.py"),
                          __path__=[str(self.installed / "residual")])}

    def binding(self):
        return soak.Binding(self.wheel, soak.digest(self.wheel.read_bytes()), self.installed,
                            self.config, "representative", "a"*40, "b"*40,
                            expected_configuration_sha256=soak.digest(soak.canonical({"mode": "offline"})),
                            expected_configuration_bytes_sha256=soak.digest(b'{"mode":"offline"}'))

    def test_loaded_origin_and_frozen_hash_match(self):
        b = self.binding()
        seen = b.observe(self.modules)
        self.assertEqual(seen["identity"]["artifact_sha256"], soak.digest(self.wheel.read_bytes()))
        self.assertEqual(seen["origins"]["residual"]["sha256"], soak.digest(self.source))
        b.check_search_path([str(self.installed)])

    def test_artifact_configuration_and_installed_file_drift(self):
        for path in (self.wheel, self.config, self.installed / "residual/__init__.py"):
            with self.subTest(path=path):
                b = self.binding(); original = path.read_bytes()
                path.write_bytes(b'{}')
                with self.assertRaises(ValueError):
                    b.observe(self.modules)
                path.write_bytes(original)

    def test_source_shadowing_even_when_bytes_identical(self):
        checkout = self.root / "checkout" / "residual"
        checkout.mkdir(parents=True)
        (checkout / "__init__.py").write_bytes(self.source)
        with self.assertRaisesRegex(ValueError, "checkout_shadowing"):
            self.binding().observe({"residual": SimpleNamespace(__file__=str(checkout / "__init__.py"))})
        with self.assertRaisesRegex(ValueError, "checkout_shadowing"):
            self.binding().check_search_path([str(checkout.parent), str(self.installed)])

    def test_missing_origin_package_path_and_cached_bytecode_reject(self):
        b = self.binding()
        with self.assertRaises(ValueError):
            b.observe({})
        with self.assertRaises(ValueError):
            b.observe({"residual": SimpleNamespace()})
        self.modules["residual"].__path__ = [str(self.root)]
        with self.assertRaisesRegex(ValueError, "search_path"):
            b.observe(self.modules)
        self.modules["residual"].__path__ = [str(self.installed / "residual")]
        cache = self.root / "cached.pyc"; cache.write_bytes(b"stale")
        self.modules["residual"].__cached__ = str(cache)
        with self.assertRaisesRegex(ValueError, "cached_runtime"):
            b.observe(self.modules)

    def test_invalid_configuration_and_unsafe_archive(self):
        for value in ('{"x":NaN}', '{"x":1,"x":2}', '[]', '"SECRET"'):
            self.config.write_text(value)
            with self.assertRaises(ValueError):
                self.binding()
        self.config.write_text('{"mode":"offline"}')
        with zipfile.ZipFile(self.wheel, "a") as z:
            z.writestr("../escape", b"bad")
        with self.assertRaisesRegex(ValueError, "unsafe_wheel"):
            self.binding()


class RunnerTests(unittest.TestCase):
    def execute(self, root, *, failure=None, journal_factory=soak.Journal):
        config = root / "config.json"; config.write_text('{"mode":"offline"}')
        clock = [0]
        identity = sample()["identity"]
        binding = SimpleNamespace(observe=lambda: {"identity": identity, "origins": sample()["origins"]}, profile="representative", config=config,
                                  config_hash=soak.digest(soak.canonical({"mode": "offline"})))
        counts = [0]
        reused = {"submit": 0, "complete": 0}
        def step(profile, cfg):
            counts[0] += 1
            if failure == "interrupt" and counts[0] == 2:
                raise KeyboardInterrupt
            if failure == "exception" and counts[0] == 2:
                raise RuntimeError("SECRET https://signed.invalid/token")
            if failure == "slow":
                clock[0] += 7
            reused.update(submit=counts[0], complete=counts[0])
            return {"profile": profile, "effective_configuration": cfg if failure != "config" else {},
                    "counts": reused, "SECRET": "never-persist"}
        journal = journal_factory(root / "evidence")
        result = soak.run(binding, policy(), step, journal, clock=lambda: clock[0],
                          wall=lambda: 1000+clock[0], sleep=lambda n: clock.__setitem__(0, clock[0]+n),
                          metrics=lambda: (100, 5))
        raw = (root / "evidence/observations.jsonl").read_text()
        return result, raw, [json.loads(line) for line in raw.splitlines()]

    def test_synthetic_complete_is_explicitly_not_rc_qualification(self):
        with tempfile.TemporaryDirectory() as temp:
            code, raw, rows = self.execute(Path(temp), journal_factory=SyntheticJournal)
            self.assertEqual(code, 0)
            self.assertEqual(rows[-1]["event"], "provisional_completion")
            self.assertFalse(rows[-1]["rc_qualified"])
            seal = soak.validate_sealed(Path(temp) / "evidence", rows[0]["identity"], rows[0]["epoch"], policy())
            self.assertEqual(seal["sample_count"], 3)
            self.assertEqual([r["counts"]["complete"] for r in rows if r["event"] == "sample"], [1, 2, 3])
            self.assertNotIn("PASS", raw)
            self.assertNotIn("SECRET", raw)

    def test_failure_interruption_and_slow_workload_retain_first_failure(self):
        for failure in ("exception", "interrupt", "config", "slow"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                code, raw, rows = self.execute(Path(temp), failure=failure)
                self.assertEqual(code, 1)
                self.assertEqual(sum(r["event"] == "first_failure" for r in rows), 1)
                self.assertEqual(rows[-1]["event"], "first_failure")
                self.assertNotIn('"event":"complete"', raw)
                self.assertNotIn("SECRET", raw)
                self.assertNotIn("https:", raw)

    def test_output_cannot_overwrite_or_resume_and_first_failure_is_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run"
            j = soak.Journal(path)
            j.fail("first", 0); j.fail("second", 1); j.close()
            before = (path / "observations.jsonl").read_bytes()
            with self.assertRaises(FileExistsError):
                soak.Journal(path)
            self.assertEqual(before, (path / "observations.jsonl").read_bytes())
            self.assertNotIn(b"second", before)


class MemoryRunnerTests(unittest.TestCase):
    """Independent runner interactions, not a substitute for blocked file tests."""
    def test_completion_and_failures_without_files_or_processes(self):
        for failure in (None, "exception", "interrupt", "slow", "config", "drift", "metric"):
            with self.subTest(failure=failure):
                ticks = [0]
                calls = [0]
                rows = []
                closed = []
                cfg = {"mode": "synthetic"}
                b = SimpleNamespace(profile="synthetic", config=Path("unused"),
                    config_hash=soak.digest(soak.canonical(cfg)),
                    observe=lambda: {"identity": {"id": "drift" if failure == "drift" and calls[0] > 1 else "frozen"},
                                     "origins": sample()["origins"]})
                def step(profile, config):
                    calls[0] += 1
                    if calls[0] == 2:
                        if failure == "exception":
                            raise RuntimeError("SECRET https://signed.invalid")
                        if failure == "interrupt":
                            raise KeyboardInterrupt
                        if failure == "slow":
                            ticks[0] += 7
                    return {"profile": profile, "effective_configuration": {} if failure == "config" else config,
                            "counts": {"submit": calls[0], "complete": calls[0]}, "SECRET": "hidden"}
                journal = SimpleNamespace(write=lambda r: rows.append(copy.deepcopy(r)),
                    fail=lambda reason, index: rows.append({"event": "first_failure", "reason": reason, "index": index}),
                    close=lambda: closed.append(True), finalize=lambda identity, epoch, expected_policy: None)
                with patch.object(soak, "read_config", return_value=cfg):
                    code = soak.run(b, policy(), step, journal, clock=lambda: ticks[0],
                        wall=lambda: 1000+ticks[0], sleep=lambda n: ticks.__setitem__(0, ticks[0]+n),
                        metrics=lambda: (float("nan"), 1) if failure == "metric" else (100, 5))
                self.assertEqual(code, 0 if failure is None else 1)
                self.assertEqual(rows[-1]["event"], "provisional_completion" if failure is None else "first_failure")
                self.assertEqual(closed, [True])
                self.assertNotIn("SECRET", json.dumps(rows))
                if failure is None:
                    self.assertFalse(rows[-1]["rc_qualified"])


class AdmissionTests(unittest.TestCase):
    """Real CLI subprocesses execute only synthetic reject/negative-control code."""
    setUp = BindingTests.setUp
    binding = BindingTests.binding
    def prepare_adapter(self):
        self.marker = self.root / "import-side-effect"
        self.bad = ("from pathlib import Path\nPath(" + repr(str(self.marker)) + ").write_text('executed')\n").encode()
        self.adapter = self.installed / "residual/adapter.py"
        source = b"def qualification_soak_step(profile, config):\n    raise RuntimeError('synthetic stop')\n"
        self.adapter.write_bytes(source)
        with zipfile.ZipFile(self.wheel, "a") as archive:
            archive.writestr("residual/adapter.py", source)

    def command(self):
        manifest, expected = write_selected_fixture(self.root, self.wheel, self.config,
                                                    profile_policy=policy(workload=("complete",)))
        return [sys.executable, "-I", "-B", str(Path(soak.__file__).absolute()),
                "--manifest", str(manifest), "--manifest-sha256", expected, "--inputs-root", str(self.root),
                "--artifact", str(self.wheel), "--sha256", soak.digest(self.wheel.read_bytes()),
                "--installed-root", str(self.installed), "--configuration", str(self.config),
                "--profile", "synthetic", "--commit", "a"*40, "--tree", "b"*40,
                "--adapter", "residual.adapter", "--output-dir", str(self.root / "evidence"),
                "--duration", "10", "--interval", "5", "--max-gap", "6",
                "--max-rss", "10000", "--max-fds", "100", "--workload", "complete"]

    def test_real_entry_rejects_tampered_initializer_without_side_effect(self):
        self.prepare_adapter()
        (self.installed / "residual/__init__.py").write_bytes(self.bad)
        result = subprocess.run(self.command(), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid_binding_or_policy", result.stderr)
        self.assertFalse(self.marker.exists())

    def test_real_entry_rejects_tampered_adapter_without_side_effect(self):
        self.prepare_adapter(); self.adapter.write_bytes(self.bad)
        result = subprocess.run(self.command(), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.marker.exists())

    def test_real_entry_rejects_executable_cache_without_side_effect(self):
        import importlib.util
        import marshal
        self.prepare_adapter()
        # Valid sourceless cache with observable malicious code; admission must reject it.
        (self.installed / "residual/extra.pyc").write_bytes(
            importlib.util.MAGIC_NUMBER + bytes(12) + marshal.dumps(compile(self.bad, "extra", "exec")))
        result = subprocess.run(self.command(), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.marker.exists())

    def test_substitution_after_admission_cannot_execute_replacement(self):
        self.prepare_adapter()
        saved = {k: v for k, v in sys.modules.items() if k.split('.')[0] in soak.Binding.PREFIXES}
        for k in saved: del sys.modules[k]
        importer = None
        try:
            b = self.binding()
            importer = b.admit("residual.adapter", [str(self.installed)])
            self.adapter.write_bytes(self.bad)
            sys.meta_path.insert(0, importer)
            module = importlib.import_module("residual.adapter")
            self.assertTrue(callable(module.qualification_soak_step))
            self.assertFalse(self.marker.exists())
            with self.assertRaisesRegex(ValueError, "installed_bytes_drift"):
                b.observe()
        finally:
            if importer in sys.meta_path: sys.meta_path.remove(importer)
            for k in list(sys.modules):
                if k.split('.')[0] in soak.Binding.PREFIXES: del sys.modules[k]
            sys.modules.update(saved)

    def test_lazy_import_keeps_identity_and_validates_each_new_origin(self):
        self.prepare_adapter()
        lazy = self.installed / "residual/lazy.py"
        lazy.write_bytes(b"VALUE = 1\n")
        with zipfile.ZipFile(self.wheel, "a") as archive:
            archive.writestr("residual/lazy.py", lazy.read_bytes())
        saved = {k: v for k, v in sys.modules.items() if k.split('.')[0] in soak.Binding.PREFIXES}
        for k in saved: del sys.modules[k]
        importer = None
        try:
            b = self.binding(); importer = b.admit("residual.adapter", [str(self.installed)])
            sys.meta_path.insert(0, importer)
            importlib.import_module("residual.adapter")
            initial = b.observe()
            module = importlib.import_module("residual.lazy")
            after = b.observe()
            self.assertEqual(initial["identity"], after["identity"])
            self.assertNotIn("residual.lazy", initial["origins"])
            self.assertIn("residual.lazy", after["origins"])
            monitor = soak.Continuity(policy(), initial["identity"], sample()["epoch"])
            self.assertTrue(monitor.add(sample(identity=initial["identity"], origins=initial["origins"])))
            self.assertTrue(monitor.add(sample(5, identity=after["identity"], origins=after["origins"])))
            foreign = self.root / "foreign.py"; foreign.write_bytes(lazy.read_bytes())
            module.__file__ = str(foreign)
            with self.assertRaisesRegex(ValueError, "checkout_shadowing"):
                b.observe()
            module.__file__ = str(lazy)
            lazy.write_bytes(b"VALUE = 2\n")
            with self.assertRaisesRegex(ValueError, "installed_bytes_drift"):
                b.observe()
        finally:
            if importer in sys.meta_path: sys.meta_path.remove(importer)
            for k in list(sys.modules):
                if k.split('.')[0] in soak.Binding.PREFIXES: del sys.modules[k]
            sys.modules.update(saved)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        BindingTests.setUp(self)
        self.adapter_bytes = b"def qualification_soak_step(profile, config):\n    return {}\n"
        (self.installed / "residual/adapter.py").write_bytes(self.adapter_bytes)
        with zipfile.ZipFile(self.wheel, "a") as archive:
            archive.writestr("residual/adapter.py", self.adapter_bytes)
        self.manifest, self.expected = write_selected_fixture(self.root, self.wheel, self.config)
        self.facts = json.loads(self.manifest.read_bytes())

    def load(self, expected=None):
        return soak.SelectedManifest.load(self.manifest, self.root, self.expected if expected is None else expected)

    def rewrite(self, facts):
        self.manifest.write_bytes(soak.canonical(facts))
        return soak.digest(soak.canonical(facts))

    def test_canonical_digest_and_explicit_nonqualification_states(self):
        self.manifest.write_text(json.dumps(self.facts, indent=4, sort_keys=False))
        selected = self.load()
        self.assertEqual(selected.sha256, self.expected)
        binding = soak.Binding.from_selected_manifest(selected, self.installed)
        self.assertEqual(binding.identity["manifest_sha256"], self.expected)
        self.assertEqual(binding.identity["profile_bytes_sha256"], self.facts["profile"]["sha256"])
        self.assertFalse(binding.identity["rc_qualified"])
        self.assertEqual(binding.identity["external_attestation_status"], "not_established")
        self.assertEqual(binding.identity["prerequisite_authority_status"], "not_established")
        self.assertEqual(binding.identity["declared_environment_status"], "declaration_only")
        # Dependency/interpreter claims are deliberately synthetic, not measured.
        self.assertEqual(binding.identity["declared_environment_sha256"], soak.digest(soak.canonical(self.facts["environment"])))

    def test_selected_digest_mismatch_cannot_be_relearned(self):
        self.facts["source"]["head"] = "c"*40
        self.rewrite(self.facts)
        with self.assertRaisesRegex(ValueError, "selected_manifest_digest_mismatch"):
            self.load()
        with self.assertRaisesRegex(ValueError, "selected_manifest_digest_mismatch"):
            soak.SelectedManifest(self.manifest, self.root, self.expected, soak.canonical(self.facts))

    def test_cli_source_override_rejected_before_any_runtime_or_evidence(self):
        command = [sys.executable, "-I", "-B", str(Path(soak.__file__).absolute()),
                   "--manifest", str(self.manifest), "--manifest-sha256", self.expected,
                   "--inputs-root", str(self.root), "--artifact", str(self.wheel),
                   "--sha256", self.facts["artifacts"][0]["sha256"], "--installed-root", str(self.installed),
                   "--configuration", str(self.config), "--profile", "synthetic", "--commit", "c"*40,
                   "--tree", "b"*40, "--adapter", "residual.adapter", "--output-dir", str(self.root / "evidence"),
                   "--duration", "10", "--interval", "5", "--max-gap", "6", "--max-rss", "10000",
                   "--max-fds", "100", "--workload", "submit", "--workload", "complete"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid_binding_or_policy", result.stderr)
        self.assertFalse((self.root / "evidence").exists())

    def test_missing_unknown_and_duplicate_json_fields_rejected(self):
        for scope in (None, "source", "configuration", "profile", "runner", "adapter", "environment"):
            for change in ("missing", "unknown"):
                with self.subTest(scope=scope, change=change):
                    facts = copy.deepcopy(self.facts)
                    target = facts if scope is None else facts[scope]
                    if change == "missing": del target[next(iter(target))]
                    else: target["unexpected"] = True
                    with self.assertRaises(ValueError): self.load(self.rewrite(facts))
        self.manifest.write_bytes(b'{"schema":"one","schema":"two"}')
        with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
            self.load()

    def test_wrong_source_artifact_adapter_runner_and_profile_rejected(self):
        mutations = [
            lambda f: f["artifacts"][0]["source"].update(head="c"*40),
            lambda f: f["artifacts"][0].update(sha256="0"*64),
            lambda f: f.update(candidate_artifact="missing"),
            lambda f: f["adapter"].update(artifact_id="other"),
            lambda f: f["adapter"].update(sha256="0"*64),
            lambda f: f["runner"].update(sha256="0"*64),
            lambda f: f["profile"].update(id="other"),
            lambda f: f["source"].update(head=True),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                facts = copy.deepcopy(self.facts); mutate(facts)
                with self.assertRaises(ValueError):
                    soak.Binding.from_selected_manifest(self.load(self.rewrite(facts)), self.installed)

    def test_configuration_profile_and_manifest_drift_after_selection(self):
        for path in (self.config, self.root / "profile.json", self.manifest):
            with self.subTest(path=path):
                selected = self.load(); original = path.read_bytes()
                path.write_bytes(b'{}')
                with self.assertRaises(ValueError): selected.verify_inputs()
                path.write_bytes(original)
        # Even semantically identical config whitespace violates the byte binding.
        selected = self.load()
        self.config.write_text('{ "mode" : "offline" }')
        with self.assertRaisesRegex(ValueError, "manifest_input_hash_mismatch"):
            selected.verify_inputs()

    def test_profile_substitution_after_read_cannot_replace_verified_policy(self):
        selected = self.load()
        original_read = soak.read_bounded
        profile_path = self.root / "profile.json"
        reads = []
        def replaced(path, limit=65536):
            raw = original_read(path, limit)
            if Path(path) == profile_path:
                reads.append(path)
                changed = json.loads(raw); changed["policy"]["duration"] = 20
                profile_path.write_bytes(soak.canonical(changed))
            return raw
        with patch.object(soak, "read_bounded", replaced):
            self.assertEqual(selected.verify_inputs(), soak.policy_requirements(policy()))
        self.assertEqual(len(reads), 1)
        with self.assertRaisesRegex(ValueError, "manifest_input_hash_mismatch"):
            selected.verify_inputs()

    def test_configuration_expectations_are_not_adopted_from_current_files(self):
        facts = copy.deepcopy(self.facts)
        facts["configuration"]["canonical_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "manifest_configuration_mismatch"):
            self.load(self.rewrite(facts))
        with self.assertRaises(TypeError):
            soak.Binding(self.wheel, self.facts["artifacts"][0]["sha256"], self.installed,
                         self.config, "synthetic", "a"*40, "b"*40)

    def test_profile_requires_exact_schema_policy_and_configuration_identity(self):
        original = json.loads((self.root / "profile.json").read_bytes())
        for mutate in (lambda p: p.update(configuration_sha256="0"*64),
                       lambda p: p.update(extra=True), lambda p: p["policy"].update(extra=True),
                       lambda p: p["policy"].pop("duration"), lambda p: p.update(schema="future")):
            with self.subTest(mutation=mutate):
                profile = copy.deepcopy(original); mutate(profile)
                raw = soak.canonical(profile); (self.root / "profile.json").write_bytes(raw)
                facts = copy.deepcopy(self.facts); facts["profile"]["sha256"] = soak.digest(raw)
                with self.assertRaises(ValueError): self.load(self.rewrite(facts))

    def test_duplicate_config_and_profile_keys_rejected_even_when_hash_matches(self):
        for which, raw in (("configuration", b'{"x":1,"x":2}'), ("profile", b'{"id":"one","id":"two"}')):
            with self.subTest(which=which):
                path = self.config if which == "configuration" else self.root / "profile.json"
                original = path.read_bytes(); path.write_bytes(raw)
                facts = copy.deepcopy(self.facts); facts[which]["sha256"] = soak.digest(raw)
                with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
                    self.load(self.rewrite(facts))
                path.write_bytes(original)

    def test_path_bounds_and_reserved_names_rejected(self):
        for path in ("../outside", "/absolute", "C:/file", "a\\b", "a//b", "./file",
                     "NUL.json", "a/COM1", "a.", "a:stream", "x"*241):
            with self.subTest(path=path):
                facts = copy.deepcopy(self.facts); facts["configuration"]["path"] = path
                with self.assertRaisesRegex(ValueError, "unsafe_manifest_path"):
                    self.load(self.rewrite(facts))
        with self.assertRaisesRegex(ValueError, "json_size_limit"):
            soak.strict_json(b' ' * 65537)
        with self.assertRaisesRegex(ValueError, "json_depth_limit"):
            soak.strict_json(b'['*18+b'0'+b']'*18)
        for raw in (b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'{"x":9223372036854775808}'):
            with self.assertRaises(ValueError): soak.strict_json(raw)

    def test_declared_environment_dependency_facts_are_strict(self):
        for mutate in (lambda f: f["environment"].pop("dependencies"),
                       lambda f: f["environment"]["python"].pop("executable_sha256"),
                       lambda f: f["environment"]["python"].update(executable_sha256="unknown"),
                       lambda f: f["environment"].update(attested=True),
                       lambda f: f["environment"]["dependencies"].append(copy.deepcopy(f["environment"]["dependencies"][0]))):
            with self.subTest(mutation=mutate):
                facts = copy.deepcopy(self.facts); mutate(facts)
                with self.assertRaises(ValueError): self.load(self.rewrite(facts))

    def test_evidence_and_ledger_cannot_override_external_selection(self):
        selected = self.load()
        altered = selected.facts; altered["source"]["head"] = "c"*40
        (self.root / "qualification-manifest.json").write_bytes(soak.canonical(altered))
        (self.root / "closure-ledger.json").write_bytes(soak.canonical({"approved": True, "expected_manifest": altered}))
        self.assertEqual(selected.facts["source"]["head"], "a"*40)
        self.assertEqual(selected.verify_inputs(), soak.policy_requirements(policy()))
        altered["ledger"] = {"override": True}
        with self.assertRaisesRegex(ValueError, "missing_or_unknown_manifest_fields"):
            self.load(self.rewrite(altered))


class SyntheticJournal(soak.Journal):
    """Test-only publication dependency. Ordinary exclusive copies, NEVER os.link.

    This exercises sealing logic, not atomic publication or real filesystem
    capability. Production Journal.publish is neither replaced nor retried.
    """
    def publish(self, pending, target):
        with target.open("xb") as stream:
            stream.write(pending.read_bytes())
        return soak.file_token(target)


class BlockedActualSealTests(unittest.TestCase):
    @unittest.skip("NOT RUN: actual os.link publication denied; no retry authorized")
    def test_actual_terminal_publication_and_consumption(self):
        pass

    @unittest.skip("NOT RUN: post-actual-publication faults require blocked os.link")
    def test_actual_postpublication_faults(self):
        pass


class SealTests(unittest.TestCase):
    def run_fixture(self, root, factory=SyntheticJournal):
        return RunnerTests().execute(root, journal_factory=factory)

    def test_consumer_rejects_truncation_tamper_sequence_identity_and_missing_seal(self):
        for mode in ("truncate", "tamper", "sequence", "identity", "missing", "failure"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); code, raw, rows = self.run_fixture(root)
                self.assertEqual(code, 0)
                path = root / "evidence"
                if mode == "truncate": (path / "observations.jsonl").write_text(raw[:-4])
                if mode == "tamper": (path / "observations.jsonl").write_text(raw.replace('"rss":100', '"rss":101'))
                if mode == "sequence": (path / "observations.jsonl").write_text(raw.replace('"seq":1', '"seq":9'))
                if mode == "missing": (path / "terminal-seal.json").unlink()
                if mode == "failure": (path / "first-failure.json").write_text('{}')
                identity = {"id": "wrong"} if mode == "identity" else rows[0]["identity"]
                with self.assertRaises((ValueError, OSError)):
                    soak.validate_sealed(path, identity, rows[0]["epoch"], policy())

    def test_externally_expected_policy_cannot_be_replaced_by_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); code, raw, rows = self.run_fixture(root)
            self.assertEqual(code, 0)
            path = root / "evidence"
            for expected in (policy(duration=20), policy(max_rss=9999),
                             policy(workload=("other",)), {}, None,
                             {**policy().__dict__, "unknown": True},
                             {**policy().__dict__, "duration": float("nan")}):
                with self.subTest(expected=expected), self.assertRaises(ValueError):
                    soak.validate_sealed(path, rows[0]["identity"], rows[0]["epoch"], expected)
            # Even internally rehashed altered requirements must not satisfy the caller.
            rows[0]["policy"]["max_rss"] = 20000
            rows[0]["policy_sha256"] = soak.digest(soak.canonical(rows[0]["policy"]))
            changed = b"".join(soak.canonical(r)+b"\n" for r in rows)
            with self.assertRaisesRegex(ValueError, "evidence_policy_mismatch"):
                soak.validate_observations(changed, rows[0]["identity"], rows[0]["epoch"], policy())
            del rows[0]["policy"]["workload"]
            changed = b"".join(soak.canonical(r)+b"\n" for r in rows)
            with self.assertRaisesRegex(ValueError, "invalid_expected_policy"):
                soak.validate_observations(changed, rows[0]["identity"], rows[0]["epoch"], policy())

    def test_preexisting_and_substituted_seals_are_preserved(self):
        for mode in ("preexisting", "substituted", "owned"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); reached = []; journals = []
                competitor = b"competing-evidence-do-not-delete"
                class OwnedJournal(SyntheticJournal):
                    def __init__(self, path):
                        super().__init__(path); journals.append(self)
                    def publish(self, pending, target):
                        if mode == "preexisting":
                            target.write_bytes(competitor)
                            try: return super().publish(pending, target)
                            except FileExistsError:
                                reached.append("FileExistsError"); raise
                        return super().publish(pending, target)
                    def finalize(self, identity, epoch, requirements):
                        original = soak.validate_sealed
                        def after_publish(path, *args):
                            reached.append("postpublish")
                            if mode == "substituted":
                                replacement = path / "competitor.json"
                                replacement.write_bytes(competitor)
                                soak.os.replace(replacement, path / "terminal-seal.json")
                            if mode in ("substituted", "owned"):
                                raise OSError("injected postpublication error")
                            return original(path, *args)
                        with patch.object(soak, "validate_sealed", after_publish):
                            return super().finalize(identity, epoch, requirements)
                code, raw, rows = self.run_fixture(root, OwnedJournal)
                self.assertEqual(code, 1)
                self.assertEqual(reached, ["FileExistsError"] if mode == "preexisting" else ["postpublish"])
                target = root / "evidence/terminal-seal.json"
                if mode != "owned":
                    self.assertEqual(target.read_bytes(), competitor)
                    self.assertFalse((target.parent / "owned-seal-revocation.json").exists())
                else:
                    self.assertEqual(soak.file_token(target), journals[0].publication)
                    self.assertTrue((target.parent / "owned-seal-revocation.json").exists())
                with self.assertRaisesRegex(ValueError, "failure_record_present"):
                    soak.validate_sealed(target.parent, rows[0]["identity"], rows[0]["epoch"], policy())

    def test_finalization_faults_reach_intended_stage_with_exact_expectations(self):
        for mode in ("write", "flush", "fsync", "close", "truncate", "tamper",
                     "pending_close", "publish", "publish_after"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); streams = []; reached = []; starts = []
                class FaultJournal(SyntheticJournal):
                    def __init__(self, path):
                        super().__init__(path); streams.append(self.stream)
                    def write(self, record):
                        if record["event"] == "start": starts.append(copy.deepcopy(record))
                        if record["event"] == "provisional_completion" and mode == "write":
                            reached.append(mode); self.stream.write('{"partial":')
                            raise OSError("SECRET")
                        super().write(record)
                    def publish(self, pending, target):
                        if mode == "publish":
                            reached.append(mode); raise OSError("SECRET")
                        token = super().publish(pending, target)
                        if mode == "publish_after":
                            reached.append(mode); raise OSError("SECRET")
                        return token
                    def finalize(self, identity, epoch, requirements):
                        if mode == "fsync":
                            def broken_fsync(fd):
                                reached.append(mode); raise OSError("SECRET")
                            with patch.object(soak.os, "fsync", broken_fsync):
                                return super().finalize(identity, epoch, requirements)
                        if mode in ("flush", "close"):
                            class BrokenStream:
                                def __init__(self, real): self.real = real
                                def __getattr__(self, name): return getattr(self.real, name)
                                def flush(self):
                                    if mode == "flush":
                                        reached.append(mode); raise OSError("SECRET")
                                    return self.real.flush()
                                def close(self):
                                    if mode == "close":
                                        reached.append(mode); raise OSError("SECRET")
                                    return self.real.close()
                            self.stream = BrokenStream(self.stream)
                        if mode in ("truncate", "tamper"):
                            self.close()
                            p = self.path / "observations.jsonl"; data = p.read_bytes()
                            p.write_bytes(data[:-8] if mode == "truncate" else data.replace(b'"rss":100', b'"rss":101'))
                            reached.append(mode)
                        if mode == "pending_close":
                            original = Path.open
                            class Pending:
                                def __init__(self, stream): self.stream = stream
                                def __enter__(self): return self.stream
                                def __exit__(self, *args):
                                    self.stream.close(); reached.append(mode); raise OSError("SECRET")
                            def opened(p, *args, **kw):
                                stream = original(p, *args, **kw)
                                return Pending(stream) if p.name == "seal.pending.json" else stream
                            with patch.object(Path, "open", opened):
                                return super().finalize(identity, epoch, requirements)
                        return super().finalize(identity, epoch, requirements)
                try:
                    code, raw, rows = self.run_fixture(root, FaultJournal)
                    self.assertEqual(code, 1)
                except json.JSONDecodeError:
                    self.assertIn(mode, ("write", "truncate"))
                finally:
                    for stream in streams: stream.close()
                self.assertTrue(reached, "intended injected fault never reached")
                self.assertEqual(set(reached), {mode})
                self.assertEqual(len(starts), 1)
                path = root / "evidence"
                failure = json.loads((path / "first-failure.json").read_text())
                self.assertEqual(failure["reason"], "interrupted_or_observation_failed")
                self.assertNotIn("SECRET", (path / "first-failure.json").read_text())
                with self.assertRaisesRegex(ValueError, "failure_record_present"):
                    soak.validate_sealed(path, starts[0]["identity"], starts[0]["epoch"], policy())


if __name__ == "__main__":
    unittest.main()
