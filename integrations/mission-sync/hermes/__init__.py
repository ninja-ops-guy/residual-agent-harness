"""Hermes plugin. Registration has no filesystem or network side effects.

The host must be able to import the RESIDUAL checkout containing mission_client.
Set RESIDUAL_MISSION_CONFIG to a private config file for ONE native session.
Full-text capture additionally requires RESIDUAL_MISSION_CAPTURE_TEXT=1.
"""
from __future__ import annotations

import logging
import os


def register(ctx):
    client = None

    def get_client(session_id):
        nonlocal client
        if client is None:
            from residual.station.mission_client import MissionClient
            client = MissionClient.from_environment()
        if client is None or session_id != client.config["conversation_id"]:
            return None
        return client

    def observe(phase, session_id, content, turn_id=None):
        try:
            current = get_client(session_id)
            if current is None:
                return None
            # Check actual host session against the server-pinned native identity
            # before attributing a single inbound report to this binding.
            current.context(consume=False)
            capture = os.environ.get("RESIDUAL_MISSION_CAPTURE_TEXT") == "1"
            value = content if capture else f"Hermes {phase} observed; text capture disabled."
            source = f"{phase}:{turn_id}" if isinstance(turn_id, str) and turn_id else None
            current.record("message" if capture else "progress", value, native_event_id=source)
            current.pump(maximum=2)
            return current.context() if phase == "user_turn" else None
        except Exception:
            logging.getLogger(__name__).warning("RESIDUAL mission sync DEGRADED; inspect local spool and Station binding. No task acceptance implied.")
            return "RESIDUAL mission synchronization unavailable. Do not assume current task state or acceptance from this conversation."

    def pre(session_id=None, user_message="", **kwargs):
        value = observe("user_turn", session_id, user_message, kwargs.get("turn_id"))
        return {"context": value} if value else None

    def post(session_id=None, assistant_response="", **kwargs):
        observe("assistant_turn", session_id, assistant_response, kwargs.get("turn_id"))
        # A successful model turn is NOT a task completion or acceptance.

    ctx.register_hook("pre_llm_call", pre)
    ctx.register_hook("post_llm_call", post)
