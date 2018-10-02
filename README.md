P-REX
=====
The pushdown MPLS network checker


P-Rex is a model checker based on pushdowns for exploring and verifying
MPLS networks. P-Rex takes in the mpls network in one of two formats, either
in a bespoke XML format, or as a juniper dump. It then puts it together with
a query and generates a pushdown in such a way that reachability in the
pushdown implies something about reachability in the source MPLS network.

P-Rex is written in Python3, and only deals with the translation of
xml/juniper -> (MPLS-model + query) -> Pushdown. The tool uses moped
(Version 1), bundled with the application, to compute reachability in the
pushdown. Moped can be found [here](http://www2.informatik.uni-stuttgart.de/fmi/szs/tools/moped/) and we want to
thank the authors for making it available :).

Structure
---------
The repository follows a simple structure. All code related to the core tool
is located in the `prex` folder. The entrypoint of prex is `prex/main.py`.

The `bin` folder containes the binaries we rely on, just moped. The `bin`
folder should be in the `$PATH` of P-Rex in order for us to find it.

`res` contains test data. `res/nestable` is a simple network, in the
bespoke xml format, used extensively throughout testing and development
of the tool, and has a myriad of fun edge cases to explore. It is also
the network used in the majority of the test cases distributed with the
tool, so you can glance some of them through there. `res/new_mpls_dump`
is a dump of a real network, used to benchmark the tool in the
whitepaper. It's in the juniper dump format.

Lastly, the `test` folder includes a bunch of tests used during
development. They are structure such that a linux machine should only
have to run `./test/test_cli.sh` to run the full test suite and get
a regression report. That also makes it a repository of examples.

Running
-------
As said in structure, the tool needs moped to be in the path, luckily
a compiled moped is located in `bin`. Due to P-Rex being bundled as a python
module it's also necessary to include the project root in the `$PYTHONPATH`.
The full command to run P-Rex on the nestable network with the query `<> .*
<>` for `k = 1` in over-approximation mode becomes.

    PATH="./bin/:$PATH" PYTHONPATH=. python3 prex/main.py xml res/nestable/topo.xml  res/nestable/routing.xml adv-query "<> .* <>" 1 compile run

The juniper dump is run with, (beware this takes a while):

    PATH="./bin/:$PATH" PYTHONPATH=. python3 prex/main.py juniper-xml res/new_mpls_dump/isis  res/new_mpls_dump/forwarding adv-query "<> .* <>" 1 compile run

It should be possible to use the `--help` flag at any point to get help
about the possible options.
