"""Educational Dijkstra shortest-path implementation (no NetworkX path functions).

Complexity: O((V + E) log V) with a binary heap; O(V^2) with an array scan.
Only *active* links and nodes are relaxed, so failures change the result.
"""
import heapq
import math
from dataclasses import dataclass

from core.network import Network


@dataclass(frozen=True)
class RouteResult:
    found: bool
    path: tuple[str, ...] = ()
    cost_ms: float = math.inf
    reason: str = ""

    @property
    def hops(self) -> int:
        return max(len(self.path) - 1, 0)


def _no_route(reason: str) -> RouteResult:
    return RouteResult(found=False, reason=reason)


def find_shortest_path(network: Network, source: str, destination: str) -> RouteResult:
    """Lowest-latency path from source to destination over active components."""
    for node_id in (source, destination):
        if not network.has_node(node_id):
            return _no_route(f"Unknown node '{node_id}'")
        if not network.is_node_active(node_id):
            return _no_route(f"Node '{node_id}' is down")

    distance: dict[str, float] = {source: 0.0}
    previous: dict[str, str] = {}
    visited: set[str] = set()
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        dist_u, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == destination:
            break
        for v, link in network.usable_neighbors(u):          # relax active links
            candidate = dist_u + link.latency_ms
            if v not in visited and candidate < distance.get(v, math.inf):
                distance[v] = candidate
                previous[v] = u
                heapq.heappush(heap, (candidate, v))

    if destination not in visited:
        return _no_route(f"No active path from {source} to {destination} (network partitioned)")

    path = [destination]
    while path[-1] != source:
        path.append(previous[path[-1]])
    path.reverse()
    return RouteResult(True, tuple(path), distance[destination])
