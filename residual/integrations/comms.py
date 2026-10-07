"""Communication connectors: Slack, Microsoft Teams, Email.

Implements ENT6-R4: HITL challenge notifications, receipt delivery on
approval, swarm status updates, and alert routing to on-call channels.
Implements ENT6-R6 (bidirectional: replies/decisions flow back) and
ENT6-R7 (via IntegrationConnector).
"""
from __future__ import annotations

from typing import Any

from ..core import ContractError
from .base import IntegrationConnector, ConnectorReceipt, TransportResponse


class CommsConnector(IntegrationConnector):
    """Generic communication platform connector. Implements ENT6-R4, ENT6-R6, ENT6-R7."""

    system_name = "comms"
    message_path = "/api/messages"

    def send_message(self, channel: str, text: str,
                     blocks: list | None = None) -> TransportResponse:
        if not channel or not text:
            raise ContractError("channel and text are required")
        resp = self.call("POST", self.message_path,
                         {"channel": channel, "text": text, "blocks": blocks or []})
        self.require_ok(resp, "message send")
        return resp

    def notify_hitl_challenge(self, channel: str, challenge_id: str,
                              challenge: dict) -> TransportResponse:
        """Deliver a HITL challenge notification. Implements ENT6-R4."""
        return self.send_message(
            channel, f"HITL challenge {challenge_id}: "
                     f"{challenge.get('question', 'approval required')}",
            blocks=[{"type": "actions", "challenge_id": challenge_id,
                     "options": ["approve", "reject", "inspect"]}])

    def deliver_receipt(self, channel: str, receipt: ConnectorReceipt) -> TransportResponse:
        """Deliver a receipt on approval. Implements ENT6-R4."""
        if not receipt.accepted:
            raise ContractError("receipt delivery is for approved (accepted) receipts")
        return self.send_message(
            channel, f"Receipt accepted for {receipt.subject_id} "
                     f"(hash {receipt.receipt_hash[:12]})",
            blocks=[{"type": "receipt", "receipt": receipt.to_dict()}])

    def send_swarm_status(self, channel: str, swarm_id: str,
                          status: dict) -> TransportResponse:
        """Post a swarm status update. Implements ENT6-R4."""
        summary = ", ".join(f"{k}={v}" for k, v in sorted(status.items())) or "idle"
        return self.send_message(channel, f"Swarm {swarm_id}: {summary}",
                                 blocks=[{"type": "swarm_status", "status": status}])

    def route_alert(self, oncall_channel: str, alert: dict) -> TransportResponse:
        """Route an alert to the on-call channel. Implements ENT6-R4."""
        return self.send_message(oncall_channel,
                                 f"ALERT: {alert.get('title', 'residual alert')}",
                                 blocks=[{"type": "alert", "alert": alert}])

    # -- inbound (ENT6-R6): humans reply with decisions -------------------

    def poll_decision(self, challenge_id: str) -> dict:
        """Read back a HITL decision from the platform. Implements ENT6-R6."""
        body = self.require_ok(
            self.call("GET", f"{self.message_path}/decisions/{challenge_id}"),
            "decision poll")
        return {"challenge_id": challenge_id,
                "decision": (body or {}).get("decision", "pending"),
                "responder": (body or {}).get("user", "unknown")}

    def import_task(self, external_id: str) -> dict:
        body = self.require_ok(self.call("GET", f"{self.message_path}/{external_id}"),
                               "message fetch")
        return {"external_id": external_id, "source": self.system_name,
                "goal": (body or {}).get("text", ""), "raw": body}

    def post_receipt(self, external_id: str, receipt: ConnectorReceipt) -> TransportResponse:
        return self.send_message(external_id,
                                 f"Receipt {receipt.verdict} for {receipt.subject_id}",
                                 blocks=[{"type": "receipt", "receipt": receipt.to_dict()}])

    def sync_status(self, external_id: str, task_status: str) -> TransportResponse:
        return self.send_message(external_id, f"Task status: {task_status}")


class SlackConnector(CommsConnector):
    """Slack connector. Implements ENT6-R4, ENT6-R6, ENT6-R7."""

    system_name = "slack"
    message_path = "/api/chat.postMessage"


class TeamsConnector(CommsConnector):
    """Microsoft Teams connector. Implements ENT6-R4, ENT6-R6, ENT6-R7."""

    system_name = "teams"
    message_path = "/v1.0/chats/messages"

    def send_message(self, channel: str, text: str,
                     blocks: list | None = None) -> TransportResponse:
        if not channel or not text:
            raise ContractError("channel and text are required")
        resp = self.call("POST", f"/v1.0/chats/{channel}/messages",
                         {"body": {"contentType": "html", "content": text},
                          "attachments": blocks or []})
        self.require_ok(resp, "teams message send")
        return resp


class EmailConnector(CommsConnector):
    """Email (SMTP/HTTP API) connector. Implements ENT6-R4, ENT6-R6, ENT6-R7."""

    system_name = "email"
    message_path = "/v3/mail/send"

    def send_message(self, channel: str, text: str,
                     blocks: list | None = None) -> TransportResponse:
        if not channel or not text:
            raise ContractError("recipient and text are required")
        resp = self.call("POST", self.message_path, {
            "to": channel,
            "subject": text.splitlines()[0][:78],
            "body": text,
            "metadata": {"blocks": blocks or []},
        })
        self.require_ok(resp, "email send")
        return resp
