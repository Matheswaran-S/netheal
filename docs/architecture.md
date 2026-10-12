# Architecture

```
Streamlit UI (app.py, visualization/dashboard.py)
      | SimulationConfig                ^ SimulationResult / ComparisonResult
Experiment runner (core/experiment.py)   -> runs the engine twice (recovery OFF / ON)
      |
Simulation (core/simulation.py, SimPy environment)
   |-- Network model (core/network.py on NetworkX; Node, Link, Packet)
   |-- Routing engine (routing/dijkstra.py, route_manager.py)
   |-- Failure manager (routing/failure_manager.py)
   |-- Metrics engine (core/metrics.py) and Event log (core/events.py)
      |
Visualization (visualization/topology.py, charts.py) + CSV export (utils/helpers.py)
```

## Data flow
1. The UI builds a `SimulationConfig` (topology preset, source/destination, packets, loss, seed, scheduled `FailureSpec`s).
2. `run_comparison` copies the network and runs the `Simulation` twice with the same seed/failures.
3. During a run, SimPy processes generate packets, move them hop by hop (delay = link latency, loss = seeded RNG),
   apply failures at their scheduled times and run recovery.
4. `compute_metrics` derives all numbers from the packet list; the event log keeps SimPy-clock timestamps.
5. The UI only renders `SimulationResult`s; it contains no routing or simulation logic.

## Interfaces (stable contracts for three developers)
- `find_shortest_path(network, src, dst) -> RouteResult`
- `RouteManager.primary_route / alternate_route / recover / is_route_valid`
- `FailureManager.apply / restore`, `FailureSpec(time, kind, target, restore_time)`
- `Simulation(network, config).run() -> SimulationResult`
- `run_comparison(network, config) -> ComparisonResult`
