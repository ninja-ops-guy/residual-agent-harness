"""Deterministic fault-injection simulation (DSM-R10).

A FaultSchedule is an explicit, replayable list of faults applied at fixed
send indices. The FaultyChannel applies them deterministically, so every
run of the same (messages, schedule) pair produces byte-identical delivery
traces. Fault classes:

  duplicate — deliver the same message twice
  delay     — hold the message for N subsequent pump cycles
  reorder   — swap the message with the next one
  loss      — drop the message (only recoverable via outbox retransmission)
"""
from __future__ import annotations

from dataclasses import dataclass, field

FAULT_KINDS = ("duplicate", "delay", "reorder", "loss")


@dataclass(frozen=True)
class Fault:
    at: int                 # send index at which the fault fires
    kind: str               # one of FAULT_KINDS
    param: int = 0          # delay cycles for kind="delay"


@dataclass(frozen=True)
class FaultSchedule:
    faults: tuple = field(default_factory=tuple)

    @staticmethod
    def of(*faults):
        return FaultSchedule(tuple(faults))

    def at_index(self, index):
        return [f for f in self.faults if f.at == index]

    def as_list(self):
        return [{"at": f.at, "kind": f.kind, "param": f.param} for f in self.faults]


class FaultyChannel:
    """Applies a FaultSchedule deterministically to an ordered send stream."""

    def __init__(self, schedule=None):
        self.schedule = schedule or FaultSchedule()

    def transmit(self, messages):
        """Return the delivery trace (list of messages in delivery order)."""
        messages = list(messages)
        # reorder faults are applied pairwise on the source stream first
        swap = {f.at: f for f in self.schedule.faults if f.kind == "reorder"}
        for at in sorted(swap):
            if at + 1 < len(messages):
                messages[at], messages[at + 1] = messages[at + 1], messages[at]

        delivered = []
        held = {}   # message index -> cycles remaining
        for index, message in enumerate(messages):
            faults = {f.kind: f for f in self.schedule.at_index(index)}
            # release held messages whose delay expired before this send
            for held_index in sorted(held):
                held[held_index] -= 1
                if held[held_index] <= 0:
                    delivered.append(messages[held_index])
                    del held[held_index]
            if "loss" in faults:
                continue
            if "delay" in faults:
                held[index] = max(1, faults["delay"].param or 1)
                continue
            delivered.append(message)
            if "duplicate" in faults:
                delivered.append(message)
        for held_index in sorted(held):
            delivered.append(messages[held_index])
        return delivered


def simulate(messages, schedule):
    """Deterministic delivery trace for (messages, schedule) — pure function."""
    return FaultyChannel(schedule).transmit(messages)


def lost_indices(messages, schedule):
    """Send indices whose messages never arrive under the schedule."""
    delivered_ids = [id(m) for m in simulate(list(messages), schedule)]
    return [i for i, m in enumerate(messages) if id(m) not in delivered_ids]
