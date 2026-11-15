"""Dependent rounding of Wilson flows into integer person -> POI assignments.

    X = dependent_round_fast(T, cap, rng)

T: people (or groups of identical people) x POIs flows with column sums <= cap, e.g. from
wilson_allocation.capped_production(O, P, cap). cap must be whole numbers.
X: integer matrix with E[X] = T, every cell floor or ceil of T, column sums <= cap and each
row sum floor or ceil of T's row sum. With one person per row (rows sum to <= 1) X is 0/1:
each person at most one POI.

Method (Gandhi et al. 2006, bipartite dependent rounding): keep the whole part of each cell
and round the fractional parts. Take a cycle of fractional cells, shift values around it with
alternating signs by a random step chosen so the expectation is unchanged, until a cell hits
0 or 1; repeat. Every vertex sum is preserved.

Same algorithm and interface as the first version, made near-linear:
  * two slack vertices make every vertex sum a whole number (a "nobody" POI tops each row,
    a "nobody" person each POI, up to the next whole number). Then no vertex has exactly one
    fractional cell, so there are no dead ends and no path case: every walk closes a cycle.
  * the walk is kept between steps and only cut back to where the cycle began, instead of
    searching the whole graph each step (that was quadratic: 100 agents on POI.csv did not
    finish in 4 minutes).
  * the loop is compiled with numba if it is installed (pip install numba); without numba
    the same code runs as plain Python, correct but far slower.
"""
import numpy as np

try:
    from numba import njit
except ImportError:                                        # plain Python fallback
    def njit(*a, **k):
        return a[0] if a and callable(a[0]) else (lambda f: f)

TOL = 1e-10


def dependent_round_fast(T, cap, rng):
    x = np.array(T, dtype=float, copy=True)
    cap = np.asarray(cap, dtype=float)
    n, m = x.shape
    assert np.allclose(cap, np.rint(cap))
    assert np.all(x >= -TOL)
    assert np.all(x.sum(axis=0) <= cap + 1e-8)
    x[x < TOL] = 0.0
    base = np.floor(x + TOL)                               # whole part kept as is
    x = np.where(x - base < TOL, 0.0, x - base)            # fractional part, rounded below
    rowcap = np.ceil(x.sum(axis=1) - 1e-9) + base.sum(axis=1)

    # edges (person-side vertex, POI-side vertex, value):
    # people 0..n-1, slack person n | POIs n+1..n+m, slack POI n+m+1
    SP, SQ = n, n + m + 1
    ii, jj = np.nonzero(x > 0)
    row, col = x.sum(axis=1), x.sum(axis=0)
    rs, cs = np.ceil(row - 1e-9) - row, np.ceil(col - 1e-9) - col   # top-ups to whole numbers
    ri, cj = np.nonzero(rs > TOL)[0], np.nonzero(cs > TOL)[0]
    S = rs[ri].sum()
    e = np.ceil(S - 1e-9) - S                              # makes both slack sums whole
    eu = np.concatenate([ii, ri, np.full(len(cj), SP), [SP] if e > TOL else []]).astype(np.int64)
    ew = np.concatenate([n + 1 + jj, np.full(len(ri), SQ), n + 1 + cj, [SQ] if e > TOL else []]).astype(np.int64)
    val = np.concatenate([x[ii, jj], rs[ri], cs[cj], [e] if e > TOL else []]).astype(float)

    val = _round_cycles(eu, ew, val, n + m + 2, int(rng.integers(2**32)))

    real = ew < SQ
    real &= eu < n
    x[eu[real], ew[real] - n - 1] = val[real]
    X = (base + np.rint(x)).astype(int)
    assert np.all(X.sum(axis=1) <= rowcap)
    assert np.all(X.sum(axis=0) <= cap)
    return X


@njit(cache=True)
def _kill(k, v, inc, where, end, eu):
    """Remove edge k from vertex v's live incidence segment (swap with the last live one)."""
    side = 0 if eu[k] == v else 1
    p = where[2 * k + side]
    last = end[v] - 1
    m = inc[last]
    inc[p] = m
    where[2 * m + (0 if eu[m] == v else 1)] = p
    inc[last] = k
    where[2 * k + side] = last
    end[v] -= 1


