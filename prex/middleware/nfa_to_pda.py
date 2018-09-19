from . import (
    builder,
)
from prex.pushdown import (
    graph as pda,
)


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

        self.pda.start_location(self.nfa.initial.visit(self))
        self.pda.end_location(self.nfa.final.visit(self))

        return self.pda

    def visit_location(self, location, *args, **kwargs):
        return self.builder.location(location.name)

    def visit_symbol(self, symbol, *args, **kwargs):
        return self.builder.symbol(symbol.value)

    def visit_transition(self, transition, *args, **kwargs):
        from_ = transition.from_.visit(self)
        to = transition.to.visit(self)
        symbol = transition.symbol.visit(self)
        self.pda.star_transition(
            from_,
            to,
            pda.PushAction(symbol),
        ).attach()

    def visit_epsilon_transition(self, transition, *args, **kwargs):
        from_ = transition.from_.visit(self)
        to = transition.to.visit(self)
        self.pda.star_transition(
            from_,
            to,
            pda.NoopAction(),
        ).attach()


class DestructingPDA:
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
        return self.builder.location(f"destroy_{step}")

    def convert(self):
        if self.next_step != 0:
            raise RuntimeError('Tried to convert NFA to PDA twice')

        self.pda.specials["end"] = self.builder.bos()
        # Construct PDA from NFA
        for transition in self.nfa.transitions:
            transition.visit(self)

        self.pda.start_location(self.nfa.initial.visit(self))
        self.pda.end_location(self.nfa.final.visit(self))

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
            symbol,
            pda.PopAction(),
        ).attach()

    def visit_epsilon_transition(self, transition, *args, **kwargs):
        from_ = transition.from_.visit(self)
        to = transition.to.visit(self)
        self.pda.star_transition(
            from_,
            to,
            pda.NoopAction(),
        ).attach()
