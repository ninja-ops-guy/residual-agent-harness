"""Synthetic, offline verifier regressions; no native service or credentials."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("nativeq", ROOT / "scripts/qualify_native_mission_sync.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
C, T, W = "1" * 40, "2" * 40, "3" * 64
DEFAULT_DOC = object()
CANDIDATE = dict(commit=C, tree=T, wheel_sha256=W)
FACTS = dict(project_id="synthetic-project", task_id="synthetic-task", attempt=2, spec_hash="5" * 64)
EXPECTED = dict(expected_commit=C, expected_tree=T, expected_wheel_sha256=W,
                **{"expected_" + key: value for key, value in FACTS.items()})


def good(root):
    """Write actual synthetic fixture bytes and compute every listed digest."""
    station = dict(**FACTS, false_completion_before_state="review",
                   false_completion_after_state="review", verified_transition_observed=True,
                   acceptance_authority="station_only", evidence_file="station.json")
    common = dict(runtime_version="synthetic-runtime", build_identity="synthetic-build",
                  plugin_source_sha256="4" * 64, context_delivery_proven=True,
                  inbound_observation_proven=True, reconnect_proven=True, restart_proven=True,
                  wrong_id_rejected=True, revoked_binding_rejected=True, stale_attempt_rejected=True,
                  text_private_by_default=True, no_acceptance_authority=True,
                  gateway_restart_proven=False, cancellation_stop_proven=False)
    raw_name = "raw/synthetic-trace.txt"
    records = {raw_name: b"SYNTHETIC OFFLINE FIXTURE; NOT NATIVE EXECUTION EVIDENCE.\n"}
    records["station.json"] = dict(schema="residual.mc-v1-native-station.v1",
        candidate=CANDIDATE, station=FACTS, **{k: station[k] for k in m.STATES},
        raw_evidence_files=[raw_name])
    harnesses = []
    for name, hooks in m.HOOKS.items():
        harness = dict(common, name=name, conversation_id=name + "-conversation",
                       instance_id=name + "-instance", binding_id=name + "-binding", hook_executions=[])
        if name == "openclaw":
            harness.update(gateway_restart_proven=True, cancellation_stop_proven=True)
        for hook in sorted(hooks):
            filename = name + "-" + hook + ".json"
            harness["hook_executions"].append(dict(hook=hook, evidence_file=filename))
            records[filename] = dict(schema="residual.mc-v1-native-hook.v1",
                candidate=CANDIDATE, station=FACTS, harness=name,
                **{key: harness[key] for key in m.PROVENANCE}, hook=hook,
                event_id=name + "-" + hook, observed_at="2026-10-05T00:00:00Z",
                executed=True, raw_evidence_files=[raw_name])
        harnesses.append(harness)
    files = []
    for name, record in records.items():
        raw = record if isinstance(record, bytes) else json.dumps(record).encode()
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        files.append(dict(name=name, sha256=hashlib.sha256(raw).hexdigest()))
    return dict(schema="residual.mc-v1-native-evidence.v2", candidate=copy.deepcopy(CANDIDATE),
        station=station, harnesses=harnesses,
        two_conversation_demo=dict(same_station_task=True, both_conversations_received_current_context=True,
            bidirectional_observation_proven=True, false_completion_did_not_accept=True,
            station_verifier_completed_transition=True),
        independent_review=dict(reviewer="synthetic-other-person", reviewed_at="2026-10-05T00:00:00Z",
                                verdict="PASS", reviewer_not_executor=True),
        evidence_files=files, non_claims=["SYNTHETIC fixture. No native or release authority."])


class NativeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.doc = good(self.root)

    def validate(self, doc=DEFAULT_DOC, **overrides):
        return m.validate(self.doc if doc is DEFAULT_DOC else doc, evidence_root=self.root, **(EXPECTED | overrides))

    def reject(self, doc=DEFAULT_DOC, **overrides):
        with self.assertRaises(m.NativeEvidenceError):
            self.validate(doc, **overrides)

    def rewrite(self, name, change):
        target = self.root / name
        value = json.loads(target.read_bytes())
        change(value)
        raw = json.dumps(value).encode()
        target.write_bytes(raw)
        for entry in self.doc["evidence_files"]:
            if entry["name"] == name:
                entry["sha256"] = hashlib.sha256(raw).hexdigest()

    def test_good_actual_bytes(self):
        self.assertTrue(self.validate())

    def test_all_missing_required_fields(self):
        objects = [self.doc, self.doc["candidate"], self.doc["station"],
                   *self.doc["harnesses"], self.doc["two_conversation_demo"],
                   self.doc["independent_review"], self.doc["evidence_files"][0]]
        for obj in objects:
            for key in list(obj):
                with self.subTest(key=key, fields=list(obj)):
                    value = obj.pop(key)
                    try:
                        self.reject()
                    finally:
                        obj[key] = value

    def test_station_facts_missing_wrong_and_external_mismatch(self):
        for key, wrong in dict(project_id="other", task_id="other", attempt=3, spec_hash="9" * 64).items():
            with self.subTest(key=key):
                d = copy.deepcopy(self.doc)
                d["station"][key] = wrong
                self.reject(d)
                self.reject(**{"expected_" + key: wrong})

    def test_invalid_external_identity(self):
        for field, value in dict(expected_commit="x", expected_tree="2" * 40 + "\n",
                                  expected_wheel_sha256=None, expected_project_id=" ",
                                  expected_task_id="", expected_attempt=True, expected_spec_hash="g" * 64).items():
            with self.subTest(field=field):
                self.reject(**{field: value})

    def test_candidate_self_selection(self):
        for field in CANDIDATE:
            with self.subTest(field=field):
                d = copy.deepcopy(self.doc)
                d["candidate"][field] = "9" * len(d["candidate"][field])
                self.reject(d)

    def test_missing_blank_null_changed_states(self):
        for value in (None, "", " ", 1, "integrated"):
            with self.subTest(value=value):
                d = copy.deepcopy(self.doc)
                d["station"]["false_completion_after_state"] = value
                self.reject(d)
        d = copy.deepcopy(self.doc)
        for key in ("false_completion_before_state", "false_completion_after_state"):
            del d["station"][key]
        self.reject(d)

    def test_malformed_schema_inputs(self):
        for value in (None, [], 1, "text", True):
            with self.subTest(root=value):
                self.reject(value)
        mutations = [("attempt", True), ("attempt", 0), ("spec_hash", "g" * 64),
                     ("project_id", " " * 2), ("task_id", "t" * 97)]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                d = copy.deepcopy(self.doc)
                d["station"][key] = value
                self.reject(d)
        for member in (None, [], "hermes", 4):
            d = copy.deepcopy(self.doc)
            d["harnesses"][0] = member
            self.reject(d)

    def test_unknown_fields_and_nonclaims(self):
        for section in (None, "candidate", "station", "two_conversation_demo", "independent_review"):
            d = copy.deepcopy(self.doc)
            (d if section is None else d[section])["surprise"] = True
            self.reject(d)
        for value in ([], [""], [" "]):
            d = copy.deepcopy(self.doc)
            d["non_claims"] = value
            self.reject(d)

    def test_review_timestamp(self):
        for value in ("yesterday", "", "2026-02-30T00:00:00Z", "2026-10-05T00:00:00",
                      "2026-10-05T00:00:00+00:99"):
            with self.subTest(value=value):
                d = copy.deepcopy(self.doc)
                d["independent_review"]["reviewed_at"] = value
                self.reject(d)

    def test_schema_is_actually_loaded_and_unknown_keyword_fails_closed(self):
        schema = m.load_schema()
        schema["$defs"]["facts"]["properties"]["attempt"]["minimum"] = 3
        with patch.object(m, "load_schema", return_value=schema):
            self.reject()
        schema["$defs"]["candidate"]["unsupported_future_constraint"] = True
        path = self.root / "changed-schema.json"
        path.write_text(json.dumps(schema), encoding="utf-8")
        with patch.object(m, "SCHEMA_PATH", path):
            self.reject()

    def test_actual_digest_and_missing_file(self):
        (self.root / "raw/synthetic-trace.txt").write_bytes(b"tampered")
        self.reject()
        (self.root / "raw/synthetic-trace.txt").unlink()
        with self.assertRaises((m.NativeEvidenceError, OSError)):
            self.validate()

    def test_each_hook_required_and_registration_boolean_insufficient(self):
        for index, harness in enumerate(self.doc["harnesses"]):
            for position in range(len(harness["hook_executions"])):
                with self.subTest(harness=index, hook=position):
                    d = copy.deepcopy(self.doc)
                    del d["harnesses"][index]["hook_executions"][position]
                    self.reject(d)
        d = copy.deepcopy(self.doc)
        del d["harnesses"][0]["hook_executions"]
        d["harnesses"][0]["hook_registration_proven"] = True
        self.reject(d)

    def test_capture_missing_or_not_executed(self):
        name = self.doc["harnesses"][0]["hook_executions"][0]["evidence_file"]
        self.doc["evidence_files"] = [e for e in self.doc["evidence_files"] if e["name"] != name]
        self.reject()
        self.doc = good(self.root)
        self.rewrite(name, lambda r: r.update(executed=False))
        self.reject()

    def test_capture_candidate_station_and_native_binding_mismatch(self):
        name = self.doc["harnesses"][0]["hook_executions"][0]["evidence_file"]
        changes = [lambda r, k=k: r["candidate"].update({k: "9" * len(CANDIDATE[k])}) for k in CANDIDATE]
        changes += [lambda r, k=k: r["station"].update({k: 3 if k == "attempt" else "9" * 64 if k == "spec_hash" else "other"}) for k in FACTS]
        changes += [lambda r, k=k: r.update({k: "9" * 64 if k == "plugin_source_sha256" else "other"}) for k in m.PROVENANCE]
        changes += [lambda r: r.update(hook="message_sent"), lambda r: r.update(harness="openclaw")]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                self.doc = good(self.root)
                self.rewrite(name, change)
                self.reject()

    def test_capture_missing_fields_and_malformed_json(self):
        name = self.doc["harnesses"][0]["hook_executions"][0]["evidence_file"]
        keys = list(json.loads((self.root / name).read_bytes()))
        for key in keys:
            with self.subTest(key=key):
                self.doc = good(self.root)
                self.rewrite(name, lambda r, k=key: r.pop(k))
                self.reject()
        for raw in (b"null", b"[]", b"{}", b"broken", b"\xff"):
            self.doc = good(self.root)
            (self.root / name).write_bytes(raw)
            next(e for e in self.doc["evidence_files"] if e["name"] == name)["sha256"] = hashlib.sha256(raw).hexdigest()
            self.reject()

    def test_station_capture_mismatch(self):
        for change in (lambda r: r["station"].update(attempt=3),
                       lambda r: r.update(false_completion_before_state="working"),
                       lambda r: r.pop("false_completion_after_state"),
                       lambda r: r.update(acceptance_authority="conversation")):
            self.doc = good(self.root)
            self.rewrite("station.json", change)
            self.reject()

    def test_raw_references_are_required_and_digest_bound(self):
        for refs in ([], ["absent.txt"], ["station.json"], ["raw/synthetic-trace.txt"] * 2):
            self.doc = good(self.root)
            self.rewrite("station.json", lambda r: r.update(raw_evidence_files=refs))
            self.reject()

    def test_duplicates_harness_binding_hook_event_and_file(self):
        d = copy.deepcopy(self.doc)
        d["harnesses"][0]["name"] = "openclaw"
        self.reject(d)
        d = copy.deepcopy(self.doc)
        d["harnesses"][1]["binding_id"] = d["harnesses"][0]["binding_id"]
        self.reject(d)
        d = copy.deepcopy(self.doc)
        d["harnesses"][0]["hook_executions"][1] = d["harnesses"][0]["hook_executions"][0]
        self.reject(d)
        d = copy.deepcopy(self.doc)
        d["evidence_files"].append(d["evidence_files"][0])
        self.reject(d)
        hooks = self.doc["harnesses"][0]["hook_executions"]
        event = json.loads((self.root / hooks[0]["evidence_file"]).read_bytes())["event_id"]
        self.rewrite(hooks[1]["evidence_file"], lambda r: r.update(event_id=event))
        self.reject()

    def test_path_traversal_absolute_windows_aliases_and_urls(self):
        paths = ("../outside", "/absolute", "C:/outside", "C:relative", "//server/share",
                 "a/../b", "a/./b", "a//b", "a\\b", "file:stream", "https://example/a",
                 "%2e%2e/file", "NUL", "con.txt", "COM1", "LPT9.log", "x.", "x/aux",
                 "", "a\x00b", " spaced ", "x" * 257)
        for name in paths:
            with self.subTest(name=name):
                d = copy.deepcopy(self.doc)
                d["evidence_files"][0]["name"] = name
                self.reject(d)
        d = copy.deepcopy(self.doc)
        d["evidence_files"].insert(1, dict(d["evidence_files"][0], name=d["evidence_files"][0]["name"].upper()))
        self.reject(d)

    def test_file_json_and_total_bounds(self):
        for attr, limit in (("MAX_FILE", 8), ("MAX_TOTAL", 8), ("MAX_JSON", 8)):
            with self.subTest(limit=attr), patch.object(m, attr, limit):
                self.reject()

    def test_directory_hardlink_and_reparse_rejection(self):
        for path in ("//server/share", "\\\\server\\share", "\\\\?\\C:\\evidence"):
            with self.assertRaises(m.NativeEvidenceError):
                m.checked_path(path)
        with self.assertRaises(m.NativeEvidenceError):
            m.read_regular(self.root, m.MAX_FILE)
        original = self.root / "raw/synthetic-trace.txt"
        os.link(original, self.root / "hardlink.txt")
        self.reject()
        (self.root / "hardlink.txt").unlink()
        # Portable metadata negatives; no privilege-dependent symlink creation.
        for mode, attrs in ((stat.S_IFLNK, 0), (stat.S_IFDIR, 0x400)):
            with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=mode, st_file_attributes=attrs)):
                self.reject()

    def test_secret_key_check_has_explicit_limits(self):
        d = copy.deepcopy(self.doc)
        d["harnesses"][0]["token"] = "SYNTHETIC-NOT-A-SECRET"
        self.reject(d)
        self.rewrite("station.json", lambda r: r.update(password="SYNTHETIC-NOT-A-SECRET"))
        self.reject()
        self.doc = good(self.root)
        self.doc["non_claims"] = ["Arbitrary values are not scanned for secrets."]
        self.assertTrue(self.validate())

    def test_openclaw_stop_and_authority_flags(self):
        for field in ("cancellation_stop_proven", "gateway_restart_proven", "no_acceptance_authority"):
            d = copy.deepcopy(self.doc)
            d["harnesses"][1][field] = False
            self.reject(d)
        d = copy.deepcopy(self.doc)
        d["station"]["acceptance_authority"] = "native"
        self.reject(d)

    def cli_args(self):
        return [str(self.root / "manifest.json"), "--evidence-root", str(self.root)] + [
            part for key, value in EXPECTED.items() for part in ("--" + key.replace("_", "-"), str(value))]

    def test_real_cli_positive_and_digest_negative(self):
        (self.root / "manifest.json").write_text(json.dumps(self.doc), encoding="utf-8")
        command = [sys.executable, str(ROOT / "scripts/qualify_native_mission_sync.py"), *self.cli_args()]
        run = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("authenticity and secret review remain external", run.stdout)
        (self.root / "raw/synthetic-trace.txt").write_bytes(b"tampered")
        run = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 1)
        self.assertIn("digest mismatch", run.stdout)

    def test_strict_json_cli_failures_do_not_echo_input(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'null', b'\xff',
                    b'{"SYNTHETIC-PRIVATE-MARKER":', b"[" * 2000 + b"]" * 2000):
            with self.subTest(raw=raw[:20]):
                (self.root / "manifest.json").write_bytes(raw)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(m.main(self.cli_args()), 1)
                self.assertNotIn("SYNTHETIC-PRIVATE-MARKER", output.getvalue())
                self.assertNotIn("Traceback", output.getvalue())


if __name__ == "__main__":
    unittest.main()
