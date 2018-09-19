import sys

from pathlib import Path

import copy

from prex.prnml import (
    xml as x,
)

routes = Path(sys.argv[1])
topology = Path(sys.argv[2])
out_path = Path(sys.argv[3])

network = x.read_network(topology.absolute().as_uri(), routes.absolute().as_uri())

for i, _ in enumerate(network.topology.links):
    tmp_network = copy.deepcopy(network)
    link = tmp_network.topology.links[i]

    t_out = out_path / f"{topology.parent.name}_{link}" / topology.name
    r_out = out_path / f"{routes.parent.name}_{link}" / routes.name

    for si in (link.from_, link.to):
        # remove link and rules ?!?
        to_delete = list()

        for (from_, label), dest in tmp_network.routing._routingTables[si.router].destinations.items():
            if from_ == si.interface:
                to_delete.append((from_, label,))
                continue
            for te in dest.te_groups:
                rules_to_delete = list()
                for rule in te.rules:
                    if rule.to == si.interface:
                        rules_to_delete.append(rule)

                for rtd in rules_to_delete:
                    te.rules.remove(rtd)


        for td in to_delete:
            del tmp_network.routing._routingTables[si.router].destinations[td]

    tmp_network.topology.links.remove(link)
    topology_str, routing_str = x.write_network(tmp_network)

    import os

    if not os.path.exists(t_out.parent.absolute()):
        os.makedirs(t_out.parent.absolute())

    with open(t_out, 'wt') as t:
        t.write(topology_str)

    with open(r_out, 'wt') as r:
        r.write(routing_str)
