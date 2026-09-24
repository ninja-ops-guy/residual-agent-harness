"""Proposed strict-seal-JSON boundary controls; disposable fixtures only.

These are supplemental candidate tests, not an adopted private Seal v2 schema.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_r4_seal_manifest import module

GOOD = {'entry_count': 1, 'entries_verified': 1,
        'entries_failed': 0, 'verification': 'PASS'}


class SealJsonBoundarySupplement(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        content = b'synthetic authority only'
        (self.root / 'data').write_bytes(content)
        self.manifest = self.root / 'SHA256SUMS'
        self.manifest.write_text(hashlib.sha256(content).hexdigest() + '  data\n')
        self.seal = self.root / 'SEAL.json'

    def rejects(self, raw):
        self.seal.write_text(raw, encoding='utf-8')
        with self.assertRaises(module.ManifestError):
            module.verify_seal_cardinality(self.manifest, self.seal)

    def test_duplicate_disposition_cannot_replace_failure_with_pass(self):
        raw = '{"authoritative_manifest":{"entry_count":1,"entries_verified":1,' \
              '"entries_failed":0,"verification":"FAIL","verification":"PASS"}}'
        self.rejects(raw)

    def test_duplicate_counter_cannot_replace_invalid_type(self):
        self.rejects('{"authoritative_manifest":{"entry_count":true,"entry_count":1,'
                     '"entries_verified":1,"entries_failed":0,"verification":"PASS"}}')

    def test_duplicate_root_metadata_is_rejected(self):
        self.rejects('{"authoritative_manifest":null,"authoritative_manifest":'
                     + json.dumps(GOOD) + '}')

    def test_non_object_root_is_typed_failure(self):
        for obj in (None, [], 0, True, 'text'):
            with self.subTest(obj=obj):
                self.rejects(json.dumps(obj))

    def test_invalid_present_primary_metadata_cannot_fall_back_to_legacy(self):
        for obj in (None, [], False, 1, 'text'):
            with self.subTest(obj=obj):
                self.rejects(json.dumps({'authoritative_manifest': obj,
                    'authoritative_evidence': {'sha256sums_verification': GOOD}}))

    def test_malformed_legacy_parent_is_typed_failure(self):
        for obj in (None, [], False, 1, 'text'):
            with self.subTest(obj=obj):
                self.rejects(json.dumps({'authoritative_evidence': obj}))

    def test_invalid_json_is_typed_failure(self):
        self.rejects('{broken')

    def test_nonstandard_numeric_constants_are_rejected(self):
        for spelling in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(spelling=spelling):
                self.rejects('{"authoritative_manifest":' + json.dumps(GOOD)
                             + ',"extra":' + spelling + '}')

    def test_valid_primary_metadata_positive_control(self):
        self.seal.write_text(json.dumps({'authoritative_manifest': GOOD}))
        self.assertEqual(module.verify_seal_cardinality(
            self.manifest, self.seal)['verification'], 'PASS')

    def test_valid_legacy_metadata_positive_control(self):
        self.seal.write_text(json.dumps({'authoritative_evidence': {
            'sha256sums_verification': GOOD}}))
        self.assertEqual(module.verify_seal_cardinality(
            self.manifest, self.seal)['verification'], 'PASS')


if __name__ == '__main__':
    unittest.main()
