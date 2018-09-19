from prex.util import (
    memoized,
)
from prex.prnml import (
    model as prnml,
)
from prex.util import (
    keydefaultdict,
)
from collections import defaultdict


class Interface(object):
    def __init__(self, name, router):
        self.name = name
        self.router = router
        self.link = None

    def connect_interface(self, destination_interface):
        return Link(self, destination_interface)


class Router(object):
    def __init__(self, name):
        self.name = name
        self.interfaces = dict()
        self.outgoing_links = dict()

    def connect(self, outgoing_interface, destination_interface=None):
        if isinstance(outgoing_interface, str):
            outgoing_interface = self.interfaces[outgoing_interface]

        link = outgoing_interface.connect_interface(destination_interface)
        self.outgoing_links[outgoing_interface] = link
        return link

    def get_link(self, interface):
        return self.outgoing_links[interface]

    def add_interface(self, name):
        self.interfaces[name] = Interface(name, self)
        return self.interfaces[name]

    def get_interface(self, name):
        return self.interfaces[name]

    def add_or_get_interface(self, name):
        try:
            return self.get_interface(name)
        except KeyError:
            self.add_interface(name)
            return self.get_interface(name)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_router(self, *args, **kwargs)

    def __str__(self):
        return f'{self.name}'


class Link(object):
    def __init__(self, from_, to):
        if (from_.link is not None
                or to.link is not None):
            raise RuntimeError(
                'Interface already connected to other interface.'
                'Interface can only be connected to one other interface'
            )
        self.from_ = from_
        self.to = to
        from_.link = self
        to.link = self

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_link(self, *args, **kwargs)

    def __str__(self):
        return f'{self.from_} -> {self.to}'


class EthernetRule(object):
    def __init__(self, in_interface, out_interface, actions, weight):
        self.in_interface = in_interface
        self.out_interface = out_interface
        self.actions = actions
        self.weight = weight

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_ethernet_rule(self, *args, **kwargs)

    def __str__(self):
        actions = "-".join((str(a) for a in self.actions))
        return f'({self.weight}) {self.in_interface.name}-{actions}> {self.out_interface.name}'  # noqa


class Rule(object):
    def __init__(self, label, out_interface, actions, weight):
        self.label = label
        self.out_interface = out_interface
        self.actions = actions
        self.weight = weight

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_rule(self, *args, **kwargs)

    def __eq__(self, other):
        if isinstance(other, Rule):
            return (
                    self.label == other.label
                    and self.out_interface == other.out_interface
                    and self.weight == other.weight
                    and self.actions == other.actions
            )
        raise NotImplementedError

    def __str__(self):
        actions = "-".join((str(a) for a in self.actions))
        return f'({self.weight}) {self.label}-{actions}> {self.out_interface.name}'  # noqa


class RoutingTable(object):
    def __init__(self, router, rules=None):
        self.router = router
        self.rules = rules if rules else []

    def add_rule(self, rule):
        self.rules.append(rule)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_routing_table(self, *args, **kwargs)


class Label(object):
    def __init__(self, name):
        self.name = name

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_label(self, *args, **kwargs)


