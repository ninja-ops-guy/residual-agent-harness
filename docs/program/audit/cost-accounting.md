# Cost accounting audit and proposed event contract

Audit base: `dec571992a97b4ae80f0310aa32ffd8f542aef8c`. Status: **partial existing
coverage; global per-attempt economics is not yet proven**. This is a design
contract plus limited offline executable checks, not installed instrumentation.

| Entry point | Existing evidence | Remaining gap |
|---|---|---|
| `residual.engine` native Provider | Reserves call before I/O; packet hash, obligation IDs, usage, elapsed time, known cost or null; failed calls retained | No universal cross-adapter attempt/run/receipt linkage; final-usefulness attribution needs explicit joins |
| `residual.study.MeteredProvider` | Durable journal reservation with run/call/role/provider before call; terminal record in finally; missing completion synthesized on replay | Freeze price provenance and link each record to final candidate/cell; local zero inference cost is not zero total ownership cost |
| `ai_providers.Router` | Request UUID, numbered attempts, before/after callbacks, failed/completed status, usage and elapsed time for each actual failover attempt | Callbacks are optional; observation failures swallowed/countable; no built-in dollar tariff, workload/receipt/task topology joins, or durable reservation sink |
| `ProviderExecutionEngine` | Successful provider/model and total tokens in EngineResult | Calls provider directly, collapses input/output usage, and supplies no universal attempt receipt for failures or price breakdown |
| Distributed Station worker | Usage travels with a submitted candidate as `worker_reported`; submission retry reuses idempotency key | Failure proposal does not retain usage; worker report is not provider-authoritative billing; controller restart reconciliation requires separate durable attempt ledger |

Pinned source: [engine call reservation/completion](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/engine.py#L320-L367),
[study reservations and finally records](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/study.py#L178-L229),
[Router per-attempt callbacks](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/ai_providers/router.py#L26-L80),
[provider bridge](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/engines/provider_bridge.py#L66-L100),
[worker usage/failure paths](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/station/worker.py#L41-L81),
[native price unknown semantics](https://github.com/ninja-ops-guy/residual-agent-harness/blob/dec571992a97b4ae80f0310aa32ffd8f542aef8c/residual/providers.py#L47-L95).

Offline probe: actual Router, fake transports, first attempt returns retryable
500 and second succeeds. Both attempts invoke reservation before dispatch and
completion afterward, share request identity and retain attempt numbers 1/2.
Failed usage stays unavailable. These callbacks use an in-memory test sink, so
this demonstrates ordering and failover coverage, not durable crash recovery.
Native Prices returns null for missing/estimated usage and unsupported cache
write pricing. Tests preserve those semantics.

## Proposed attempt evidence contract (not implemented)

| Field group | Required fields/semantics |
|---|---|
| Identity | schema version; run ID; immutable request ID; immutable attempt ID; retry-of/fallback-from; workload cell/task/arm/replicate; plan and contract hashes |
| Routing | task class; topology ID/hash; role; selected engine/provider/requested and actual model revision; endpoint class; local/cloud placement |
| Reservation | dispatch sequence; persisted timestamp; monotonic clock identity; prompt/packet hash; policy/budget decision reference; reserved input/output token caps |
| Terminal | succeeded/failed/cancelled/UNKNOWN; fixed safe error code; provider HTTP class; finish reason; start/end/elapsed; response digest; candidate hash |
| Usage | input/output/cache-read/cache-write/reasoning tokens as supported; nullable values; source (`reported`, `estimated`, `unavailable`); provider request ID when safe; schema explaining inclusions to avoid double-counting reasoning tokens |
| Dollars | currency; tariff snapshot hash/effective time; each billed tier; reported invoice vs tariff-derived amount; known subtotal; null total if any billed dimension is unknown; local compute model separate from inference charges |
| Outcome join | candidate → worker receipt → integration receipt → workload cell; accepted/rejected/pending/UNKNOWN; independent correctness; contributed-to-final-tree vs merely accepted; attribution-rule revision |

Persist a reservation before external I/O and one immutable terminal record.
Identical delivery may replay idempotently; conflicting terminal records must
fail validation. Reservation with no completion after recovery remains an
unknown-cost attempt, never refunded or deleted. A retry has a new attempt ID
and immutable linkage to the original request, even if prompt bytes are equal.
An in-flight completion delivered after cancellation must not silently create
acceptance or refund uncertainty. Replaying metric projection cannot dispatch.

Accounting rules to freeze with the statistical protocol:

1. Include all attempted calls, including failed, rejected, abandoned, and
   verifier/coordinator calls. A provider may bill a failed request.
2. Sum known amounts as `known_cost_subtotal`; disclose unknown-attempt count
   and fraction. Total cost is null if any required component is unresolved.
3. Free-tier or local placement does not imply zero economic cost. Distinguish
   observed invoice, effective tariff, subscription allocation and modeled
   hardware/energy cost. Never infer a price from model quality.
4. Cost per accepted-and-correct result uses a frozen independent correctness
   denominator. Zero successes yields undefined/infinite, not zero dollars.
5. Shared planning, verifier and batching costs need a preregistered allocation
   rule. Keep full totals alongside per-task allocation; never count the shared
   spend twice or drop it because a contribution was rejected.
6. A useful-cheap-worker claim needs a retained contribution to the final tree
   plus the total coordinator/verifier/retry cost. Token reduction alone is not
   proof of dollar savings.

Required future fault checks: pre-dispatch reservation failure prevents I/O;
post-dispatch sink failure leaves an unresolved reservation; provider 429/500,
timeout, stream-prefix failure, cancellation and fallback all retain attempts;
duplicate terminal delivery cannot double bill; totals remain null for missing
usage/tariff; accepted-state joins survive scheduler/Station restarts. The
engineering lane has not implemented or passed that complete install matrix.
