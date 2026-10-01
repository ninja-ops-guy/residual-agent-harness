"""Offline contract tests. Synthetic fixtures are NOT live-provider receipts."""
import ast
import copy
import hashlib
import inspect
import io
import json
import unittest
import urllib.error
import urllib.request
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from residual import decision_models as dm


def questions():
    return {
        "urgent": {"type": "noul", "instructions": "Is this an urgent incident?"},
        "team": {"type": "choice", "criteria": {"network": "Network fault", "app": "Application fault"}},
        "severity": {"type": "score", "criteria": ["Low", "Medium", "High"]},
    }


def request():
    return dm.DecisionRequest.build(subject="SYNTHETIC-1", state={"event": "checkout errors"},
                                    questions=questions(), evidence_refs=("fixture:synthetic-1",))


def response(model="clef-flash"):
    return {"model": model, "answers": {
        "urgent": {"type": "noul", "noul": 0.95},
        "team": {"type": "choice", "choice": "app", "confidence": 0.6,
                 "probabilities": {"network": 0.1, "app": 0.9}},
        "severity": {"type": "score", "score": 1.7, "confidence": 0.7,
                     "legend": {"0": "Low", "1": "Medium", "2": "High"},
                     "probabilities": {"0": 0.1, "1": 0.1, "2": 0.8}},
    }, "usage": {"input_tokens": 100, "output_tokens": 0}}


def raw(value=None):
    return json.dumps(response() if value is None else value).encode()


