"""Dependency-free public-asset and build safety checks."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from html.parser import HTMLParser

spec = importlib.util.spec_from_file_location("pages_build", Path(__file__).parents[1] / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class BuildTests(unittest.TestCase):
    def test_only_allowlisted_public_assets_and_exact_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            shutil.copytree(builder.SOURCE, source)
            (source / "private.env").write_text("should not publish")
            target = builder.build(Path(temp) / "out", "a" * 40, source)
            self.assertEqual(set(p.name for p in target.iterdir()), set(builder.ASSETS))
            html = (target / "index.html").read_text()
            self.assertNotIn("__SOURCE_REVISION__", html)
            self.assertEqual(html.count("a" * 40), 2)

    def test_rejects_revision_injection(self):
        with tempfile.TemporaryDirectory() as temp:
            for revision in ['main', '<script>', '" onload="x', 'A' * 40]:
                with self.assertRaises(ValueError):
                    builder.build(Path(temp) / "out", revision)

    def test_does_not_delete_or_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "out"
            output.mkdir()
            marker = output / "keep"
            marker.write_text("preserve")
            with self.assertRaises(ValueError):
                builder.build(output)
            self.assertEqual(marker.read_text(), "preserve")

    def test_rejects_symlink_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            shutil.copytree(builder.SOURCE, source)
            (source / "app.mjs").unlink()
            (source / "app.mjs").symlink_to(builder.SOURCE / "app.mjs")
            with self.assertRaises(ValueError):
                builder.build(Path(temp) / "out", source=source)

    def test_rejects_missing_assets_and_output_inside_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            shutil.copytree(builder.SOURCE, source)
            with self.assertRaises(ValueError):
                builder.build(source / "out", source=source)
            (source / "model.mjs").unlink()
            with self.assertRaises(ValueError):
                builder.build(Path(temp) / "out", source=source)

    def test_relative_assets_no_inline_script_no_backend_forms(self):
        tags = Tags((builder.SOURCE / "index.html").read_text()).tags
        for tag, attrs in tags:
            self.assertFalse(any(key.startswith('on') for key in attrs))
            self.assertNotEqual(tag, 'form')
            if tag == 'script':
                self.assertTrue(attrs.get('src', '').startswith('./'))
            if tag == 'link':
                self.assertTrue(attrs.get('href', '').startswith('./'))
        csp = next(attrs['content'] for tag, attrs in tags if attrs.get('http-equiv') == 'Content-Security-Policy')
        for directive in ["connect-src 'none'", "form-action 'none'", "object-src 'none'", "base-uri 'none'"]:
            self.assertIn(directive, csp)
        self.assertNotIn('unsafe-inline', csp)
        ids = [attrs['id'] for _, attrs in tags if 'id' in attrs]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
