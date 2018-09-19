class Location(object):
    def __init__(self, nfa, name):
        self.nfa = nfa
        self.name = name
        self._incoming = []
        self._outgoing = []

        self.nfa.attach_location(self)

    def attach_outgoing(self, transition):
        self._outgoing.append(transition)

    def attach_incoming(self, transition):
        self._incoming.append(transition)

    def detach_outgoing(self, transition):
        self._outgoing.remove(transition)

    def detach_incoming(self, transition):
        self._incoming.remove(transition)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_location(self, *args, **kwargs)

    def __repr__(self):
        return f'<NFALocation {self.name!r} {id(self)}>'


class Symbol(object):
    _symbols = dict()

    def __init__(self, nfa, value):
        self.nfa = nfa
        self._value = value
        self.nfa.attach_symbol(self)

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        try:
            return self.str
        except AttributeError:
            self.str = self.value
            return str(self)

    def __repr__(self):
        return repr(self.value)

    @classmethod
    def get_symbol(cls, value):
        try:
            return cls._symbols[value]
        except KeyError:
            symbol = cls(value)
            cls._symbols[value] = symbol
            return cls.get_symbol(value)

    @classmethod
    def get_symbols(cls, values):
        return {cls.get_symbol(value) for value in values}

    @property
    def value(self):
        return self._value

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_symbol(self, *args, **kwargs)


class Transition(object):
    def __init__(self, nfa, from_, to, symbol):
        self.nfa = nfa
        self.from_ = from_
        self.to = to

        self.symbol = symbol

    def attach(self):
        self.nfa.attach_transition(self)
        self.from_.attach_outgoing(self)
        self.to.attach_incoming(self)
        return self

    def detach(self):
        self.nfa.detach_transition(self)
        self.from_.detach_outgoing(self)
        self.to.detach_incoming(self)
        return self

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_transition(self, *args, **kwargs)

    def __repr__(self):
        return f'<NFATransition {self.from_!r}{self.to!r}{self.symbol!r}{id(self)}'  # noqa


class EpsilonTransition(object):
    def __init__(self, nfa, from_, to):
        self.nfa = nfa
        self.from_ = from_
        self.to = to

    def attach(self):
        self.nfa.attach_transition(self)
        self.from_.attach_outgoing(self)
        self.to.attach_incoming(self)
        return self

    def detach(self):
        self.nfa.detach_transition(self)
        self.from_.detach_outgoing(self)
        self.to.detach_incoming(self)
        return self

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_epsilon_transition(self, *args, **kwargs)


class NFA(object):
    def __init__(self):
        self.initial = None
        self.final = None

        self.locations = set()
        self.transitions = set()
        self.symbols = set()
        pass

    def start_location(self, name):
        location = self.location(name)
        assert(self.initial is None)
        self.initial = location
        return location

    def end_location(self, name):
        location = self.location(name)
        assert(self.final is None)
        self.final = location
        return location

    def location(self, name):
        return Location(self, name)

    def attach_location(self, transition):
        self.locations.add(transition)

    def transition(self, from_, to, symbol):
        return Transition(self, from_, to, symbol)

    def epsilon_transition(self, from_, to):
        return EpsilonTransition(self, from_, to)

    def attach_transition(self, transition):
        self.transitions.add(transition)

    def detach_transition(self, transition):
        self.transitions.remove(transition)

    def symbol(self, name):
        return Symbol(self, name)

    def attach_symbol(self, symbol):
        self.symbols.add(symbol)
