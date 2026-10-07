"""Active-active multi-region station registry with automatic takeover.

Implements ENT4-R1: multiple station instances across regions operate
simultaneously (active-active), and if one instance fails another takes
over automatically. Failure detection is driven by heartbeats against an
injected clock so takeover is deterministic and testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ContractError
from .clock import Clock
from .events import EventJournal, TAKEOVER_EVENT

DEFAULT_HEARTBEAT_TIMEOUT = 15.0


@dataclass
class Station:
    """A station instance in a region. Implements ENT4-R1."""

    station_id: str
    region: str
    workers: tuple[str, ...]
    alive: bool = True
    active: bool = True
    last_heartbeat: float = 0.0
    reachable: bool = True

    def __post_init__(self):
        if not isinstance(self.station_id, str) or not self.station_id.strip():
            raise ContractError("station_id is required")
        if not isinstance(self.region, str) or not self.region.strip():
            raise ContractError("region is required")
        if not isinstance(self.workers, tuple) or any(
                not isinstance(w, str) or not w.strip() for w in self.workers):
            raise ContractError("workers must be a tuple of names")
        if not self.workers:
            raise ContractError("a station needs at least one worker")

    def fail(self) -> None:
        self.alive = False
        self.active = False

    def restart(self, at: float) -> None:
        self.alive = True
        self.active = True
        self.last_heartbeat = float(at)


@dataclass(frozen=True)
class Takeover:
    """Record of an automatic takeover. Implements ENT4-R1 and ENT4-R4."""

    failed_station: str
    successor_station: str
    detected_at: float
    completed_at: float

    @property
    def rto_seconds(self) -> float:
        """Measured failover time. Implements ENT4-R4 (RTO < 60s)."""
        return self.completed_at - self.detected_at


@dataclass
class StationRegistry:
    """Active-active registry across regions.

    Implements ENT4-R1: every registered, alive station is active and
    serving; ``tick`` detects dead stations (missed heartbeats) and
    automatically promotes a successor without human intervention.
    Takeovers are observed and receipted per ENT4-R8.
    """

    clock: Clock
    journal: EventJournal
    heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT
    stations: dict[str, Station] = field(default_factory=dict)
    takeovers: list[Takeover] = field(default_factory=list)

    def register(self, station: Station) -> None:
        if station.station_id in self.stations:
            raise ContractError("duplicate station registration")
        station.last_heartbeat = self.clock.now()
        self.stations[station.station_id] = station

    def heartbeat(self, station_id: str) -> None:
        station = self._get(station_id)
        if not station.alive:
            raise ContractError("dead stations cannot heartbeat")
        station.last_heartbeat = self.clock.now()

    def active_stations(self) -> list[Station]:
        """All simultaneously operating instances. Implements ENT4-R1."""
        return [s for s in self.stations.values() if s.active]

    def regions(self) -> set[str]:
        return {s.region for s in self.active_stations()}

    def tick(self) -> list[Takeover]:
        """Detect failures and take over automatically. Implements ENT4-R1."""
        now = self.clock.now()
        new_takeovers: list[Takeover] = []
        for station in sorted(self.stations.values(), key=lambda s: s.station_id):
            if station.alive and now - station.last_heartbeat > self.heartbeat_timeout:
                station.fail()
                takeover = self._take_over(station, detected_at=now)
                if takeover is not None:
                    new_takeovers.append(takeover)
        return new_takeovers

    def _take_over(self, failed: Station, detected_at: float) -> Takeover | None:
        successor = self._successor_for(failed)
        completed = self.clock.now()
        takeover = Takeover(
            failed_station=failed.station_id,
            successor_station=successor.station_id,
            detected_at=detected_at,
            completed_at=completed,
        )
        self.takeovers.append(takeover)
        self.journal.record(TAKEOVER_EVENT, {
            "failed_station": failed.station_id,
            "successor_station": successor.station_id,
            "region": failed.region,
            "rto_seconds": takeover.rto_seconds,
        })
        return takeover

    def _successor_for(self, failed: Station) -> Station:
        """Pick an active successor, preferring the same region. Implements ENT4-R1."""
        candidates = [s for s in self.active_stations() if s.station_id != failed.station_id]
        if not candidates:
            raise ContractError("no active station available for takeover")
        same_region = [s for s in candidates if s.region == failed.region]
        pool = same_region or candidates
        return sorted(pool, key=lambda s: s.station_id)[0]

    def is_reachable(self, station_id: str) -> bool:
        """Whether the cluster is reachable from a station. Implements ENT4-R7."""
        station = self._get(station_id)
        return station.reachable and station.alive

    def _get(self, station_id: str) -> Station:
        try:
            return self.stations[station_id]
        except KeyError:
            raise ContractError(f"unknown station: {station_id!r}") from None
