"""Offline, synchronous single-caller bridge; no publisher or runtime launcher.

Journal adapters append immutable bytes and retain a separate failure record.
They are trusted storage dependencies, not proof of durability or atomic sealing.
"""
from dataclasses import asdict
from . import qualification_rc_soak as soak
from . import qualification_rc_supervision as sup


SCHEMA = "residual.rc-supervision-journal.v1"
MISSING = (*sup.Supervisor.MISSING_CAPABILITIES, "actual_seal_unverified",
           "journal_durability_unverified", "elapsed_soak_gates_unverified")


def selection_identity(selected, requirements, epoch):
    """Caller constructs/selects this digest before creating or replaying a run."""
    if type(selected) is not soak.SelectedManifest or type(requirements) is not sup.Requirements:
        raise ValueError("external_selection_required")
    sup.text(epoch)
    return {"manifest_sha256": selected.sha256,
            "profile_sha256": selected.facts["profile"]["sha256"],
            "requirements_sha256": soak.digest(sup.canonical(asdict(requirements))),
            "run_id": requirements.run_id, "epoch": epoch}


def _selection(selected, requirements, epoch, expected_sha256):
    sup.sha256(expected_sha256)
    identity = selection_identity(selected, requirements, epoch)
    if soak.digest(sup.canonical(identity)) != expected_sha256:
        raise ValueError("selection_mismatch")
    return identity


def _decode(raw):
    if type(raw) is not bytes:
        raise ValueError("immutable_record_bytes_required")
    return soak.strict_json(raw, limit=2*1024*1024)


def _report(value, requirements, previous):
    sup.fields(value, ("schema", "run_id", "requirements_sha256", "state", "first_failure",
                       "accepted", "accepted_result_count", "rc_qualified", "missing_capabilities"))
    if (value["schema"] != "residual.rc-supervision.observations.v1" or
            value["run_id"] != requirements.run_id or
            value["requirements_sha256"] != soak.digest(sup.canonical(asdict(requirements))) or
            value["rc_qualified"] is not False or value["first_failure"] is not None or
            value["missing_capabilities"] != list(sup.Supervisor.MISSING_CAPABILITIES)):
        raise ValueError("supervision_selection_or_capability_mismatch")
    receipts = value["accepted"]
    if (type(receipts) is not list or type(value["accepted_result_count"]) is not int or
            value["accepted_result_count"] != len(receipts) or
            not len(previous) <= len(receipts) <= min(len(previous)+1, len(requirements.tasks)) or
            sup.canonical(receipts[:len(previous)]) != sup.canonical(previous)):
        raise ValueError("receipt_history_mismatch")
    seen = set()
    observed = requirements.start_at
    for receipt, task in zip(receipts, requirements.tasks):
        sup.fields(receipt, ("task_id", "attempt_id", "nonce", "sequence", "result_id",
                             "payload_sha256", "observed_at"))
        sup.text(receipt["result_id"])
        if receipt["result_id"] in seen:
            raise ValueError("duplicate_result")
        seen.add(receipt["result_id"])
        if (type(receipt["sequence"]) is not int or
                any(receipt[k] != getattr(task, k) for k in ("task_id", "attempt_id", "nonce", "sequence")) or
                receipt["payload_sha256"] != task.expected_payload_sha256):
            raise ValueError("receipt_correlation_mismatch")
        timestamp = sup.moment(receipt["observed_at"])
        if not observed <= timestamp < task.deadline:
            raise ValueError("receipt_time_mismatch")
        observed = timestamp
    expected_state = "observed_complete" if len(receipts) == len(requirements.tasks) else "pending"
    if value["state"] != expected_state:
        raise ValueError("missing_outcomes_or_invalid_state")
    return receipts


def replay(records, *, selected, requirements, epoch, expected_sha256,
           failure=None, require_complete=False):
    """Replay against external selection, never adopt journal-selected authority.

    The caller must provide the storage failure sidecar, if present. Absence of
    that sidecar is not independently authenticated by this offline interface.
    """
    identity = _selection(selected, requirements, epoch, expected_sha256)
    selected.verify_inputs()
    if type(records) not in (tuple, list) or not 1 <= len(records) <= 10000:
        raise ValueError("missing_or_excessive_records")
    accepted = []
    committed = len(records)
    fail = None
    if failure is not None:
        fail = _decode(failure)
        sup.fields(fail, ("schema", "selection", "event", "first_failure", "committed_records"))
        if fail["schema"] != SCHEMA or fail["selection"] != identity or fail["event"] != "failure":
            raise ValueError("invalid_failure_record")
        committed = fail["committed_records"]
        if type(committed) is not int or not 0 <= committed <= len(records) <= committed+1:
            raise ValueError("invalid_failure_commit_boundary")
    committed_accepted = []
    complete = False
    for index, raw in enumerate(records):
        row = _decode(raw)
        sup.fields(row, ("schema", "selection", "sequence", "event", "value"))
        if (row["schema"] != SCHEMA or row["selection"] != identity or
                type(row["sequence"]) is not int or row["sequence"] != index):
            raise ValueError("record_selection_or_sequence_mismatch")
        if index == 0:
            if row["event"] != "start" or sup.canonical(row["value"]) != sup.canonical({"missing_capabilities": list(MISSING), "rc_qualified": False}):
                raise ValueError("invalid_start_record")
        else:
            if row["event"] != "observation" or complete:
                raise ValueError("invalid_event_order")
            sup.fields(row["value"], ("target", "driver", "report"))
            for role in ("target", "driver"):
                process = row["value"][role]
                sup.fields(process, ("host", "pid", "birth_token", "image_sha256"))
                sup.ProcessIdentity(**process)
                if process != asdict(getattr(requirements, role)):
                    raise ValueError("receipt_process_identity_mismatch")
            accepted = _report(row["value"]["report"], requirements, accepted)
            complete = len(accepted) == len(requirements.tasks)
        if index < committed:
            committed_accepted = accepted
    first_failure = None
    if fail is not None:
        first_failure = fail["first_failure"]
        sup.fields(first_failure, ("reason", "supervision"))
        sup.text(first_failure["reason"])
        if first_failure["supervision"] is not None:
            detail = first_failure["supervision"]
            sup.fields(detail, ("reason", "task_index", "last_monotonic"))
            if (detail["reason"] != first_failure["reason"] or type(detail["task_index"]) is not int or
                    not 0 <= detail["task_index"] < len(requirements.tasks)):
                raise ValueError("invalid_failure_detail")
            if detail["last_monotonic"] is not None: sup.moment(detail["last_monotonic"])
        accepted = committed_accepted
    if require_complete and not complete and first_failure is None:
        raise ValueError("missing_outcomes")
    return sup.frozen_copy({"state": "failed" if first_failure else "plan_observed_complete" if complete else "pending",
        "selection": identity, "accepted": accepted, "accepted_result_count": len(accepted),
        "first_failure": first_failure, "missing_capabilities": MISSING,
        "elapsed_soak_satisfied": False, "rc_qualified": False}, limit=2*1024*1024)


