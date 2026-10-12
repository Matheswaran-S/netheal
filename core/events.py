"""Simulation event log. Timestamps are always taken from the SimPy clock."""
from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    SIM_START = "SIM_START"
    SIM_END = "SIM_END"
    PACKET_CREATED = "PACKET_CREATED"
    PACKET_HOP = "PACKET_HOP"
    PACKET_DELIVERED = "PACKET_DELIVERED"
    PACKET_DROPPED = "PACKET_DROPPED"
    PACKET_REROUTED = "PACKET_REROUTED"
    FAILURE = "FAILURE"
    RESTORE = "RESTORE"
    ROUTE_INVALIDATED = "ROUTE_INVALIDATED"
    RECOVERY_SEARCH = "RECOVERY_SEARCH"
    ROUTE_CHANGED = "ROUTE_CHANGED"
    NO_ROUTE = "NO_ROUTE"


@dataclass(frozen=True)
class SimEvent:
    time: float
    event_type: EventType
    message: str
    packet_id: str = ""
    element: str = ""


class EventLog:
    def __init__(self) -> None:
        self.events: list[SimEvent] = []

    def record(self, time: float, event_type: EventType, message: str,
               packet_id: str = "", element: str = "") -> None:
        self.events.append(SimEvent(time, event_type, message, packet_id, element))

    def of_type(self, *types: EventType) -> list[SimEvent]:
        return [e for e in self.events if e.event_type in types]
