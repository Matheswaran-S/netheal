"""Plotly charts. Each one answers a specific networking question."""
import plotly.graph_objects as go

from core.metrics import Metrics, outcome_timeline
from core.simulation import SimulationResult

from . import theme

COMPARISON_CHARTS = [
    ("delivery_ratio_pct", "Did failure reduce delivery?", "Delivery ratio (%)"),
    ("loss_rate_pct", "How much packet loss occurred?", "Packet loss (%)"),
    ("avg_delay_ms", "Did rerouting increase delay?", "Average delay (ms)"),
    ("throughput_pps", "Did throughput hold up?", "Throughput (packets/s)"),
]
MODE_COLOURS = {"Without recovery": theme.WITHOUT, "With recovery": theme.WITH}


def _style(fig: go.Figure, title: str, height: int = 320) -> go.Figure:
    fig.update_layout(title=title, height=height, margin=dict(l=10, r=10, t=50, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=theme.TEXT))
    fig.update_yaxes(gridcolor=theme.GRID)
    return fig


def comparison_figure(without: Metrics, with_recovery: Metrics, key: str,
                      title: str, y_title: str) -> go.Figure:
    values = {"Without recovery": getattr(without, key), "With recovery": getattr(with_recovery, key)}
    fig = go.Figure(go.Bar(x=list(values), y=list(values.values()),
                           marker_color=[MODE_COLOURS[m] for m in values],
                           text=[f"{v:.1f}" for v in values.values()], textposition="outside"))
    fig.update_yaxes(title=y_title)
    return _style(fig, title)


def timeline_figure(results: dict[str, SimulationResult], metric: str = "delivery_ratio_pct",
                    title: str = "Did the network recover?", y_title: str = "Delivery ratio (%)") -> go.Figure:
    """Metric per time bucket for each run, with failure times marked."""
    fig = go.Figure()
    failures = set()
    for mode, result in results.items():
        rows = outcome_timeline(result.packets, result.config.duration)
        fig.add_trace(go.Scatter(x=[r["start"] for r in rows], y=[r[metric] for r in rows],
                                 mode="lines+markers", name=mode, connectgaps=False,
                                 line=dict(color=MODE_COLOURS.get(mode, theme.ALTERNATE))))
        failures.update(f.time for f in result.config.failures)
    for t in sorted(failures):
        fig.add_vline(x=t, line_dash="dot", line_color=theme.FAILED,
                      annotation_text=f"failure @ {t:g}s", annotation_font_color=theme.FAILED)
    fig.update_xaxes(title="Packet creation time (s)")
    fig.update_yaxes(title=y_title)
    return _style(fig, title, height=340)
