"""Before/after comparison: same topology, seed and failures, recovery OFF vs ON."""
from dataclasses import dataclass, replace

from .network import Network
from .simulation import Simulation, SimulationConfig, SimulationResult


@dataclass
class ComparisonResult:
    without_recovery: SimulationResult
    with_recovery: SimulationResult


def run_simulation(network: Network, config: SimulationConfig) -> SimulationResult:
    return Simulation(network, config).run()


def run_comparison(network: Network, config: SimulationConfig) -> ComparisonResult:
    return ComparisonResult(
        without_recovery=run_simulation(network, replace(config, recovery_enabled=False)),
        with_recovery=run_simulation(network, replace(config, recovery_enabled=True)),
    )
