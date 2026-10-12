"""Failure injection: scheduled failure specs and state changes with validation."""
from dataclasses import dataclass

from core.network import Network, NetworkError


class FailureError(NetworkError):
    """Invalid failure request (already failed, unknown target, ...)."""


@dataclass(frozen=True)
class FailureSpec:
    """A failure scheduled at `time` seconds; optionally restored later.

    kind 'link' -> target = (a, b);  kind 'node' -> target = (node,).
    """

    time: float
    kind: str
    target: tuple[str, ...]
    restore_time: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in ("link", "node"):
            raise FailureError("kind must be 'link' or 'node'")
        if len(self.target) != (2 if self.kind == "link" else 1):
            raise FailureError(f"Invalid target {self.target} for a {self.kind} failure")
        if self.time < 0:
            raise FailureError("Failure time cannot be negative")
        if self.restore_time is not None and self.restore_time <= self.time:
            raise FailureError("Restore time must be after the failure time")

    @property
    def label(self) -> str:
        if self.kind == "link":
            return "-".join(sorted(self.target))
        return self.target[0]


class FailureManager:
    def __init__(self, network: Network) -> None:
        self.network = network

    def apply(self, spec: FailureSpec) -> str:
        """Fail the target; returns its label."""
        if spec.kind == "link":
            link = self._link(spec)
            if not link.active:
                raise FailureError(f"Link {spec.label} has already failed")
            link.active = False
        else:
            node = self.network.node(spec.target[0])
            if not node.active:
                raise FailureError(f"Node {spec.label} has already failed")
            node.active = False
        return spec.label

    def restore(self, spec: FailureSpec) -> str:
        if spec.kind == "link":
            self._link(spec).active = True
        else:
            self.network.node(spec.target[0]).active = True
        return spec.label

    def restore_all(self) -> None:
        for node in self.network.nodes:
            node.active = True
        for link in self.network.links:
            link.active = True

    def failed_links(self) -> list[str]:
        return [link.label for link in self.network.links if not link.active]

    def failed_nodes(self) -> list[str]:
        return [n.node_id for n in self.network.nodes if not n.active]

    def _link(self, spec: FailureSpec):
        try:
            return self.network.link(*spec.target)
        except NetworkError as exc:
            raise FailureError(str(exc)) from exc
