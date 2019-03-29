import io
import logging
from . import model


logger = logging.getLogger(__name__)


class TransitionCollector(object):
    def __init__(self):
        self.visited = set()
        self.frontier = set()
        self.transitions = set()

    def start(self, node):
        self.frontier = {node}
        while self.frontier:
            current_frontier = self.frontier
            self.visited |= self.frontier
            self.frontier = set()
            for node in current_frontier:
                node.visit(self)
        return self.transitions

    def visit_location(self, location):
        for transition in location._outgoing:
            transition.visit(self)
        for transition in location._incoming:
            transition.visit(self)

    def visit_transition(self, transition):
        if transition not in self.transitions:
            self.transitions.add(transition)

        if (transition.from_ not in self.visited):
            self.frontier.add(transition.from_)

        if (transition.to not in self.visited):
            self.frontier.add(transition.to)

    def visit_epsilon_transition(self, transition):
        self.visit_transition(transition)


class StarTransitionVisitor(object):
    def make_string(self, eps_transition):
        return eps_transition.visit(self)

    def visit_location(self, location):
        return location.name

    def visit_pop(self, action):
        return ""

    def visit_push(self, action):
        return f"{action.label.visit(self)} *"

    def visit_noop(self, action):
        return "*"

    def visit_replace(self, action):
        return f"{action.label.visit(self)}"

    def visit_pushreplace(self, action):
        return f"{action.label1.visit(self)} {action.label2.visit(self)}"

    def visit_guard(self, guard):
        return f"({guard.expression})"

    def visit_label(self, label):
        return "_" + str(label)

    def visit_special_label(self, label):
        return str(label)

    def visit_epsilon_transition(self, transition):
        from_str = transition.from_.visit(self)
        to_str = transition.to.visit(self)
        outlabel_str = transition.action.visit(self)
        guard_str = transition.guard.visit(self)

        return "{}<*> --> {}<{}> {}".format(
            from_str,
            to_str,
            outlabel_str,
            guard_str,
        )

    def visit_star_transition(self, transition):
        return self.visit_epsilon_transition(transition)


class PerfectPrintVisitor(object):
    def __init__(self):
        pass

    def specify_list(self, transitions):
        for transition in transitions:
            transition.comments.append(transition.visit(self))

    def visit_location(self, location):
        return repr(location)

    def visit_pop(self, action, inlabel=None):
        return ""

    def visit_push(self, action, inlabel=None):
        return (action.label.visit(self), inlabel.visit(self))

    def visit_noop(self, action, inlabel=None):
        return (inlabel.visit(self), )

    def visit_replace(self, action, inlabel=None):
        return (action.label.visit(self), )

    def visit_pushreplace(self, action, inlabel=None):
        return (
            action.label1.visit(self),
            action.label2.visit(self),
        )

    def visit_label(self, label):
        return repr(label)

    def visit_special_label(self, label):
        return repr(label)

    def visit_transition(self, transition):
        from_str = transition.from_.visit(self)
        to_str = transition.to.visit(self)
        in_label_str = transition.inlabel.visit(self)
        out_label_str = ','.join(
            transition.action.visit(self, inlabel=transition.inlabel)
        )

        return "{}<{}> --> {}<{}>".format(
            from_str,
            in_label_str,
            to_str,
            out_label_str,
        )

    def visit_star_transition(self, transition):
        return self.visit_epsilon_transition(transition)

    def visit_epsilon_transition(self, transition):
        from_str = transition.from_.visit(self)
        to_str = transition.to.visit(self)
        in_label_str = '*'
        out_label_str = ','.join(
            "_WHO_KNOWS_"
            # @INCOMPLETE: You can't just create arbitrary labels
            # transition.action.visit(self, inlabel=graph.Label('*'))
        )

        return "{!r}<{!r}> --> {!r}<{!r}>".format(
            from_str,
            in_label_str,
            to_str,
            out_label_str,
        )


