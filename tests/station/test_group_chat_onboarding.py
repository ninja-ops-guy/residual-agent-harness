"""Shared Comms onboarding tests.

Station Shared Comms is an operator/event-log surface, not a residual.mesh client.
These tests pin what a new operator can safely do before any future mesh UI bridge.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from residual.station.service import Station, demo_spec


class SharedCommsOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]

    def test_new_mission_has_visible_project_created_event(self):
        events = self.station.store.events(self.pid)
        self.assertTrue(events)
        self.assertEqual(events[0]["event_type"], "project.created")
        self.assertEqual(events[0]["actor"], "station")

    def test_operator_note_roundtrip_preserves_actor_and_text(self):
        text = "Hello runners — onboarding note"
        event = self.station.store.event(
            self.pid, "project.note", {"message": text}, actor="operator"
        )
        self.assertEqual(event["actor"], "operator")
        loaded = self.station.store.events(self.pid)[-1]
        self.assertEqual(loaded["data"]["message"], text)
        self.assertEqual(loaded["event_type"], "project.note")

    def test_operator_note_survives_station_restart(self):
        self.station.store.event(
            self.pid, "project.note", {"message": "persist me"}, actor="operator"
        )
        reopened = Station(self.temp.name)
        notes = [
            event for event in reopened.store.events(self.pid)
            if event["event_type"] == "project.note"
        ]
        self.assertEqual(notes[-1]["data"]["message"], "persist me")

    def test_event_sequence_and_hash_chain_remain_valid_after_notes(self):
        for i in range(5):
            self.station.store.event(
                self.pid, "project.note", {"message": f"note-{i}"}, actor="operator"
            )
        events = self.station.store.events(self.pid)
        self.assertEqual([e["seq"] for e in events], list(range(1, len(events) + 1)))
        for previous, current in zip(events, events[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])

    def test_group_chat_text_is_data_not_an_execution_channel(self):
        payload = '<img src=x onerror=alert(1)> ; rm -rf /'
        self.station.store.event(
            self.pid, "project.note", {"message": payload}, actor="operator"
        )
        loaded = self.station.store.events(self.pid)[-1]
        self.assertEqual(loaded["data"]["message"], payload)
        task_states = [t["state"] for t in self.station.store.project(self.pid)["tasks"]]
        self.assertTrue(all(state == "proposed" for state in task_states))

    def test_shared_comms_frontend_escapes_rendered_event_text(self):
        app = (Path(__file__).resolve().parents[2] / "residual/station/static/app.js").read_text()
        self.assertIn('$' + '{e(eventText(ev))}', app)
        self.assertIn('case"project.note"', app)
        self.assertIn('Agents receive task-specific context and report deltas', app)

    def test_setup_checklist_covers_training_model_cloud_and_spec_import(self):
        app = (Path(__file__).resolve().parents[2] / "residual/station/static/app.js").read_text()
        for phrase in (
            "Ready for your first shift?",
            "Test the workflow",
            "Power up a local model",
            "Connect cloud support",
            "Import your specification",
        ):
            self.assertIn(phrase, app)

    def test_ui_does_not_claim_shared_comms_is_mesh_transport(self):
        app = (Path(__file__).resolve().parents[2] / "residual/station/static/app.js").read_text()
        self.assertIn("SHARED EVENT LOG", app)
        self.assertIn("The chat displays recorded activity", app)
        self.assertNotIn("/api/mesh/", app)
