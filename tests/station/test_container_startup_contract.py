from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ContainerStartupContractTests(unittest.TestCase):
    def test_compose_publishes_only_host_loopback(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:8765:8765"', compose)
        self.assertNotIn('"0.0.0.0:8765:8765"', compose)

    def test_dockerfile_uses_loopback_station_entrypoint(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('ENTRYPOINT ["/usr/local/bin/residual-container-station"]', dockerfile)
        self.assertIn('CMD ["--start-ollama"]', dockerfile)
        self.assertNotIn('"--host", "0.0.0.0"', dockerfile)
        self.assertIn("127.0.0.1:8766/api/bootstrap", dockerfile)

    def test_container_entrypoint_keeps_station_loopback_bound(self):
        script = (ROOT / "scripts/container_station_entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("--host 127.0.0.1", script)
        self.assertIn('TCP-LISTEN:$PROXY_PORT', script)
        self.assertIn("bind=0.0.0.0", script)
        self.assertIn("TCP:127.0.0.1:$STATION_PORT", script)
        self.assertNotIn("RESIDUAL_REMOTE_EXPOSURE=1", script)


if __name__ == "__main__":
    unittest.main()
