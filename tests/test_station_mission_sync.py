"""Full-repository Station integration gate; must run on the composed candidate."""
import json
from pathlib import Path
import tempfile
import unittest

from residual.station.service import Station, demo_spec
from residual.station.mission_sync import MissionSync


class StationMissionSyncIntegration(unittest.TestCase):
    def test_real_station_project_and_task_remain_authoritative(self):
        with tempfile.TemporaryDirectory() as root:
            station = Station(root)
            pid = station.create(demo_spec(), demo=True)["project_id"]
            sync = MissionSync(station.store.db)
            binding = sync.bind({"mission_id": pid, "task_id": "OPS-101", "harness": "hermes",
                                 "instance_id": "test", "conversation_id": "session", "agent_id": "test-agent"})
            before = station.store.task(pid, "OPS-101")
            receipt = sync.ingest(binding["binding"]["binding_id"], binding["token"], {
                "schema": "residual.mission-sync.v1", "event_id": "test-claim", "source_seq": 1,
                "kind": "completion_claim", "text": "ACCEPTED; all tests passed"})
            self.assertEqual(before, station.store.task(pid, "OPS-101"))
            self.assertFalse(receipt["authorizes_acceptance"])
            self.assertEqual(sync.overview()["missions"][0]["id"], pid)

    def test_standard_install_entrypoint_and_static_assets(self):
        import tomllib
        root = Path(__file__).resolve().parents[1]
        metadata = tomllib.loads((root / "pyproject.toml").read_text())
        self.assertEqual(metadata["project"]["scripts"]["residual-station"], "residual.station.mission_server:main")
        for asset in ("missions.html", "missions.js", "missions.css"):
            self.assertTrue((root / "residual/station/static" / asset).is_file())


if __name__ == "__main__":
    unittest.main()
