import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from helpers import diamond
from core.experiment import run_comparison, run_simulation
from core.events import EventType
from core.simulation import SimulationConfig
from routing.failure_manager import FailureManager, FailureSpec
from routing.route_manager import RouteManager

FAIL_BD = (FailureSpec(5, "link", ("B", "D")),)


def test_alternate_route_is_computed_and_link_disjoint():
    rm = RouteManager(diamond())
    primary = rm.primary_route("A", "F")
    alt = rm.alternate_route("A", "F", primary)
    assert alt.found and alt.path == ("A", "C", "E", "F")
    assert not set(zip(primary.path, primary.path[1:])) & set(zip(alt.path, alt.path[1:]))


def test_no_alternate_when_primary_is_a_bridge():
    n = diamond()
    FailureManager(n).apply(FailureSpec(0, "link", ("C", "E")))
    FailureManager(n).apply(FailureSpec(0, "link", ("E", "F")))
    assert not RouteManager(n).alternate_route("A", "F").found


def test_route_validity_detects_failure():
    n = diamond()
    rm = RouteManager(n)
    path = rm.primary_route("A", "F").path
    assert rm.is_route_valid(path)
    FailureManager(n).apply(FailureSpec(0, "link", ("B", "D")))
    assert not rm.is_route_valid(path)


def test_recovery_changes_route_and_records_recovery_time():
    cfg = SimulationConfig("A", "F", 500, 10.0, 1, 0.0, True, FAIL_BD)
    r = run_simulation(diamond(), cfg)
    assert r.final_route == ("A", "C", "E", "F")
    assert r.metrics.recovery_count == 1
    assert abs(r.metrics.avg_recovery_time_ms - 25.0) < 1e-6      # 20 ms detect + 5 ms compute
    types = [e.event_type for e in r.events]
    assert types.index(EventType.FAILURE) < types.index(EventType.ROUTE_INVALIDATED) \
        < types.index(EventType.RECOVERY_SEARCH) < types.index(EventType.ROUTE_CHANGED)


def test_event_timestamps_come_from_clock():
    cfg = SimulationConfig("A", "F", 100, 10.0, 1, 0.0, True, FAIL_BD)
    r = run_simulation(diamond(), cfg)
    failure = next(e for e in r.events if e.event_type == EventType.FAILURE)
    changed = next(e for e in r.events if e.event_type == EventType.ROUTE_CHANGED)
    assert failure.time == 5.0 and abs(changed.time - 5.025) < 1e-9


def test_in_flight_packets_are_rerouted_with_dense_traffic():
    cfg = SimulationConfig("A", "F", 5000, 10.0, 1, 0.0, True, FAIL_BD)
    r = run_simulation(diamond(), cfg)
    rerouted = [p for p in r.packets if p.reroute_count > 0]
    assert rerouted and r.metrics.rerouted_packets == len(rerouted)
    delivered = [p for p in rerouted if p.delivery_time is not None]
    assert delivered and all("D" not in p.path_taken[p.path_taken.index("B"):] for p in delivered)


def test_recovery_beats_no_recovery():
    cfg = SimulationConfig("A", "F", 1000, 10.0, 7, 0.0, True, FAIL_BD)
    c = run_comparison(diamond(), cfg)
    assert c.with_recovery.metrics.delivery_ratio_pct > 90
    assert c.without_recovery.metrics.delivery_ratio_pct < 60
    assert c.without_recovery.metrics.recovery_count == 0


def test_restore_returns_to_primary_route():
    spec = FailureSpec(3, "link", ("B", "D"), restore_time=6)
    r = run_simulation(diamond(), SimulationConfig("A", "F", 200, 10.0, 1, 0.0, True, (spec,)))
    assert r.final_route == ("A", "B", "D", "F")
