"""Predefined topologies (positions are fixed so drawings are stable)."""
from collections.abc import Callable
from dataclasses import dataclass

from core.network import Network


@dataclass(frozen=True)
class TopologyPreset:
    name: str
    build: Callable[[], Network]
    default_source: str
    default_destination: str


def _build(name: str, positions: dict[str, tuple[float, float]],
           links: list[tuple[str, str, float]]) -> Network:
    network = Network(name)
    for node_id, (x, y) in positions.items():
        network.add_node(node_id, x, y)
    for a, b, latency in links:
        network.add_link(a, b, latency)
    return network


def small_demo() -> Network:
    pos = {"A": (0, 1), "B": (1, 2), "C": (1, 0), "D": (2, 2), "E": (2, 0), "F": (3, 1)}
    links = [("A", "B", 10), ("A", "C", 20), ("B", "D", 15),
             ("C", "E", 10), ("D", "F", 10), ("E", "F", 10)]
    return _build("Small Demo", pos, links)


def medium() -> Network:
    pos = {"A": (0, 1.5), "B": (1, 3), "C": (1, 0), "D": (2, 3.5), "E": (2, 1.5),
           "F": (2, -0.5), "G": (3, 2.5), "H": (4, 1.5)}
    links = [("A", "B", 8), ("A", "C", 12), ("B", "D", 10), ("B", "E", 15),
             ("C", "E", 9), ("C", "F", 20), ("D", "G", 12), ("E", "G", 8),
             ("E", "H", 14), ("F", "H", 11), ("G", "H", 7)]
    return _build("Medium", pos, links)


def mesh() -> Network:
    ids = "ABCDEFGHI"
    pos = {n: (i % 3, 2 - i // 3) for i, n in enumerate(ids)}
    links = [("A", "B", 8), ("B", "C", 12), ("D", "E", 10), ("E", "F", 9),
             ("G", "H", 14), ("H", "I", 7), ("A", "D", 11), ("D", "G", 13),
             ("B", "E", 6), ("E", "H", 10), ("C", "F", 15), ("F", "I", 8),
             ("A", "E", 16), ("E", "I", 12)]
    return _build("Mesh", pos, links)


TOPOLOGIES: dict[str, TopologyPreset] = {
    "Small Demo": TopologyPreset("Small Demo", small_demo, "A", "F"),
    "Medium": TopologyPreset("Medium", medium, "A", "H"),
    "Mesh": TopologyPreset("Mesh", mesh, "A", "I"),
}


def get_topology(name: str) -> TopologyPreset:
    if name not in TOPOLOGIES:
        raise KeyError(f"Unknown topology '{name}'")
    return TOPOLOGIES[name]