class ClefContractTests(unittest.TestCase):
    def test_all_types(self):
        data = dm.replay_clef(request(), raw()).to_dict()
        self.assertEqual(set(data["answers"]), set(questions()))
        self.assertAlmostEqual(data["answers"]["urgent"]["probabilities"]["false"], 0.05)
        self.assertEqual(data["answers"]["severity"]["value"], 1.7)

    def test_no_authority_or_acceptance(self):
        evidence = dm.replay_clef(request(), raw())
        data = evidence.to_dict()
        self.assertIs(data["authority"], False)
        self.assertEqual(data["status"], "UNVERIFIED_CANDIDATE")
        self.assertEqual(data["calibration_status"], "UNQUALIFIED")
        self.assertEqual(data["input_completeness"], "NOT_ATTESTED")
        self.assertNotIn("overall_verdict", data)
        self.assertNotIn("receipt_hash", data)
        self.assertEqual(evidence.review_hint("urgent"), "ADVISORY_ONLY")

    def test_provider_confidence_is_not_max_probability(self):
        answer = dm.replay_clef(request(), raw()).to_dict()["answers"]["team"]
        self.assertEqual(answer["provider_confidence"], 0.6)
        self.assertEqual(answer["probabilities"]["app"], 0.9)

    def test_request_snapshot_immutable(self):
        source = questions()
        req = dm.DecisionRequest.build(subject="fixture", state={}, questions=source,
                                       evidence_refs=("fixture:1",))
        source["urgent"]["type"] = "tool_call"
        self.assertEqual(req.payload()["questions"]["urgent"]["type"], "noul")
        exported = req.payload()
        exported["questions"].clear()
        self.assertEqual(len(req.payload()["questions"]), 3)
        with self.assertRaises(FrozenInstanceError):
            req.subject = "mutated"

    def test_evidence_snapshot_immutable(self):
        evidence = dm.replay_clef(request(), raw())
        exported = evidence.to_dict()
        exported["authority"] = True
        self.assertIs(evidence.to_dict()["authority"], False)

    def test_hash_bindings(self):
        req, body = request(), raw()
        evidence = dm.replay_clef(req, body)
        data = evidence.to_dict()
        self.assertEqual(data["request_sha256"], hashlib.sha256(req.wire_bytes("clef-flash")).hexdigest())
        self.assertEqual(data["response_sha256"], hashlib.sha256(body).hexdigest())
        path, artifact = evidence.candidate_artifact()
        self.assertEqual(path, f"decision-claims/{hashlib.sha256(artifact).hexdigest()}.json")
        self.assertEqual(data["evidence_refs"], ["fixture:synthetic-1"])

    def test_replay_deterministic_and_explicit(self):
        a = dm.replay_clef(request(), raw(), captured_at_ns=123)
        b = dm.replay_clef(request(), raw(), captured_at_ns=123)
        self.assertEqual(a.document_json, b.document_json)
        self.assertEqual(a.to_dict()["source_kind"], "OFFLINE_REPLAY")

    def test_model_alias_not_claimed_as_pinned_weights(self):
        identity = dm.replay_clef(request(), raw()).to_dict()["producer"]
        self.assertIsNone(identity["model_revision"])
        self.assertEqual(identity["model_identity_status"], "UNPINNED_ALIAS")

    def test_cloudflare_envelope(self):
        envelope = {"success": True, "errors": [], "messages": [], "result": response()}
        self.assertEqual(dm.replay_clef(request(), raw(envelope)).to_dict()["answers"]["team"]["value"], "app")

    def test_model_both_variants(self):
        for model in ("clef", "clef-flash"):
            with self.subTest(model=model):
                self.assertEqual(dm.replay_clef(request(), raw(response(model)), model=model)
                                 .to_dict()["producer"]["reported_model"], model)

    def test_low_probability_requires_review(self):
        self.assertEqual(dm.replay_clef(request(), raw()).review_hint("severity"), "REVIEW_REQUIRED")

    def test_ties_require_review_even_with_zero_thresholds(self):
        value = response()
        value["answers"]["urgent"]["noul"] = 0.5
        self.assertEqual(dm.replay_clef(request(), raw(value)).review_hint(
            "urgent", min_probability=0, min_margin=0), "REVIEW_REQUIRED")

    def test_invalid_thresholds(self):
        evidence = dm.replay_clef(request(), raw())
        for threshold in (True, -1, 2, float("nan"), float("inf"), 10**1000):
            with self.subTest(threshold=repr(threshold)[:30]), self.assertRaises(dm.DecisionError):
                evidence.review_hint("urgent", min_probability=threshold)

    def test_invalid_request_questions(self):
        invalid = [{}, {"q": {"type": "tool_call"}}, {"q/../../": {"type": "noul"}},
                   {"q": {"type": "noul", "authority": True}},
                   {"q": {"type": "choice", "criteria": {"a": "single"}}},
                   {"q": {"type": "score", "criteria": ["one"]}},
                   {"q": {"type": "noul", "criteria": None}},
                   {"q": {"type": "noul", "instructions": " "}},
                   {str(i): {"type": "noul"} for i in range(65)}]
        for qs in invalid:
            with self.subTest(qs=qs), self.assertRaises(dm.DecisionError):
                dm.DecisionRequest.build(subject="test", state="x", questions=qs, evidence_refs=("fixture:x",))

    def test_question_limit_64(self):
        req = dm.DecisionRequest.build(subject="test", state="x", evidence_refs=("fixture:x",),
                                       questions={str(i): {"type": "noul"} for i in range(64)})
        self.assertEqual(len(req.payload()["questions"]), 64)

    def test_invalid_provenance(self):
        for refs in ((), ["x"], ("x", "x"), ("",), ("x" * 513,)):
            with self.subTest(refs=refs), self.assertRaises(dm.DecisionError):
                dm.DecisionRequest.build(subject="test", state={}, questions=questions(), evidence_refs=refs)

    def test_oversize_request(self):
        with self.assertRaises(dm.DecisionError):
            dm.DecisionRequest.build(subject="test", state="x" * dm.MAX_REQUEST_BYTES,
                                     questions=questions(), evidence_refs=("fixture:x",))

    def test_invalid_json_state(self):
        for state in (float("nan"), {1: "bad key"}, {"x": object()}, b"bytes"):
            with self.subTest(state=state), self.assertRaises(dm.DecisionError):
                dm.DecisionRequest.build(subject="test", state=state, questions=questions(), evidence_refs=("fixture:x",))

    def test_noncanonical_request(self):
        with self.assertRaisesRegex(dm.DecisionError, "NONCANONICAL_REQUEST"):
            dm.DecisionRequest("test", json.dumps(request().payload()).encode(), ("fixture:x",))

    def test_missing_and_extra_answers(self):
        for mutation in ("missing", "extra"):
            value = response()
            if mutation == "missing":
                del value["answers"]["team"]
            else:
                value["answers"]["approve"] = {"noul": 1}
            with self.subTest(mutation=mutation), self.assertRaisesRegex(dm.DecisionError, "ANSWER_SET_MISMATCH"):
                dm.replay_clef(request(), raw(value))

    def test_invalid_probabilities(self):
        for probability in (True, None, "0.9", -0.1, 1.1, float("nan"), float("inf"), 10**1000):
            value = response()
            value["answers"]["urgent"]["noul"] = probability
            with self.subTest(p=repr(probability)[:30]), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), raw(value))

    def test_distribution_errors(self):
        for probabilities in ({"app": 1.0}, {"app": 0.9, "network": 0.2},
                              {"app": 0.9, "network": 0.0, "execute": 0.1},
                              {"app": 0.9, "network": True}):
            value = response()
            value["answers"]["team"]["probabilities"] = probabilities
            with self.subTest(p=probabilities), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), raw(value))

    def test_choice_must_be_valid_argmax(self):
        for choice in ("network", "execute", [], True):
            value = response()
            value["answers"]["team"]["choice"] = choice
            with self.subTest(choice=choice), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), raw(value))

    def test_score_expectation_and_legend(self):
        for key, replacement in (("score", 1.2), ("score", True), ("score", 10**1000),
                                 ("legend", {"0": "High", "1": "Medium", "2": "Low"})):
            value = response()
            value["answers"]["severity"][key] = replacement
            with self.subTest(key=key), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), raw(value))

    def test_wrong_answer_type(self):
        value = response()
        value["answers"]["urgent"]["type"] = "choice"
        with self.assertRaisesRegex(dm.DecisionError, "ANSWER_TYPE_MISMATCH"):
            dm.replay_clef(request(), raw(value))

    def test_unknown_fields_fail_closed(self):
        for place in ("top", "answer"):
            value = response()
            target = value if place == "top" else value["answers"]["urgent"]
            target["authority"] = True
            with self.subTest(place=place), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), raw(value))

    def test_duplicate_json_keys(self):
        for body in (b'{"model":"clef","model":"clef-flash"}',
                     b'{"answers":{"q":{"noul":0.1,"noul":0.9}}}'):
            with self.subTest(body=body), self.assertRaisesRegex(dm.DecisionError, "DUPLICATE_JSON_KEY"):
                dm.replay_clef(request(), body)

    def test_malformed_response(self):
        for body in (b"", b"[]", b"null", b"not json", b"\xff", b"x" * (dm.MAX_RESPONSE_BYTES + 1)):
            with self.subTest(size=len(body)), self.assertRaises(dm.DecisionError):
                dm.replay_clef(request(), body)

    def test_provider_failure_envelopes(self):
        for envelope in ({"success": False, "result": response()},
                         {"success": "true", "result": response()},
                         {"success": True, "errors": [{"message": "failure"}], "result": response()}):
            with self.subTest(envelope=envelope), self.assertRaisesRegex(dm.DecisionError, "PROVIDER_FAILURE"):
                dm.replay_clef(request(), raw(envelope))

    def test_wrong_model(self):
        with self.assertRaisesRegex(dm.DecisionError, "MODEL_IDENTITY_MISMATCH"):
            dm.replay_clef(request(), raw(response("clef")))

    def test_missing_usage_not_zero(self):
        value = response()
        del value["usage"]
        data = dm.replay_clef(request(), raw(value)).to_dict()
        self.assertIsNone(data["usage"])
        self.assertEqual(data["usage_status"], "UNKNOWN")

    def test_invalid_usage(self):
        for usage in ([], {"input_tokens": -1}, {"input_tokens": True}, {"input_tokens": 1.5}):
            value = response()
            value["usage"] = usage
            with self.subTest(usage=usage), self.assertRaisesRegex(dm.DecisionError, "INVALID_USAGE"):
                dm.replay_clef(request(), raw(value))

    def test_state_change_rebinds_request(self):
        first = dm.replay_clef(request(), raw()).to_dict()
        second = dm.replay_clef(dm.DecisionRequest.build(subject="SYNTHETIC-1", state={"event": "different"},
                questions=questions(), evidence_refs=("fixture:synthetic-1",)), raw()).to_dict()
        self.assertNotEqual(first["request_sha256"], second["request_sha256"])
        self.assertNotEqual(first["state_sha256"], second["state_sha256"])

    def test_no_protected_module_imports(self):
        tree = ast.parse(inspect.getsource(dm))
        imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(n.startswith(("residual.factory", "residual.station", "residual.verifier")) for n in imports))


