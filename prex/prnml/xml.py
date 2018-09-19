from lxml import etree
from prex.prnml import model
from prex.util import memoized
from itertools import groupby


def get_routers(routers_tree):
    routers = {}
    # Create routers
    for rdef in routers_tree.findall("router"):
        router = model.Router(rdef.get("name"))
        # Create interfaces on router
        ifaces_tree = rdef.find('interfaces')
        for idef in ifaces_tree.findall("interface"):
            router.addInterface(
                idef.get("name"),
                idef.get("external", "no") == "yes"
            )
        routers[rdef.get("name")] = router
    return routers


def get_sides(sides_tree, routers):
    shared = []
    for sidef in sides_tree.findall("shared_interface"):
        router = routers[sidef.get("router")]
        if sidef.get("interface") not in router.interfaces:
            print("Router {} does not have an interface {}".format(
                router.name,
                sidef.get("interface")
            ))
        interface = router.interfaces[sidef.get("interface")]
        sharedInterface = model.SharedInterface(
            router,
            interface
        )
        shared.append(sharedInterface)
    return shared


def get_links(links_tree, routers):
    links = []
    for ldef in links_tree.findall("link"):
        sh = get_sides(ldef.find("sides"), routers)
        li = model.Link(sh[0], sh[1])
        links.append(li)
    return links


@memoized
def get_label(label_name):
    if label_name is None or label_name == "" or label_name == "e":
        return model.NoLabel()
    return model.Label(label_name)


def get_action(rule_elem):
    action_name = rule_elem.get("type")
    if action_name == "push":
        return model.PushAction(get_label(rule_elem.get("arg")))
    if action_name == "swap":
        return model.SwapAction(get_label(rule_elem.get("arg")))
    if action_name == "pop":
        return model.PopAction()
    if action_name is None:
        return model.NoopAction()


def get_actions(actions_tree):
    actions = []
    for adef in actions_tree.findall("action"):
        action = get_action(adef)
        actions.append(action)
    return tuple(actions)


def get_routes(routes_tree, destination, router):
    rules = []
    for routedef in routes_tree.findall('route'):
        to = router.interfaces[routedef.get("to")]
        actions = get_actions(routedef.find("actions"))
        rule = model.Rule(
            destination.from_,
            to,
            destination.label,
            actions,
        )
        rules.append(rule)

    return rules


def get_te_groups(te_groups_tree, destination, router):
    te_groups = []
    for te_groupdef in te_groups_tree.findall('te-group'):
        routes_tree = te_groupdef.find('routes')
        rules = get_routes(routes_tree, destination, router)
        te_groups.append(model.TEGroup(rules))

    return te_groups


def get_destinations(destinations_tree, router):
    destinations = {}
    for ddef in destinations_tree.findall("destination"):
        try:
            from_ = router.interfaces[ddef.get("from")]
        except Exception as e:
            print(router)
            raise e
        label = get_label(ddef.get("label"))
        destination = model.Destination(from_, label)
        te_groups_tree = ddef.find('te-groups')
        destination.add_te_groups(get_te_groups(te_groups_tree, destination, router))
        destinations[(from_, label)] = destination

    return destinations


def get_routings(routings_tree, topology):
    routings = {}
    for rdef in routings_tree.findall("routing"):
        for_ = topology.router_by_name(rdef.get("for"))
        destinations = get_destinations(rdef.find("destinations"), for_)
        routings[for_] = model.RoutingTable(for_, destinations)
    return routings


def read_topology(file_):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(file_, parser)

    # Take out all the useless whitespace
    for element in tree.iter("*"):
        if element.text is not None and not element.text.strip():
            element.text = None

    routers = get_routers(tree.find("routers"))
    links = get_links(tree.find("links"), routers)
    return model.Topology(routers, links)


def read_routing(file_, topology):
    parser = etree.XMLParser(remove_blank_text=True)
    rtree = etree.parse(file_, parser)

    # Take out all the useless whitespace
    for element in rtree.iter("*"):
        if element.text is not None and not element.text.strip():
            element.text = None

    routings = get_routings(rtree.find("routings"), topology)
    return model.Routing(routings)


