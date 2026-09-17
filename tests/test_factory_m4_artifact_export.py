"""Real ZIP fixtures exercise the M4 exporter's evidence-shape and size gates."""
from contextlib import redirect_stdout
import base64
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch
import zipfile

from scripts import export_m4_artifact as exporter


class ArtifactExportTests(unittest.TestCase):
    @staticmethod
    def archive(entries):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries:
                archive.writestr(name, data)
        return stream.getvalue()

    @staticmethod
    def entries():
        return [(name, b'fixture') for name in sorted(exporter.FILES)]

    def export(self, data):
        self.output = io.StringIO()
        environment = {
            'M4_ARTIFACT_ID': '17',
            'M4_ARTIFACT_DIGEST': hashlib.sha256(data).hexdigest(),
            'GITHUB_REPOSITORY': 'fixture/repository',
            'GH_TOKEN': 'fixture-token',
        }
        with patch.dict(os.environ, environment), \
             patch.object(exporter.urllib.request, 'build_opener') as builder, \
             redirect_stdout(self.output):
            builder.return_value.open.return_value = io.BytesIO(data)
            exporter.main()
        return self.output.getvalue()

    def reject(self, entries, message):
        with self.assertRaisesRegex(RuntimeError, message):
            self.export(self.archive(entries))
        self.assertEqual(self.output.getvalue(), '', 'Rejected bytes must not enter the export')

    def test_exact_six_unique_members_export_byte_exactly(self):
        data = self.archive(self.entries())
        lines = self.export(data).splitlines()
        header = json.loads(lines[0].removeprefix('M4_ARCHIVE_BEGIN '))
        self.assertEqual(header['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(header['size'], len(data))
        encoded = ''.join(line.removeprefix('M4_ARCHIVE_DATA ') for line in lines[1:-1])
        self.assertEqual(base64.b64decode(encoded, validate=True), data)
        self.assertEqual(lines[-1], 'M4_ARCHIVE_END')

    def test_each_missing_member_is_rejected(self):
        for missing in sorted(exporter.FILES):
            with self.subTest(missing=missing):
                self.reject([(name, value) for name, value in self.entries() if name != missing],
                            'exactly six unique expected files')

    def test_empty_archive_is_rejected(self):
        self.reject([], 'exactly six unique expected files')

    def test_duplicate_member_is_rejected_even_with_all_expected_names(self):
        entries = self.entries()
        with self.assertWarnsRegex(UserWarning, 'Duplicate name'):
            data = self.archive(entries + [entries[0]])
        with self.assertRaisesRegex(RuntimeError, 'exactly six unique expected files'):
            self.export(data)
        self.assertEqual(self.output.getvalue(), '')

    def test_unexpected_member_is_rejected(self):
        self.reject(self.entries() + [('unexpected.txt', b'extra')],
                    'exactly six unique expected files')

    def sized_entries(self, total):
        names = sorted(exporter.FILES)
        return [(names[0], b'x' * total)] + [(name, b'') for name in names[1:]]

    def test_compressible_archive_above_uncompressed_bound_is_rejected(self):
        data = self.archive(self.sized_entries(exporter.MAX_UNCOMPRESSED_BYTES + 1))
        self.assertLess(len(data), exporter.MAX_ARCHIVE_BYTES)
        with self.assertRaisesRegex(RuntimeError, 'Uncompressed archive exceeds size bound'):
            self.export(data)
        self.assertEqual(self.output.getvalue(), '')

    def test_uncompressed_bound_is_inclusive(self):
        data = self.archive(self.sized_entries(exporter.MAX_UNCOMPRESSED_BYTES))
        self.assertTrue(self.export(data).endswith('M4_ARCHIVE_END\n'))