class Bridge:
    """Owns one supervisor; only tick() can introduce accepted receipt progress.

    The injected journal must expose append(bytes) and fail(bytes), returning None
    on success and raising on failure. No finalize, publish or seal API is called.
    """
    def __init__(self, *, selected, installed_root, requirements, epoch, expected_sha256,
                 clock, observer, target, driver, journal):
        self._identity = _selection(selected, requirements, epoch, expected_sha256)
        self._selected, self._requirements = selected, requirements
        self._epoch, self._expected = epoch, expected_sha256
        self._binding = soak.Binding.from_selected_manifest(selected, installed_root)
        self._binding.admit(selected.facts["adapter"]["module"], [str(installed_root)])
        self._supervisor = sup.Supervisor(requirements, clock=clock, observer=observer, target=target, driver=driver)
        self._journal = journal
        self._records = []
        self._first_failure = None
        self._failure_recorded = False
        self._busy = False
        self._state = {"state": "pending", "selection": self._identity, "accepted": [],
            "accepted_result_count": 0, "first_failure": None, "missing_capabilities": MISSING,
            "elapsed_soak_satisfied": False, "rc_qualified": False}
        self._append("start", {"missing_capabilities": list(MISSING), "rc_qualified": False})

    def report(self):
        return sup.frozen_copy({**self._state, "state": "failed" if self._first_failure else self._state["state"],
            "first_failure": self._first_failure, "failure_recorded": self._failure_recorded}, limit=2*1024*1024)

    def _fail(self, reason, detail=None):
        if self._first_failure is None:
            self._first_failure = sup.frozen_copy({"reason": reason, "supervision": detail})
            self._supervisor.cancel()
            raw = sup.canonical({"schema": SCHEMA, "selection": self._identity,
                                  "event": "failure", "first_failure": self._first_failure,
                                  "committed_records": len(self._records)})
            try:
                self._failure_recorded = self._journal.fail(raw) is None
            except (Exception, KeyboardInterrupt):
                self._failure_recorded = False
        return self.report()

    def cancel(self):
        return self._fail("cancelled_by_caller")

    def interrupt(self):
        return self._fail("observer_interrupted")

    def _append(self, event, value):
        raw = sup.canonical({"schema": SCHEMA, "selection": self._identity,
                            "sequence": len(self._records), "event": event, "value": value})
        try:
            if self._journal.append(raw) is not None:
                raise ValueError("invalid_journal_acknowledgment")
        except KeyboardInterrupt:
            self._fail("observer_interrupted")
            return False
        except Exception:
            self._fail("journal_write_failed")
            return False
        if self._first_failure is not None:
            return False
        self._records.append(raw)
        return True

    def tick(self):
        if self._first_failure:
            return self.report()
        if self._state["state"] == "plan_observed_complete":
            return self.finish()
        if self._busy:
            return self._fail("reentrant_tick")
        self._busy = True
        try:
            self._binding.validate_installation()
            report = self._supervisor.tick()
            if self._first_failure: return self.report()
            if report["first_failure"] is not None:
                return self._fail(report["first_failure"]["reason"], report["first_failure"])
            # Poll callbacks can change installed bytes after the entry check.
            # Validate again before any returned receipt reaches the journal.
            self._binding.validate_installation()
            _report(report, self._requirements, self._state["accepted"])
            value = {"target": asdict(self._requirements.target), "driver": asdict(self._requirements.driver),
                     "report": report}
            prospective = sup.canonical({"schema": SCHEMA, "selection": self._identity,
                "sequence": len(self._records), "event": "observation", "value": value})
            state = replay([*self._records, prospective], selected=self._selected, requirements=self._requirements,
                           epoch=self._epoch, expected_sha256=self._expected)
            if not self._append("observation", value): return self.report()
            self._state = state
            return self.report()
        except KeyboardInterrupt:
            return self._fail("observer_interrupted")
        except Exception:
            return self._fail("invalid_admission_or_observation")
        finally:
            self._busy = False

    def finish(self):
        if self._first_failure:
            return self.report()
        if self._state["state"] != "plan_observed_complete":
            return self._fail("missing_outcomes")
        try:
            self._binding.validate_installation()
        except KeyboardInterrupt:
            return self._fail("observer_interrupted")
        except Exception:
            return self._fail("invalid_admission_or_observation")
        return self.report()
