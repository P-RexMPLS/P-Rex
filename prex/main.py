import sys
import click
import logging
import yaml
import logging.config
from pathlib import Path
from prex.middleware import (
    query_to_nfa,
)
from prex import (
    middleware,
)
from prex.middleware import (
    optimized_nfa_to_pda,
)
from prex.pushdown.variant import moped
from prex.mpls.juniper.xml import (
    juniper as new_jp,
    model as juniper_model,
)
from prex.mpls.nester import Nester
from prex.prnml import (
    xml as x,
)
from prex.pushdown import (
    operations,
    expression,
)
import timeit
from types import (
    SimpleNamespace,
)
import contextlib
import random
import pathlib


logger = logging.getLogger(__name__)
chain = []


@click.group(invoke_without_command=True)
@click.option('-c', '--config', default='config.yml', type=click.Path())
def cli(config):
    config_path = Path(config)
    if config_path.is_file():
        with config_path.open('rt') as f:
            raw_config = yaml.load(f)
    else:
        click.echo(f'{config_path!s} not found. Using default config')
        raw_config = {
            'logging': {
                "version": 1,
                "root": {}
            }
        }

    config = SimpleNamespace(**raw_config)
    logging.config.dictConfig(config.logging)


@cli.resultcallback()
def cli_runner(_, config):
    for op in chain:
        op()


@cli.group('juniper-xml')
@click.argument(
    'isis-dir',
    required=True,
    type=click.Path(file_okay=False, exists=True))
@click.argument(
    'forwarding-dir',
    required=True,
    type=click.Path(file_okay=False, exists=True))
@click.option(
    '-r',
    '--ip-router-maps',
    multiple=True,
    type=click.Path(dir_okay=False, exists=True))
@click.pass_context
def juniper_xml(ctx, isis_dir, forwarding_dir, ip_router_maps):
    def inner():
        t0 = timeit.default_timer()
        ip_router_map = {}
        for path in ip_router_maps:
            ip_router_map.update(new_jp.parse_router_ips(path))
        topology = new_jp.parse_isis(isis_dir)
        parser = new_jp.ForwardingParser(topology, ip_dns_map=ip_router_map)
        juniper_network = parser.parse_forwarding(forwarding_dir)
        network = juniper_model.PRNMLConverter(juniper_network).convert()
        ctx.obj['network'] = network
        t1 = timeit.default_timer()
        print(f'Loading: {t1 - t0:.3}s')

    chain.append(inner)


@cli.group()
@click.argument(
    "topology",
    required=True,
    default='./topo.xml',
    type=click.Path(exists=True)
)
@click.argument(
    "routes",
    required=True,
    default='./routing.xml',
    type=click.Path(exists=True)
)
@click.pass_context
def xml(ctx, topology, routes):
    def inner():
        t0 = timeit.default_timer()
        network = x.read_network(topology, routes)
        ctx.obj['network'] = network
        t1 = timeit.default_timer()
        print(f'Loading: {t1 - t0:.3}s')

    chain.append(inner)


@cli.group('nest-network')
@click.argument(
    "topology",
    required=True,
    default='./topo.xml',
    type=click.Path(exists=True)
)
@click.argument(
    "routes",
    required=True,
    default='./routing.xml',
    type=click.Path(exists=True)
)
@click.option('-n', '--nesting-level', type=int)
@click.pass_context
def nest_network(ctx, topology, routes, nesting_level):
    def inner():
        nester = Nester(topology, routes)
        network = nester.nest(nesting_level)
        ctx.obj['network'] = network

    chain.append(inner)


@click.command('dump-network')
@click.argument(
    "topology",
    required=True,
    default='./topo.xml',
    type=click.Path(writable=True)
)
@click.argument(
    "routing",
    required=True,
    default='./routing.xml',
    type=click.Path(writable=True)
)
@click.pass_context
def dump_network(ctx, topology, routing):
    def inner():
        network = ctx.obj['network']
        with contextlib.ExitStack() as stack:
            topology_f = stack.enter_context(open(topology, 'wt'))
            routing_f = stack.enter_context(open(routing, 'wt'))
            topology_str, routing_str = x.write_network(network)
            topology_f.write(topology_str)
            routing_f.write(routing_str)

    chain.append(inner)
xml.add_command(dump_network)  # noqa
juniper_xml.add_command(dump_network)
nest_network.add_command(dump_network)


