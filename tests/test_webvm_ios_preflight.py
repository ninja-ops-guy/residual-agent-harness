from pathlib import Path
import sys
import tempfile
import unittest

VM_DIR = Path(__file__).resolve().parents[1] / "demo" / "vm"
sys.path.insert(0, str(VM_DIR))

from patch_webvm import patch_index  # noqa: E402


class IOSWebKitPreflightTests(unittest.TestCase):
    def patched(self, html: str) -> str:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text(html, encoding="utf-8")
            patch_index(path)
            return path.read_text(encoding="utf-8")

    def test_ios_preflight_runs_before_webvm_application_script(self):
        out = self.patched(
            '<!doctype html><html><head><script type="module" src="/_app/webvm.js"></script></head><body></body></html>'
        )
        marker = 'data-residual-ios-webkit-preflight'
        self.assertIn(marker, out)
        self.assertLess(out.index(marker), out.index('src="/_app/webvm.js"'))
        for expected in (
            "iPhone", "iPad", "iPod", "MacIntel", "maxTouchPoints",
            "full_vm", "../demo.html", "ios-webkit", "location.replace",
        ):
            self.assertIn(expected, out)

    def test_explicit_full_vm_override_is_preserved_for_debugging(self):
        out = self.patched('<html><head></head><body></body></html>')
        self.assertIn('params.get("full_vm") === "1"', out)
        self.assertIn('if (!ios) return;', out)

    def test_index_patch_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "index.html"
            path.write_text('<html><head></head><body></body></html>', encoding="utf-8")
            patch_index(path)
            patch_index(path)
            out = path.read_text(encoding="utf-8")
        self.assertEqual(out.count("data-residual-ios-webkit-preflight"), 1)
        self.assertEqual(out.count('name="theme-color"'), 1)


if __name__ == "__main__":
    unittest.main()
