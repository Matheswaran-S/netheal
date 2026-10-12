import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from core.metrics import compute_metrics, outcome_timeline
from core.packet import DropReason, Packet


def pk(i, created, delivered=None, hops=3, drop=None, reroutes=0):
    p = Packet(f"P{i}", "A", "F", created)
    p.hops, p.reroute_count = hops, reroutes
    if delivered is not None:
        p.mark_delivered(delivered)
    if drop:
        p.mark_dropped(drop)
    return p


def sample():
    return [pk(1, 0.0, 0.040), pk(2, 1.0, 1.020, hops=2, reroutes=1),
            pk(3, 2.0, drop=DropReason.LINK_DOWN), pk(4, 3.0, drop=DropReason.PACKET_LOSS)]


def test_formulas():
    m = compute_metrics(sample(), duration=10.0, recovery_times_s=[0.02, 0.04])
    assert (m.packets_sent, m.packets_delivered, m.packets_dropped) == (4, 2, 2)
    assert m.delivery_ratio_pct == 50 and m.loss_rate_pct == 50
    assert m.avg_delay_ms == pytest.approx(30.0)
    assert m.throughput_pps == pytest.approx(0.2)
    assert m.avg_hops == 2.5 and m.rerouted_packets == 1
    assert m.recovery_count == 2 and m.avg_recovery_time_ms == pytest.approx(30.0)


def test_empty_inputs_are_safe():
    m = compute_metrics([], 10.0, [])
    assert m.delivery_ratio_pct == 0 and m.avg_delay_ms == 0 and m.avg_recovery_time_ms == 0
    assert compute_metrics(sample(), 0.0, []).throughput_pps == 0


def test_timeline_buckets_outcomes():
    rows = outcome_timeline(sample(), duration=4.0, buckets=2)
    assert [r["sent"] for r in rows] == [2, 2]
    assert rows[0]["delivery_ratio_pct"] == 100 and rows[1]["delivery_ratio_pct"] == 0
    assert rows[1]["avg_delay_ms"] is None