class MopedPrintVisitor(object):
    def __init__(self, possible_tops):
        self.star_stringifyer = StarTransitionVisitor()
        self.possible_tops = possible_tops

    def specify_list(self, transitions, f, mapping, transition_mapping):
        self.transition_mapping = transition_mapping
        self.mapping = mapping
        # Then we print!
        size = 0
        for transition in transitions:
            size += transition.visit(self, f)

        return size

    def visit_location(self, location):
        return self.mapping[location]

    def visit_pop(self, action, inlabel=None):
        return ()

    def visit_push(self, action, inlabel=None):
        return (
            action.label.visit(self),
            inlabel.visit(self)
        )

    def visit_noop(self, action, inlabel=None):
        return (inlabel.visit(self), )

    def visit_replace(self, action, inlabel=None):
        return (action.label.visit(self), )

    def visit_pushreplace(self, action, inlabel=None):
        return (
            action.label1.visit(self),
            action.label2.visit(self),
        )

    def visit_guard(self, guard):
        return (f"({guard.expression})"
                if guard.expression is not None
                else None)

    def visit_label(self, label):
        return self.mapping[label]

    def visit_special_label(self, label):
        return self.mapping[label]

    def visit_transition(self, transition, f):
        if transition.inlabel not in self.possible_tops[transition.from_]:
            return 0
        outlabels = transition.action.visit(self, inlabel=transition.inlabel)
        if len(outlabels) == 0:
            outlabel1 = None
            outlabel2 = None
        elif len(outlabels) == 1:
            outlabel1 = outlabels[0]
            outlabel2 = None
        elif len(outlabels) == 2:
            outlabel1 = outlabels[0]
            outlabel2 = outlabels[1]
        else:
            raise RuntimeError(f"Internal error: Wrong numer of out"
                               f"labels in compiler: {len(outlabels)}")

        model.emit_comments(f, transition.comments)
        model.emit_transition(
            f,
            transition.from_.visit(self),
            transition.inlabel.visit(self),
            transition.to.visit(self),
            outlabel1, outlabel2,
            self.transition_mapping[transition],
            transition.guard.visit(self),
        )
        return 1

    def visit_epsilon_transition(self, transition, f):
        model.emit_comments(f, transition.comments)
        eps = self.star_stringifyer.make_string(transition)
        with model.emit_transition_group(f, eps):
            from_str = transition.from_.visit(self)
            to_str = transition.to.visit(self)
            text_str = self.transition_mapping[transition]
            guard_str = transition.guard.visit(self)

            for inlabel in transition.in_label_domain:
                inlabel_str = inlabel.visit(self)

                outlabels = transition.action.visit(self, inlabel=inlabel)
                if len(outlabels) == 0:
                    outlabel1 = None
                    outlabel2 = None
                elif len(outlabels) == 1:
                    outlabel1 = outlabels[0]
                    outlabel2 = None
                elif len(outlabels) == 2:
                    outlabel1 = outlabels[0]
                    outlabel2 = outlabels[1]
                else:
                    raise RuntimeError(f"Internal error: Wrong numer of out"
                                       f"labels in compiler: {len(outlabels)}")

                model.emit_transition(
                    f,
                    from_str,
                    inlabel_str,
                    to_str,
                    outlabel1,
                    outlabel2,
                    text_str,
                    guard_str,
                )
        return len(transition.in_label_domain)

    def visit_star_transition(self, transition, f):
        model.emit_comments(f, transition.comments)
        eps = self.star_stringifyer.make_string(transition)
        with model.emit_transition_group(f, eps):
            from_str = transition.from_.visit(self)
            to_str = transition.to.visit(self)
            text_str = self.transition_mapping[transition]
            guard_str = transition.guard.visit(self)

            for inlabel in self.possible_tops[transition.from_]:
                inlabel_str = inlabel.visit(self)

                outlabels = transition.action.visit(self, inlabel=inlabel)
                if len(outlabels) == 0:
                    outlabel1 = None
                    outlabel2 = None
                elif len(outlabels) == 1:
                    outlabel1 = outlabels[0]
                    outlabel2 = None
                elif len(outlabels) == 2:
                    outlabel1 = outlabels[0]
                    outlabel2 = outlabels[1]
                else:
                    raise RuntimeError(f"Internal error: Wrong numer of out"
                                       f"labels in compiler: {len(outlabels)}")

                model.emit_transition(
                    f,
                    from_str,
                    inlabel_str,
                    to_str,
                    outlabel1,
                    outlabel2,
                    text_str,
                    guard_str,
                )
        return len(self.possible_tops[transition.from_])


