"""CI/CD connectors: Jenkins, GitLab CI, GitHub Actions, Azure DevOps, CircleCI.

Implements ENT6-R2: task triggering from pipeline stages, pipeline gating
on Residual verification (the pipeline waits for an ConnectorReceipt),
and receipt publication as pipeline artifacts.
Implements ENT6-R6 (bidirectional) and ENT6-R7 (via IntegrationConnector).
"""
from __future__ import annotations

from typing import Any

from ..core import ContractError
from .base import IntegrationConnector, ConnectorReceipt, TransportResponse


class CICDConnector(IntegrationConnector):
    """Generic CI/CD connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "cicd"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        """Trigger a pipeline run from a Residual task. Implements ENT6-R2 and ENT6-R6."""
        resp = self.call("POST", f"/pipelines/{pipeline_id}/trigger",
                         {"parameters": params or {}})
        body = self.require_ok(resp, "pipeline trigger")
        return {"run_id": str((body or {}).get("id", "unknown")), "raw": body}

    def import_task(self, external_id: str) -> dict:
        """Build a task spec from a pipeline stage event. Implements ENT6-R2."""
        body = self.require_ok(self.call("GET", f"/pipelines/{external_id}"),
                               "pipeline fetch")
        return {"external_id": external_id, "source": self.system_name,
                "goal": (body or {}).get("name", ""), "raw": body}

    def gate_pipeline(self, run_id: str,
                      receipt: ConnectorReceipt) -> TransportResponse:
        """Gate a pipeline on Residual verification: the run proceeds only
        if the ConnectorReceipt verdict is accepted. Implements ENT6-R2."""
        if not isinstance(receipt, ConnectorReceipt):
            raise ContractError("pipeline gating requires an ConnectorReceipt")
        return self.call("POST", f"/runs/{run_id}/gate", {
            "decision": "proceed" if receipt.accepted else "hold",
            "receipt_hash": receipt.receipt_hash,
            "verdict": receipt.verdict,
        })

    def publish_receipt_artifact(self, run_id: str,
                                 receipt: ConnectorReceipt) -> TransportResponse:
        """Publish a receipt as a pipeline artifact. Implements ENT6-R2."""
        resp = self.call("POST", f"/runs/{run_id}/artifacts", {
            "name": f"residual-receipt-{receipt.receipt_hash[:12]}.json",
            "content_type": "application/json",
            "receipt": receipt.to_dict(),
        })
        self.require_ok(resp, "artifact publication")
        return resp

    def post_receipt(self, external_id: str, receipt: ConnectorReceipt) -> TransportResponse:
        return self.publish_receipt_artifact(external_id, receipt)

    def sync_status(self, external_id: str, task_status: str) -> TransportResponse:
        return self.call("POST", f"/runs/{external_id}/status",
                         {"residual_status": task_status})


class JenkinsConnector(CICDConnector):
    """Jenkins connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "jenkins"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        resp = self.call("POST", f"/job/{pipeline_id}/buildWithParameters",
                         params or {})
        self.require_ok(resp, "jenkins build trigger")
        return {"run_id": pipeline_id, "raw": resp.body}


class GitLabConnector(CICDConnector):
    """GitLab CI connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "gitlab"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        resp = self.call("POST", f"/api/v4/projects/{pipeline_id}/pipeline",
                         {"variables": params or {}})
        body = self.require_ok(resp, "gitlab pipeline trigger")
        return {"run_id": str((body or {}).get("id", "unknown")), "raw": body}


class GitHubActionsConnector(CICDConnector):
    """GitHub Actions connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "github_actions"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        resp = self.call("POST",
                         f"/repos/{{owner}}/actions/workflows/{pipeline_id}/dispatches",
                         {"ref": "main", "inputs": params or {}})
        self.require_ok(resp, "github actions dispatch")
        return {"run_id": pipeline_id, "raw": resp.body}


class AzureDevOpsConnector(CICDConnector):
    """Azure DevOps connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "azure_devops"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        resp = self.call("POST",
                         f"/_apis/pipelines/{pipeline_id}/runs?api-version=7.1",
                         {"templateParameters": params or {}})
        body = self.require_ok(resp, "azure devops run trigger")
        return {"run_id": str((body or {}).get("id", "unknown")), "raw": body}


class CircleCIConnector(CICDConnector):
    """CircleCI connector. Implements ENT6-R2, ENT6-R6, ENT6-R7."""

    system_name = "circleci"

    def trigger_pipeline(self, pipeline_id: str, params: dict | None = None) -> dict:
        resp = self.call("POST", f"/api/v2/project/{pipeline_id}/pipeline",
                         {"parameters": params or {}})
        body = self.require_ok(resp, "circleci pipeline trigger")
        return {"run_id": str((body or {}).get("id", "unknown")), "raw": body}
