from ..pushdown import graph
from ..pushdown import supergraph
from ..pushdown import expression

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
    "visit_swapaction": lambda x, t, _: (t.pushdown_from_mpls(x.label), ),
    "visit_pushaction": lambda x, t, _: (t.pushdown_from_mpls(x.label), ),
    "visit_popaction": lambda x, _, labels: labels,
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
    next_labels = op.visit(
        _label_pruner,
        translator,
        translator.pushdown_mpls_labels
    )
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

    # We need to keep the "has" variable around since we use that to track the
    # stage
    with expgen.variable("has") as var, \
            expgen.variable("node_state") as node_var:
        # Start conditions
        sw = network.topology.router_by_name(chain[0].switch)
        for i in sw.interfaces.values():
            # Only connect to the given interfaces
            if not chain[0].i1.isWildcard() and i.name != chain[0].i1.name:
                continue
            enterNode = _get_node_raw(f"simstart")
            exitNode = _get_node_inface(sw, i)

            exp = (expression.SetExpression(var, 0)
                   & expression.SetExpression(node_var, 0))

            graph.EpsilonTransition(
                enterNode, exitNode,
                labels | {graph.SpecialLabel.bottom_of_stack()},
                graph.NoopAction(),
                guard=graph.Guard(expgen.get_expression(
                    explicit=exp,
                    exclude=(var, node_var)
                ))
            ).attach()

        # Link land
        # a)
        for link in network.topology.links:
            exp = expression.SetExpression(node_var, 0)
            for i in range(0, k):
                enterNode = _get_node_outface(link.from_.switch,
                                              link.from_.interface, i, ())
                exitNode = _get_node_inface(link.to.switch, link.to.interface)

                graph.EpsilonTransition(
                    enterNode, exitNode,
                    labels,
                    graph.NoopAction(),
                    guard=graph.Guard(expgen.get_expression(
                        explicit=exp,
                        exclude=(node_var, )
                    ))
                ).attach()

                enterNode = _get_node_outface(
                    link.to.switch,
                    link.to.interface,
                    i,
                    ()
                )
                exitNode = _get_node_inface(
                    link.from_.switch,
                    link.from_.interface
                )

                graph.EpsilonTransition(
                    enterNode, exitNode,
                    labels,
                    graph.NoopAction(),
                    guard=graph.Guard(expgen.get_expression(
                        explicit=exp,
                        exclude=(node_var, )
                    ))
                ).attach()

        # Self link loops
        # For stepping interfaces
        for index, step in enumerate(chain):
            switch = network.topology.router_by_name(step.switch)
            # @HACK: Always looping seems a little fishy
            # Add the input loops
            for interface in switch.interfaces.values():
                if not step.i1.isWildcard() and interface.name != step.i1.name:
                    continue
                node = _get_node_inface(switch, interface)

                exp = (expression.EqExpression(var, index)
                       & expression.SetExpression(node_var, 1)
                       & expression.EqExpression(node_var, 0))

                graph.EpsilonTransition(
                    node, node,
                    translator.pushdown_mpls_labels
                    | {graph.SpecialLabel.bottom_of_stack()},
                    graph.NoopAction(),
                    guard=graph.Guard(expgen.get_expression(
                        explicit=(
                            exp
                        ),
                        exclude=(node_var,)
                    ))
                ).attach()

            # Add the output loops
            for interface in switch.interfaces.values():
                if not step.i2.isWildcard() and interface.name != step.i2.name:
                    continue
                for i in range(0, k):
                    node = _get_node_outface(switch, interface, i, ())

                    exp = (expression.SetExpression(
                        var, expression.AddExpression(var, 1))
                           & expression.SetExpression(node_var, 2)
                           & expression.EqExpression(node_var, 1))

                    graph.EpsilonTransition(
                        node, node,
                        translator.pushdown_mpls_labels
                        | {graph.SpecialLabel.bottom_of_stack()},
                        graph.NoopAction(),
                        guard=graph.Guard(expgen.get_expression(
                            explicit=(
                                exp
                            ),
                            exclude=(node_var, var)
                        ))
                    ).attach()

        # Routing table land
        # b1, b2, b3, and b4)
        for sw, rt in network.routing.routingTables:
            for rule in rt.rules:
                label = translator.pushdown_from_mpls(rule.label)
                enterNode = _get_node_inface(sw, rule.from_)
                exitNode = build_action_chain(expgen, translator, sw, rule.to,
                                              0, rule.actions, (label, ))

                # Connect the chain to the actual exitNode
                graph.Transition(
                    enterNode, exitNode,
                    label,
                    graph.NoopAction(),
                    guard=graph.Guard(expgen.get_expression())
                ).attach()

        # Protection table land
        # c1, c2, c3, and c4)
        for sw, pt in network.routing.protectionTables:
            for rule in pt.rules:
                for i in range(0, k):
                    label = translator.pushdown_from_mpls(rule.label)
                    enterNode = _get_node_outface(sw, rule.from_, i, ())
                    exitNode = build_action_chain(
                        expgen,
                        translator,
                        sw,
                        rule.to,
                        i+1,
                        rule.actions,
                        (label, )
                    )

                    exp = expression.NotEqExpression(node_var, 2)
                    # Connect the chain to the actual exitNode
                    graph.Transition(
                        enterNode, exitNode,
                        label,
                        graph.NoopAction(),
                        guard=graph.Guard(expgen.get_expression(
                            explicit=exp,
                            exclude=(node_var,)
                        ))
                    ).attach()

        # Complete Conditions
        sw = network.topology.router_by_name(chain[-1].switch)
        for i in sw.interfaces.values():
            # Only connect to the given interfaces
            if not chain[-1].i2.isWildcard() and i.name != chain[-1].i2.name:
                continue
            for fails in range(0, k):
                enterNode = _get_node_outface(sw, i, 0, ())
                exitNode = _get_node_raw("simend")

                exp = expression.EqExpression(var, len(chain))

                graph.EpsilonTransition(
                    enterNode, exitNode,
                    labels | {graph.SpecialLabel.bottom_of_stack()},
                    graph.NoopAction(),
                    guard=graph.Guard(expgen.get_expression(
                        explicit=exp,
                        exclude=(var, )
                    ))
                ).attach()

    return supergraph.Fragment(
        _get_node_raw("simstart"),
        labels | {graph.SpecialLabel.bottom_of_stack()},
        _get_node_raw("simend"),
        labels | {graph.SpecialLabel.bottom_of_stack()}
    )
