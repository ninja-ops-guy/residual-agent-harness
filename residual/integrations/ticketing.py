"""Ticketing connectors: Jira, Azure Boards, Linear.

Implements ENT6-R5: requirement import (ticket -> GoalSpec), task status
sync, receipt attachment as evidence, and automatic ticket closure on
task acceptance.
Implements ENT6-R6 (bidirectional) and ENT6-R7 (via IntegrationConnector).
"""
from __future__ import annotations

from typing import Any

from ..core import ContractError
from .base import IntegrationConnector, IntegrationReceipt, TransportResponse


class TicketingConnector(IntegrationConnector):
    """Generic ticketing connector. Implements ENT6-R5, ENT6-R6, ENT6-R7."""

    system_name = "ticketing"
    issue_path = "/api/issues/{id}"
    done_status = "Done"

    def import_requirement(self, ticket_id: str) -> dict:
        """Import a ticket as a GoalSpec-shaped requirement. Implements ENT6-R5."""
        body = self.require_ok(self.call("GET", self.issue_path.format(id=ticket_id)),
                               "ticket fetch")
        if not isinstance(body, dict):
            raise ContractError(f"{self.system_name}: ticket payload must be an object")
        return {
            "schema": "residual.goalspec.v1",
            "external_id": ticket_id,
            "source": self.system_name,
            "goal": body.get("summary") or body.get("title") or "",
            "acceptance": body.get("acceptance_criteria", []),
            "labels": body.get("labels", []),
            "raw": body,
        }

    def import_task(self, external_id: str) -> dict:
        return self.import_requirement(external_id)

    def sync_status(self, ticket_id: str, task_status: str) -> TransportResponse:
        """Sync task status onto the ticket. Implements ENT6-R5."""
        mapping = {"pending": "To Do", "running": "In Progress",
                   "accepted": self.done_status, "rejected": "To Do"}
        resp = self.call("PATCH", self.issue_path.format(id=ticket_id),
                         {"status": mapping.get(task_status, task_status)})
        self.require_ok(resp, "status sync")
        return resp

    def post_receipt(self, ticket_id: str, receipt: IntegrationReceipt) -> TransportResponse:
        """Attach a receipt as evidence on the ticket. Implements ENT6-R5 and ENT6-R6."""
        resp = self.call("POST", f"{self.issue_path.format(id=ticket_id)}/attachments", {
            "kind": "evidence",
            "receipt": receipt.to_dict(),
        })
        self.require_ok(resp, "evidence attachment")
        return resp

    def close_on_acceptance(self, ticket_id: str,
                            receipt: IntegrationReceipt) -> TransportResponse:
        """Automatically close the ticket when the task is accepted;
        attaches the receipt as evidence first. Implements ENT6-R5."""
        if not receipt.accepted:
            raise ContractError("auto-close requires an accepted receipt")
        self.post_receipt(ticket_id, receipt)
        resp = self.call("PATCH", self.issue_path.format(id=ticket_id),
                         {"status": self.done_status,
                          "resolution": "residual:accepted",
                          "receipt_hash": receipt.receipt_hash})
        self.require_ok(resp, "ticket closure")
        return resp


class JiraConnector(TicketingConnector):
    """Jira connector. Implements ENT6-R5, ENT6-R6, ENT6-R7."""

    system_name = "jira"
    issue_path = "/rest/api/3/issue/{id}"

    def import_requirement(self, ticket_id: str) -> dict:
        body = self.require_ok(self.call("GET", self.issue_path.format(id=ticket_id)),
                               "jira issue fetch")
        fields = (body or {}).get("fields", {}) if isinstance(body, dict) else {}
        return {"schema": "residual.goalspec.v1", "external_id": ticket_id,
                "source": self.system_name, "goal": fields.get("summary", ""),
                "acceptance": [], "labels": fields.get("labels", []), "raw": body}

    def sync_status(self, ticket_id: str, task_status: str) -> TransportResponse:
        mapping = {"accepted": "Done", "running": "In Progress", "pending": "To Do"}
        resp = self.call("POST", f"/rest/api/3/issue/{ticket_id}/transitions",
                         {"transition": {"name": mapping.get(task_status, task_status)}})
        self.require_ok(resp, "jira transition")
        return resp


class AzureBoardsConnector(TicketingConnector):
    """Azure Boards connector. Implements ENT6-R5, ENT6-R6, ENT6-R7."""

    system_name = "azure_boards"
    issue_path = "/_apis/wit/workitems/{id}?api-version=7.1"
    done_status = "Closed"

    def sync_status(self, ticket_id: str, task_status: str) -> TransportResponse:
        mapping = {"accepted": "Closed", "running": "Active", "pending": "New"}
        resp = self.call("PATCH", self.issue_path.format(id=ticket_id), [
            {"op": "add", "path": "/fields/System.State",
             "value": mapping.get(task_status, task_status)},
        ])
        self.require_ok(resp, "azure boards status sync")
        return resp


class LinearConnector(TicketingConnector):
    """Linear connector (GraphQL). Implements ENT6-R5, ENT6-R6, ENT6-R7."""

    system_name = "linear"
    issue_path = "/graphql"
    done_status = "Done"

    def import_requirement(self, ticket_id: str) -> dict:
        body = self.require_ok(self.call("POST", "/graphql", {
            "query": "query($id: String!) { issue(id: $id) { title description labels } }",
            "variables": {"id": ticket_id},
        }), "linear issue fetch")
        issue = (((body or {}).get("data") or {}).get("issue") or {})
        return {"schema": "residual.goalspec.v1", "external_id": ticket_id,
                "source": self.system_name, "goal": issue.get("title", ""),
                "acceptance": [], "labels": issue.get("labels", []), "raw": body}
