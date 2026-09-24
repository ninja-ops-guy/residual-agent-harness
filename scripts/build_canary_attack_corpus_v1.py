#!/usr/bin/env python3
"""Generate the deterministic R4.1 canary attack corpus and review matrix."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "harness_specs/CANARY_ATTACK_CORPUS_V1.json"
MD_OUT = ROOT / "harness_specs/CANARY_ATTACK_CORPUS_V1.md"

HEAD = "8701367db6d3202f24b3eb9f4696b0cadf657985"
TREE = "79bfe6ed1743907065ed44aeb9c460c47527e0c6"
BASE_EVIDENCE = [
    "candidate_identity", "authorization_receipt", "prestate", "network_action_trace",
    "operation_id", "outbox_transitions", "receipt_lookup_and_result",
    "receiver_event_count", "process_service_prestate_and_poststate", "timestamps",
    "operator_interventions", "rollback_evidence", "sha256_manifest",
]
FIELDS = [
    "attack_id", "category", "classification", "preconditions", "initial_durable_state",
    "injected_fault", "expected_network_action_sequence", "expected_outbox_state",
    "expected_receipt_state", "expected_receiver_event_count",
    "expected_process_service_state", "required_evidence", "abort_condition",
    "deterministic_oracle", "severity", "risk_if_oracle_violated", "r4_1_coverage",
    "proposed_future_gate", "research_relevance",
]

def c(attack_id, title, category, fault, sequence, outbox, receipt, count, gate,
      coverage="NONE", classification="R5_CANDIDATE", severity="HIGH",
      initial="one authorized operation is durably PENDING with a stable operation_id",
      process="only the experiment-owned sender may stop; protected services remain byte/state stable",
      abort="any action or state outside the expected oracle; preserve evidence and stop further network actions",
      oracle=None, relevance=None, evidence=()):
    return {
        "attack_id": attack_id,
        "title": title,
        "category": category,
        "classification": classification,
        "preconditions": ["synthetic/disposable receiver and outbox", "exact candidate identity", "bounded authorization scope", "canary execution remains disabled"],
        "initial_durable_state": initial,
        "injected_fault": fault,
        "expected_network_action_sequence": sequence,
        "expected_outbox_state": outbox,
        "expected_receipt_state": receipt,
        "expected_receiver_event_count": count,
        "expected_process_service_state": process,
        "required_evidence": BASE_EVIDENCE + list(evidence),
        "abort_condition": abort,
        "deterministic_oracle": oracle or {"pass_when": "observed sequence, durable states, receipt state, receiver count, and protected-service state exactly equal expected values", "fail_when": "any unexpected POST, duplicate effect, authority widening, protected-service drift, or evidence mismatch", "incomplete_when": "any required evidence is absent, malformed, or hash-invalid"},
        "severity": severity,
        "risk_if_oracle_violated": "PRE_CANARY_BLOCKER" if severity in {"CRITICAL", "HIGH"} else "R5_CANDIDATE",
        "r4_1_coverage": {"status": coverage, "gates": gate, "basis": "No untested case is classified as an R4.1 defect; coverage states only what the completed gate exercised."},
        "proposed_future_gate": f"R5-{category.upper().replace('_','-')}",
        "research_relevance": relevance or "Tests whether receipt-first recovery remains fail-closed under adversarial timing and durable-state faults.",
    }

cases = [
 c("CAA-001","commit succeeds + ACK lost","lost_ack","Remote commit succeeds; ACK is lost before local persistence.",["POST comms -> indeterminate transport result","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"],"ACKED","matching authoritative receipt",1,["R4-G13","R4-G14"],"DIRECT","PROVEN","CRITICAL",initial="PENDING payload not yet known locally to be committed",relevance="Core R4-F02 counterexample and repaired receipt-first invariant."),
 c("CAA-002","receipt lookup unavailable","reconciliation","Receipt service is unreachable on restart.",["GET comms/receipt -> unavailable"],"PENDING","UNKNOWN",[0,1],["R4-G13"],"PARTIAL","OBSERVED","CRITICAL"),
 c("CAA-003","receipt lookup timeout","reconciliation","Receipt GET exceeds the bounded lookup timeout.",["GET comms/receipt -> timeout"],"PENDING","UNKNOWN",[0,1],["R4-G13"],"PARTIAL"),
 c("CAA-004","receipt endpoint 4xx","http_semantics","Receipt GET returns a non-auth 4xx response.",["GET comms/receipt -> 4xx","ABORT"],"PENDING","REJECTED_OR_UNKNOWN",[0,1],["R4-G13"],"NONE"),
 c("CAA-005","receipt endpoint 5xx","http_semantics","Receipt GET returns 5xx.",["GET comms/receipt -> 5xx","ABORT"],"PENDING","UNKNOWN",[0,1],["R4-G13"],"NONE"),
 c("CAA-006","malformed receipt","receipt_integrity","Receipt endpoint returns invalid schema or undecodable JSON.",["GET comms/receipt -> malformed","ABORT"],"PENDING","INVALID",[0,1],["R4-G11","R4-G13"],"PARTIAL","R5_CANDIDATE","CRITICAL"),
 c("CAA-007","wrong operation_id receipt","receipt_integrity","Receipt is validly shaped but binds another operation_id.",["GET comms/receipt -> mismatched operation_id","ABORT"],"PENDING","MISMATCHED",[0,1],["R4-G13"],"NONE","R5_CANDIDATE","CRITICAL"),
 c("CAA-008","wrong project receipt","receipt_integrity","Receipt binds the operation_id in another project.",["GET comms/receipt -> mismatched project","ABORT"],"PENDING","MISMATCHED",[0,1],["R4-G13"],"NONE","R5_CANDIDATE","CRITICAL"),
 c("CAA-009","stale receipt","receipt_integrity","A valid old receipt is replayed outside the authorized operation epoch.",["GET comms/receipt -> stale receipt","ABORT"],"PENDING","STALE",[0,1],["R4-G13"],"NONE","OPEN_HYPOTHESIS","CRITICAL"),
 c("CAA-010","duplicate operation_id / same payload","idempotency","Submit the same operation_id and byte-identical canonical payload twice.",["POST comms","POST comms same key/payload"],"ACKED","same receipt returned twice",1,["R4-G10","R4-G17"],"PARTIAL","OBSERVED","HIGH",initial="first invocation PENDING; second invocation uses identical canonical payload"),
 c("CAA-011","duplicate operation_id / different payload","idempotency","Reuse operation_id with a different canonical payload.",["POST comms payload A","POST comms payload B -> reject"],"ACKED_FOR_A_AND_REJECT_B","receipt binds payload A only",1,["R4-G10","R4-G17"],"PARTIAL","OBSERVED","CRITICAL",initial="payload A is durably associated with operation_id"),
 c("CAA-012","sender crash before POST","crash_boundary","SIGKILL after durable enqueue and before POST.",["PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> absent","POST comms","LOCAL_ACK"],"ACKED","matching new receipt",1,["R4-G10","R4-G14"],"PARTIAL","R5_CANDIDATE","HIGH"),
 c("CAA-013","sender crash during POST","crash_boundary","SIGKILL while POST outcome is indeterminate.",["POST comms -> indeterminate","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> receipt_or_absent","POST only if absent","LOCAL_ACK"],"ACKED_OR_PENDING_FAIL_CLOSED","MATCHING_OR_UNKNOWN",[0,1],["R4-G13","R4-G14"],"PARTIAL","R5_CANDIDATE","CRITICAL"),
 c("CAA-014","sender crash after remote commit","crash_boundary","SIGKILL after server commit but before response completion.",["POST comms -> remote commit","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"],"ACKED","matching authoritative receipt",1,["R4-G13","R4-G14"],"DIRECT","PROVEN","CRITICAL"),
 c("CAA-015","sender crash before local ACK","crash_boundary","SIGKILL after matching receipt response and before local ACK begins.",["GET comms/receipt -> matching receipt","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"],"ACKED","matching authoritative receipt",1,["R4-G13","R4-G14"],"PARTIAL","R5_CANDIDATE","HIGH"),
 c("CAA-016","sender crash during local ACK persistence","crash_boundary","SIGKILL inside the local ACK transaction.",["GET comms/receipt -> matching receipt","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"],"ACKED_AFTER_ATOMIC_RECOVERY","matching authoritative receipt",1,["R4-G10","R4-G14"],"PARTIAL","OPEN_HYPOTHESIS","CRITICAL",evidence=["sqlite_transaction_and_integrity_check"]),
 c("CAA-017","repeated restart","restart","Restart recovery repeatedly after reconciliation completed.",["RESTART","RESTART","RESTART"],"ACKED","matching receipt retained",1,["R4-G13","R4-G14"],"DIRECT","OBSERVED","HIGH",initial="operation is ACKED after prior receipt-first recovery"),
 c("CAA-018","two simultaneous recovery processes","concurrency","Release two recovery processes against one outbox row at the same barrier.",["GET receipt by A","GET receipt by B","at most one POST if absent"],"ACKED_ONCE_OR_PENDING_FAIL_CLOSED","single matching receipt or unknown",[0,1],["R4-G10","R4-G13"],"NONE","OPEN_HYPOTHESIS","CRITICAL",evidence=["process_barrier_trace","sqlite_lock_trace"]),
 c("CAA-019","SQLite lock/contention","storage","Hold a conflicting SQLite lock through the bounded recovery interval.",["GET receipt only if durable row can be read safely","NO_POST_ON_STORAGE_UNCERTAINTY"],"PENDING_OR_EXPLICIT_STORAGE_ERROR","UNCHANGED_OR_UNKNOWN",[0,1],["R4-G10"],"PARTIAL","R5_CANDIDATE","HIGH",evidence=["sqlite_lock_trace"]),
 c("CAA-020","corrupted outbox","storage","Mutate disposable outbox pages/checksum so integrity_check fails.",[],"QUARANTINED_OR_EXPLICIT_ERROR","UNQUERIED",[0,1],["R4-G10"],"NONE","R5_CANDIDATE","CRITICAL",initial="disposable copy contains a PENDING row before controlled corruption",evidence=["before_after_outbox_hash","sqlite_integrity_check"]),
 c("CAA-021","truncated outbox","storage","Truncate a disposable outbox file at a deterministic byte offset.",[],"QUARANTINED_OR_EXPLICIT_ERROR","UNQUERIED",[0,1],["R4-G10"],"NONE","R5_CANDIDATE","CRITICAL",initial="disposable copy contains a PENDING row before controlled truncation",evidence=["before_after_outbox_size_hash","sqlite_integrity_check"]),
 c("CAA-022","stale pending operation","retention","Advance synthetic clock beyond the recovery age bound.",[],"PENDING_STALE_NOT_AUTO_SENT","UNQUERIED",[0,1],["R4-G10","R4-G17"],"PARTIAL","OBSERVED","HIGH",initial="PENDING operation timestamp is older than max_age_s"),
 c("CAA-023","server restart during reconciliation","server_lifecycle","Restart only a disposable receiver between request acceptance and receipt response.",["GET receipt -> disconnect_or_timeout","ABORT_WITHOUT_POST"],"PENDING","UNKNOWN",[0,1],["R4-G13","R4-G15"],"PARTIAL","R5_CANDIDATE","CRITICAL",process="disposable receiver may restart; protected services remain unchanged"),
 c("CAA-024","evidence collector failure","evidence","Inject deterministic collector write/hash failure after protocol completion.",["protocol actions may complete","NO_SUCCESS_DECLARATION"],"ACKED_OR_PENDING_AS_OBSERVED","as observed but not sufficient for PASS",[0,1],["R4-G16"],"PARTIAL","R5_CANDIDATE","CRITICAL",evidence=["collector_failure_record"],oracle={"pass_when":"verifier returns EVIDENCE_INCOMPLETE and never CANARY_PASS","fail_when":"CANARY_PASS is emitted or evidence loss is hidden","incomplete_when":"collector failure itself is not retained by an independent channel"}),
 c("CAA-025","rollback invocation failure","rollback","Make the disposable rollback adapter return nonzero.",[],"PRESERVED","UNCHANGED",[0,1],["R4-G16"],"PARTIAL","R5_CANDIDATE","HIGH",evidence=["rollback_exit_status_and_trace"],oracle={"pass_when":"canary aborts, records rollback failure, and never declares PASS","fail_when":"failure is hidden or authority widens","incomplete_when":"rollback trace is absent"}),
 c("CAA-026","network partition","network","Partition the disposable sender from the receiver for the bounded interval.",["GET receipt -> unavailable","ABORT_WITHOUT_POST"],"PENDING","UNKNOWN",[0,1],["R4-G02","R4-G13"],"PARTIAL","R5_CANDIDATE","CRITICAL",evidence=["partition_rule_and_lifetime"]),
 c("CAA-027","authentication expiration","authorization","Expire transport authentication immediately before receipt lookup.",["GET receipt -> auth failure","ABORT_WITHOUT_POST"],"PENDING","UNKNOWN",[0,1],["R4-G13"],"NONE","R5_CANDIDATE","CRITICAL"),
 c("CAA-028","authorization rejection","authorization","Provide absent, expired, mismatched, or out-of-scope operator authorization.",[],"UNCHANGED","UNQUERIED",0,["R4-G11","R4-G12"],"PARTIAL","R5_CANDIDATE","CRITICAL",initial="no canary durable operation may be created",oracle={"pass_when":"preflight refuses before evidence directory mutation or network action","fail_when":"any POST, receipt GET, credential mutation, or authority widening occurs","incomplete_when":"preflight trace is absent"}),
 c("CAA-029","disk-write failure","storage","Inject ENOSPC/EIO into a disposable outbox or evidence filesystem.",["NO_POST_IF_DURABLE_ENQUEUE_OR_SCOPE_EVIDENCE_FAILED"],"PENDING_IF_PREEXISTING_OTHERWISE_ABSENT","UNQUERIED_OR_UNKNOWN",[0,1],["R4-G10","R4-G16"],"PARTIAL","R5_CANDIDATE","CRITICAL",evidence=["fault_injection_mount_or_shim_trace"]),
]

sigkills = [
 ("CAA-030A","before receipt lookup","PROCESS_EXIT; after restart first network action must be GET receipt",["PROCESS_RESTART","GET comms/receipt"]),
 ("CAA-030B","during receipt lookup","GET becomes indeterminate; restart must issue GET again and no POST first",["GET comms/receipt -> indeterminate","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt"]),
 ("CAA-030C","after receipt hit before ACK","matching receipt is known only in volatile memory",["GET comms/receipt -> matching receipt","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"]),
 ("CAA-030D","during ACK transaction","ACK transaction is interrupted atomically",["GET comms/receipt -> matching receipt","LOCAL_ACK -> interrupted","PROCESS_RESTART","GET comms/receipt -> matching receipt","LOCAL_ACK"]),
 ("CAA-030E","after ACK commit before exit","durable ACK exists before process death",["PROCESS_EXIT","PROCESS_RESTART"]),
 ("CAA-030F","after absent receipt before POST","receipt absence is volatile and cannot authorize later blind POST",["GET comms/receipt -> absent","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt","POST only if still absent"]),
 ("CAA-030G","during conditional POST","POST outcome is indeterminate",["GET comms/receipt -> absent","POST comms -> indeterminate","PROCESS_EXIT","PROCESS_RESTART","GET comms/receipt"]),
]
for attack_id, boundary, fault, sequence in sigkills:
    cases.append(c(attack_id, f"SIGKILL {boundary}", "sigkill_matrix", fault, sequence,
        "ACKED_IF_MATCHING_RECEIPT_ELSE_PENDING_FAIL_CLOSED", "MATCHING_OR_UNKNOWN", [0,1],
        ["R4-G13","R4-G14"], "PARTIAL", "R5_CANDIDATE", "CRITICAL",
        relevance="Systematically locates crash-consistency boundaries in receipt-first recovery."))

corpus = {
    "schema": "residual-canary-attack-corpus/1",
    "corpus_id": "CANARY_ATTACK_CORPUS_V1",
    "candidate": {"head": HEAD, "tree": TREE, "qualification_disposition": "READY_FOR_CANARY", "r4_1_gates": "17/17 PASS"},
    "seal_v2_status": "VALID",
    "canary_authorized": False,
    "allowed_classifications": ["OBSERVED", "PROVEN", "OPEN_HYPOTHESIS", "R5_CANDIDATE"],
    "conditional_blocker_label": "PRE_CANARY_BLOCKER",
    "method": "deterministic synthetic/disposable fixtures only; no live canary execution",
    "cases": cases,
}

assert len(cases) == 36
assert len({x["attack_id"] for x in cases}) == len(cases)
assert all(list(x.keys()) == ["attack_id", "title", *FIELDS[1:]] for x in cases)
assert all(x["classification"] in corpus["allowed_classifications"] for x in cases)
assert all(x["risk_if_oracle_violated"] in {"PRE_CANARY_BLOCKER", "R5_CANDIDATE"} for x in cases)
JSON_OUT.write_text(json.dumps(corpus, sort_keys=True, indent=2) + "\n", encoding="utf-8")

coverage = {}
for item in cases:
    for gate in item["r4_1_coverage"]["gates"]:
        coverage.setdefault(gate, []).append(item["attack_id"])
future = {}
for item in cases:
    future.setdefault(item["proposed_future_gate"], []).append(item["attack_id"])
hypotheses = [x for x in cases if x["classification"] in {"OPEN_HYPOTHESIS", "R5_CANDIDATE"}]

md = [
    "# CANARY_ATTACK_CORPUS_V1", "",
    "Status: **review-only; canary execution is not authorized**.", "",
    "This matrix is generated from `CANARY_ATTACK_CORPUS_V1.json`. Cases use disposable/synthetic fixtures only. `R4.1 coverage` does not classify an untested case as an R4.1 defect. `PRE_CANARY_BLOCKER` is conditional: it applies only if the deterministic oracle is violated by pre-canary validation.", "",
    f"Corpus cases: **{len(cases)}**. Candidate: `{HEAD}` / `{TREE}`.", "",
    "## Human-readable matrix", "",
    "| ID | Scenario | Category | Status | Severity | Expected network actions | Expected durable result | R4.1 coverage | Future gate |", "|---|---|---|---|---|---|---|---|---|",
]
for x in cases:
    seq = " → ".join(x["expected_network_action_sequence"]) or "none"
    gates = ", ".join(x["r4_1_coverage"]["gates"])
    md.append(f"| {x['attack_id']} | {x['title']} | {x['category']} | {x['classification']} | {x['severity']} | {seq} | {x['expected_outbox_state']}; receipt={x['expected_receipt_state']}; receiver={x['expected_receiver_event_count']} | {x['r4_1_coverage']['status']}: {gates} | {x['proposed_future_gate']} |")
md += ["", "## Coverage map against R4 gates", ""]
for gate in [f"R4-G{i:02d}" for i in range(1,18)]:
    ids = coverage.get(gate, [])
    md.append(f"- **{gate}:** {', '.join(ids) if ids else 'No direct attack-corpus mapping; existing gate scope remains unchanged.'}")
md += ["", "## Proposed R5 gates", ""]
for gate, ids in sorted(future.items()):
    md.append(f"- **{gate}:** {', '.join(ids)}")
md += ["", "Each proposed gate must use a frozen fixture, bounded clock/attempt budget, exact network trace, durable-state postconditions, receiver count, protected-service comparison, and hash-complete evidence. Missing evidence yields `EVIDENCE_INCOMPLETE`, not PASS.", "", "## Unresolved hypotheses", ""]
for x in hypotheses:
    md.append(f"- **{x['attack_id']} — {x['title']} ({x['classification']}):** {x['research_relevance']} If its oracle is violated, disposition is `{x['risk_if_oracle_violated']}`; this document does not assert that violation exists.")
md += ["", "## Integrity", "", "The JSON is canonicalized with sorted keys and a trailing newline. Validate by rerunning the generator and requiring a clean diff. Current JSON SHA-256 is inserted below after generation.", ""]
MD_OUT.write_text("\n".join(md), encoding="utf-8")
json_hash = hashlib.sha256(JSON_OUT.read_bytes()).hexdigest()
with MD_OUT.open("a", encoding="utf-8") as handle:
    handle.write(f"- `CANARY_ATTACK_CORPUS_V1.json`: `{json_hash}`\n")
print(json.dumps({"cases": len(cases), "json_sha256": json_hash, "json": str(JSON_OUT), "matrix": str(MD_OUT)}, sort_keys=True))
