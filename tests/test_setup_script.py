import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "setup.sh"


class SetupScriptSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SETUP.read_text(encoding="utf-8")

    def test_shell_syntax_is_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(SETUP)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_defaults_are_persistent_and_loopback_only(self):
        self.assertIn('DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"', self.text)
        self.assertIn('STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"', self.text)
        self.assertIn('HOST="${RESIDUAL_HOST:-127.0.0.1}"', self.text)
        self.assertNotIn('RESIDUAL_VENV:-/tmp/', self.text)
        self.assertNotIn('RESIDUAL_HOST:-0.0.0.0', self.text)

    def test_noninteractive_execution_does_not_enable_macro(self):
        self.assertIn('reply="N"', self.text)
        self.assertIn("no TTY detected - leaving the macro disabled", self.text)
        self.assertNotIn('reply="Y"', self.text)

    def test_rc_edits_use_bounded_markers_and_atomic_replace(self):
        for marker in (
            "# BEGIN residual-agent-harness PATH",
            "# END residual-agent-harness PATH",
            "# BEGIN residual-agent-harness serve macro",
            "# END residual-agent-harness serve macro",
        ):
            self.assertIn(marker, self.text)
        self.assertIn("tempfile.NamedTemporaryFile", self.text)
        self.assertIn("os.replace(temp_name, path)", self.text)
        self.assertIn("refusing to replace an unrecognized user-defined residual function", self.text)

    def test_existing_broken_venv_has_bounded_repair(self):
        self.assertIn('"$PY" -m venv --clear "$VENV_DIR"', self.text)
        self.assertIn('"$VENV_DIR/bin/python" -c \'import sys\'', self.text)

    def test_setup_does_not_launch_browser_or_server(self):
        self.assertNotIn("xdg-open", self.text)
        self.assertNotIn('\nopen "$LINK"', self.text)
        self.assertNotIn('\nstart "$LINK"', self.text)


if __name__ == "__main__":
    unittest.main()