class TopResolver(object):
    def __init__(self, pda):
        self.pda = pda

    def visit_push(self, action, inlabel=None):
        return {action.label}

    def visit_replace(self, action, inlabel=None):
        return {action.label}

    def visit_pushreplace(self, action, inlabel=None):
        return {action.label1}

    def visit_pop(self, action, inlabel=None):
        return self.pda.symbols

    def visit_noop(self, action, inlabel=None):
        return inlabel

    def visit_transition(self, transition, labels):
        if transition.inlabel not in labels:
            return set()
        return transition.action.visit(self, inlabel={transition.inlabel})

    def visit_epsilon_transition(self, transition, labels):
        if labels & transition.in_label_domain == set():
            return set()
        return transition.action.visit(
            self,
            inlabel=labels & transition.in_label_domain,
        )

    def visit_star_transition(self, transition, labels):
        return transition.action.visit(self, labels)

iteration_count = 10000
def compile(expgen, pda, start_label, end_label, emit_comments=True):
    # This is where we calculate the top of stack for every location
    # @CLEANUP: Hoist this to somewhere more appropriate, I'm thinking in the
    # general pushdown operations, since it's pretty generic -Jesper 19/06-2018
    logger.info("Calculating the possible tops of stack")
    T = {}
    Tfront = {
        pda.initial
    }

    resolver = TopResolver(pda)
    for location in pda.locations:
        T[location] = set()
    T[pda.initial].add(start_label)

    # Some values to print while doing the pruning
    max_front = 0
    count = 0
    while Tfront:
        count += 1
        max_front = max(len(Tfront), max_front)
        if count % iteration_count == 0:
            print(f"Iteration {count}.")
            print(f"Max front in last batch: {max_front}.")
            max_front = 0
        location = Tfront.pop()

        for transition in location._outgoing:
            addedTops = transition.visit(resolver, T[location])
            newTops = addedTops - T[transition.to]
            if newTops:
                Tfront.add(transition.to)
                T[transition.to].update(newTops)

    for (key, value) in T.items():
        print(f"(key, value) = ({key},\n\t {value})")

    # f = open("pds.pds", "wt")
    f = io.StringIO()

    # First we mangle!
    logger.info("Assigning new names")
    mapping = {}
    transition_mapping = {}
    count = 0
    for transition in pda.transitions:
        transition_mapping[transition] = str(count)
        count += 1
    for symbol in pda.symbols:
        mapping[symbol] = f"_{count}"
        count += 1
    for location in pda.locations:
        mapping[location] = f"_{count}"
        count += 1

    # Then we dangle (make it pretty)!
    if emit_comments:
        logger.info("Pretty printing")
        perfect_printer = PerfectPrintVisitor()
        perfect_printer.specify_list(pda.transitions)

    variables = ",".join(["var_0 (4)"])
    model.emit_system_start(
        f,
        variables,
        mapping[pda.initial],
        mapping[pda.final],
        mapping[start_label],
        mapping[end_label],
    )
    compiler = MopedPrintVisitor(T)

    logger.info("Emitting transitions")
    size = compiler.specify_list(
        pda.transitions,
        f,
        mapping,
        transition_mapping,
    )

    # f.close()

    return model.System(f, size, pda.final, end_label, mapping,
                        transition_mapping)

