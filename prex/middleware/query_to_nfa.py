from ..lang.prex import (
    Analysis,
    Lexer,
    Parser,
    AZeroOrMoreQuantifier,
    AOneOrMoreQuantifier,
    AZeroOrOneQuantifier,
)
from ..nfa.graph import (
    NFA,
    Symbol,
)
from prex.prnml import (
    model as prnml,
)
from prex.util import (
    memoized,
    keydefaultdict,
)
import io
import re
import pathlib
from collections import defaultdict


class NFAConstructor(Analysis):
    def __init__(self, location_prefix):
        super().__init__()
        self.location_prefix = location_prefix
        self._nfa = NFA()
        self.location_number = 0

    def _get_loc(self):
        loc = self._nfa.location(
            f'{self.location_prefix}_{self.location_number}'
        )
        self.location_number += 1
        return loc

    def _get_symbol_domain(self, exclude=set()):
        raise NotImplementedError

    def get_nfa(self):
        return self._nfa

    def caseASimpleAtom(self, node, in_loc, out_loc):
        symbols = node.getSymbol().apply(self)

        for symbol in symbols:
            self._nfa.transition(
                in_loc,
                out_loc,
                symbol
            ).attach()

        return out_loc

    def caseASequenceAtom(self, node, in_loc, out_loc):
        in_ = in_loc
        for atom in node.getAtoms()[:-1]:
            out = self._get_loc()
            in_ = atom.apply(self, in_, out)
        node.getAtoms()[-1].apply(self, in_, out_loc)

        return out_loc

    def caseAAnyAtom(self, node, in_loc, out_loc):
        for symbol in self._get_symbol_domain():
            self._nfa.transition(
                in_loc,
                out_loc,
                symbol
            ).attach()

        return out_loc

    def caseAAlternativeAtom(self, node, in_loc, out_loc):
        node.getLeft().apply(self, in_loc, out_loc)
        node.getRight().apply(self, in_loc, out_loc)

        return out_loc

    def caseAQuantifiedAtom(self, node, in_loc, out_loc):
        node.getAtom().apply(self, in_loc, out_loc)

        quantifier = node.getQuantifier()
        if isinstance(quantifier, AZeroOrMoreQuantifier):
            # Add loop
            self._nfa.epsilon_transition(out_loc, in_loc).attach()
            # Add a bypass transition
            self._nfa.epsilon_transition(in_loc, out_loc).attach()
        elif isinstance(quantifier, AOneOrMoreQuantifier):
            # Add loop
            self._nfa.epsilon_transition(out_loc, in_loc).attach()
        elif isinstance(quantifier, AZeroOrOneQuantifier):
            # Add a bypass transition
            self._nfa.epsilon_transition(in_loc, out_loc).attach()
        else:
            raise RuntimeError('Unknown quantifier')

        return out_loc

    def caseANegativeSetAtom(self, node, in_loc, out_loc):
        symbols = set()
        for child in node.getSymbols():
            child_symbols = child.apply(self)
            symbols.update(child_symbols)
        # Add a transition for every symbol in the domain,
        # not in the negative set
        for symbol in self._get_symbol_domain(exclude=symbols):
            self._nfa.transition(
                in_loc,
                out_loc,
                symbol
            ).attach()

        return out_loc

    def caseAPositiveSetAtom(self, node, in_loc, out_loc):
        symbols = set()
        for child in node.getSymbols():
            child_symbols = child.apply(self)
            symbols.update(child_symbols)
        # Add a transition for every symbol in the set
        for symbol in symbols:
            self._nfa.transition(
                in_loc,
                out_loc,
                symbol
            ).attach()

        return out_loc

    escape_expander = re.compile(r'\\(.)')

    def caseALiteralSymbolType(self, node):
        return self.escape_expander.sub(
            r'\1',
            node.getWord().getText()
        )

    def parse_ast(self, ast):
        if ast is None:
            # Empty query
            only_node = self._get_loc()
            start = only_node
            end = only_node
        else:
            # Transform the AST
            start = self._get_loc()
            end = self._get_loc()
            ast.apply(self, start, end)

        self._nfa.initial = start
        self._nfa.final = end

        return self._nfa


