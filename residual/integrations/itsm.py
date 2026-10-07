"""ITSM connectors: ServiceNow, Jira Service Management (JSM), BMC Helix.

Implements ENT6-R1: task creation from tickets, receipt attachment to
tickets, status synchronization (ticket status reflects task status),
and HITL challenge delivery via ticket assignment.
Implements ENT6-R6 (bidirectional) and ENT6-R7 (via IntegrationConnector).
"""
from __future__ import annotations

from typing import Any

from ..core import ContractError
from .base import IntegrationConnector, ConnectorReceipt, TransportResponse


class ITSMConnector(IntegrationConnector):
    """Generic ITSM connector. Implements ENT6-R1, ENT6-R6, ENT6-R7."""

    ticket_list_path = "/api/tickets"
    ticket_path = "/api/tickets/{id}"
    attachment_path = "/api/tickets/{id}/attachments"
    status_field = "state"

    def import_task(self, ticket_id: str) -> dict:
        """Create a task spec from a ticket. Implements ENT6-R1."""
        body = self.require_ok(self.call("GET", self.ticket_path.format(id=ticket_id)),
                               "ticket fetch")
        if not isinstance(body, dict):
            raise ContractError(f"{self.system_name}: ticket payload must be an object")
        return {
            "external_id": ticket_id,
            "source": self.system_name,
            "goal": body.get("short_description") or body.get("summary") or "",
            "description": body.get("description", ""),
            "priority": body.get("priority", "normal"),
            "status": body.get(self.status_field, "open"),
        }

    def post_receipt(self, ticket_id: str, receipt: ConnectorReceipt) -> TransportResponse:
        """Attach a receipt to a ticket as evidence. Implements ENT6-R1 and ENT6-R6."""
        resp = self.call("POST", self.attachment_path.format(id=ticket_id), {
            "name": f"residual-receipt-{receipt.receipt_hash[:12]}.json",
            "content_type": "application/json",
            "receipt": receipt.to_dict(),
        })
        self.require_ok(resp, "receipt attachment")
        return resp

    def sync_status(self, ticket_id: str, task_status: str) -> TransportResponse:
        """Push task status so the ticket reflects it. Implements ENT6-R1."""
        mapping = {"pending": "open", "running": "in_progress",
                   "accepted": "resolved", "rejected": "open", "failed": "open"}
        ticket_state = mapping.get(task_status, task_status)
        return self.call("PATCH", self.ticket_path.format(id=ticket_id),
                         {self.status_field: ticket_state})

    def deliver_hitl_challenge(self, ticket_id: str, assignee: str,
                               challenge: dict) -> TransportResponse:
        """Deliver a HITL challenge via ticket assignment. Implements ENT6-R1."""
        return self.call("PATCH", self.ticket_path.format(id=ticket_id), {
            "assigned_to": assignee,
            "work_notes": f"HITL challenge: {challenge.get('question', challenge)}",
            "residual_challenge": challenge,
        })


class ServiceNowConnector(ITSMConnector):
    """ServiceNow connector. Implements ENT6-R1, ENT6-R6, ENT6-R7."""

    system_name = "servicenow"
    ticket_path = "/api/now/table/incident/{id}"
    attachment_path = "/api/now/table/incident/{id}/attachments"


class JSMConnector(ITSMConnector):
    """Jira Service Management connector. Implements ENT6-R1, ENT6-R6, ENT6-R7."""

    system_name = "jsm"
    ticket_path = "/rest/api/2/issue/{id}"
    attachment_path = "/rest/api/2/issue/{id}/attachments"
    status_field = "status"

    def sync_status(self, ticket_id: str, task_status: str) -> TransportResponse:
        mapping = {"accepted": "Done", "running": "In Progress", "pending": "To Do"}
        return self.call("POST", f"/rest/api/2/issue/{ticket_id}/transitions",
                         {"transition": {"name": mapping.get(task_status, task_status)}})


class BMCConnector(ITSMConnector):
    """BMC Helix connector. Implements ENT6-R1, ENT6-R6, ENT6-R7."""

    system_name = "bmc"
    ticket_path = "/api/arsys/v1/entry/HPD:IncidentInterface/{id}"
    attachment_path = "/api/arsys/v1/entry/HPD:IncidentInterface/{id}/attachments"
