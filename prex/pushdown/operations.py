from . import graph

from functools import singledispatch
import logging


logger = logging.getLogger(__name__)


class ReplicateActionVisitor(object):
    def __init__(self, pda, symbols):
        self.pda = pda
        self.symbols = symbols

    def visit_noop(self, action):
        return graph.NoopAction()

    def visit_pop(self, action):
        return graph.PopAction()

    def visit_push(self, action):
        label = self.symbols[action.label.value]
        return graph.PushAction(label)

    def visit_replace(self, action):
        label = self.symbols[action.label.value]
        return graph.ReplaceAction(label)

    def visit_pushreplace(self, action):
        label1 = self.symbols[action.label1.value]
        label2 = self.symbols[action.label2.value]
        return graph.PushReplaceAction(label1, label2)


def concat_disjoint(p1, p2, destructive=False):
    skip1 = False
    skip2 = False
    if destructive:
        logger.info("We are being destructive")
        if len(p1.transitions) < len(p2.transitions):
            logger.info("P2 is reused")
            skip2 = True
            pda = p2
        else:
            logger.info("P1 is reused")
            skip1 = True
            pda = p1
    else:
        pda = graph.PDA()

    symbols = {}
    # Union the alphabets
    logger.info(f"Transferring {len(p1.symbols)} symbols from P1")
    for symbol in p1.symbols:
        if skip1:
            symbols[symbol.value] = symbol
        else:
            if symbol.value not in symbols:
                symbols[symbol.value] = pda.symbol(symbol.value)

    logger.info(f"Transferring {len(p2.symbols)} symbols from P2")
    for symbol in p2.symbols:
        if skip2:
            symbols[symbol.value] = symbol
        else:
            if symbol.value not in symbols:
                symbols[symbol.value] = pda.symbol(symbol.value)

    if not skip1:
        for k, v in p1.specials.items():
            pda.specials[k] = symbols[v.value]

    if not skip2:
        for k, v in p2.specials.items():
            pda.specials[k] = symbols[v.value]

    locations = {}
    # Union locations, since we are computing the disjoint concat, we don't
    # deduplicate based on value
    logger.info(f"Transferring {len(p1.locations)} locations from P1")
    for location in p1.locations:
        if skip1:
            locations[location] = location
        else:
            locations[location] = pda.location(location.name)

    logger.info(f"Transferring {len(p2.locations)} locations from P2")
    for location in p2.locations:
        if skip2:
            locations[location] = location
        else:
            locations[location] = pda.location(location.name)

    replicateVisitor = ReplicateActionVisitor(pda, symbols)

    @singledispatch
    def add_trans(transition, pda):
        symbol = symbols[transition.inlabel.value]
        action = transition.action.visit(replicateVisitor)
        from_ = locations[transition.from_]
        to = locations[transition.to]
        pda.transition(
            from_,
            to,
            symbol,
            action,
            transition.text,
            transition.guard
        ).attach()

    @add_trans.register(graph.StarTransition)
    def add_star(transition, pda):
        action = transition.action.visit(replicateVisitor)
        from_ = locations[transition.from_]
        to = locations[transition.to]
        pda.star_transition(
            from_, to,
            action,
            transition.text,
            transition.guard
        ).attach()

    if not skip1:
        logger.info(f"Transferring {len(p1.transitions)} transitions from P1")
        for transition in p1.transitions:
            add_trans(transition, pda)

    if not skip2:
        logger.info(f"Transferring {len(p2.transitions)} transitions from P2")
        for transition in p2.transitions:
            add_trans(transition, pda)

    p1_end = locations[p1.final]
    p2_start = locations[p2.initial]

    pda.star_transition(
        p1_end,
        p2_start,
        graph.NoopAction()
    ).attach()

    if skip1:
        p1.final = None
    if skip2:
        p2.initial = None

    if not skip1:
        pda.start_location(locations[p1.initial])

    if not skip2:
        pda.end_location(locations[p2.final])

    return pda
