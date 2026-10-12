import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from helpers import diamond
from core.packet import DropReason
from core.simulation import ConfigError, Simulation, SimulationConfig
from routing.failure_manager import FailureSpec


def run(**kw):
    base = dict(source="A", destination="F", num_packets=200, duration=10.0, seed=42, link_loss=0.0)
    base.update(kw)
    return Simulation(diamond(), SimulationConfig(**base)).run()


def test_packets_reach_destination_with_correct_delay():
    r = run()
    assert r.metrics.packets_delivered == 200
    assert all(abs(p.delay - 0.035) < 1e-9 for p in r.packets)
    assert r.metrics.avg_hops == 3


def test_zero_loss_and_total_loss_extremes():
    assert run(link_loss=0.0).metrics.packets_dropped == 0
    r = run(link_loss=1.0)
    assert r.metrics.packets_delivered == 0
    assert all(p.drop_reason == DropReason.PACKET_LOSS for p in r.packets)


def test_same_seed_is_reproducible_and_different_seed_differs():
    a, b, c = run(link_loss=0.1), run(link_loss=0.1), run(link_loss=0.1, seed=7)
    assert a.metrics == b.metrics
    assert a.metrics.packets_dropped != c.metrics.packets_dropped or a.metrics != c.metrics


def test_loss_rate_is_statistically_plausible():
    r = run(num_packets=3000, link_loss=0.05)           # 3 hops -> 1-0.95^3 = 14.3%
    assert 11.0 < r.metrics.loss_rate_pct < 17.5


def test_zero_packets_does_not_crash():
    m = run(num_packets=0).metrics
    assert m.packets_sent == 0 and m.delivery_ratio_pct == 0 and m.avg_delay_ms == 0


def test_no_alternate_route_drops_gracefully():
    fails = (FailureSpec(2, "link", ("B", "D")), FailureSpec(4, "link", ("C", "E")))
    r = run(failures=fails)
    assert r.partitioned and r.final_route is None
    late = [p for p in r.packets if p.creation_time > 5]
    assert late and all(p.drop_reason == DropReason.NO_ROUTE for p in late)


def test_failed_destination_drops_everything_after_failure():
    r = run(failures=(FailureSpec(0, "node", ("F",)),))
    assert r.metrics.packets_delivered == 0


def test_invalid_config_is_rejected():
    for bad in (dict(destination="A"), dict(destination="Z"), dict(num_packets=-1),
                dict(duration=0), dict(link_loss=2.0)):
        with pytest.raises(ConfigError):
            run(**bad)


def test_caller_topology_is_not_mutated():
    n = diamond()
    Simulation(n, SimulationConfig("A", "F", 50, 5.0, 1, 0.5,
                                   failures=(FailureSpec(1, "link", ("B", "D")),))).run()
    assert n.link("B", "D").active and n.link("A", "B").loss_probability == 0.0


def test_duplicate_failure_is_logged_not_crashing():
    spec = FailureSpec(1, "link", ("B", "D"))
    r = run(failures=(spec, spec))
    assert any("ignored" in e.message for e in r.events)