@njit(cache=True)
def _round_cycles(eu, ew, val, V, seed):
    np.random.seed(seed)
    E = len(val)
    # live incident edges of vertex v are inc[start[v]:end[v]]
    deg = np.zeros(V + 1, np.int64)
    for k in range(E):
        deg[eu[k] + 1] += 1
        deg[ew[k] + 1] += 1
    start = np.cumsum(deg)
    end = start[:-1].copy()
    inc = np.empty(2 * E, np.int64)
    where = np.empty(2 * E, np.int64)                      # slot of edge k at eu (2k) and ew (2k+1)
    for k in range(E):
        inc[end[eu[k]]] = k; where[2 * k] = end[eu[k]]; end[eu[k]] += 1
        inc[end[ew[k]]] = k; where[2 * k + 1] = end[ew[k]]; end[ew[k]] += 1
    pos = np.full(V, -1, np.int64)
    path = np.empty(V, np.int64)                           # vertices on the walk
    pedge = np.empty(V, np.int64)                          # edge used to reach path[k]
    cyc = np.empty(V + 1, np.int64)
    L = 0
    s = 0
    while True:
        if L == 0:                                         # new start vertex
            while s < V and end[s] == start[s]:
                s += 1
            if s == V:
                break
            path[0] = s; pedge[0] = -1; pos[s] = 0; L = 1
        u = path[L - 1]
        arr = pedge[L - 1]
        q = start[u]
        if q < end[u] and inc[q] == arr:
            q += 1
        if q >= end[u]:                                    # only from float drift: settle and back off
            if arr >= 0:
                val[arr] = np.round(val[arr])
                _kill(arr, eu[arr], inc, where, end, eu)
                _kill(arr, ew[arr], inc, where, end, eu)
            pos[u] = -1; L -= 1
            continue
        nxt = inc[q]
        w = eu[nxt] + ew[nxt] - u
        if pos[w] < 0:
            pos[w] = L; path[L] = w; pedge[L] = nxt; L += 1
            continue
        # cycle: edges pedge[pos[w]+1 .. L-1], then nxt
        k0 = pos[w]
        c = 0
        for q in range(k0 + 1, L):
            cyc[c] = pedge[q]; c += 1
        cyc[c] = nxt; c += 1
        a = 1.0; b = 1.0                                   # largest steps in + and - directions
        for q in range(c):
            v = val[cyc[q]]
            if q % 2 == 0:
                a = min(a, 1.0 - v); b = min(b, v)
            else:
                a = min(a, v); b = min(b, 1.0 - v)
        d = a if np.random.random() < b / (a + b) else -b  # mean shift 0
        for q in range(c):
            k = cyc[q]
            v = val[k] + (d if q % 2 == 0 else -d)
            if v < 1e-10 or v > 1.0 - 1e-10:
                v = np.round(v)
                _kill(k, eu[k], inc, where, end, eu)
                _kill(k, ew[k], inc, where, end, eu)
            val[k] = v
        for q in range(k0 + 1, L):
            pos[path[q]] = -1
        L = k0 + 1
    return val


def _self_test():
    import wilson_allocation as wa
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(10):
        n, m = rng.integers(3, 8), rng.integers(2, 5)
        P = rng.random((n, m)); P /= P.sum(1, keepdims=True)
        cap = rng.integers(1, 4, m).astype(float)
        T, _ = wa.capped_production(np.ones(n), P, cap)
        mean = sum(dependent_round_fast(T, cap, rng) for _ in range(4000)) / 4000
        worst = max(worst, np.abs(mean - T).max())
    assert worst < 0.04, worst                             # E[X] = T up to sampling noise
    T = np.array([[0.4, 0.4], [0.4, 0.4], [0.2, 0.0]])     # unmet shares, one part-full POI
    for _ in range(200):
        X = dependent_round_fast(T, np.array([1.0, 1.0]), rng)
        assert X[2, 1] == 0 and X.sum() >= 1 and X.max() <= 1
    T = np.array([[2.6, 1.4], [0.5, 3.5]])                 # groups: integer counts
    mean = sum(dependent_round_fast(T, np.array([4.0, 5.0]), rng) for _ in range(4000)) / 4000
    assert np.abs(mean - T).max() < 0.05
    print(f'dependent_rounding self-test passed (max |mean - T| = {worst:.3f})')


if __name__ == '__main__':
    _self_test()
