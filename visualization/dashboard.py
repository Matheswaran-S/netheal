"""Streamlit dashboard. It only *consumes* engine results; no routing logic lives here."""
import pandas as pd
import streamlit as st

from core.events import EventType
from core.experiment import run_comparison
from core.network import NetworkError
from core.simulation import ConfigError, SimulationConfig
from routing.failure_manager import FailureError, FailureSpec
from routing.route_manager import RouteManager
from scenarios.default_topologies import TOPOLOGIES, get_topology
from scenarios.experiments import SCENARIOS
from utils.helpers import (comparison_frame, events_frame, export_csv, format_route,
                           results_frame)

from . import theme
from .charts import COMPARISON_CHARTS, comparison_figure, timeline_figure
from .topology import build_topology_figure

DEFAULTS = {"topology": "Small Demo", "source": "A", "destination": "F",
            "packets": 1000, "loss_pct": 1, "duration": 20, "seed": 42}
CSS = """<style>
.nh-title{font-size:2rem;font-weight:700;letter-spacing:.12em;margin-bottom:0}
.nh-sub{color:#8aa0b8;margin-top:0}
.nh-pill{display:inline-block;padding:.2rem .8rem;border-radius:999px;font-weight:600;color:#0b1220}
div[data-testid="stMetric"]{background:#111c2e;border:1px solid #243447;border-radius:8px;padding:.6rem .9rem}
</style>"""
KEY_EVENTS = [e for e in EventType if e not in (EventType.PACKET_CREATED, EventType.PACKET_DELIVERED,
                                                 EventType.PACKET_HOP)]


# ---------------------------------------------------------------- state / callbacks
def _init_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("failures", [])
    st.session_state.setdefault("comparison", None)
    st.session_state.setdefault("run_config", None)


def _on_topology_change() -> None:
    preset = get_topology(st.session_state.topology)
    st.session_state.source = preset.default_source
    st.session_state.destination = preset.default_destination
    st.session_state.failures = []
    st.session_state.comparison = None


def _load_scenario() -> None:
    scenario = SCENARIOS[st.session_state.scenario_pick]
    st.session_state.update(topology=scenario.topology, source=scenario.source,
                            destination=scenario.destination,
                            loss_pct=round(scenario.link_loss * 100),
                            failures=list(scenario.failures), comparison=None)


def _reset() -> None:
    st.session_state.update(DEFAULTS)
    st.session_state.failures = []
    st.session_state.comparison = None


def _clear_failures() -> None:
    st.session_state.failures = []
    st.session_state.comparison = None


# ---------------------------------------------------------------- sidebar
def _sidebar(network) -> bool:
    ids = network.node_ids
    with st.sidebar:
        st.header("Simulation configuration")
        st.selectbox("Topology", list(TOPOLOGIES), key="topology", on_change=_on_topology_change)
        st.selectbox("Source", ids, key="source")
        st.selectbox("Destination", ids, key="destination")
        st.number_input("Packets", 0, 5000, key="packets", step=100)
        st.slider("Packet loss per link (%)", 0, 100, key="loss_pct")
        st.number_input("Simulation duration (s)", 5, 300, key="duration", step=5)
        st.number_input("Random seed", 0, 10**6, key="seed")
        invalid = st.session_state.source == st.session_state.destination
        if invalid:
            st.error("Source and destination must be different.")
        run = st.button("RUN SIMULATION", type="primary", disabled=invalid)
        st.button("RESET", on_click=_reset)
        st.divider()
        st.selectbox("Predefined scenario", list(SCENARIOS), key="scenario_pick")
        st.caption(SCENARIOS[st.session_state.scenario_pick].description)
        st.button("Load scenario", on_click=_load_scenario)
    return run


def _build_config() -> SimulationConfig:
    s = st.session_state
    return SimulationConfig(s.source, s.destination, int(s.packets), float(s.duration),
                            int(s.seed), s.loss_pct / 100, True, tuple(s.failures))


def _run(network) -> None:
    try:
        config = _build_config()
        with st.spinner("Running with and without self-healing..."):
            st.session_state.comparison = run_comparison(network, config)
            st.session_state.run_config = config
    except (ConfigError, NetworkError) as exc:
        st.error(f"Cannot run simulation: {exc}")


# ---------------------------------------------------------------- header / KPIs
def _status(result) -> tuple[str, str]:
    if result is None:
        return "READY", theme.IDLE
    if result.partitioned:
        return "PARTITIONED", theme.FAILED
    if result.metrics.delivery_ratio_pct >= 90:
        return "HEALTHY", theme.ACTIVE_ROUTE
    return "DEGRADED", theme.WITHOUT


def _header(result) -> None:
    label, colour = _status(result)
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown('<p class="nh-title">NETHEAL</p>', unsafe_allow_html=True)
    st.markdown('<p class="nh-sub">Fault-Tolerant Self-Healing Network Simulator · '
                'Adaptive Routing • Failure Recovery • Network Resilience</p>', unsafe_allow_html=True)
    st.markdown(f'Status: <span class="nh-pill" style="background:{colour}">● {label}</span>',
                unsafe_allow_html=True)


