"""Export manifest: provenance and qualification metadata.

Schema conventions follow the program-wide schema-on-branch agreement:
every model artifact carries model hash, tokenizer hash, dataset
manifest hash, training config, code commit, seed, a qualification
receipt, and model-card fields. Until training runs post-freeze, all
values tied to real data/weights are null or fixed placeholders and the
qualification receipt is pinned to `non-production-test-artifact`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..runtime.backend import MANIFEST_SCHEMA_VERSION

QUALIFICATION_TEST_ARTIFACT = "non-production-test-artifact"


def sha256_file(path: str) -> str:
    """Hex SHA-256 of a file's bytes, prefixed per schema convention."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


@dataclass
class QualificationReceipt:
    """Qualification status of the exported artifact."""

    qualification: str = QUALIFICATION_TEST_ARTIFACT
    basis: str = (
        "randomly-initialized tiny config; no training, no benchmark "
        "access, no real weights (pre-SLM-00-freeze)"
    )
    issued_utc: str = ""


@dataclass
class ModelCard:
    """Model-card fields carried on the manifest."""

    name: str = "unnamed"
    description: str = ""
    architecture: str = "NanoLM (decoder-only transformer, scaffold)"
    intended_use: str = "inference-runtime path validation only"
    out_of_scope: str = "any production or benchmark-facing use"
    license: str = "inherited from repository"
    caveats: str = (
        "Random-initialized weights; outputs are meaningless. Artifact "
        "exists only to prove the export -> reload -> serve path."
    )


@dataclass
class ExportManifest:
    """Top-level manifest written next to every exported artifact."""

    backend: str
    artifacts: dict[str, Any]
    model_hash: str
    tokenizer_hash: str | None
    dataset_manifest_hash: str | None
    source_config: dict[str, Any]
    training_config: dict[str, Any] | None
    code_commit: str
    seed: int
    qualification_receipt: QualificationReceipt = field(
        default_factory=QualificationReceipt
    )
    model_card: ModelCard = field(default_factory=ModelCard)
    schema_version: str = MANIFEST_SCHEMA_VERSION
    created_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the canonical JSON-ready dict."""
        return asdict(self)

    def write(self, path: str) -> None:
        """Write manifest JSON with stable key ordering."""
        if not self.created_utc:
            self.created_utc = datetime.now(timezone.utc).isoformat()
        if not self.qualification_receipt.issued_utc:
            self.qualification_receipt.issued_utc = self.created_utc
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")
