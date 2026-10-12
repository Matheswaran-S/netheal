import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from helpers import diamond
from routing.dijkstra import find_shortest_path


def test_known_shortest_path_and_cost():
    r = find_shortest_path(diamond(), "A", "F")
    assert r.found and r.path == ("A", "B", "D", "F") and r.cost_ms == 35


def test_prefers_lower_total_cost_not_fewer_hops():
    n = diamond()
    n.add_link("A", "F", 100)           # 1 hop but expensive
    assert find_shortest_path(n, "A", "F").path == ("A", "B", "D", "F")


def test_source_equals_destination_is_zero_cost():
    r = find_shortest_path(diamond(), "A", "A")
    assert r.found and r.path == ("A",) and r.cost_ms == 0


def test_unknown_node_is_graceful():
    assert not find_shortest_path(diamond(), "A", "Z").found


def test_disconnected_graph_has_no_route():
    n = diamond()
    n.add_node("Z")
    r = find_shortest_path(n, "A", "Z")
    assert not r.found and "partitioned" in r.reason
