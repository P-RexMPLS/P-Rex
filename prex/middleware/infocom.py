from ..pushdown import graph
from ..pushdown import supergraph

from types import SimpleNamespace


locations = {}
inface_locations = {}
outface_locations = {}


def _get_node_raw(string):
    if string not in locations:
        locations[string] = graph.Location(string)
    return locations[string]


def _get_node_inface(switch, interface):
    key = (switch, interface)
    if key not in inface_locations:
        inface_locations[key] = (
            _get_node_raw(f"{switch.name}_{interface.name}")
        )
    return inface_locations[key]


def rcar(tup):
    while True:
        if tup == ():
            break
        head, *rest = tup
        tup = tuple(rest)
        yield (head, tup)


_label_pruner = SimpleNamespace(**{
    "visit_swapaction": lambda x, t: {t.pushdown_from_mpls(x.label)},
    "visit_pushaction": lambda x, t: {t.pushdown_from_mpls(x.label)},
    "visit_popaction": lambda x, t: (t.pushdown_mpls_labels
                                     | {graph.SpecialLabel.bottom_of_stack()}),
})


def build_action_chain(expgen, translator, switch, interface, fail, ops,
                       incoming_labels):
    key = (switch, interface, fail, ops)
    if key in outface_locations:
        return outface_locations[key]
    enterNode = _get_node_outface(switch, interface, fail, ops)

    if ops is ():
        return enterNode

    op, *tail = ops
    ops = tuple(tail)
    next_labels = op.visit(_label_pruner, translator)
    exitNode = build_action_chain(
        expgen,
        translator,
        switch,
        interface,
        fail,
        ops,
        next_labels
    )

    graph.EpsilonTransition(
        enterNode, exitNode,
        incoming_labels,
        op.to_graph(),
        guard=graph.Guard(expgen.get_expression())
    ).attach()
    return enterNode


_action_namer = SimpleNamespace(**{
    "visit_swapaction": lambda x: f"s{x.label.name}",
    "visit_pushaction": lambda x: f"p{x.label.name}",
    "visit_popaction": lambda x: f"p",
    "visit_noopaction": lambda x: f"n",
})


def _make_ops_str(tup):
    if tup is ():
        return "__"
    return "__".join([x.visit(_action_namer) for x in tup])


def _get_node_outface(switch, interface, fail, ops):
    key = (switch, interface, fail, ops)
    if key not in outface_locations:
        ops_str = _make_ops_str(ops)
        outface_locations[key] = (
            _get_node_raw(f"{switch.name}_{interface.name}_{fail}_{ops_str}")
        )
    return outface_locations[key]


def to_pushdown(expgen, translator, network, chain, k):
    # This is bad
    k += 1

    labels = translator.pushdown_mpls_labels

    # This isn't in the infocom paper, but lets just play that any interface is
    # a start location
    for switch in network.topology.routers:
        for interface in switch.interfaces.values():
            enterNode = _get_node_raw("simstart")
            exitNode = _get_node_inface(switch, interface)

            graph.EpsilonTransition(
                enterNode, exitNode,
                labels | {graph.SpecialLabel.bottom_of_stack()},
                graph.NoopAction(),
            ).attach()

    # Link land
    # a)
    for link in network.topology.links:
        for i in range(0, k):
            enterNode = _get_node_outface(
                link.from_.switch,
                link.from_.interface,
                i,
                ()
            )
            exitNode = _get_node_inface(link.to.switch, link.to.interface)

            graph.EpsilonTransition(
                enterNode, exitNode,
                labels,
                graph.NoopAction(),
            ).attach()

            # Connect the link the reverse direction
            enterNode = _get_node_outface(link.to.switch, link.to.interface, i,
                                          ())
            exitNode = _get_node_inface(
                link.from_.switch,
                link.from_.interface
            )

            graph.EpsilonTransition(
                enterNode, exitNode,
                labels,
                graph.NoopAction(),
            ).attach()

    # Routing table land
    # b1, b2, b3, and b4)
    for sw, rt in network.routing.routingTables:
        for rule in rt.rules:
            label = translator.pushdown_from_mpls(rule.label)
            enterNode = _get_node_inface(sw, rule.from_)
            exitNode = build_action_chain(expgen, translator, sw, rule.to, 0,
                                          rule.actions, (label, ))

            # Connect the chain to the actual exitNode
            graph.Transition(
                enterNode, exitNode,
                label,
                graph.NoopAction(),
            ).attach()

    # Protection table land
    # c1, c2, c3, and c4)
    for sw, pt in network.routing.protectionTables:
        for rule in pt.rules:
            for i in range(1, k):
                label = translator.pushdown_from_mpls(rule.label)
                enterNode = _get_node_outface(sw, rule.from_, i-1, ())
                exitNode = build_action_chain(expgen, translator, sw, rule.to,
                                              i, rule.actions, (label, ))

                # Connect the chain to the actual exitNode
                graph.Transition(
                    enterNode, exitNode,
                    label,
                    graph.NoopAction(),
                ).attach()

    # Just like the start, this isn't in the infocom paper, but lets play that
    # every interface is a valid exit as well
    for switch in network.topology.routers:
        for interface in switch.interfaces.values():
            for fail in (0, k-1):
                enterNode = _get_node_outface(switch, interface, fail, ())
                exitNode = _get_node_raw("simend")
                graph.EpsilonTransition(
                    enterNode, exitNode,
                    labels | {graph.SpecialLabel.bottom_of_stack()},
                    graph.NoopAction(),
                ).attach()

    return supergraph.Fragment(
        _get_node_raw("simstart"),
        labels | {graph.SpecialLabel.bottom_of_stack()},
        _get_node_raw("simend"),
        labels | {graph.SpecialLabel.bottom_of_stack()},
    )
