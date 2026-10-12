import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from helpers import diamond
from core.link import Link
from core.network import Network, NetworkError


def test_duplicate_and_invalid_links_rejected():
    n = diamond()
    with pytest.raises(NetworkError):
        n.add_link("A", "B", 5)
    with pytest.raises(NetworkError):
        n.add_link("A", "Z", 5)
    with pytest.raises(NetworkError):
        n.add_link("A", "A", 5)


def test_link_is_bidirectional_and_validated():
    n = diamond()
    assert n.link("B", "A") is n.link("A", "B")
    with pytest.raises(ValueError):
        Link("A", "B", latency_ms=0)
    with pytest.raises(ValueError):
        Link("A", "B", latency_ms=5, loss_probability=1.5)


def test_usable_neighbors_skip_failed_components():
    n = diamond()
    n.set_link_state("A", "B", False)
    assert [v for v, _ in n.usable_neighbors("A")] == ["C"]
    n.set_node_state("C", False)
    assert list(n.usable_neighbors("A")) == []


def test_copy_is_independent():
    n = diamond()
    c = n.copy()
    c.set_link_state("A", "B", False)
    assert n.link("A", "B").active
