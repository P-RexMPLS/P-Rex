def nfa_to_nx(nfa):
    import networkx as nx
    G = nx.MultiDiGraph()
    names = {location: location.name for location in nfa.locations}
    for transition in nfa.transitions:
        G.add_edge(names[transition.from_], names[transition.to])
    return G


def draw_nfa(nfa):
    import networkx as nx
    import matplotlib.pyplot as plt
    G = nfa_to_nx(nfa)
    pos = nx.nx_pydot.pydot_layout(G, prog="dot")
    nx.nx_pydot.write_dot(G, 'graph.dot')
    nx.draw_networkx(G, pos=pos)
    plt.show()