def _kpis(m) -> None:
    cards = [("Packets sent", f"{m.packets_sent}"), ("Delivered", f"{m.packets_delivered}"),
             ("Lost", f"{m.packets_dropped}"), ("Delivery ratio", f"{m.delivery_ratio_pct:.1f}%"),
             ("Avg delay", f"{m.avg_delay_ms:.1f} ms"), ("Throughput", f"{m.throughput_pps:.1f} pkt/s"),
             ("Rerouted packets", f"{m.rerouted_packets}"),
             ("Recoveries", f"{m.recovery_count} ({m.avg_recovery_time_ms:.0f} ms avg)")]
    for row in (cards[:4], cards[4:]):
        for col, (label, value) in zip(st.columns(4), row):
            col.metric(label, value)


# ---------------------------------------------------------------- tabs
def _tab_dashboard(network, comparison) -> None:
    if comparison is None:
        primary = RouteManager(network).primary_route(st.session_state.source, st.session_state.destination)
        alt = RouteManager(network).alternate_route(st.session_state.source, st.session_state.destination, primary)
        st.info("Configure the simulation in the sidebar and press RUN SIMULATION.")
        c1, c2 = st.columns(2)
        c1.metric("Primary route", format_route(primary.path), f"{primary.cost_ms:.0f} ms" if primary.found else None)
        c2.metric("Alternate route", format_route(alt.path), f"{alt.cost_ms:.0f} ms" if alt.found else None)
        return
    r = comparison.with_recovery
    _kpis(r.metrics)
    c1, c2, c3 = st.columns(3)
    c1.metric("Initial route", format_route(r.initial_route.path),
              f"{r.initial_route.cost_ms:.0f} ms" if r.initial_route.found else None)
    c2.metric("Final route", format_route(r.final_route))
    c3.metric("Backup route (computed)", format_route(r.alternate_route.path))
    if r.partitioned:
        st.warning("Network partitioned: no active path from source to destination remains. "
                   "Packets are dropped with reason NO_ROUTE.")
    st.plotly_chart(timeline_figure({"With recovery": r}, title="Delivery ratio over time (self-healing ON)"))


def _tab_topology(network, comparison) -> None:
    if comparison is None:
        primary = RouteManager(network).primary_route(st.session_state.source, st.session_state.destination)
        alt = RouteManager(network).alternate_route(st.session_state.source, st.session_state.destination, primary)
        st.plotly_chart(build_topology_figure(network, primary.path, alt.path, "Healthy network"))
        return
    r = comparison.with_recovery
    left, right = st.columns(2)
    left.plotly_chart(build_topology_figure(network, r.initial_route.path, r.alternate_route.path,
                                            "Before failures: primary + backup"))
    right.plotly_chart(build_topology_figure(r.final_network, r.final_route or (), (),
                                             "After failures: recovered route"))
    st.subheader("Packet inspector")
    ordered = sorted(r.packets, key=lambda p: (p.reroute_count == 0, p.drop_reason is None, p.packet_id))
    packet = next(p for p in ordered if p.packet_id == st.selectbox(
        "Packet", [p.packet_id for p in ordered], help="Rerouted and dropped packets are listed first."))
    st.write(f"**{packet.packet_id}** · status `{packet.status.value}` · reroutes {packet.reroute_count} · "
             f"hops {packet.hops} · delay "
             f"{'—' if packet.delay is None else f'{packet.delay * 1000:.1f} ms'}"
             f"{'' if packet.drop_reason is None else f' · dropped: {packet.drop_reason.value}'}")
    st.write("Path taken: " + format_route(packet.path_taken))
    st.plotly_chart(build_topology_figure(r.final_network, packet.path_taken, (), "Selected packet's path"))


def _tab_failure(network, comparison) -> None:
    st.caption("Failures are scheduled events on the simulation clock. Add them here, then press RUN SIMULATION.")
    s = st.session_state
    kind = st.radio("Failure type", ["Link", "Node"], horizontal=True)
    links = {link.label: link.key for link in network.links}
    targets = list(links) if kind == "Link" else network.node_ids
    target = st.selectbox("Target", targets, key=f"target_{kind}_{s.topology}")
    c1, c2 = st.columns(2)
    when = c1.number_input("Fail at (s)", 0.0, float(s.duration), float(s.duration) / 2, step=0.5)
    restore = c2.checkbox("Restore later")
    restore_at = c2.number_input("Restore at (s)", 0.0, float(s.duration), min(float(s.duration), when + 5), step=0.5,
                                 disabled=not restore)
    if st.button("INJECT FAILURE"):
        try:
            spec = FailureSpec(when, kind.lower(), links[target] if kind == "Link" else (target,),
                               restore_at if restore else None)
            if any(f.kind == spec.kind and f.target == spec.target for f in s.failures):
                raise FailureError(f"{kind} {spec.label} is already scheduled to fail")
            s.failures = s.failures + [spec]
            s.comparison = None
            st.rerun()
        except FailureError as exc:
            st.error(str(exc))
    st.button("RECOVER NETWORK (clear all failures)", on_click=_clear_failures)
    if s.failures:
        st.dataframe(pd.DataFrame([{"type": f.kind, "target": f.label, "fail at (s)": f.time,
                                    "restore at (s)": f.restore_time} for f in s.failures]),
                     hide_index=True)
    else:
        st.write("No failures scheduled.")
    if comparison is None:
        return
    r = comparison.with_recovery
    st.subheader("Recovery sequence (from the simulation event log)")
    shown = [e for e in r.events if e.event_type in KEY_EVENTS]
    st.dataframe(pd.DataFrame([{"time (s)": round(e.time, 4), "event": e.event_type.value,
                                "details": e.message} for e in shown]), hide_index=True)
    if r.route_history:
        st.subheader("Route history")
        st.dataframe(pd.DataFrame([{"time (s)": round(c.time, 4), "route": format_route(c.path),
                                    "cost (ms)": c.cost_ms} for c in r.route_history]), hide_index=True)


