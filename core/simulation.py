"""SimPy discrete-event simulation of packets, failures and route recovery.

Failures are *scheduled events* on the simulation clock. Self-healing model:
  failure -> (detection_delay) -> route search -> (compute_delay) -> new route.
During that blackout window packets that hit the dead component are dropped,
exactly like a real network before routing reconverges.
"""
import random
from dataclasses import dataclass, field

import simpy

from routing.dijkstra import RouteResult
from routing.failure_manager import FailureError, FailureManager, FailureSpec
from routing.route_manager import RouteManager

from .events import EventLog, EventType, SimEvent
from .metrics import Metrics, compute_metrics
from .network import Network, NetworkError
from .packet import DropReason, Packet, PacketStatus


class ConfigError(ValueError):
    """Invalid simulation configuration."""


@dataclass
class SimulationConfig:
    source: str
    destination: str
    num_packets: int = 1000
    duration: float = 20.0             # seconds over which packets are generated
    seed: int = 42
    link_loss: float | None = None     # overrides every link's loss probability
    recovery_enabled: bool = True      # False = static route, never recomputed
    failures: tuple[FailureSpec, ...] = ()
    detection_delay: float = 0.02      # modelled failure-detection time (s)
    compute_delay: float = 0.005      # modelled route-computation time (s)
    log_hops: bool = False

    def validate(self, network: Network) -> None:
        if self.source == self.destination:
            raise ConfigError("Source and destination must be different")
        for node_id in (self.source, self.destination):
            if not network.has_node(node_id):
                raise ConfigError(f"Unknown node '{node_id}'")
        if self.num_packets < 0:
            raise ConfigError("Packet count cannot be negative")
        if self.duration <= 0:
            raise ConfigError("Duration must be positive")
        if self.link_loss is not None and not 0.0 <= self.link_loss <= 1.0:
            raise ConfigError("Packet loss must be between 0 and 1")
        if self.detection_delay < 0 or self.compute_delay < 0:
            raise ConfigError("Delays cannot be negative")


@dataclass
class RouteChange:
    time: float
    path: tuple[str, ...]
    cost_ms: float


@dataclass
class SimulationResult:
    config: SimulationConfig
    metrics: Metrics
    events: list[SimEvent]
    packets: list[Packet]
    initial_route: RouteResult
    alternate_route: RouteResult
    final_route: tuple[str, ...] | None
    route_history: list[RouteChange]
    recovery_times: list[float]
    final_network: Network = field(repr=False, default=None)  # type: ignore[assignment]

    @property
    def partitioned(self) -> bool:
        return self.final_route is None


