"""Primary / alternate route selection and route validation."""
from core.network import Network

from .dijkstra import RouteResult, find_shortest_path


class RouteManager:
    def __init__(self, network: Network) -> None:
        self.network = network

    def primary_route(self, source: str, destination: str) -> RouteResult:
        return find_shortest_path(self.network, source, destination)

    def recover(self, source: str, destination: str) -> RouteResult:
        """Recompute the best route on the *current* (possibly damaged) topology."""
        return find_shortest_path(self.network, source, destination)

    def is_route_valid(self, path: tuple[str, ...] | list[str]) -> bool:
        """A route is valid only if every hop is currently usable."""
        if not path or not self.network.is_node_active(path[0]):
            return False
        return all(self.network.is_link_usable(a, b) for a, b in zip(path, path[1:]))

    def alternate_route(self, source: str, destination: str,
                        primary: RouteResult | None = None) -> RouteResult:
        """
        Backup route computed from the topology (never hard-coded):
        1. Remove ALL links of the primary path on a copy and run Dijkstra
           (gives a link-disjoint backup if one exists).
        2. Otherwise remove each primary link one at a time and keep the cheapest
           route found. This is "a route avoiding a failed primary link", not
           guaranteed to be the mathematically second-best path.
        """
        primary = primary or self.primary_route(source, destination)
        if not primary.found or primary.hops == 0:
            return RouteResult(False, reason="No primary route to back up")
        edges = list(zip(primary.path, primary.path[1:]))

        trial = self.network.copy()
        for a, b in edges:
            trial.set_link_state(a, b, False)
        result = find_shortest_path(trial, source, destination)
        if result.found:
            return result

        best = RouteResult(False, reason="No alternate route exists")
        for a, b in edges:
            trial = self.network.copy()
            trial.set_link_state(a, b, False)
            candidate = find_shortest_path(trial, source, destination)
            if candidate.found and (not best.found or candidate.cost_ms < best.cost_ms):
                best = candidate
        return best