def _tab_performance(comparison) -> None:
    if comparison is None:
        st.info("Run a simulation to see the before/after comparison.")
        return
    results = {"Without recovery": comparison.without_recovery, "With recovery": comparison.with_recovery}
    st.subheader("Without vs with self-healing (both runs use the same seed and failures)")
    st.dataframe(comparison_frame(results))
    pairs = [comparison_figure(results["Without recovery"].metrics, results["With recovery"].metrics, *c)
             for c in COMPARISON_CHARTS]
    for row in (pairs[:2], pairs[2:]):
        for col, fig in zip(st.columns(2), row):
            col.plotly_chart(fig)
    st.plotly_chart(timeline_figure(results))
    st.plotly_chart(timeline_figure(results, "avg_delay_ms", "Did rerouting change delay over time?",
                                    "Average delay (ms)"))
    st.subheader("Export")
    st.download_button("Download simulation_results.csv", results_frame(results).to_csv(index=False),
                       "simulation_results.csv", "text/csv")
    if st.button("Save all CSVs to exports/ folder"):
        st.success("Saved: " + ", ".join(p.name for p in export_csv(results)))


def _tab_events(comparison) -> None:
    if comparison is None:
        st.info("Run a simulation to see its event log.")
        return
    mode = st.radio("Run", ["With recovery", "Without recovery"], horizontal=True)
    result = comparison.with_recovery if mode == "With recovery" else comparison.without_recovery
    chosen = st.multiselect("Event types", [e.value for e in EventType], [e.value for e in KEY_EVENTS])
    frame = events_frame(result)
    frame = frame[frame.event_type.isin(chosen)]
    st.caption(f"{len(frame)} events (showing first 2000). Timestamps come from the SimPy clock.")
    st.dataframe(frame.head(2000), hide_index=True)
    st.download_button("Download event_log.csv", events_frame(result).to_csv(index=False),
                       "event_log.csv", "text/csv")


HOW_IT_WORKS = """
**Routing** – Dijkstra finds the lowest-latency path between source and destination over *active* links.
**Failure** – a simulated link or node becomes unavailable at a scheduled simulation time.
**Detection** – the active route is checked against the current network state; a broken route is invalidated.
**Recovery** – after a modelled detection + computation delay, Dijkstra runs again on the surviving topology.
**Rerouting** – new packets use the new route; packets already in flight are re-routed from where they are.
Packets that hit the dead component *before* routing reconverges are dropped — that is the cost of failure.
**Metrics** – delivery ratio, loss, delay, throughput, hops and recovery time are computed from simulated packets.
**Comparison** – *Without recovery* keeps the original route forever; *With recovery* recomputes it. Same seed, same failures.
"""

ABOUT = """
### NetHeal — Fault-Tolerant Self-Healing Network Simulator
An educational discrete-event simulator built for a Computer Networks laboratory to study adaptive routing,
network failures and fault-tolerant communication.

**This is a simulation, not a real network controller.** Delay is link propagation only (no queueing),
loss is random per link traversal, and failure detection time is a configurable model parameter.
Stack: Python, SimPy, NetworkX, Streamlit, Plotly, Pandas.
"""


def main() -> None:
    st.set_page_config(page_title="NetHeal", page_icon="🛡", layout="wide")
    _init_state()
    network = get_topology(st.session_state.topology).build()
    run_clicked = _sidebar(network)
    if run_clicked:
        _run(network)
    comparison = st.session_state.comparison
    _header(comparison.with_recovery if comparison else None)
    if comparison and st.session_state.run_config != _build_config():
        st.warning("Settings or scheduled failures changed since the last run; "
                   "the results below are from the previous run. Press RUN SIMULATION to refresh.")

    tabs = st.tabs(["Dashboard", "Network Topology", "Failure & Recovery", "Performance Analysis",
                    "Event Log", "How It Works", "About"])
    with tabs[0]:
        _tab_dashboard(network, comparison)
    with tabs[1]:
        _tab_topology(network, comparison)
    with tabs[2]:
        _tab_failure(network, comparison)
    with tabs[3]:
        _tab_performance(comparison)
    with tabs[4]:
        _tab_events(comparison)
    with tabs[5]:
        st.markdown(HOW_IT_WORKS)
    with tabs[6]:
        st.markdown(ABOUT)
