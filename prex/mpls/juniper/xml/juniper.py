import re
import pathlib
from lxml import etree
from . import model
import io


# http://wiki.tei-c.org/index.php/Remove-Namespaces.xsl
ns_stripper_xslt = b'''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="xml" indent="no"/>

<xsl:template match="/|comment()|processing-instruction()">
    <xsl:copy>
      <xsl:apply-templates/>
    </xsl:copy>
</xsl:template>

<xsl:template match="*">
    <xsl:element name="{local-name()}">
      <xsl:apply-templates select="@*|node()"/>
    </xsl:element>
</xsl:template>

<xsl:template match="@*">
    <xsl:attribute name="{local-name()}">
      <xsl:value-of select="."/>
    </xsl:attribute>
</xsl:template>
</xsl:stylesheet>
'''  # noqa
ns_stripper_doc = etree.parse(io.BytesIO(ns_stripper_xslt))
ns_stripper = etree.XSLT(ns_stripper_doc)



_parse_ip_re = re.compile(r'^.\s*(?P<ip>(?:\d{1,3}\.?){4})/\d{1,2}\s*H\s*-\s*(?P<domain>[^\s]+)')  # noqa


def parse_router_ips(router_ip_path):
    mapping = {}

    with open(router_ip_path, 'rt') as f:
        for line in f:
            match = _parse_ip_re.match(line)
            if match:
                mapping[match['ip']] = match['domain']

    return mapping


def parse_isis(dump_folder):
    path = pathlib.Path(dump_folder)
    files = [node for node in path.iterdir() if node.is_file()]

    topology = model.Topology(dict())

    # Setup links
    for file in files:
        router = topology.add_or_get_router(f'{file.stem}')
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(str(file), parser)
        tree = ns_stripper(tree)

        root = tree.getroot()
        isis = root.find('isis-adjacency-information')
        for adjacency in isis.findall('isis-adjacency'):
            system_name = adjacency.find('system-name')
            interface_name = adjacency.find('interface-name')

            outgoing_interface = router.add_interface(interface_name.text)

            # Remove routing engine suffix
            norm_system_name = (
                re.sub(r'-re\d$', '', system_name.text)
            )
            destination_router = topology.add_or_get_router(norm_system_name)
            destination_interface = destination_router.add_interface(
                (f'{router.name}_{outgoing_interface.name}')
            )
            router.connect(outgoing_interface, destination_interface)

    return topology


