"""Network node (router) model."""
from dataclasses import dataclass


@dataclass
class Node:
    """A router in the simulated network. x/y are only used for drawing."""

    node_id: str
    x: float = 0.0
    y: float = 0.0
    active: bool = True
