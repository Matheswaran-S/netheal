"""Interactive topology figure (NetworkX graph data drawn with Plotly)."""
import plotly.graph_objects as go

from core.network import Network

from . import theme


def _edges(path) -> set[tuple[str, str]]:
    return {tuple(sorted(pair)) for pair in zip(path or (), (path or ())[1:])}


def build_topology_figure(network: Network, current_route=(), alternate_route=(),
                          title: str = "") -> go.Figure:
    """Colour code: green=current route, blue dashed=alternate, red dashed=failed."""
    route_edges = _edges(current_route)
    alt_edges = _edges(alternate_route) - route_edges
    groups = {"Active route": ([], theme.ACTIVE_ROUTE, 6, "solid"),
              "Alternate route": ([], theme.ALTERNATE, 4, "dash"),
              "Failed link": ([], theme.FAILED, 4, "dot"),
              "Idle link": ([], theme.IDLE, 2, "solid")}
    mid_x, mid_y, mid_text, mid_hover = [], [], [], []

    for link in network.links:
        a, b = network.node(link.a), network.node(link.b)
        if not link.active:
            name = "Failed link"
        elif link.key in route_edges:
            name = "Active route"
        elif link.key in alt_edges:
            name = "Alternate route"
        else:
            name = "Idle link"
        groups[name][0].append((a.x, a.y, b.x, b.y))
        mid_x.append((a.x + b.x) / 2)
        mid_y.append((a.y + b.y) / 2)
        mid_text.append("✕" if not link.active else f"{link.latency_ms:g} ms")
        mid_hover.append(f"{link.label}<br>latency {link.latency_ms:g} ms<br>"
                         f"bandwidth {link.bandwidth_mbps:g} Mbps<br>"
                         f"loss {link.loss_probability * 100:.1f}%<br>"
                         f"{'UP' if link.active else 'DOWN'}")

    fig = go.Figure()
    for name, (segments, colour, width, dash) in groups.items():
        xs, ys = [], []
        for x0, y0, x1, y1 in segments:
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        fig.add_trace(go.Scatter(x=xs or [None], y=ys or [None], mode="lines", name=name,
                                 line=dict(color=colour, width=width, dash=dash),
                                 hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mid_x, y=mid_y, mode="text", text=mid_text,
                             textfont=dict(color=theme.TEXT, size=11), hovertext=mid_hover,
                             hoverinfo="text", showlegend=False))

    nodes = network.nodes
    fig.add_trace(go.Scatter(
        x=[n.x for n in nodes], y=[n.y for n in nodes], mode="markers+text",
        text=[n.node_id for n in nodes], textfont=dict(color="#0b1220", size=15),
        marker=dict(size=40, color=[theme.NODE_OK if n.active else theme.FAILED for n in nodes],
                    line=dict(color=theme.TEXT, width=2)),
        hovertext=[f"Node {n.node_id}: {'UP' if n.active else 'DOWN'}" for n in nodes],
        hoverinfo="text", name="Node", showlegend=False))

    fig.update_layout(title=title, height=380, margin=dict(l=10, r=10, t=45, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=theme.TEXT), legend=dict(orientation="h", y=-0.05))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x")
    return fig