class ForwardingParser:
    def __init__(self, topology, ip_dns_map=None):
        self.topology = topology
        self.ip_dns_map = ip_dns_map if ip_dns_map is not None else dict()

    def parse_forwarding(self, dump_folder):
        path = pathlib.Path(dump_folder)
        files = [node for node in path.iterdir() if node.is_file()]

        routing = model.Routing(dict())
        for file in files:
            lsi_list = []
            router = self.topology.get_router(file.stem)
            routing_table = routing.add_table(
                model.RoutingTable(router)
            )
            parser = etree.XMLParser(remove_blank_text=True)
            tree = etree.parse(str(file), parser)
            tree = ns_stripper(tree)

            root = tree.getroot()
            table = root.find('forwarding-table-information')
            for route_table in table.findall('route-table'):
                for rt_entry in route_table.findall('rt-entry'):
                    self.parse_rt_entry(
                        rt_entry,
                        router,
                        routing_table,
                        lsi_list
                    )

            # Fixup LSI
            for lsi_interface, out_interface, actions, weight in lsi_list:
                matching_rules = (rule for rule in routing_table.rules
                                  if rule.out_interface.name == lsi_interface)
                for matching_rule in matching_rules:
                    matching_rule.out_interface = out_interface
                    matching_rule.actions.extend(actions)
                    matching_rule.weight = weight

        self.fixup_labels(routing._routingTables.values())

        return model.Network(self.topology, routing)

    def parse_rt_entry(self, rt_entry, router, routing_table, lsi_list):
        for x_nh in rt_entry.findall('nh'):
            # x_via is the outgoing interface
            x_via = x_nh.find('via')
            if x_via is None or x_via.text is None:
                # Weird built-in entry, skip
                continue

            # Destination IP
            x_to = x_nh.find('to')
            if x_to.text is None:
                outgoing_interface = router.add_or_get_interface(x_via.text)
            else:
                # If the interface is not present or not connected,
                # it means we did not learn
                # about the other router from the IS-IS database.
                # This should only happen if we do not have any
                # extracts from the destination router.
                outgoing_interface = router.add_or_get_interface(x_via.text)
                if outgoing_interface not in router.outgoing_links:
                    try:
                        dest_router_name = self.ip_dns_map[x_to.text]
                    except KeyError:
                        dest_router_name = x_to.text.strip()
                    dest_router = self.topology.add_or_get_router(
                        dest_router_name
                    )
                    destination_interface = dest_router.add_or_get_interface(
                        (f'{router.name}_{outgoing_interface.name}')
                    )
                    router.connect(
                        outgoing_interface,
                        destination_interface
                    )

            # nh-type is the operation to perform on the packet.
            # This is a superset of the MPLS operations
            nh_type = x_nh.find('nh-type').text.lower().replace('(top)', '')
            op_sequence = [elem.strip() for elem in nh_type.split(',')]
            actions = []
            for op in op_sequence:
                try:
                    actions.append(self.make_action(op))
                except RuntimeError:
                    # Unknown op, ignore
                    continue

            # Weight of the rule. Lower is higher priority
            # May be absent, hence the None check
            x_nh_weight = x_nh.find('nh-weight')
            if x_nh_weight is not None:
                weight = int(x_nh_weight.text, 16)
            else:
                # No weight implies only a single alternative
                # Set dummy weight
                weight = 1

            # Incoming label or virtual interface
            x_rt_destination = rt_entry.find('rt-destination')
            if re.fullmatch(r'[\w=()]+', x_rt_destination.text):
                label = model.Label(x_rt_destination.text)
                routing_table.add_rule(
                    model.Rule(
                        label,
                        outgoing_interface,
                        actions,
                        weight,
                    )
                )
            elif re.match(r'[\w./-]+', x_rt_destination.text):
                # Ethernet packet or LSI interface
                # Cut off after whitespace
                in_interface, *_ = x_rt_destination.text.split()
                # Save LSI for later
                if in_interface.lower().startswith('lsi'):
                    lsi_list.append((
                        in_interface,
                        outgoing_interface,
                        actions,
                        weight,
                    ))
                else:
                    routing_table.add_rule(
                        model.EthernetRule(
                            in_interface,
                            outgoing_interface,
                            actions,
                            weight,
                        )
                    )
            else:
                raise RuntimeError('Unknown destination type')

    def make_action(self, action_str):
        op, *rest = re.split(r'\s', action_str)
        if op == 'push':
            label_name, *rest = rest
            action = model.PushAction(model.Label(label_name))
        elif op == 'pop':
            action = model.PopAction()
        elif op == 'swap':
            label_name, *rest = rest
            action = model.SwapAction(model.Label(label_name))
        else:
            raise RuntimeError(f'Invalid action {op}')

        if len(rest) != 0:
            raise AssertionError(f'Unknown text at end of {action_str}')
        return action

    def clone_action(self, action):
        if isinstance(action, model.PushAction):
            return model.PushAction(action.label)
        elif isinstance(action, model.SwapAction):
            return model.SwapAction(action.label)
        elif isinstance(action, model.PopAction):
            return model.PopAction()
        else:
            raise RuntimeError('Unknown action type')

    def fixup_labels(self, routing_tables):
        # Modify routing to pass along bottom-of-stack bit
        for table in routing_tables:
            mpls_rules = [rule for rule in table.rules
                          if isinstance(rule, model.Rule)]
            # Extract rules with bottom_of_stack bit = 0
            s0_rules = [rule for rule in mpls_rules
                        if rule.label.name.endswith('(S=0)')]
            # Rules without bottom_of_stack bit
            other_rules = [rule for rule in mpls_rules if rule not in s0_rules]
            # Set bottom_of_stack bit to 1 for all unannotated rules
            for rule in mpls_rules:
                if not rule.label.name.endswith('(S=0)'):
                    rule.label.name += '(S=1)'
            # Find unpaired rules (rules without a different rule matching S=0)
            s0_label_names = [rule.label.name for rule in s0_rules]
            unpaired_rules = [rule for rule in other_rules
                              if rule.label.name not in s0_label_names]
            # Clone all unpaired rules and modify the clone to work with S=0
            for rule in unpaired_rules:
                table.add_rule(
                    model.Rule(
                        model.Label(rule.label.name.replace('(S=1)', '(S=0)')),
                        rule.out_interface,
                        tuple([self.clone_action(action)
                               for action in rule.actions]),
                        rule.weight
                    )
                )

        # Fix actions for all rules
        for table in routing_tables:
            for rule in table.rules:
                if isinstance(rule, model.Rule):
                    for action in rule.actions:
                        if isinstance(action, model.PopAction):
                            # Do nothing
                            pass
                        elif isinstance(action, model.PushAction):
                            # Always push (S=0) variant
                            if action.label.name.endswith('(S=1)'):
                                action.label.name = (
                                    action.label.name.replace('(S=1)', '(S=0)')
                                )
                            else:
                                action.label.name = action.label.name + '(S=0)'
                        elif isinstance(action, model.SwapAction):
                            # Swap to the label with the same BoS bit
                            if rule.label.name.endswith('(S=0)'):
                                if action.label.name.endswith('(S=1)'):
                                    action.label.name = (
                                        action.label.name.replace('(S=1)', '(S=0)')  # noqa
                                    )
                                else:
                                    action.label.name = action.label.name + '(S=0)'  # noqa
                            elif rule.label.name.endswith('(S=1)'):
                                if action.label.name.endswith('(S=0)'):
                                    action.label.name = (
                                        action.label.name.replace('(S=0)', '(S=1)')  # noqa
                                    )
                                else:
                                    action.label.name = action.label.name + '(S=1)'  # noqa
                            else:
                                # This should not happen.
                                # All rules should have been fixed above
                                # Panic!
                                raise RuntimeError('Something has gone horribly wrong')  # noqa
                        else:
                            raise RuntimeError(
                                "Someone added a new rule type and forgot this code"  # noqa
                            )
                elif isinstance(rule, model.EthernetRule):
                    for action in rule.actions:
                        if isinstance(action, model.PopAction):
                            # No MPLS labels on stack for EthernetRules
                            # Popping is illegal
                            raise RuntimeError('PopAction is illegal for EthernetRule')  # noqa
                        elif isinstance(action, model.PushAction):
                            # Always push (S=1) variant
                            if action.label.name.endswith('(S=0)'):
                                action.label.name = (
                                    action.label.name.replace('(S=0)', '(S=1)')
                                )
                            else:
                                action.label.name = action.label.name + '(S=0)'
                        elif isinstance(action, model.SwapAction):
                            # No MPLS labels on stack for EthernetRules
                            # Swapping is illegal
                            raise RuntimeError('SwapAction is illegal for EthernetRule')  # noqa
                        else:
                            raise RuntimeError(
                                "Someone added a new rule type and forgot this code"  # noqa
                            )
                else:
                    # wtf?
                    raise RuntimeError(
                        "Someone added a new rule type and forgot this code"
                    )
