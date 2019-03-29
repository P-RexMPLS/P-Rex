class Action():
    def labels(self):
        return set()

class NoopAction(Action):
    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_noop(self, *args, **kwargs)

class PopAction(Action):
    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pop(self, *args, **kwargs)

class LabelAction(Action):
    def __init__(self, label):
        self.label = label

    def labels(self):
        return {self.label}

class PushAction(LabelAction):
    def __init__(self, label):
        super(PushAction, self).__init__(label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_push(self, *args, **kwargs)


class ReplaceAction(LabelAction):
    def __init__(self, label):
        super(ReplaceAction, self).__init__(label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_replace(self, *args, **kwargs)

class PushReplaceAction(Action):
    def __init__(self, label1, label2):
        self.label1 = label1
        self.label2 = label2

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pushreplace(self, *args, **kwargs)

    def labels(self):
        return {self.label1, self.label2}


class Guard(object):
    def __init__(self, expression=None):
        self.expression = expression

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_guard(self, *args, **kwargs)


class Label(object):
    _labels = dict()

    def __init__(self, pda, value):
        self._value = value

        pda._attach_symbol(self)

    def __eq__(self, other):
        try:
            return self.value == other.value
        except AttributeError:
            return False

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"<Label: {self.value!r}>"

    @property
    def value(self):
        return self._value

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_label(self, *args, **kwargs)

class Location(object):
    def __init__(self, pda, name):
        self.name = name
        self._incoming = []
        self._outgoing = []

        pda._attach_location(self)

    def attach_outgoing(self, transition):
        self._outgoing.append(transition)

    def attach_incoming(self, transition):
        self._incoming.append(transition)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_location(self, *args, **kwargs)

    def __repr__(self):
        return f"<Location {self.name}@{id(self)}>"

class ATransition(object):
    def __init__(self, pda, from_, to, action, text=None,
                 guard=Guard()):
        self.from_ = from_
        self.to = to

        self.action = action

        self.text = text
        self.guard = guard

        self.comments = []

        self.pda = pda

    def attach(self):
        self.pda._attach_transition(self)
        self.from_.attach_outgoing(self)
        self.to.attach_incoming(self)
        return self

    def add_comment(self, comment):
        self.comments.append(comment)
        return self

    def visit(self, visitor, *args, **kwargs):
        raise NotImplementedError("Calling visit on Abstract Transition.")

    def __repr__(self):
        raise NotImplementedError("Abstract Transition has no representation.")

# @IMPROVEMENT: Maybe we should have some "graph" class that we pass into all
# these objects.
class Transition(ATransition):
    def __init__(self, pda, from_, to, inlabel, action, text=None,
                 guard=Guard()):
        super(Transition, self).__init__(pda, from_, to, action, text, guard)
        self.inlabel = inlabel

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_transition(self, *args, **kwargs)

    def __repr__(self):
        return (
            f'{self.inlabel}{self.from_!r}{self.to!r}{self.action!r}'
            f'<{id(self)}>'
        )


class StarTransition(ATransition):
    def __init__(self, pda, from_, to, action, text=None,
                 guard=Guard()):
        super(StarTransition, self).__init__(pda, from_, to, action, text, guard)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_star_transition(self, *args, **kwargs)

    def __repr__(self):
        return f'(*){self.from_!r}{self.to!r}{self.action!r}{id(self)}'


class PDA(object):
    def __init__(self):
        self.initial = None
        self.final = None

        self.symbols = set()
        self.locations = set()
        self.transitions = set()
        

        self.specials = {}

    def start_location(self, location):
        assert(self.initial is None)
        self.initial = location
        return location

    def end_location(self, location):
        assert(self.final is None)
        self.final = location
        return location


    # Only called in Label.__init__
    def _attach_symbol(self, symbol):
        self.symbols.add(symbol)

    # Only called in Location.__init__
    def _attach_location(self, location):
        self.locations.add(location)

    # Only called in ATransition.attach
    def _attach_transition(self, transition):
        self.transitions.add(transition)


    def symbol(self, value):
        return Label(self, value)
        
    def location(self, name):
        return Location(self, name)

    def transition(self, from_, to, symbol, action, text=None, guard=Guard()):
        return Transition(self, from_, to, symbol, action, text, guard)

    def star_transition(self, from_, to, action, text=None, guard=Guard()):
        return StarTransition(
            self,
            from_,
            to,
            action,
            text,
            guard
        )




