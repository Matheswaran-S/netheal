# Algorithms

## Dijkstra (`routing/dijkstra.py`)
- **Input:** network, source, destination. **Output:** `RouteResult(found, path, cost_ms, reason)`.
- **Steps:** set dist[source]=0; repeatedly pop the unvisited node with the smallest distance (min-heap);
  relax every *usable* neighbour (link up, both nodes up); stop when the destination is popped; rebuild the
  path from the `previous` map. Unknown/failed endpoints and partitions return `found=False` with a reason.
- **Complexity:** O((V+E) log V) with a heap (O(V²+E) with an array scan).
- **Why suitable:** link costs are non-negative latencies; Dijkstra gives the minimum-latency path and
  mirrors how link-state protocols (OSPF) compute routes.

## Failure detection (`Simulation._handle_failure`)
After a component fails, `RouteManager.is_route_valid(active_route)` checks every hop. If any hop is unusable
the route is invalidated. A failure off the active route changes nothing.

## Route recovery (`Simulation._recover`)
invalidate -> wait `detection_delay` -> log search -> wait `compute_delay` -> Dijkstra on the surviving topology ->
install route (or declare the network partitioned). Recovery time = installation time - failure time.

## Primary and alternate routes (`RouteManager.alternate_route`)
Remove all primary links on a copy and run Dijkstra (link-disjoint backup). If none exists, remove each primary
link individually and keep the cheapest result. The graph is copied, so live state is never touched.

## Packet simulation
Packet i is created at i * (duration / packets). Each hop: check the next link is usable (else reroute/drop),
draw loss, `timeout(latency)`, re-check the link and node (failure while on the wire drops the packet), advance.
Drop reasons: PACKET_LOSS, LINK_DOWN, NODE_DOWN, NO_ROUTE. A packet that finds a dead hop *after* convergence is
rerouted by Dijkstra from its current node; *before* convergence it is dropped (routing blackout).

## Packet loss
`random.Random(seed).random() < link.loss_probability` per link traversal, so a seed reproduces results exactly.

## Metrics
See `core/metrics.py`. Throughput = delivered packets / configured duration (packets per second).
