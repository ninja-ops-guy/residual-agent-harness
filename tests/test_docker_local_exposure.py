from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerLocalExposureContractTests(unittest.TestCase):
    def test_compose_publishes_station_only_on_host_loopback(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:8765:8765"', compose)
        self.assertNotRegex(compose, re.compile(r'(?m)^\s*-\s*"?(?:0\.0\.0\.0:)?8765:8765"?\s*$'))

    def test_compose_declares_explicit_local_container_boundary(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('RESIDUAL_CONTAINER_LOCAL_ONLY: "1"', compose)
        self.assertIn(
            'RESIDUAL_ALLOWED_HOSTS: "localhost:8765,127.0.0.1:8765"',
            compose,
        )
        self.assertIn('RESIDUAL_PUBLIC_URL: "http://localhost:8765"', compose)
        self.assertNotIn("RESIDUAL_REMOTE_EXPOSURE: \"1\"", compose)

    def test_image_default_requires_explicit_compose_policy_to_start(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('CMD ["--host", "0.0.0.0", "--port", "8765", "--start-ollama"]', dockerfile)
        # Bare image execution remains fail-closed because the Dockerfile does
        # not bake the local-only trust exception into the image.
        self.assertNotIn("RESIDUAL_CONTAINER_LOCAL_ONLY=1", dockerfile)
        self.assertNotIn("RESIDUAL_REMOTE_EXPOSURE=1", dockerfile)


if __name__ == "__main__":
    unittest.main()