@cli.command()
@click.argument('pds-path', default='./dump.pds', type=click.Path(exists=True))
@click.option('-v', '--verbose', count=True)
def pds(pds_path, verbose):
    def inner():
        output = moped.runner.query_file(pds_path)
        do_output(output, verbose)

    chain.append(inner)


@click.group('adv-query')
@click.argument('query', type=str)
@click.argument('max-failed-links', type=click.IntRange(0, None))
@click.pass_context
def prex_query(ctx, query, max_failed_links):
    def inner():
        label_domain = ctx.obj['network'].routing.collect_labels()

        def parser(pda):
            return query_to_nfa.parse_query(query, label_domain, pda)
        ctx.obj['parser'] = parser
        ctx.obj['k'] = max_failed_links

    chain.append(inner)
juniper_xml.add_command(prex_query)  # noqa
xml.add_command(prex_query)


@click.group('adv-file-query')
@click.argument('query-file', type=str)
@click.argument('max-failed-links', type=click.IntRange(0, None))
@click.pass_context
def prex_file_query(ctx, query_file, max_failed_links):
    def inner():
        qf_path = pathlib.Path(query_file)
        label_domain = ctx.obj['network'].routing.collect_labels()

        def parser(pda):
            return query_to_nfa.parse_query(qf_path, label_domain, pda)
        ctx.obj['parser'] = parser
        ctx.obj['k'] = max_failed_links

    chain.append(inner)
juniper_xml.add_command(prex_file_query)  # noqa
xml.add_command(prex_file_query)


@click.group('random-query')
@click.argument('query-size', type=int)
@click.argument('max-failed-links', type=click.IntRange(0, None))
@click.pass_context
def random_query(ctx, query_size, max_failed_links):
    def inner():
        network = ctx.obj['network']
        query = (
            '<.*>' +
            ' .* '.join(
                map(
                    lambda r: r.name,
                    random.choices(
                        tuple(network.topology.routers),
                        k=query_size
                    )
                )
            ) +
            '<.*>'
        )
        label_domain = ctx.obj['network'].routing.collect_labels()

        def parser(pda):
            return query_to_nfa.parse_query(query, label_domain, pda)
        ctx.obj['parser'] = parser
        ctx.obj['k'] = max_failed_links

    chain.append(inner)
juniper_xml.add_command(random_query)  # noqa
xml.add_command(random_query)


@click.group()
@click.pass_context
@click.option('-v', '--verbose', count=True)
@click.option('--under/--over', default=False)
@click.option('--journal/--old', default=False)
@click.option('--alltops/--tosreduction', default=False)
def compile(ctx, under, verbose, journal):
    def inner():
        ctx.obj['under'] = under
        t0 = timeit.default_timer()
        network = ctx.obj.pop('network')
        k = ctx.obj['k']

        expgen = expression.Generator()
        ctx.obj['expgen'] = expgen

        logging.info(
            f"Processing {len(network.routing._routingTables)} routing"
            f" tables with a total of {network.routing.count_rules()} rules"
        )

        logging.info("Constructing mpls simulation")
        print(f"Under is {under}")
        if under:
            mpls_fragment = middleware.underapprox.to_pushdown(
                expgen,
                network,
                k=k
            )
        else:
            mpls_fragment = middleware.outonly.to_pushdown(
                expgen,
                network,
                k=k
            )

        logging.info(f"Constructing NFAs")
        parser = ctx.obj.pop('parser')
        nfa_c, nfa_n, nfa_d = parser(mpls_fragment)
        logging.info(f"Constructing builder")
        constructor = optimized_nfa_to_pda.ConstructingPDA(expgen, nfa_c)
        build_fragment = constructor.convert()
        logging.info(f"Constructing destroyer")
        destructor = optimized_nfa_to_pda.DestructingPDA(expgen, nfa_d)
        destroy_fragment = destructor.convert()

        logging.info(
            f"Constructing APDA from NFA ({len(nfa_n.transitions)}) and PDA"
            f" ({len(mpls_fragment.transitions)})"
        )
        apda_fragment = middleware.apda.compose(
            mpls_fragment,
            nfa_n
        )

        logging.info(
            f"Concating the builder ({len(build_fragment.transitions)})"
            f" with the apda ({len(apda_fragment.transitions)})"
        )
        with_builder = operations.concat_disjoint(
            build_fragment,
            apda_fragment,
            destructive=True
        )

        logging.info(f"Concating the destroyer"
                     f" ({len(destroy_fragment.transitions)}) with the"
                     f" builder-apda ({len(with_builder.transitions)})")
        with_destroy = operations.concat_disjoint(
            with_builder,
            destroy_fragment,
            destructive=True
        )

        logger.info(f"Compiling pushdown with {len(with_destroy.transitions)}"
                    f" symbolic transitions")

        if journal:
            print("Using journal pruning")
            system = moped.compiler.compile2(
                expgen,
                with_destroy,
                with_destroy.specials["start"],
                with_destroy.specials["end"],
                bool(verbose),
            )
        elif notops:
            print("Using no pruning")
            system = moped.compiler.compile0(
                expgen,
                with_destroy,
                with_destroy.specials["start"],
                with_destroy.specials["end"],
                bool(verbose),
            )
        else:
            print("Using paper pruning")
            system = moped.compiler.compile(
                expgen,
                with_destroy,
                with_destroy.specials["start"],
                with_destroy.specials["end"],
                bool(verbose),
            )

        ctx.obj['system'] = system

        t1 = timeit.default_timer()

        print(f"Compiling: {t1 - t0:.3f}s")
        print(f"Size: {system.size}")

        rate = system.size / (t1 - t0)
        print(f"Transitions/s: {rate:.3f} t/s")

    chain.append(inner)
