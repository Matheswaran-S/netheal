"""Network topology model. NetworkX stores the graph; Node/Link hold the state."""
import copy
from collections.abc import Iterator

import networkx as nx

from .link import Link
from .node import Node


class NetworkError(ValueError):
    """Invalid topology operation (unknown node/link, duplicates, ...)."""


class Network:
    def __init__(self, name: str = "network") -> None:
        self.name = name
        self.graph: nx.Graph = nx.Graph()

    # ---- construction -------------------------------------------------
    def add_node(self, node_id: str, x: float = 0.0, y: float = 0.0) -> Node:
        if node_id in self.graph:
            raise NetworkError(f"Node '{node_id}' already exists")
        node = Node(node_id, x, y)
        self.graph.add_node(node_id, node=node)
        return node

    def add_link(self, a: str, b: str, latency_ms: float,
                 bandwidth_mbps: float = 100.0, loss_probability: float = 0.0) -> Link:
        if a == b:
            raise NetworkError("A link cannot connect a node to itself")
        self.node(a)
        self.node(b)
        if self.graph.has_edge(a, b):
            raise NetworkError(f"Link {a}-{b} already exists")
        link = Link(a, b, latency_ms, bandwidth_mbps, loss_probability)
        self.graph.add_edge(a, b, link=link)
        return link

    # ---- lookup -------------------------------------------------------
    def has_node(self, node_id: str) -> bool:
        return node_id in self.graph

    def has_link(self, a: str, b: str) -> bool:
        return self.graph.has_edge(a, b)

    def node(self, node_id: str) -> Node:
        if node_id not in self.graph:
            raise NetworkError(f"Unknown node '{node_id}'")
        return self.graph.nodes[node_id]["node"]

    def link(self, a: str, b: str) -> Link:
        if not self.graph.has_edge(a, b):
            raise NetworkError(f"Unknown link {a}-{b}")
        return self.graph.edges[a, b]["link"]

    @property
    def node_ids(self) -> list[str]:
        return list(self.graph.nodes)

    @property
    def nodes(self) -> list[Node]:
        return [d["node"] for _, d in self.graph.nodes(data=True)]

    @property
    def links(self) -> list[Link]:
        return [d["link"] for _, _, d in self.graph.edges(data=True)]

    # ---- state --------------------------------------------------------
    def is_node_active(self, node_id: str) -> bool:
        return self.has_node(node_id) and self.node(node_id).active

    def is_link_usable(self, a: str, b: str) -> bool:
        """A link carries traffic only if it and both end nodes are up."""
        return (self.has_link(a, b) and self.link(a, b).active
                and self.is_node_active(a) and self.is_node_active(b))

    def usable_neighbors(self, node_id: str) -> Iterator[tuple[str, Link]]:
        """Yield (neighbour, link) pairs reachable over active components."""
        if not self.is_node_active(node_id):
            return
        for neighbour, data in self.graph.adj[node_id].items():
            if self.is_link_usable(node_id, neighbour):
                yield neighbour, data["link"]

    def set_node_state(self, node_id: str, active: bool) -> None:
        self.node(node_id).active = active

    def set_link_state(self, a: str, b: str, active: bool) -> None:
        self.link(a, b).active = active

    def set_all_loss(self, probability: float) -> None:
        if not 0.0 <= probability <= 1.0:
            raise NetworkError("Loss probability must be between 0 and 1")
        for link in self.links:
            link.loss_probability = probability

    def copy(self) -> "Network":
        return copy.deepcopy(self)