def read_network(topology_file, routing_file):
    topology = read_topology(topology_file)
    routing = read_routing(routing_file, topology)
    return model.Network(topology, routing)


def write_network(network):
    topology_root = write_topology(network.topology)
    routing_root = write_routing(network.routing)
    return (
        etree.tostring(topology_root, encoding='unicode', pretty_print=True),
        etree.tostring(routing_root, encoding='unicode', pretty_print=True)
    )


def write_network_bytes(network, topology_f=None, routing_f=None):
    topology_root = write_topology(network.topology)
    routing_root = write_routing(network.routing)
    return (
        etree.tostring(topology_root),
        etree.tostring(routing_root)
    )


def write_topology(topology):
    x_network = etree.Element('network')

    # Serialize routers
    x_routers = etree.SubElement(x_network, 'routers')
    for router in topology.routers:
        x_router = etree.SubElement(x_routers, 'router', name=router.name)
        x_interfaces = etree.SubElement(x_router, 'interfaces')
        for interface in router.interfaces.values():
            etree.SubElement(x_interfaces, 'interface', name=interface.name)

    # Serialize links
    x_links = etree.SubElement(x_network, 'links')
    for link in topology.links:
        x_link = etree.SubElement(x_links, 'link')
        x_sides = etree.SubElement(x_link, 'sides')
        etree.SubElement(x_sides,
                         'shared_interface',
                         router=link.to.router.name,
                         interface=link.to.interface.name)
        etree.SubElement(x_sides,
                         'shared_interface',
                         router=link.from_.router.name,
                         interface=link.from_.interface.name)

    return x_network


def write_routing(routing):
    x_routes = etree.Element('routes')

    # Serialize routing table
    x_routings = etree.SubElement(x_routes, 'routings')
    for route_table in routing._routingTables.values():
        x_routing = etree.SubElement(x_routings, 'routing',
                                     attrib={'for': route_table.router.name})
        x_routing.append(write_destinations(route_table.destinations.values()))

    return x_routes


def write_destinations(destinations):
    x_destinations = etree.Element('destinations')
    for destination in destinations:
        if isinstance(destination.label, model.NoLabel):
            label_out = ''
        else:
            label_out = destination.label.name
        x_destination = etree.SubElement(
            x_destinations,
            'destination',
            attrib={
                'from': destination.from_.name,
                'label': label_out,
            }
        )
        x_destination.append(write_te_groups(destination.te_groups))

    return x_destinations


def write_te_groups(te_groups):
    x_te_groups = etree.Element('te-groups')
    for te_group in te_groups:
        x_te_group = etree.SubElement(x_te_groups, 'te-group')
        x_te_group.append(write_routes(te_group.rules))

    return x_te_groups


def write_routes(rules):
    x_routes = etree.Element('routes')
    for rule in rules:
        x_route = etree.SubElement(
            x_routes,
            'route',
            attrib={
                'to': rule.to.name
            }
        )
        x_route.append(write_actions(rule.actions))

    return x_routes


def write_actions(actions):
    x_actions = etree.Element('actions')
    for action in actions:
        write_action(action, x_actions)

    return x_actions


def write_action(action, x_actions):
    if isinstance(action, model.PushAction):
        x_actions.append(etree.Element(
            'action',
            attrib={
                'type': 'push',
                'arg': action.label.name,
            }
        ))
    elif isinstance(action, model.PopAction):
        x_actions.append(etree.Element(
            'action',
            attrib={
                'type': 'pop',
            }
        ))
    elif isinstance(action, model.SwapAction):
        x_actions.append(etree.Element(
            'action',
            attrib={
                'type': 'swap',
                'arg': action.label.name,
            }
        ))
    elif isinstance(action, model.NoopAction):
        # Noops are implicit
        pass
    else:
        raise NotImplementedError(
            f'Unknown action type `{action.__class__.__name__}'
        )