class ClefTransportTests(unittest.TestCase):
    def adapter(self, **kwargs):
        return dm.ClefAdapter("a" * 32, "TEST_ONLY_TOKEN", **kwargs)

    def test_disabled_by_default_no_transport(self):
        transport = Mock()
        with self.assertRaisesRegex(dm.DecisionError, "ADAPTER_DISABLED"):
            self.adapter(transport=transport).evaluate(request())
        transport.assert_not_called()

    def test_endpoint_model_wire_and_no_provenance_egress(self):
        for model in ("clef", "clef-flash"):
            transport = Mock(return_value=raw(response(model)))
            evidence = self.adapter(model=model, transport=transport, enabled=True).evaluate(request())
            url, token, payload, timeout = transport.call_args.args
            self.assertEqual(url, f"https://api.cloudflare.com/client/v4/accounts/{'a' * 32}/ai/run/@cf/cloudflare/{model}")
            self.assertEqual(token, "TEST_ONLY_TOKEN")
            self.assertEqual(set(json.loads(payload)), {"model", "state", "questions"})
            self.assertEqual(timeout, 15.0)
            self.assertEqual(evidence.to_dict()["source_kind"], "INJECTED_TRANSPORT")
            self.assertNotIn("TEST_ONLY_TOKEN", evidence.document_json.decode())
            self.assertNotIn("TEST_ONLY_TOKEN", repr(self.adapter()))

    def test_invalid_config(self):
        cases = [{"model": "clef/../../evil"}, {"model": []}, {"enabled": "true"},
                 {"timeout_seconds": 0}, {"timeout_seconds": float("nan")},
                 {"timeout_seconds": 10**1000}, {"transport": "bad"}]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(dm.DecisionError):
                self.adapter(**kwargs)

    def test_account_and_token_injection_rejected(self):
        for account, token in (("../metadata", "token"), ("a" * 32, "token\r\nInjected:1"),
                               ("a" * 32, ""), ("https://evil.example", "token")):
            with self.subTest(account=account), self.assertRaises(dm.DecisionError):
                dm.ClefAdapter(account, token)

    def test_injected_transport_errors_redacted_no_retry(self):
        for error in (OSError("TEST_ONLY_TOKEN"), dm.DecisionError("TEST_ONLY_TOKEN"), TimeoutError("TEST_ONLY_TOKEN")):
            transport = Mock(side_effect=error)
            with self.assertRaisesRegex(dm.DecisionError, "^TRANSPORT_FAILURE$"):
                self.adapter(enabled=True, transport=transport).evaluate(request())
            self.assertEqual(transport.call_count, 1)

    def test_redirect_handler_rejects(self):
        with self.assertRaisesRegex(dm.DecisionError, "REDIRECT_REJECTED"):
            dm._NoRedirect().redirect_request(None, None, 307, "", {}, "https://evil.example")

    def test_http_request_caps_and_proxy_disabled(self):
        result = Mock(status=200)
        result.read.return_value = raw()
        context = Mock()
        context.__enter__ = Mock(return_value=result)
        context.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = context
        with patch.object(dm.urllib.request, "build_opener", return_value=opener) as factory:
            evidence = self.adapter(enabled=True).evaluate(request())
        self.assertEqual(factory.call_args.args[0].proxies, {})
        self.assertIsInstance(factory.call_args.args[1], dm._NoRedirect)
        result.read.assert_called_once_with(dm.MAX_RESPONSE_BYTES + 1)
        sent = opener.open.call_args.args[0]
        self.assertEqual(sent.method, "POST")
        self.assertEqual(sent.get_header("Authorization"), "Bearer TEST_ONLY_TOKEN")
        self.assertEqual(evidence.to_dict()["source_kind"], "CLOUDFLARE_HTTPS")

    def test_http_failures_safe_and_single_attempt(self):
        for status, code in ((401, "AUTH_FAILURE"), (403, "AUTH_FAILURE"), (429, "RATE_LIMITED"),
                             (500, "HTTP_FAILURE"), (307, "REDIRECT_REJECTED")):
            error = urllib.error.HTTPError("https://api.cloudflare.com", status, "TEST_ONLY_TOKEN", {}, io.BytesIO(b"secret"))
            opener = Mock()
            opener.open.side_effect = error
            with self.subTest(status=status), patch.object(dm.urllib.request, "build_opener", return_value=opener):
                with self.assertRaisesRegex(dm.DecisionError, f"^{code}$"):
                    self.adapter(enabled=True).evaluate(request())
                self.assertEqual(opener.open.call_count, 1)

    def test_timeout_and_url_failure(self):
        for error, code in ((TimeoutError("secret"), "TRANSPORT_TIMEOUT"),
                            (urllib.error.URLError("secret"), "TRANSPORT_FAILURE")):
            opener = Mock()
            opener.open.side_effect = error
            with patch.object(dm.urllib.request, "build_opener", return_value=opener):
                with self.assertRaisesRegex(dm.DecisionError, f"^{code}$"):
                    self.adapter(enabled=True).evaluate(request())

    def test_http_response_too_large(self):
        result = Mock(status=200)
        result.read.return_value = b"x" * (dm.MAX_RESPONSE_BYTES + 1)
        context = Mock()
        context.__enter__ = Mock(return_value=result)
        context.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = context
        with patch.object(dm.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(dm.DecisionError, "RESPONSE_TOO_LARGE"):
                self.adapter(enabled=True).evaluate(request())


if __name__ == "__main__":
    unittest.main()
