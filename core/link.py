"""Bidirectional network link model."""
from dataclasses import dataclass


@dataclass
class Link:
    """A bidirectional link. Latency (ms) is also the routing cost."""

    a: str
    b: str
    latency_ms: float
    bandwidth_mbps: float = 100.0
    loss_probability: float = 0.0
    active: bool = True

    def __post_init__(self) -> None:
        if self.latency_ms <= 0:
            raise ValueError("Link latency must be positive")
        if not 0.0 <= self.loss_probability <= 1.0:
            raise ValueError("Loss probability must be between 0 and 1")

    @property
    def key(self) -> tuple[str, str]:
        """Order-independent identifier of the link."""
        return tuple(sorted((self.a, self.b)))  # type: ignore[return-value]

    @property
    def label(self) -> str:
        return f"{self.key[0]}-{self.key[1]}"

    @property
    def latency_s(self) -> float:
        return self.latency_ms / 1000.0
