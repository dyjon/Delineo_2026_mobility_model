import numpy as np
import networkx as nx

def dependent_round_fast(T, cap, rng):
    x = np.array(T, dtype=float, copy=True)
    cap = np.asarray(cap, dtype=float)
    tol = 1e-10

    assert np.allclose(cap, np.rint(cap))
    assert np.all(x >= -tol)
    assert np.all(x.sum(axis=1) <= 1 + 1e-8)
    assert np.all(x.sum(axis=0) <= cap + 1e-8)

    x[np.abs(x) < tol] = 0.0
    x[np.abs(x - 1) < tol] = 1.0

    rows, cols = np.where((x > tol) & (x < 1 - tol))
    G = nx.Graph()
    G.add_edges_from((("person", int(i)), ("poi", int(j))) for i, j in zip(rows, cols))

    while G.number_of_edges() > 0:

        try:
            walk = nx.find_cycle(G)

        except nx.NetworkXNoCycle:
            leaf = next(v for v in G if G.degree[v] == 1)
            other = next(v for v in nx.node_connected_component(G, leaf) if v != leaf and G.degree[v] == 1)
            path = nx.shortest_path(G, leaf, other)
            walk = list(zip(path[:-1], path[1:]))

        ij = [(u[1] if u[0] == "person" else v[1], u[1] if u[0] == "poi" else v[1]) for u, v in walk]
        values = np.array([x[i, j] for i, j in ij])

        signs = np.where(np.arange(len(ij)) % 2 == 0, 1, -1)
        a = np.min(np.where(signs > 0, 1 - values, values))
        b = np.min(np.where(signs > 0, values, 1 - values))
        delta = (a if rng.random() < b / (a + b) else -b)

        for (u, v), (i, j), value in zip(walk, ij, values + delta * signs):

            if abs(value) < tol:
                x[i, j] = 0.0
                G.remove_edge(u, v)

            elif abs(value - 1) < tol:
                x[i, j] = 1.0
                G.remove_edge(u, v)

            else:
                x[i, j] = value

    X = np.rint(x).astype(int)

    assert np.all(X.sum(axis=1) <= 1)
    assert np.all(X.sum(axis=0) <= cap)

    return X