class SwapAction(object):
    def __init__(self, label):
        self.label = label

    def collectLabels(self):
        return {self.label}

    def clone(self):
        return type(self)(self.label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_swap_action(self, *args, **kwargs)

    def __str__(self):
        return f'swap({self.label})'


class PopAction(object):
    def __init__(self):
        pass

    def collectLabels(self):
        return set()

    def clone(self):
        return type(self)()

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_pop_action(self, *args, **kwargs)

    def __str__(self):
        return 'pop'


class PushAction(object):
    def __init__(self, label):
        self.label = label

    def collectLabels(self):
        return {self.label}

    def clone(self):
        return type(self)(self.label)

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_push_action(self, *args, **kwargs)

    def __str__(self):
        return f'push({self.label})'


class Topology(object):
    def __init__(self, routers):
        self._routers = routers

    @property
    def routers(self):
        return self._routers.items()

    def add_or_get_router(self, name):
        try:
            return self.get_router(name)
        except KeyError:
            self.add_router(Router(name))
            return self.get_router(name)

    def get_router(self, name):
        return self._routers[name]

    def add_router(self, router):
        self._routers[router.name] = router
        return router

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_topology(self, *args, **kwargs)


class Routing(object):
    def __init__(self, routingTables):
        self._routingTables = routingTables

    @property
    def routingTables(self):
        return self._routingTables.items()

    def collect_labels(self):
        labels = set()

        for _, rt in self.routingTables:
            for rule in rt.rules:
                for action in rule.actions:
                    labels.update(action.collectLabels())
                if rule.label.collectable:
                    labels.add(rule.label)

        return labels

    def add_table(self, table):
        self._routingTables[table.router] = table
        return table

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_routing(self, *args, **kwargs)


class Network(object):
    def __init__(self, topology, routing):
        self.topology = topology
        self.routing = routing

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_network(self, *args, **kwargs)


class PRNMLConverter():
    def __init__(self, juniper_network_model):
        self.juniper_network_model = juniper_network_model

        self.Label = memoized(prnml.Label)
        self.NoLabel = memoized(prnml.NoLabel)
        self.Switch = memoized(prnml.Router)
        self.SharedInterface = memoized(prnml.SharedInterface)
        self.Link = memoized(prnml.Link)
        self.Rule = memoized(prnml.Rule)

    def convert(self):
        prnml_network = self.juniper_network_model.visit(self)
        return prnml_network

    def visit_label(self, label):
        return self.Label(label.name)

    def visit_link(self, link):
        from_router = self.Switch(link.from_.router.name)
        to_router = self.Switch(link.to.router.name)
        from_interface = from_router.addInterface(link.from_.name)
        to_interface = to_router.addInterface(link.to.name)
        prnml_link = self.Link(
            self.SharedInterface(from_router, from_interface),
            self.SharedInterface(to_router, to_interface)
        )

        return prnml_link

    def visit_network(self, network):
        topology = network.topology.visit(self)
        routing = network.routing.visit(self)
        network = prnml.Network(topology, routing)

        return network

    def visit_router(self, router):
        prnml_router = self.Switch(router.name)
        prnml_links = [link.visit(self) for link in router.outgoing_links.values()]  # noqa
        for interface_name in router.interfaces.keys():
            prnml_router.addInterface(interface_name)

        return prnml_router, prnml_links

    def visit_interface(self, interface, prnml_router):
        pass

    def visit_routing(self, routing):
        prnml_tables = {self.Switch(router.name): table.visit(self)
                        for router, table in routing.routingTables}

        return prnml.Routing(prnml_tables)

    def visit_routing_table(self, table):
        prnml_router = self.Switch(table.router.name)
        prnml_rules = [prnml_rule for rule in table.rules
                       for prnml_rule in rule.visit(self, prnml_router)]

        destinations = keydefaultdict(lambda x: prnml.Destination(x[0], x[1]))
        te_groups_list = defaultdict(lambda: defaultdict(prnml.TEGroup))

        for weight, rule in prnml_rules:
            destination = destinations[(rule.from_, rule.label)]
            te_groups_list[destination][weight].rules.append(rule)

        for destination in destinations.values():
            te_groups = te_groups_list[destination].items()
            sorted_te_groups = sorted(te_groups, key=lambda x: x[0])
            destination.te_groups = [val[1] for val in sorted_te_groups]

        return prnml.RoutingTable(prnml_router, dict(destinations))

    def visit_ethernet_rule(self, rule, prnml_router):
        prnml_rule = self.Rule(
            prnml_router.getInterface(rule.in_interface),
            prnml_router.getInterface(rule.out_interface.name),
            self.NoLabel(),
            tuple([action.visit(self) for action in rule.actions]),
        )

        return [(rule.weight, prnml_rule)]

    def visit_rule(self, rule, prnml_router):
        prnml_rules = []
        for _, interface in prnml_router.interfaces.items():
            prnml_rule = self.Rule(
                interface,
                prnml_router.getInterface(rule.out_interface.name),
                rule.label.visit(self),
                tuple([action.visit(self) for action in rule.actions]),
            )
            prnml_rules.append((rule.weight, prnml_rule))

        return prnml_rules

    def visit_pop_action(self, action):
        return prnml.PopAction()

    def visit_push_action(self, action):
        return prnml.PushAction(self.Label(action.label.name))

    def visit_swap_action(self, action):
        return prnml.SwapAction(self.Label(action.label.name))

    def visit_topology(self, topology):
        prnml_topology = prnml.Topology(dict(), [])
        for _, router in topology.routers:
            prnml_router, prnml_links = router.visit(self)
            prnml_topology._routers[prnml_router.name] = prnml_router
            prnml_topology._links.extend(prnml_links)

        return prnml_topology
