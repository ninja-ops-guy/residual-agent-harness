"""Work partitioner: requirement DAG -> parallel work packets.

ORCH-I-R11: Requirements in the same BFS level are independent and MAY be
            scheduled in parallel.
ORCH-I-R12: Two packets in the same level that claim overlapping file
            ownership MUST be merged into one serial packet (deny
            concurrent writers on one path).
ORCH-I-R13: Packet ordering and identifiers MUST be deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .requirements import RequirementGraph


@dataclass(frozen=True)
class WorkPacket:
    packet_id: str
    level: int
    requirement_ids: tuple[str, ...]
    files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "level": self.level,
            "requirement_ids": list(self.requirement_ids),
            "files": list(self.files),
        }


class WorkPartitioner:
    """Groups level-independent requirements into conflict-free packets."""

    def partition(self, graph: RequirementGraph) -> tuple[WorkPacket, ...]:
        packets: list[WorkPacket] = []
        for level, group in enumerate(graph.levels()):
            # greedy deterministic binning by file overlap
            bins: list[list[str]] = []
            bin_files: list[set[str]] = []
            for rid in group:  # group is already sorted
                files = set(graph.get(rid).files)
                placed = False
                for members, owned in zip(bins, bin_files):
                    if owned & files:
                        members.append(rid)
                        owned |= files
                        placed = True
                # ORCH-I-R12: transitive conflicts collapse into the earliest bin
                if placed:
                    continue
                bins.append([rid])
                bin_files.append(set(files))
            # merge bins that became connected through transitive overlap
            merged = True
            while merged:
                merged = False
                for i in range(len(bins)):
                    for j in range(i + 1, len(bins)):
                        if bin_files[i] & bin_files[j]:
                            bins[i] = sorted(bins[i] + bins[j])
                            bin_files[i] |= bin_files[j]
                            del bins[j], bin_files[j]
                            merged = True
                            break
                    if merged:
                        break
            for index, (members, owned) in enumerate(zip(bins, bin_files)):
                members = sorted(members)
                packets.append(WorkPacket(
                    packet_id=f"packet-{level}-{index}",
                    level=level,
                    requirement_ids=tuple(members),
                    files=tuple(sorted(owned)),
                ))
        return tuple(packets)
