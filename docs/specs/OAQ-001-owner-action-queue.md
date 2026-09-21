# Owner Action Queue — OAQ-001

Status: implementation candidate

## Purpose

Compress machine-verified state into the smallest possible set of human authority decisions without weakening existing gates.

The queue is **not** an approval engine. It cannot create, infer, or simulate human authorization.

## Invariants

1. Human authorization is explicit and fail-closed.
2. Maintainer approval is bound to the exact 40-character PR head SHA.
3. A stale head invalidates the corresponding approval action.
4. Research freezes are a distinct authority class from PR maintainer attestations.
5. Status summaries, model conclusions, automated reviews, and red-team PASS results never equal human approval.
6. Only blocking actions should interrupt the owner by default; non-blocking actions remain visible but can be deferred.
7. Every action carries evidence sufficient for a binary owner decision without reconstructing the entire swarm transcript.

## Action kinds

- `maintainer_attestation`
- `research_freeze`
- `physical_intervention`
- `credential`
- `scope_decision`
- `exception`

## Producer/consumer boundary

Station, research tooling, CI, and future Research Conductor components may **produce** queue records.

`residual owner-queue <queue.json>` validates and renders them.

The renderer refuses malformed authority records rather than repairing them.

## SLM-00 example

The current SLM-00 human freeze package should be represented as a `research_freeze` action whose COPY field is exactly:

`freeze SLM-00`

Only the owner issuing that explicit command permits creation of `SLM-00-FREEZE-RECEIPT.md`. G/G2 PASS states alone do not authorize it.

## Next extensions

- GitHub/Station producer that emits maintainer-attestation records only when all non-human gates are green.
- Research Conductor producer for freeze/replication/contradiction gates.
- owner-action event receipt so elapsed human-block time can be measured.
- dashboard/Command Station surface with blocking-only default view.
