from ..pushdown import graph
from . import builder as b

from types import SimpleNamespace
import logging


logger = logging.getLogger(__name__)


locations = {}
inface_locations = {}
outface_locations = {}
action_chains = {}


def _get_node_raw(pda, string):
    if string not in locations:
        locations[string] = pda.location(string)
    return locations[string]


_label_pruner = SimpleNamespace(**{
    "visit_swapaction": lambda x, t, _: {t.symbol(x.label)},
    "visit_pushaction": lambda x, t, _: {t.symbol(x.label)},
    "visit_popaction": lambda x, t, l: (l | {t.bos()}),
})
_action_maker = SimpleNamespace(**{
    "visit_swapaction": lambda x, b: graph.ReplaceAction(b.symbol(x.label)),
    "visit_pushaction": lambda x, b: graph.PushAction(b.symbol(x.label)),
    "visit_popaction": lambda x, _: graph.PopAction(),
})


def tuple_head(t):
    op, *tail = t
    return op, tuple(tail)


def build_action_chain(expgen, builder, k, switch, interface, ops):
    key = (builder.pda, switch, interface, ops, k)
    if key in action_chains:
        return action_chains[key]

    enterNode = _get_node_outface(builder.pda, switch, interface, ops, k)
    action_chains[key] = enterNode

    if ops is ():
        return enterNode

    op, ops = tuple_head(ops)
    exitNode = build_action_chain(
        expgen,
        builder,
        k,
        switch,
        interface,
        ops
    )

    builder.pda.star_transition(
        enterNode, exitNode,
        op.visit(_action_maker, builder),
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


def _get_node_outface(pda, switch, interface, ops, k):
    key = (switch, interface, ops, k)
    if key not in outface_locations:
        outface_locations[key] = (
            pda.location(key)
        )
    return outface_locations[key]


def _get_inface_rules(network, router, interface):
    for r, rt in network.routing.routingTables:
        if r != router:
            continue
        for destination in rt.get_destinations_from(interface):
            failures = 0
            for te_group in destination.te_groups:
                yield from ((failures, rule) for rule in te_group.rules)
                failures += len(te_group.rules)


def to_pushdown(expgen, network, k):
    pda = graph.PDA()
    builder = b.PDABuilder(pda)

    # This isn't in the infocom paper, but lets just play that any interface is
    # a start location
    logger.info("Adding start location to all routings")
    startNode = _get_node_raw(pda, "simstart")
    for router in network.topology.routers:
        for interface in router.interfaces.values():
            for (failures, rule) in (
                    _get_inface_rules(network, router, interface)):
                if failures > k:
                    break

                label = builder.symbol(rule.label)
                exitNode = build_action_chain(
                    expgen,
                    builder,
                    failures,
                    router,
                    rule.to,
                    rule.actions,
                )

                # Connect the chain to the actual exitNode
                pda.transition(
                    startNode, exitNode,
                    label,
                    graph.NoopAction(),
                ).add_comment("To start the simulation").attach()
    logger.debug(f"We now have {len(pda.transitions)} transitions")

    # Link land
    # a)
    logger.info("Adding routing rules")
    for i in range(0, k+1):
        logger.info(f"For k={i}")
        for link in network.topology.links:
            for failures, rule in (
                    _get_inface_rules(network, link.to.router, link.to.interface)):  # noqa
                    if failures + i > k:
                        continue  # We don't know if they are sorted

                    label = builder.symbol(rule.label)
                    enterNode = _get_node_outface(
                        pda,
                        link.from_.router,
                        link.from_.interface,
                        (),
                        i,
                    )
                    exitNode = build_action_chain(
                        expgen,
                        builder,
                        i + failures,
                        link.to.router,
                        rule.to,
                        rule.actions,
                    )
                    pda.transition(
                        enterNode, exitNode,
                        label,
                        graph.NoopAction(),
                    ).add_comment(f"Through {rule.from_}").attach()

            for failures, rule in (
                    _get_inface_rules(network, link.from_.router, link.from_.interface)):  # noqa
                    if failures + i > k:
                        continue  # We don't know if they are sorted

                    label = builder.symbol(rule.label)
                    enterNode = _get_node_outface(
                        pda,
                        link.to.router,
                        link.to.interface,
                        (),
                        i
                    )
                    exitNode = build_action_chain(
                        expgen,
                        builder,
                        i + failures,
                        link.from_.router,
                        rule.to,
                        rule.actions,
                    )
                    pda.transition(
                        enterNode, exitNode,
                        label,
                        graph.NoopAction(),
                    ).add_comment(f"Through {rule.from_}").attach()
    logger.debug(f"We now have {len(pda.transitions)} transitions")

    # Just like the start, this isn't in the infocom paper, but lets play that
    # every interface is a valid exit as well
    logger.info("Adding end transition from all outfaces")
    exitNode = _get_node_raw(pda, "simend")
    for i in range(0, k+1):
        for router in network.topology.routers:
            for interface in router.interfaces.values():
                enterNode = _get_node_outface(pda, router, interface, (), i)
                pda.star_transition(
                    enterNode, exitNode,
                    graph.NoopAction(),
                ).attach()
    logger.debug(f"We now have {len(pda.transitions)} transitions")

    pda.start_location(startNode)
    pda.end_location(exitNode)

    return pda
