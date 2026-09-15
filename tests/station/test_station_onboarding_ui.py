from __future__ import annotations

import threading
import urllib.request
from pathlib import Path

from residual.station.server import Server
from residual.station.service import Station


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "residual" / "station" / "static"


def test_first_run_uses_existing_command_station_demo_path():
    html = (STATIC / "index.html").read_text()
    app = (STATIC / "app.js").read_text()
    onboarding = (STATIC / "onboarding.js").read_text()

    assert 'data-action="demo" data-onboarding-run' in html
    assert 'case"demo"' in app
    assert 'await api("/api/demo",{})' in app
    assert 'queue(`/api/projects/${r.project_id}/run`)' in app
    assert "/api/" not in onboarding, "onboarding must delegate execution to the existing station action"


def test_onboarding_is_external_csp_safe_and_project_aware():
    html = (STATIC / "index.html").read_text()
    onboarding = (STATIC / "onboarding.js").read_text()

    assert '<link rel="stylesheet" href="/website-theme.css">' in html
    assert '<script src="/onboarding.js" defer></script>' in html
    assert "<style" not in html
    assert "residual-project" in onboarding
    assert "residual-onboarding-v1-dismissed" in onboarding
    assert "showModal" in onboarding


def test_station_theme_matches_public_website_visual_tokens():
    theme = (STATIC / "website-theme.css").read_text()
    website = (ROOT / "site" / "index.html").read_text()

    for token in ("#39ff68", "#72ff8d", "#030603", "#123d1e", "#68d6cb", "#ffd166"):
        assert token in website
        assert token in theme

    assert "repeating-linear-gradient" in theme
    assert ".first-run-dialog" in theme
    assert "--sans:var(--mono)" in theme


def test_station_serves_onboarding_assets_with_csp(tmp_path):
    station = Station(str(tmp_path))
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
                assert response.status == 200
                assert response.headers.get_content_type() == expected_type
                csp = response.headers["Content-Security-Policy"]
                assert "script-src 'self'" in csp
                assert "style-src 'self'" in csp
                assert "unsafe-inline" not in csp
                assert response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
