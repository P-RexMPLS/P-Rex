import jinja2
import click
import sys


__loader = jinja2.FileSystemLoader(searchpath='gen/templates')
__environment = jinja2.Environment(loader=__loader)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('topo_out', type=click.Path(writable=True))
@click.argument('routing_out', type=click.Path(writable=True))
@click.argument('scale', type=int)
def scaling_h(topo_out, routing_out, scale):
    name = 'scaling_h'
    topo_template = __environment.get_template(f'{name}_topo.jinja')
    routing_template = __environment.get_template(f'{name}_routing.jinja')
    with open(topo_out, 'wt') as f:
        f.write(topo_template.render(n=scale))
    with open(routing_out, 'wt') as f:
        f.write(routing_template.render(n=scale))

    query = '<> s1 .* s3 <>'
    click.echo(query)


@cli.command()
@click.argument('topo_out', type=click.Path(writable=True))
@click.argument('routing_out', type=click.Path(writable=True))
@click.argument('scale', type=int)
def scaling_L(topo_out, routing_out, scale):
    name = 'scaling_L'
    topo_template = __environment.get_template(f'{name}_topo.jinja')
    routing_template = __environment.get_template(f'{name}_routing.jinja')
    with open(topo_out, 'wt') as f:
        f.write(topo_template.render(n=scale))
    with open(routing_out, 'wt') as f:
        f.write(routing_template.render(n=scale))

    query = '<0> s1 .* s3 <>'
    click.echo(query)


@cli.command()
@click.argument('topo_out', type=click.Path(writable=True))
@click.argument('routing_out', type=click.Path(writable=True))
@click.argument('scale', type=int)
def scaling_V(topo_out, routing_out, scale):
    name = 'scaling_V'
    topo_template = __environment.get_template(f'{name}_topo.jinja')
    routing_template = __environment.get_template(f'{name}_routing.jinja')
    with open(topo_out, 'wt') as f:
        f.write(topo_template.render(n=scale))
    with open(routing_out, 'wt') as f:
        f.write(routing_template.render(n=scale))

    query = f'<10> s0 .* s{scale - 1} <10>'
    click.echo(query)


@cli.command()
@click.argument('topo_out', type=click.Path(writable=True))
@click.argument('routing_out', type=click.Path(writable=True))
@click.argument('scale_h', type=click.IntRange(min=1))
@click.argument('scale_k', type=click.IntRange(min=0))
def scaling_hk(topo_out, routing_out, scale_h, scale_k):
    name = 'scaling_hk'
    topo_template = __environment.get_template(f'{name}_topo.jinja')
    routing_template = __environment.get_template(f'{name}_routing.jinja')
    # This is as hack, the bounds in the templates should be fixed
    scale_k += 1
    with open(topo_out, 'wt') as f:
        f.write(topo_template.render(h=scale_h, k=scale_k))
    with open(routing_out, 'wt') as f:
        f.write(routing_template.render(h=scale_h, k=scale_k))

    query = f'<.*> s0 .* s61 <.*>'
    click.echo(query)


@cli.command()
@click.argument('topo_out', type=click.Path(writable=True))
@click.argument('routing_out', type=click.Path(writable=True))
@click.argument('scale', type=int)
def scaling_jiri(topo_out, routing_out, scale):
    name = 'scaling_jiri'
    topo_template = __environment.get_template(f'{name}_topo.jinja')
    routing_template = __environment.get_template(f'{name}_routing.jinja')
    with open(topo_out, 'wt') as f:
        f.write(topo_template.render(n=scale))
    with open(routing_out, 'wt') as f:
        f.write(routing_template.render(n=scale))

    query = f'<> s0 .* s5 <>'
    click.echo(query)



if __name__ == '__main__':
    cli(sys.argv[1:], obj=dict())