class Simulation:
    def __init__(self, network: Network, config: SimulationConfig) -> None:
        config.validate(network)
        self.config = config
        self.network = network.copy()            # caller's topology is never mutated
        if config.link_loss is not None:
            self.network.set_all_loss(config.link_loss)
        self.env = simpy.Environment()
        self.rng = random.Random(config.seed)
        self.log = EventLog()
        self.failures = FailureManager(self.network)
        self.routes = RouteManager(self.network)
        self.packets: list[Packet] = []
        self.active_route: tuple[str, ...] | None = None
        self.converged = True                    # False while routing is reconverging
        self.route_history: list[RouteChange] = []
        self.recovery_times: list[float] = []

    # ---- public ----------------------------------------------------------
    def run(self) -> SimulationResult:
        cfg = self.config
        initial = self.routes.primary_route(cfg.source, cfg.destination)
        alternate = self.routes.alternate_route(cfg.source, cfg.destination, initial)
        if initial.found:
            self._install_route(initial.path, initial.cost_ms, announce=False)
        self._log(EventType.SIM_START, f"Simulation started ({'self-healing ON' if cfg.recovery_enabled else 'self-healing OFF'}); "
                  f"route {' > '.join(initial.path) if initial.found else 'none'}")

        self.env.process(self._generate_packets())
        for spec in cfg.failures:
            self.env.process(self._failure_process(spec))
        self.env.run()
        self._log(EventType.SIM_END, "Simulation finished")

        return SimulationResult(
            config=cfg,
            metrics=compute_metrics(self.packets, cfg.duration, self.recovery_times),
            events=self.log.events, packets=self.packets,
            initial_route=initial, alternate_route=alternate,
            final_route=self.active_route, route_history=self.route_history,
            recovery_times=self.recovery_times, final_network=self.network,
        )

    # ---- processes -------------------------------------------------------
    def _generate_packets(self):
        cfg = self.config
        interval = cfg.duration / cfg.num_packets if cfg.num_packets else 0.0
        for i in range(cfg.num_packets):
            packet = Packet(f"P{i + 1:04d}", cfg.source, cfg.destination, self.env.now)
            self.packets.append(packet)
            self._log(EventType.PACKET_CREATED, f"Packet {packet.packet_id} created", packet.packet_id)
            self.env.process(self._transmit(packet))
            yield self.env.timeout(interval)

    def _failure_process(self, spec: FailureSpec):
        yield self.env.timeout(spec.time)
        try:
            label = self.failures.apply(spec)
        except (FailureError, NetworkError) as exc:
            self._log(EventType.FAILURE, f"Failure ignored: {exc}")
            return
        self._log(EventType.FAILURE, f"{spec.kind.capitalize()} {label} failed", element=label)
        self._handle_failure()
        if spec.restore_time is not None:
            yield self.env.timeout(spec.restore_time - spec.time)
            self.failures.restore(spec)
            self._log(EventType.RESTORE, f"{spec.kind.capitalize()} {label} restored", element=label)
            self._handle_restore()

    def _recover(self, failed_at: float):
        yield self.env.timeout(self.config.detection_delay)
        self._log(EventType.RECOVERY_SEARCH, "Failure detected; alternate route search started")
        yield self.env.timeout(self.config.compute_delay)
        result = self.routes.recover(self.config.source, self.config.destination)
        if result.found:
            self._install_route(result.path, result.cost_ms)
            self.recovery_times.append(self.env.now - failed_at)
        else:
            self.active_route = None
            self._log(EventType.NO_ROUTE, f"No alternate route: {result.reason}")
        self.converged = True

    def _transmit(self, packet: Packet):
        net = self.network
        if not net.is_node_active(packet.source):
            self._drop(packet, DropReason.NODE_DOWN)
            return
        if self.active_route is None:
            self._drop(packet, DropReason.NO_ROUTE)
            return
        packet.route = list(self.active_route)

        while packet.current_node != packet.destination:
            here, nxt = packet.current_node, packet.next_hop
            if not net.is_link_usable(here, nxt):
                if not self._try_reroute(packet, nxt):
                    return
                nxt = packet.next_hop
            link = net.link(here, nxt)
            if self.rng.random() < link.loss_probability:
                self._drop(packet, DropReason.PACKET_LOSS)
                return
            if packet.status == PacketStatus.CREATED:
                packet.status = PacketStatus.TRANSMITTING
            yield self.env.timeout(link.latency_s)
            if not link.active:                      # link died while packet was on the wire
                self._drop(packet, DropReason.LINK_DOWN)
                return
            if not net.is_node_active(nxt):
                self._drop(packet, DropReason.NODE_DOWN)
                return
            packet.advance()
            if self.config.log_hops:
                self._log(EventType.PACKET_HOP, f"{packet.packet_id} {here}->{nxt}", packet.packet_id, link.label)

        packet.mark_delivered(self.env.now)
        self._log(EventType.PACKET_DELIVERED,
                  f"Packet {packet.packet_id} delivered (delay {packet.delay * 1000:.1f} ms)", packet.packet_id)

    # ---- helpers ---------------------------------------------------------
    def _handle_failure(self) -> None:
        if self.active_route is None or self.routes.is_route_valid(self.active_route):
            self._log(EventType.ROUTE_INVALIDATED, "Failure does not affect the active route")
            return
        self._log(EventType.ROUTE_INVALIDATED,
                  f"Active route {' > '.join(self.active_route)} invalidated")
        if not self.config.recovery_enabled:
            self._log(EventType.NO_ROUTE, "Self-healing disabled: route is not recomputed")
            return
        self.converged = False
        self.env.process(self._recover(self.env.now))

    def _handle_restore(self) -> None:
        if not self.config.recovery_enabled:
            return
        result = self.routes.recover(self.config.source, self.config.destination)
        if result.found and result.path != self.active_route:
            self._install_route(result.path, result.cost_ms)

    def _install_route(self, path: tuple[str, ...], cost_ms: float, announce: bool = True) -> None:
        old = self.active_route
        self.active_route = path
        self.route_history.append(RouteChange(self.env.now, path, cost_ms))
        if announce and old != path:
            old_text = " > ".join(old) if old else "none"
            self._log(EventType.ROUTE_CHANGED,
                      f"Route changed {old_text} -> {' > '.join(path)} (cost {cost_ms:.1f} ms)")

    def _try_reroute(self, packet: Packet, blocked: str) -> bool:
        reason = DropReason.NODE_DOWN if not self.network.is_node_active(blocked) else DropReason.LINK_DOWN
        if not self.config.recovery_enabled or not self.converged:
            self._drop(packet, reason)
            return False
        result = self.routes.recover(packet.current_node, packet.destination)
        if not result.found:
            self._drop(packet, DropReason.NO_ROUTE)
            return False
        packet.reroute(list(result.path))
        self._log(EventType.PACKET_REROUTED,
                  f"Packet {packet.packet_id} rerouted at {packet.current_node}: {' > '.join(packet.route)}",
                  packet.packet_id)
        return True

    def _drop(self, packet: Packet, reason: DropReason) -> None:
        packet.mark_dropped(reason)
        self._log(EventType.PACKET_DROPPED,
                  f"Packet {packet.packet_id} dropped at {packet.current_node}: {reason.value}", packet.packet_id)

    def _log(self, event_type: EventType, message: str, packet_id: str = "", element: str = "") -> None:
        self.log.record(self.env.now, event_type, message, packet_id, element)
