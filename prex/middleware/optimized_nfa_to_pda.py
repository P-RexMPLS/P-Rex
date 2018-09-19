from . import (
    builder,
)
from prex.pushdown import (
    graph as pda,
)
from . import nfa_to_pda


DestructingPDA = nfa_to_pda.DestructingPDA


class ConstructingPDA:
    def __init__(self, expgen, nfa):
        self.expgen = expgen
        self.pda = pda.PDA()
        self.nfa = nfa
        self.builder = builder.PDABuilder(self.pda)
        self.next_step = 0

    def _create_node(self):
        node = self._make_node(self.next_step)
        self.next_step += 1
        return node

    def _make_node(self, step):
        return self.builder.location(f"build_{step}")

    def convert(self):
        if self.next_step != 0:
            raise RuntimeError('Tried to convert NFA to PDA twice')

        self.pda.specials["start"] = self.builder.bos()
        # Construct PDA from NFA
        for transition in self.nfa.transitions:
            transition.visit(self)

        # Fix-up start location, adding a location and transition before
        # pushing the star symbol on top of BOS
        start_node = self._create_node()
        self.pda.transition(
            start_node,
            self.builder.location(self.nfa.initial.name),
            self.builder.bos(),
            pda.PushAction(self.builder.star())
        ).attach()
        self.pda.start_location(start_node)

        # Fix-up end location, adding a location and transition after
        # removing the star symbol left over
        end_node = self._create_node()
        self.pda.transition(
            self.builder.location(self.nfa.final.name),
            end_node,
            self.builder.star(),
            pda.PopAction()
        ).attach()
        self.pda.end_location(end_node)

        return self.pda

    def visit_location(self, location, *args, **kwargs):
        return self.builder.location(location.name)

    def visit_symbol(self, symbol, *args, **kwargs):
        return self.builder.symbol(symbol.value)

    def visit_transition(self, transition, *args, **kwargs):
        from_ = transition.from_.visit(self)
        to = transition.to.visit(self)
        symbol = transition.symbol.visit(self)
        self.pda.transition(
            from_,
            to,
            self.builder.star(),
            pda.PushReplaceAction(self.builder.star(), symbol),
        ).attach()

    def visit_epsilon_transition(self, transition, *args, **kwargs):
        from_ = transition.from_.visit(self)
        to = transition.to.visit(self)
        self.pda.star_transition(
            from_,
            to,
            pda.NoopAction(),
        ).attach()

