# RESIDUAL Research Catalog

This branch is a versioned research plane, intentionally separate from production code. The production Research Workbench fetches this catalog without checking it out over the user's working tree.

Rules:
- experiment IDs are immutable once used for an authoritative run;
- acceptance contracts are frozen per experiment version;
- failures and inconclusive runs are retained;
- unknown usage is null, never zero;
- catalog commit SHA is bound into every imported run manifest;
- research definitions never grant model/tool authority by themselves.
