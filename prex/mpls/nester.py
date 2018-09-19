from prex.prnml.xml import (
    read_network,
)
from prex.prnml.model import (
    SharedInterface,
    Link,
)


def _mangle_network(prefix, network):
    # Mangle topology
    new_routers = dict()
    for router in network.topology.routers:
        router.name = f"{prefix}{router.name}"
        new_routers[router.name] = router
        #for interface in router.interfaces:
        #    interface.name = f"{prefix}_{interface.name}"
    network.topology._routers = new_routers
    # No need to mangle routing, routing only uses references to router-objects

def _merge_networks(into, from_):
    into.topology._routers.update(from_.topology._routers)
    into.topology._links.extend(from_.topology._links)
    into.routing._routingTables.update(from_.routing._routingTables)

    return into


class Nester(object):
    def __init__(self, topo_file_path, routing_file_path):
        self.topo_file_path = topo_file_path
        self.routing_file_path = routing_file_path

    def nest(self, max_depth):
        network = self._get_network()
        self._nest(network, max_depth, "_")
        return network

    def _nest(self, network, depth, mangle_prefix):
        if depth == 0:
            return
        s3_sub_network = self._inject_network(network, 's3', f's3{mangle_prefix}')
        s4_sub_network = self._inject_network(network, 's4', f's4{mangle_prefix}')
        self._nest(s3_sub_network, depth - 1, f's3{mangle_prefix}')
        self._nest(s4_sub_network, depth - 1, f's4{mangle_prefix}')
        _merge_networks(network, s3_sub_network)
        _merge_networks(network, s4_sub_network)

    def _inject_network(self, network, if_suffix, mangle_prefix):
        # Get sub network
        sub_network = self._get_network()
        _mangle_network(mangle_prefix, sub_network)

        # Inject sub network between s2 and the router identified by suffix
        for link in network.topology.links:
            test = (
                (link.from_.router.name.endswith('s2')
                and link.from_.interface.name.endswith(if_suffix))
                or (link.to.router.name.endswith('s2')
                and link.to.interface.name.endswith(if_suffix))
            )
            if test:
                inject_link = link
                break
        else:
            raise RuntimeError('Link with s2 not found in network')

        sub_entry = (sw for sw in sub_network.topology.routers
                  if sw.name.endswith('s1')).__next__()
        sub_exit = (sw for sw in sub_network.topology.routers
                  if sw.name.endswith('s7')).__next__()
        to = inject_link.to
        inject_link.to = SharedInterface(sub_entry, sub_entry.getInterface('i1'))
        out_link = Link(SharedInterface(sub_exit, sub_exit.getInterface('i1')), to)
        sub_network.topology._links.append(out_link)

        return sub_network

    def _get_network(self):
        return read_network(self.topo_file_path, self.routing_file_path)