# Ingo's fancy code attempt

class TopResolver2(object):
    def __init__(self, pda):
        self.pda = pda

    def visit_push(self, action, inlabel=None, **kwargs):
        return ({action.label}, inlabel)

    def visit_replace(self, action, inlabel=None, **kwargs):
        return ({action.label}, set())

    def visit_pushreplace(self, action, inlabel=None, **kwargs):
        return ({action.label1}, {action.label2})

    def visit_pop(self, action, inlabel=None, **kwargs):
        return (kwargs['stransition'], set())

    def visit_noop(self, action, inlabel=None, **kwargs):
        return (inlabel, set())

    def visit_transition(self, transition, labels, **kwargs):
        if transition.inlabel not in labels:
            return (set(), set())
        return transition.action.visit(self, inlabel={transition.inlabel}, **kwargs)

    def visit_epsilon_transition(self, transition, labels, **kwargs):
        if labels & transition.in_label_domain == set():
            return (set(), set())
        return transition.action.visit(
            self,
            inlabel=labels & transition.in_label_domain,
        )

    def visit_star_transition(self, transition, labels, **kwargs):
        return transition.action.visit(self, labels, **kwargs)


def compile2(expgen, pda, start_label, end_label, emit_comments=True):
    # This is where we calculate the top of stack for every location
    # @CLEANUP: Hoist this to somewhere more appropriate, I'm thinking in the
    # general pushdown operations, since it's pretty generic -Jesper 19/06-2018
    logger.info("Calculating the possible tops of stack")
    T = {}
    S = {}
    Tfront = {
        pda.initial
    }

    resolver = TopResolver2(pda)
    for location in pda.locations:
        T[location] = set()
        S[location] = set()
    T[pda.initial].add(start_label)

    # Some values to print while doing the pruning
    max_front = 0
    count = 0
    while Tfront:
        count += 1
        max_front = max(len(Tfront), max_front)
        if count % iteration_count == 0:
            print(f"Iteration {count}.")
            print(f"Max front in last batch: {max_front}.")
            max_front = 0
        location = Tfront.pop()

        for transition in location._outgoing:
            addedTops, addedTails = transition.visit(resolver, T[location], stransition=S[location])
            newTops = addedTops - T[transition.to]
            newTails = (S[location] | addedTails) - S[transition.to] #?
            if newTops or newTails:
                Tfront.add(transition.to)
                T[transition.to].update(newTops)
                S[transition.to].update(newTails)

    for (key, value) in T.items():
        print(f"(key, value) = ({key},\n\t {value})")

    # f = open("pds.pds", "wt")
    f = io.StringIO()

    # First we mangle!
    logger.info("Assigning new names")
    mapping = {}
    transition_mapping = {}
    count = 0
    for transition in pda.transitions:
        transition_mapping[transition] = str(count)
        count += 1
    for symbol in pda.symbols:
        mapping[symbol] = f"_{count}"
        count += 1
    for location in pda.locations:
        mapping[location] = f"_{count}"
        count += 1

    # Then we dangle (make it pretty)!
    if emit_comments:
        logger.info("Pretty printing")
        perfect_printer = PerfectPrintVisitor()
        perfect_printer.specify_list(pda.transitions)

    variables = ",".join(["var_0 (4)"])
    model.emit_system_start(
        f,
        variables,
        mapping[pda.initial],
        mapping[pda.final],
        mapping[start_label],
        mapping[end_label],
    )
    compiler = MopedPrintVisitor(T)

    logger.info("Emitting transitions")
    size = compiler.specify_list(
        pda.transitions,
        f,
        mapping,
        transition_mapping,
    )

    # f.close()

    return model.System(f, size, pda.final, end_label, mapping,
                        transition_mapping)