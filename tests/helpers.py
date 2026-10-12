from core.network import Network


def diamond() -> Network:
    """A-B-D-F (35) and A-C-E-F (40)."""
    n = Network("diamond")
    for node in "ABCDEF":
        n.add_node(node)
    for a, b, w in [("A", "B", 10), ("A", "C", 20), ("B", "D", 15),
                    ("C", "E", 10), ("D", "F", 10), ("E", "F", 10)]:
        n.add_link(a, b, w)
    return n