prex_query.add_command(compile)  # noqa
prex_file_query.add_command(compile)
random_query.add_command(compile)


@compile.command('dump-pds')
@click.option('-o', '--dump-path', default='./dump.pds',
              type=click.Path(writable=True))
@click.pass_context
def dump_pds(ctx, dump_path):
    def inner():
        system = ctx.obj['system']

        with open(dump_path, "wt") as f:
            f.write(system.str)

    chain.append(inner)


@compile.command()
@click.option('-v', '--verbose', count=True)
@click.option('--enable-cd/--disable-cd', default=True, help='Cycle detection')
@click.pass_context
def run(ctx, enable_cd, verbose):
    def inner():
        t0 = timeit.default_timer()

        under = ctx.obj['under']
        system = ctx.obj['system']
        moped_result, transitions = moped.runner.query_system(system)

        t1 = timeit.default_timer()
        print(f'Verifying: {t1 - t0:.3f}s')

        rate = system.size / (t1 - t0)
        print(f"Transitions/s: {rate:.3f} t/s")

        result = False
        # If we're running the under approximation
        # we need to ensure the witness is acyclic
        if enable_cd and under and moped_result:
            # Filter out internal transitions going to internal locations
            network_transitions = (
                transition for transition in transitions
                if isinstance(transition.to.name, tuple)
                and isinstance(transition.to.name[0].name, tuple)
            )
            routers = set()
            previous_router_in = None
            for transition in network_transitions:
                router_in = tuple(transition.to.name[0].name[0:2])
                if router_in == previous_router_in:
                    # Need to allow traversing action chains
                    continue
                if router_in[0] in routers:
                    # Found a repeated router, trace is cyclic
                    break
                else:
                    previous_router_in = router_in
                    routers.add(router_in[0])
            else:
                # Loop terminated normally, no duplicate routers found in trace
                result = True
        else:
            result = moped_result

        if result:
            print('YES')
            printer = TransitionPrinter()
            for transition in transitions:
                print(transition.visit(printer))
        else:
            print('NO')

    chain.append(inner)


class TransitionPrinter():
    def __init__(self):
        pass

    def _print_tuple(self, from_, to, label, out_label):
        return f'{from_} <{label}> --> {to} {out_label}'

    def visit_transition(self, transition):
        from_ = transition.from_.name
        to = transition.to.name
        label = transition.inlabel
        out_label = transition.action.visit(self, in_label=label)

        return self._print_tuple(from_, to, label, out_label)

    def visit_epsilon_transition(self, transition):
        from_ = transition.from_.name
        to = transition.to.name
        label = '*'
        out_label = transition.action.visit(self, in_label=label)

        return self._print_tuple(from_, to, label, out_label)

    visit_star_transition = visit_epsilon_transition

    def visit_pop(self, action, in_label=None):
        return ''

    def visit_noop(self, action, in_label=None):
        return f'{in_label}'

    def visit_push(self, action, in_label=None):
        return f'{action.label} {in_label}'

    def visit_replace(self, action, in_label=None):
        return f'{action.label} {in_label}'

    def visit_pushreplace(self, action, in_label=None):
        return f'{action.label1} {action.label2}'


def do_output(output, verbose):
    for line in output[10:11:]:
        print(line)

    if verbose > 0:
        for line in output[11::]:
            print(line)


if __name__ == "__main__":
    cli(sys.argv[1:], obj=dict())
