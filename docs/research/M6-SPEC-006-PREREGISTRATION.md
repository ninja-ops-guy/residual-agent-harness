# M6-SPEC-006 Preregistration — Corrected Runtime Validation

## Why a new experiment
M6-SPEC-005 aborted before producing a candidate because its first Qwen2.5-Coder 7B request hit the Ollama adapter's 300-second timeout with a 4096-token output ceiling. The workflow also observed another server already owning port 11434. M6-SPEC-005 is retained as an infrastructure/configuration failure and is not replaced.

## Harness under test
Exact corrected harness head:
`e7488199ee238f04ef1547338199096389047b2e`

Production remediation is unchanged from M6-SPEC-005:
- prior failed candidate files are bounded repair context;
- repair-context hashes are evidence;
- transport JSON is explicitly distinguished from literal source content;
- Store and Mission Control share the same five-attempt limit;
- acceptance/review/receipt/integration/M4/promotion boundaries remain unchanged.

## Runtime corrections
- model remains `qwen2.5-coder:7b`;
- max output tokens restored to 1600, the setting under which prior 7B calls completed;
- Ollama runs on a dedicated endpoint `127.0.0.1:11437`, avoiding installer/service contention on 11434;
- mission wall-clock budget increased to 1800 s so five bounded attempts plus review can execute;
- workflow timeout is 40 minutes;
- token budget remains 30000;
- batch max passes remains 5.

These changes provide execution capacity; they do not weaken correctness criteria.

## Frozen task
The M6 ImprovementSpec task instruction and deterministic acceptance/negative-path checks remain unchanged from M6-SPEC-001.

## Primary success endpoint
- integrated == 1
- final task state == integrated
- all frozen checks pass
- review approved
- verification receipt present
- generated source exported
- export_error == null

## Secondary evidence
- attempt count and repair-context use
- every retained candidate patch/check receipt
- provider calls and usage
- request bytes and timing
- review and integration events
- final brake/outcome
- generated source and SHA-256
- false acceptance, target zero

## Failure policy
The first model run is authoritative. Any further code/config remediation requires another numbered experiment.
