from . import graph


# @HACK: This is real dumb, but i don't really know how else to implement.
# Ideally i'd like the fragment class (possibly renamed to just pushdown) to
# somehow just "know" the alphabet, but that doesn't seem possible. My other
# idea is to pass it into the constructor (since the surrounding code probably
# already knows the alphabet) but i'm too lazy to do that everywhere. What i'm
# going to do is just make a visitor and fall back to inferrring the alphabet
# if it's not provided - Jesper Jensen 27/04-2018
class AlphabetDecider(object):
    def __init__(self):
        pass

    def collect(self, start):
        alphabet = set()
        backlog = {start}
        visited = set()
        while backlog:
            frontier = backlog
            backlog = set()
            for location in frontier:
                if location in visited:
                    continue
                visited.add(location)
                for transition in location._outgoing:
                    node = transition.to
                    alphabet.update(transition.visit(self))
                    backlog.add(node)
        return alphabet

    def visit_transition(self, transition):
        return {transition.inlabel} | transition.action.labels()

    def visit_epsilon_transition(self, transition):
        return transition.in_label_domain | transition.action.labels()


class Fragment(object):
    def __init__(self, entry, entryAlphabet, exit, exitAlphabet,
                 alphabet=None):
        self.entry = entry
        self.entryAlphabet = entryAlphabet
        self.exit = exit
        self.exitAlphabet = exitAlphabet

        self.alphabet = alphabet
        if alphabet is None:
            self.alphabet = AlphabetDecider().collect(entry)

        self._outgoing = set()

    def attach_outgoing(self, transition):
        self._outgoing.add(transition)

    @property
    def outgoing(self):
        return self._outgoing

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_fragment(self, *args, **kwargs)


class FragmentTransition(object):
    def __init__(self, from_, to, expression=graph.Guard(), text=None):
        self.from_ = from_
        self.to = to
        self.expression = expression

        self.text = text

    def attach(self):
        self.from_.attach_outgoing(self)
        return self

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_fragment_transition(self, *args, **kwargs)


class FragmentVisitor(object):
    def __init__(self):
        self.visited = set()
        self.frontier = set()
        self.exitFragments = set()

    def start(self, fragment):
        self.frontier = {fragment}
        while self.frontier:
            current_frontier = self.frontier
            self.visited |= self.frontier
            self.frontier = set()
            for node in current_frontier:
                node.visit(self)

        if len(self.exitFragments) != 1:
            raise RuntimeError(
                "There has to be EXACTLY a single exit fragment"
            )

        endFragment = self.exitFragments.pop()
        return Fragment(
            fragment.entry,
            fragment.entryAlphabet,
            endFragment.exit,
            endFragment.exitAlphabet,
        )

    def visit_fragment(self, fragment):
        if len(fragment._outgoing) == 0:
            self.exitFragments.add(fragment)

        for transition in fragment._outgoing:
            transition.visit(self)

            for label in (transition.from_.exitAlphabet
                          & transition.to.entryAlphabet):
                graph.Transition(
                    transition.from_.exit,
                    transition.to.entry,
                    label,
                    graph.NoopAction(),
                    transition.text,
                    transition.expression
                ).attach()

    def visit_fragment_transition(self, transition):
        if transition.from_ not in self.visited | self.frontier:
            self.frontier.add(transition.from_)

        if transition.to not in self.visited | self.frontier:
            self.frontier.add(transition.to)


def flatten_fragments(start):
    ttours = FragmentVisitor()
    return ttours.start(start)
