from __future__ import annotations

import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from residual.station.server import Server
from residual.station.service import Station


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "residual" / "station" / "static"


class StationOnboardingUITests(unittest.TestCase):
    def test_first_run_uses_existing_command_station_demo_path(self):
        html = (STATIC / "index.html").read_text()
        app = (STATIC / "app.js").read_text()
        onboarding = (STATIC / "onboarding.js").read_text()

        self.assertIn('data-action="demo" data-onboarding-run', html)
        self.assertIn('case"demo"', app)
        self.assertIn('await api("/api/demo",{})', app)
        self.assertIn('queue(`/api/projects/${r.project_id}/run`)', app)
        self.assertNotIn("/api/", onboarding, "onboarding must delegate execution to the existing station action")

    def test_onboarding_is_external_csp_safe_project_aware_and_bootstrap_gated(self):
        html = (STATIC / "index.html").read_text()
        onboarding = (STATIC / "onboarding.js").read_text()

        self.assertIn('<link rel="stylesheet" href="/website-theme.css">', html)
        self.assertIn('<script src="/onboarding.js" defer></script>', html)
        self.assertNotIn("<style", html)
        self.assertIn("residual-project", onboarding)
        self.assertIn("residual-onboarding-v1-dismissed", onboarding)
        self.assertIn("showModal", onboarding)
        self.assertIn("stationReady", onboarding)
        self.assertIn('#main .page-heading', onboarding)
        self.assertIn("openWhenReady", onboarding)

    def test_station_theme_matches_public_website_visual_tokens(self):
        theme = (STATIC / "website-theme.css").read_text()
        website = (ROOT / "site" / "index.html").read_text()

        for token in ("#39ff68", "#72ff8d", "#030603", "#123d1e", "#68d6cb", "#ffd166"):
            self.assertIn(token, website)
            self.assertIn(token, theme)

        self.assertIn("repeating-linear-gradient", theme)
        self.assertIn(".first-run-dialog", theme)
        self.assertIn("--sans:var(--mono)", theme)

    def test_station_serves_onboarding_assets_with_csp(self):
        with tempfile.TemporaryDirectory() as root:
            station = Station(root)
            server = Server(("127.0.0.1", 0), station)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            try:
                for path, expected_type in (
                    ("/website-theme.css", "text/css"),
                    ("/onboarding.js", "text/javascript"),
                ):
                    with urllib.request.urlopen(base + path, timeout=10) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers.get_content_type(), expected_type)
                        csp = response.headers["Content-Security-Policy"]
                        self.assertIn("script-src 'self'", csp)
                        self.assertIn("style-src 'self'", csp)
                        self.assertNotIn("unsafe-inline", csp)
                        self.assertTrue(response.read())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