class SequenceAtomReverser(Analysis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inverted = set()

    def caseASequenceAtom(self, node, *args, **kwargs):
        # Reverse and set a flag,
        # so multipass stages with this mixin don't mess up
        if node not in self.inverted:
            node._atoms_ = node._atoms_[::-1]
            self.inverted.add(node)
            return super().caseASequenceAtom(node, *args, **kwargs)


class Constructing(SequenceAtomReverser, NFAConstructor):
    def __init__(self, name_label_map):
        super().__init__('C')
        self.name_label_map = name_label_map
        self.Symbol = memoized(Symbol)
        self.get_symbol = lambda value: self.Symbol(self._nfa, value)

    def _get_symbol_domain(self, exclude=set()):
        # Exclude is a set of strings
        exclude_strings = {elem.value.name for elem in exclude}
        keys = self.name_label_map.keys() - exclude_strings
        labels = [self.name_label_map[key] for key in keys]
        return [self.get_symbol(label) for label in labels]

    def caseASimpleSymbol(self, node):
        label_text = node.getSymbolType().apply(self)
        label = self.name_label_map[label_text]
        return [self.get_symbol(label)]

    def caseATupleSymbol(self, node):
        raise NotImplementedError()


class Destructing(NFAConstructor):
    def __init__(self, name_label_map):
        super().__init__('D')
        self.name_label_map = name_label_map
        self.Symbol = memoized(Symbol)
        self.get_symbol = lambda value: self.Symbol(self._nfa, value)

    def _get_symbol_domain(self, exclude=set()):
        # Exclude is a set of strings
        exclude_strings = {elem.value.name for elem in exclude}
        keys = self.name_label_map.keys() - exclude_strings
        labels = [self.name_label_map[key] for key in keys]
        return [self.get_symbol(label) for label in labels]

    def caseASimpleSymbol(self, node):
        label_text = node.getSymbolType().apply(self)
        label = self.name_label_map[label_text]
        return [self.get_symbol(label)]

    def caseATupleSymbol(self, node):
        raise NotImplementedError


class Network(NFAConstructor):
    def __init__(self, router_name_location_map, pda):
        super().__init__('N')
        self.router_name_location_map = router_name_location_map
        self.pda = pda
        self.Symbol = memoized(Symbol)
        self.get_symbol = lambda value: self.Symbol(self._nfa, value)

    def _get_symbol_domain(self, exclude=set()):
        # Exclude is a set of strings
        exclude_strings = {elem.value.name[0].name for elem in exclude}
        keys = self.router_name_location_map.keys() - exclude_strings
        locations = []
        key_locations = [self.router_name_location_map[key] for key in keys]
        for locs in key_locations:
            locations.extend(locs)
        return [self.get_symbol(location) for location in locations]

    def _match_symbols(self, symbols, in_loc, out_loc):
        eps_chain_symbols = [symbol for symbol in symbols
                             if len(symbol.value.name[2]) == 0]
        chain_symbols = [symbol for symbol in symbols
                         if len(symbol.value.name[2]) != 0]
        for symbol in eps_chain_symbols:
            self._nfa.transition(
                in_loc,
                out_loc,
                symbol
            ).attach()
        for symbol in chain_symbols:
            self._nfa.transition(
                in_loc,
                in_loc,
                symbol
            ).attach()

        return out_loc

    def caseASimpleSymbol(self, node):
        router_name = node.getSymbolType().apply(self)
        locations = self.router_name_location_map[router_name]
        return [self.get_symbol(location) for location in locations]

    def caseATupleSymbol(self, node):
        raise NotImplementedError()

    def caseASimpleAtom(self, node, in_loc, out_loc):
        symbols = node.getSymbol().apply(self)

        return self._match_symbols(symbols, in_loc, out_loc)

    def caseAAnyAtom(self, node, in_loc, out_loc):
        symbols = self._get_symbol_domain()

        return self._match_symbols(symbols, in_loc, out_loc)

    def caseANegativeSetAtom(self, node, in_loc, out_loc):
        exclude_symbols = set()
        for child in node.getSymbols():
            child_symbols = child.apply(self)
            exclude_symbols.update(child_symbols)
        # Add a transition for every symbol in the domain,
        # not in the negative set
        symbols = self._get_symbol_domain(exclude=exclude_symbols)

        return self._match_symbols(symbols, in_loc, out_loc)

    def caseAPositiveSetAtom(self, node, in_loc, out_loc):
        symbols = set()
        for child in node.getSymbols():
            child_symbols = child.apply(self)
            symbols.update(child_symbols)

        return self._match_symbols(symbols, in_loc, out_loc)

    def parse_ast(self, ast):
        super().parse_ast(ast)

        # Add new start and end locations,
        # which read pda.initial and pda.final, respectively
        start_node = self._get_loc()
        end_node = self._get_loc()
        old_start_node = self._nfa.initial
        old_end_node = self._nfa.final
        self._nfa.transition(
            start_node,
            old_start_node,
            self.get_symbol(self.pda.initial)
        ).attach()
        self._nfa.transition(
            old_end_node,
            end_node,
            self.get_symbol(self.pda.final)
        ).attach()
        self._nfa.initial = start_node
        self._nfa.final = end_node

        return self._nfa


def parse_query(query, label_domain, pda):
    if isinstance(query, str):
        lexer = Lexer(io.StringIO(query))
    elif isinstance(query, io.IOBase):
        lexer = Lexer(query)
    elif isinstance(query, pathlib.Path):
        with query.open('rt')as f:
            lexer = Lexer(io.StringIO(f.read()))
    else:
        raise RuntimeError('query must be str or IOBase')
    parser = Parser(lexer)
    query_ast = parser.parse().getPQuery()

    name_label_map = {value.name: value for value in label_domain}
    name_label_map = keydefaultdict(lambda x: prnml.Label(x), **name_label_map)
    # First element of the location tuple is the router
    router_name_location_map = defaultdict(list)

    for location in pda.locations:
        if isinstance(location.name, str):
            continue
        router_name_location_map[location.name[0].name].append(location)

    router_name_location_map = dict(router_name_location_map)

    c = Constructing(name_label_map)
    n = Network(router_name_location_map, pda)
    d = Destructing(name_label_map)

    nfa_c = c.parse_ast(query_ast.getConstructing())
    nfa_n = n.parse_ast(query_ast.getNetwork())
    nfa_d = d.parse_ast(query_ast.getDestructing())

    return nfa_c, nfa_n, nfa_d
