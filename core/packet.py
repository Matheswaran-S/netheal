"""Packet model used by the simulation."""
from dataclasses import dataclass, field
from enum import Enum


class PacketStatus(str, Enum):
    CREATED = "CREATED"
    TRANSMITTING = "TRANSMITTING"
    DELIVERED = "DELIVERED"
    DROPPED = "DROPPED"
    REROUTED = "REROUTED"


class DropReason(str, Enum):
    PACKET_LOSS = "PACKET_LOSS"
    LINK_DOWN = "LINK_DOWN"
    NODE_DOWN = "NODE_DOWN"
    NO_ROUTE = "NO_ROUTE"


@dataclass
class Packet:
    """A packet travelling along `route`; `route_index` is its current position."""

    packet_id: str
    source: str
    destination: str
    creation_time: float
    route: list[str] = field(default_factory=list)
    route_index: int = 0
    status: PacketStatus = PacketStatus.CREATED
    delivery_time: float | None = None
    hops: int = 0
    reroute_count: int = 0
    drop_reason: DropReason | None = None
    path_taken: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.path_taken:
            self.path_taken = [self.source]

    @property
    def current_node(self) -> str:
        return self.path_taken[-1]

    @property
    def next_hop(self) -> str | None:
        if self.route_index + 1 < len(self.route):
            return self.route[self.route_index + 1]
        return None

    @property
    def delay(self) -> float | None:
        if self.delivery_time is None:
            return None
        return self.delivery_time - self.creation_time

    def advance(self) -> None:
        """Move one hop forward along the route."""
        self.route_index += 1
        self.hops += 1
        self.path_taken.append(self.route[self.route_index])

    def reroute(self, new_path: list[str]) -> None:
        """Replace the remainder of the route; new_path starts at current node."""
        self.route = self.route[: self.route_index] + list(new_path)
        self.reroute_count += 1
        self.status = PacketStatus.REROUTED

    def mark_delivered(self, time: float) -> None:
        self.status = PacketStatus.DELIVERED
        self.delivery_time = time

    def mark_dropped(self, reason: DropReason) -> None:
        self.status = PacketStatus.DROPPED
        self.drop_reason = reason
