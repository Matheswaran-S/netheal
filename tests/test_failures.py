import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from helpers import diamond
from routing.dijkstra import find_shortest_path
from routing.failure_manager import FailureError, FailureManager, FailureSpec


def test_failed_link_is_not_used_by_routing():
    n = diamond()
    FailureManager(n).apply(FailureSpec(0, "link", ("B", "D")))
    r = find_shortest_path(n, "A", "F")
    assert r.path == ("A", "C", "E", "F") and r.cost_ms == 40


def test_failed_node_cannot_be_traversed():
    n = diamond()
    FailureManager(n).apply(FailureSpec(0, "node", ("D",)))
    assert "D" not in find_shortest_path(n, "A", "F").path


def test_failed_destination_or_source_gives_no_route():
    n = diamond()
    FailureManager(n).apply(FailureSpec(0, "node", ("F",)))
    assert not find_shortest_path(n, "A", "F").found
    assert not find_shortest_path(n, "F", "A").found


def test_duplicate_and_invalid_failures_raise():
    n = diamond()
    fm = FailureManager(n)
    fm.apply(FailureSpec(0, "link", ("B", "D")))
    with pytest.raises(FailureError):
        fm.apply(FailureSpec(0, "link", ("D", "B")))      # same link, reversed
    with pytest.raises(FailureError):
        fm.apply(FailureSpec(0, "link", ("A", "F")))      # nonexistent
    with pytest.raises(FailureError):
        FailureSpec(5, "link", ("B", "D"), restore_time=3)


def test_restore_makes_route_available_again():
    n = diamond()
    fm = FailureManager(n)
    spec = FailureSpec(0, "link", ("B", "D"))
    fm.apply(spec)
    fm.restore(spec)
    fm.restore(spec)                                       # repeated restore is harmless
    assert find_shortest_path(n, "A", "F").path == ("A", "B", "D", "F")
    assert fm.failed_links() == []
