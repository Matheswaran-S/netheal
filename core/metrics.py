"""Performance metrics computed only from simulated packets."""
from dataclasses import dataclass

from .packet import Packet, PacketStatus


@dataclass(frozen=True)
class Metrics:
    """
    packets_sent         number of packets generated
    delivery_ratio_pct   delivered / sent * 100
    loss_rate_pct        dropped / sent * 100
    avg_delay_ms         mean (delivery_time - creation_time) of delivered packets
    throughput_pps       delivered packets / simulation duration (packets per second)
    avg_hops             mean links traversed by delivered packets (detours included)
    rerouted_packets     packets whose route was changed while in flight
    recovery_count       successful recoveries (alternate route installed)
    avg_recovery_time_ms mean (route installed - failure time) over recoveries
    """

    packets_sent: int
    packets_delivered: int
    packets_dropped: int
    delivery_ratio_pct: float
    loss_rate_pct: float
    avg_delay_ms: float
    throughput_pps: float
    avg_hops: float
    rerouted_packets: int
    recovery_count: int
    avg_recovery_time_ms: float


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_metrics(packets: list[Packet], duration: float,
                    recovery_times_s: list[float]) -> Metrics:
    sent = len(packets)
    delivered = [p for p in packets if p.status == PacketStatus.DELIVERED]
    dropped = [p for p in packets if p.status == PacketStatus.DROPPED]
    return Metrics(
        packets_sent=sent,
        packets_delivered=len(delivered),
        packets_dropped=len(dropped),
        delivery_ratio_pct=100.0 * len(delivered) / sent if sent else 0.0,
        loss_rate_pct=100.0 * len(dropped) / sent if sent else 0.0,
        avg_delay_ms=1000.0 * _mean([p.delay for p in delivered]),
        throughput_pps=len(delivered) / duration if duration > 0 else 0.0,
        avg_hops=_mean([float(p.hops) for p in delivered]),
        rerouted_packets=sum(1 for p in packets if p.reroute_count > 0),
        recovery_count=len(recovery_times_s),
        avg_recovery_time_ms=1000.0 * _mean(recovery_times_s),
    )


def outcome_timeline(packets: list[Packet], duration: float,
                     buckets: int = 20) -> list[dict]:
    """Group packets by creation time to show how delivery changes over time."""
    if duration <= 0 or buckets <= 0:
        return []
    width = duration / buckets
    rows = [{"start": i * width, "sent": 0, "delivered": 0, "dropped": 0,
             "delays": []} for i in range(buckets)]
    for p in packets:
        row = rows[min(int(p.creation_time / width), buckets - 1)]
        row["sent"] += 1
        if p.status == PacketStatus.DELIVERED:
            row["delivered"] += 1
            row["delays"].append(p.delay)
        elif p.status == PacketStatus.DROPPED:
            row["dropped"] += 1
    for row in rows:
        delays = row.pop("delays")
        row["delivery_ratio_pct"] = 100.0 * row["delivered"] / row["sent"] if row["sent"] else 0.0
        row["avg_delay_ms"] = 1000.0 * _mean(delays) if delays else None
    return rows
