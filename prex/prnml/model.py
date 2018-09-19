class Interface(object):
    def __init__(self, name, router, external=False):
        self.name = name
        self.router = router
        self.external = external

    def __repr__(self):
        return f"<Interface {self.name!r}@{id(self)}>"


class Router(object):
    def __init__(self, name, interfaces=None):
        self.name = name
        self.interfaces = interfaces if interfaces is not None else {}

    def addInterface(self, name, external=False):
        if name in self.interfaces:
            interface = self.interfaces[name]
        else:
            interface = Interface(name, self, external)
            self.interfaces[name] = interface
        return interface

    def getInterface(self, name):
        return self.interfaces[name]

    def __repr__(self):
        return f"<Router {self.name!r}@{id(self)}>"


class Link(object):
    def __init__(self, from_, to):
        self.from_ = from_
        self.to = to

    def __str__(self):
        return f"{self.from_.router.name}_{self.to.router.name}"

    def __repr__(self):
        return f"<Link {self.from_!r} -> {self.to!r}>"


class SharedInterface(object):
    def __init__(self, router, interface):
        self.router = router
        self.interface = interface

    def __repr__(self):
        return f'<SI {self.router!r}:{self.interface!r}>'


class Destination(object):
    def __init__(self, from_, label, te_groups=None):
        self.from_ = from_
        self.label = label
        # Ordering according to priority. Highest first
        self.te_groups = te_groups if te_groups else []

    def add_te_group(self, te_group):
        self.te_groups.append(te_group)

    def add_te_groups(self, te_groups):
        self.te_groups.extend(te_groups)

    def count_rules(self):
        return sum(te_group.count_rules() for te_group in self.te_groups)

    def collect_labels(self):
        labels = set()
        for te_group in self.te_groups:
            labels.update(te_group.collect_labels())
        return labels

    def __repr__(self):
        return f'({self.label!r}){self.from_!r}:{len(self.te_groups)} TEGroups'


class TEGroup(object):
    def __init__(self, rules=None):
        self.rules = rules if rules is not None else []

    def add_rule(self, rule):
        self.rules.append(rule)

    def count_rules(self):
        return len(self.rules)

    def collect_labels(self):
        labels = set()
        for rule in self.rules:
            labels.update(rule.collect_labels())
        return labels

    def __repr__(self):
        return f''


class Rule(object):
    def __init__(self, from_, to, label, actions):
        self.from_ = from_
        self.to = to
        self.label = label
        self.actions = actions

    def __str__(self):
        return f'{self.from_} -{self.label}-{"-".join((str(a) for a in self.actions))}> {self.to}'  # noqa

    def __repr__(self):
        return f'<Rule {self.from_!r} -> {self.to!r} for {self.label!r}>'

    def clone(self):
        return type(self)(
            self.from_,
            self.to,
            self.label,
            tuple([action.clone() for action in self.actions])
        )

    def collect_labels(self):
        labels = set()
        if self.label.collectable:
            labels.add(self.label)
        for action in self.actions:
            labels.update(action.collect_labels())
        return labels


class RoutingTable(object):
    def __init__(self, router, destinations):
        self.router = router
        # dict: (from_, label) -> destination
        self.destinations = destinations

    def get_destination(self, from_, label):
        return self.destinations[(from_, label)]

    def get_destinations_from(self, from_):
        for (dest_from, _), destination in self.destinations.items():
            if dest_from == from_:
                yield destination

    def get_destinations_label(self, label):
        for (_, dest_label), destination in self.destinations.items():
            if dest_label == label:
                yield destination

    def set_destination(self, destination):
        self.destinations[(destination.from_, destination.label)] = destination

    def count_rules(self):
        return sum(destination.count_rules()
                   for destination in self.destinations.values())

    def collect_labels(self):
        labels = set()
        for destination in self.destinations.values():
            labels.update(destination.collect_labels())
        return labels


class Label(object):
    def __init__(self, name):
        self.name = name
        self.collectable = True

    def __repr__(self):
        return f'<Label {self.name!r}@{id(self)}>'


class NoLabel(Label):
    def __init__(self):
        super().__init__("__NOLABEL__")
        self.collectable = False

    def __repr__(self):
        return f'<NOLABEL>'


class SwapAction(object):
    def __init__(self, label):
        self._label = label

    @property
    def label(self):
        return self._label

    def collect_labels(self):
        return {self.label}

    def clone(self):
        return type(self)(self.label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_swapaction(self, *args, **kwargs)

    def __repr__(self):
        return f'<SWAP {self.label!r}>'

    def __eq__(self, other):
        return (
            isinstance(other, SwapAction) and
            self.label == other.label
        )

    def __hash__(self):
        return hash((self.label,))


class PopAction(object):
    def __init__(self):
        pass

    def collect_labels(self):
        return set()

    def getDesc(self):
        return "pop"

    def clone(self):
        return type(self)()

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_popaction(self, *args, **kwargs)

    def __repr__(self):
        return f'<POP>'

    def __eq__(self, other):
        return isinstance(other, PopAction)

    def __hash__(self):
        return hash(NoopAction)


class NoopAction(object):
    def __init__(self):
        pass

    def collect_labels(self):
        return set()

    def getDesc(self):
        return "noop"

    def clone(self):
        return type(self)()

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_noopaction(self, *args, **kwargs)

    def __repr__(self):
        return f'<NOOP>'

    def __eq__(self, other):
        return isinstance(other, NoopAction)

    def __hash__(self):
        return hash(NoopAction)



class PushAction(object):
    def __init__(self, label):
        self._label = label

    @property
    def label(self):
        return self._label

    def collect_labels(self):
        return {self.label}

    def getDesc(self):
        return "push("+self.label+")"

    def clone(self):
        return type(self)(self.label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pushaction(self, *args, **kwargs)

    def __repr__(self):
        return f'<PUSH {self.label!r}>'

    def __eq__(self, other):
        return (
                isinstance(other, PushAction) and
                self.label == other.label
        )

    def __hash__(self):
        return hash((self.label,))


class Topology(object):
    def __init__(self, routers, links):
        self._routers = routers
        self._links = links

    @property
    def routers(self):
        return self._routers.values()

    def router_by_name(self, name):
        return self._routers[name]

    @property
    def links(self):
        return self._links


class Routing(object):
    def __init__(self, routingTable):
        self._routingTables = routingTable

    @property
    def routingTables(self):
        return self._routingTables.items()

    def count_rules(self):
        return sum(routing_table.count_rules()
                   for routing_table in self._routingTables.values())

    def collect_labels(self):
        labels = set()
        for routing_table in self._routingTables.values():
            labels.update(routing_table.collect_labels())
        return labels


class Network(object):
    def __init__(self, topology, routing):
        self.topology = topology
        self.routing = routing
