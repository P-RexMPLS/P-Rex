from ..pushdown import (
    graph,
)
from ..nfa import graph as nfagraph
from . import builder as b
import logging

logger = logging.getLogger(__name__)

locations = {}


class ReplicateActionVisitor(object):
    def __init__(self, builder):
        self.builder = builder

    def visit_noop(self, action):
        return graph.NoopAction()

    def visit_pop(self, action):
        return graph.PopAction()

    def visit_push(self, action):
        label = self.builder.symbol(action.label.value)
        return graph.PushAction(label)

    def visit_replace(self, action):
        label = self.builder.symbol(action.label.value)
        return graph.ReplaceAction(label)

    def visit_pushreplace(self, action):
        label1 = self.builder.symbol(action.label1.value)
        label2 = self.builder.symbol(action.label2.value)
        return graph.PushReplaceAction(label1, label2)


def _get_node_raw(builder, string):
    return builder.location(string)


def _get_node_compose(builder, pdaloc, nfaloc):
    key = (pdaloc, nfaloc)
    return builder.location(key)


class PushdownTransitionCollector(object):
    def __init__(self):
        pass

    def run(self, start):
        backlog = {start}
        visited = set()
        transitions = set()
        while backlog:
            frontier = backlog
            backlog = set()
            for location in frontier:
                if location in visited:
                    continue
                visited.add(location)
                for transition in location._outgoing:
                    node = transition.visit(self)
                    backlog.add(node)
                    transitions.add(transition)
        return (transitions, visited)

    def visit_transition(self, transition):
        return transition.to

    def visit_epsilon_transition(self, transition):
        return transition.to


def compose(pushdown, nfa):
    logger.info("Split nfa transitions into epsilon/non-epsilon")
    nfa_epsilon = []
    nfa_non_epsilon = []
    for transition in nfa.transitions:
        if isinstance(transition, nfagraph.EpsilonTransition):
            nfa_epsilon.append(transition)
        else:
            nfa_non_epsilon.append(transition)

    pda = graph.PDA()
    builder = b.PDABuilder(pda)

    newPDAStart = pushdown.location("apda_start")
    startNode = _get_node_compose(builder, newPDAStart, nfa.initial)
    pda.start_location(startNode)

    logger.info("Start transitions")
    for transition in nfa_non_epsilon:

        if transition.symbol.value != pushdown.initial:
            continue

        exitNode = _get_node_compose(builder, pushdown.initial, transition.to)

        pda.star_transition(
            startNode, exitNode,
            graph.NoopAction(),
        ).attach()

    logger.info("Epsilon loops")
    for transition in nfa_epsilon:
        for location in pushdown.locations:

            enterNode = _get_node_compose(builder, location, transition.from_)
            exitNode = _get_node_compose(builder, location, transition.to)

            pda.star_transition(
                enterNode, exitNode,
                graph.NoopAction()
            ).attach()

    replicateVisitor = ReplicateActionVisitor(builder)

    logger.info(f"Cross product (nfa tranitions: {len(nfa_non_epsilon)})")
    for nfaTrans in nfa_non_epsilon:
        for pdaTrans in nfaTrans.symbol.value._incoming:
            enterNode = _get_node_compose(builder, pdaTrans.from_,
                                          nfaTrans.from_)
            exitNode = _get_node_compose(builder, pdaTrans.to, nfaTrans.to)

            if isinstance(pdaTrans, graph.StarTransition):
                action = pdaTrans.action.visit(replicateVisitor)
                pda.star_transition(
                    enterNode, exitNode,
                    action,
                    pdaTrans.text,
                    pdaTrans.guard,
                ).attach()
            elif isinstance(pdaTrans, graph.Transition):
                symbol = builder.symbol(pdaTrans.inlabel.value)
                action = pdaTrans.action.visit(replicateVisitor)
                pda.transition(
                    enterNode, exitNode,
                    symbol,
                    action,
                    pdaTrans.text,
                    pdaTrans.guard,
                ).attach()
            else:
                raise RuntimeError(f"Unkonwn transition type {pdaTrans}")

    finalNode = _get_node_compose(builder, pushdown.final, nfa.final)
    pda.end_location(finalNode)

    logging.info(f"Complete (size: {len(pda.transitions)})")

    return pda
