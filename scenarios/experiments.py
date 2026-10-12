"""Predefined experiment scenarios used by the GUI and tests."""
from dataclasses import dataclass

from core.simulation import SimulationConfig
from routing.failure_manager import FailureSpec


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    topology: str
    source: str
    destination: str
    link_loss: float = 0.01
    failures: tuple[FailureSpec, ...] = ()

    def to_config(self, num_packets: int = 1000, duration: float = 20.0,
                  seed: int = 42) -> SimulationConfig:
        return SimulationConfig(self.source, self.destination, num_packets, duration,
                                seed, self.link_loss, True, self.failures)


SCENARIOS: dict[str, Scenario] = {s.name: s for s in [
    Scenario("1. Normal network", "No failures: baseline performance.",
             "Small Demo", "A", "F"),
    Scenario("2. Single link failure", "Primary link B-D fails at t=10s; traffic should reroute via C-E.",
             "Small Demo", "A", "F", failures=(FailureSpec(10, "link", ("B", "D")),)),
    Scenario("3. Node failure", "Router D goes down at t=10s; fault tolerance via the other branch.",
             "Small Demo", "A", "F", failures=(FailureSpec(10, "node", ("D",)),)),
    Scenario("4. High packet loss", "10% loss on every link, no failures: reliability study.",
             "Small Demo", "A", "F", link_loss=0.10),
    Scenario("5. Multiple failures", "Mesh: two links of the active route fail at t=7s and t=14s.",
             "Mesh", "A", "I",
             failures=(FailureSpec(7, "link", ("B", "E")), FailureSpec(14, "link", ("E", "I")))),
    Scenario("6. No alternate path", "B-D fails at t=7s, then C-E at t=14s: network is partitioned.",
             "Small Demo", "A", "F",
             failures=(FailureSpec(7, "link", ("B", "D")), FailureSpec(14, "link", ("C", "E")))),
]}
