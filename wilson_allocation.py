"""Wilson's entropy-maximising spatial interaction models, with an optional capacity limit.

Self-contained: needs only numpy. Use it as a library, or from the command line on two CSV files
(see WILSON.md for the full explanation, input format and examples):

    python wilson_allocation.py --origins examples/origins.csv --places examples/places.csv \
        --model capped --beta 2 --out examples/result
    python wilson_allocation.py --self-test

Wilson (1967; the family set out in Wilson 1971) chooses the most probable flow matrix T_ij from
origins i to destinations j, given what is known. With deterrence f_ij = f(d_ij):

  production-constrained  T_ij = O_i W_j^a f_ij / sum_k W_k^a f_ik      origin totals O_i known
  attraction-constrained  T_ij = D_j O_i f_ij / sum_k O_k f_kj          destination totals D_j known
  doubly constrained      T_ij = A_i B_j f_ij, A and B found by         both known
                          iterative proportional fitting (Furness)

capped_production() adds a capacity kappa_j to each destination. It places as much as capacity
allows and, among all allocations doing that, returns the most probable one:

  maximise allocated total, then minimise KL(T || T0)
  subject to sum_j T_ij <= O_i,  sum_i T_ij <= kappa_j

where T0 is the production-constrained solution. It equals T0 when no capacity binds and is
otherwise T_ij = T0_ij a_i b_j. Case A (total demand <= total capacity): every origin total is
placed, capacities are ceilings. Case B (demand > capacity): every destination is full, the rest is
unmet. Both are solved by exact coordinate ascent on the dual, stopping on the Karush-Kuhn-Tucker
conditions.
"""
import argparse
import csv

import numpy as np

EARTH_KM = 6371.0088
MIN_KM = 0.1          # distances below 100 m are treated as 100 m, so zero distance stays finite


# ---------------------------------------------------------------- distances and weights

def distance_matrix(origin_lat, origin_lon, dest_lat, dest_lon):
    """Great-circle distance in km, origins x destinations."""
    la1, lo1 = np.radians(np.asarray(origin_lat, float))[:, None], np.radians(np.asarray(origin_lon, float))[:, None]
    la2, lo2 = np.radians(np.asarray(dest_lat, float))[None, :], np.radians(np.asarray(dest_lon, float))[None, :]
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def deterrence(d_km, beta=2.0, form='power'):
    """f(d) = d^-beta ('power', cost = log distance) or exp(-beta d) ('exponential', Wilson's
    original form with cost = distance). Distances below MIN_KM are raised to MIN_KM."""
    d = np.maximum(MIN_KM, np.asarray(d_km, float))
    if not np.isfinite(d).all() or beta < 0:
        raise ValueError('Distances must be finite and beta nonnegative')
    if form == 'power':
        return d ** -beta
    if form == 'exponential':
        return np.exp(-beta * d)
    raise ValueError("form must be 'power' or 'exponential'")


def weights(attractiveness, d_km, alpha=1.0, beta=2.0, form='power'):
    """w_ij = W_j^alpha * f(d_ij): the unnormalised pull of destination j on origin i."""
    a = np.asarray(attractiveness, float)
    if (a < 0).any() or not np.isfinite(a).all():
        raise ValueError('Attractiveness must be finite and nonnegative')
    return a[None, :] ** alpha * deterrence(d_km, beta, form)


# ---------------------------------------------------------------- the four models

def _normalise_rows(totals, w):
    s = w.sum(axis=1, keepdims=True)
    return np.divide(w, s, out=np.zeros_like(w), where=s > 0) * totals[:, None]


def production_constrained(origin_totals, w):
    """T_ij = O_i w_ij / sum_k w_ik. Each origin's total is shared in proportion to w."""
    O, w = np.asarray(origin_totals, float), np.asarray(w, float)
    return _normalise_rows(O, w)


def attraction_constrained(destination_totals, w):
    """T_ij = D_j w_ij / sum_k w_kj, with w_ij = origin mass x deterrence."""
    D, w = np.asarray(destination_totals, float), np.asarray(w, float)
    return _normalise_rows(D, w.T).T


def doubly_constrained(origin_totals, destination_totals, f, tol=1e-10, max_iter=100_000):
    """T_ij = A_i B_j f_ij with row sums O_i and column sums D_j (iterative proportional fitting)."""
    O, D, T = (np.asarray(x, float) for x in (origin_totals, destination_totals, f))
    if not np.isclose(O.sum(), D.sum(), rtol=1e-9):
        raise ValueError('Origin and destination totals must be equal')
    T = T.copy()
    for _ in range(max_iter):
        r = T.sum(axis=1)
        T *= np.divide(O, r, out=np.zeros_like(O), where=r > 0)[:, None]
        c = T.sum(axis=0)
        T *= np.divide(D, c, out=np.zeros_like(D), where=c > 0)[None, :]
        if np.abs(T.sum(axis=1) - O).max() <= tol * max(1.0, O.max()):
            return T
    raise RuntimeError('Doubly constrained fit did not converge (are the totals reachable?)')


def capped_production(origin_totals, w, capacity, tol=1e-12, max_iter=200_000):
    """Production-constrained flows with a capacity per destination. Returns (T, unmet per origin)."""
    O, w, cap = (np.asarray(x, float) for x in (origin_totals, w, capacity))
    if w.shape != (O.size, cap.size):
        raise ValueError('Allocation dimensions disagree')
    if any(not np.isfinite(x).all() or (x < 0).any() for x in (O, w, cap)):
        raise ValueError('Allocation inputs must be finite and nonnegative')
    reach = w.sum(axis=1) > 0
    cols = w[reach].sum(axis=0) > 0
    sub = w[np.ix_(reach, cols)]
    if (sub <= 0).any():
        raise ValueError('Every reachable origin must reach every reachable place '
                         '(partial reachability is not supported)')
    T = np.zeros_like(w)
    if not reach.any() or not cols.any():
        return T, O.copy()
    o, k = O[reach], cap[cols]
    T0 = production_constrained(o, sub)
    a, b = np.ones(o.size), np.ones(k.size)
    kt, ot = k * tol + tol, o * tol + tol          # per-place / per-origin tolerances
    if o.sum() <= k.sum():                            # case A: rows = O, columns <= kappa
        for _ in range(max_iter):                     # each pass ends on the row step: rows exact
            col = a @ T0
            b = np.minimum(1.0, np.divide(k, col, out=np.ones_like(k), where=col > 0))
            row = T0 @ b
            a = np.divide(o, row, out=np.zeros_like(o), where=row > 0)
            col = (a @ T0) * b
            if (col <= k + kt).all() and (np.abs(col - k) <= kt)[b < 1].all():
                break
        else:
            raise RuntimeError('Capped allocation did not converge')
    else:                                             # case B: columns = kappa, rows <= O
        for _ in range(max_iter):                     # each pass ends on the column step: columns exact
            row = T0 @ b
            a = np.minimum(1.0, np.divide(o, row, out=np.ones_like(o), where=row > 0))
            col = a @ T0
            b = np.divide(k, col, out=np.zeros_like(k), where=col > 0)
            row = (T0 @ b) * a
            if (row <= o + ot).all() and (np.abs(row - o) <= ot)[a < 1].all():
                break
        else:
            raise RuntimeError('Capped allocation did not converge')
    T[np.ix_(reach, cols)] = T0 * a[:, None] * b[None, :]
    return T, np.maximum(0.0, O - T.sum(axis=1))


# ---------------------------------------------------------------- end-to-end on tables

MODELS = ('production', 'capped', 'attraction', 'doubly')


def run(origins, places, model='capped', alpha=1.0, beta=2.0, form='power'):
    """origins: rows with lat, lon, total. places: rows with lat, lon and, by model,
    size (production, capped), capacity (capped; blank = no limit), total (attraction, doubly).
    Returns (T origins x places, unmet per origin)."""
    if model not in MODELS:
        raise ValueError(f'model must be one of {MODELS}')

    def num(rows, key, table, blank=None):
        """Column as floats; blank cells become `blank`, or are an error if no default is given."""
        cells = [str(r.get(key, '')).strip() for r in rows]
        if blank is None and '' in cells:
            raise ValueError(f"model '{model}' needs a value in column '{key}' on every row of the {table} file")
        return np.array([float(c) if c else blank for c in cells], dtype=float)

    d = distance_matrix(num(origins, 'lat', 'origins'), num(origins, 'lon', 'origins'),
                        num(places, 'lat', 'places'), num(places, 'lon', 'places'))
    O = num(origins, 'total', 'origins')
    if model in ('production', 'capped'):
        w = weights(num(places, 'size', 'places'), d, alpha, beta, form)
        if model == 'production':
            T = production_constrained(O, w)
            return T, O - T.sum(axis=1)
        cap = num(places, 'capacity', 'places', blank=1e300)   # blank or missing = no limit
        return capped_production(O, w, cap)
    f = deterrence(d, beta, form)
    D = num(places, 'total', 'places')
    if model == 'attraction':
        T = attraction_constrained(D, O[:, None] ** alpha * f)
    else:
        T = doubly_constrained(O, D, f)
    return T, np.zeros(len(origins))


def _read(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _write(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main(argv=None):
    p = argparse.ArgumentParser(description="Wilson spatial interaction model on two CSV files.")
    p.add_argument('--origins', required=False, help='CSV: origin_id, lat, lon, total')
    p.add_argument('--places', required=False, help='CSV: place_id, lat, lon, size[, capacity][, total]')
    p.add_argument('--model', choices=MODELS, default='capped')
    p.add_argument('--alpha', type=float, default=1.0, help='size exponent (default 1)')
    p.add_argument('--beta', type=float, default=2.0, help='distance exponent (default 2)')
    p.add_argument('--form', choices=('power', 'exponential'), default='power')
    p.add_argument('--out', default='wilson', help='output prefix (default: wilson)')
    p.add_argument('--flows', action='store_true', help='also write every origin-place flow')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args(argv)
    if a.self_test:
        _self_test()
        return
    if not (a.origins and a.places):
        p.error('--origins and --places are required (or use --self-test)')
    origins, places = _read(a.origins), _read(a.places)
    T, unmet = run(origins, places, a.model, a.alpha, a.beta, a.form)
    inflow, allocated = T.sum(axis=0), T.sum(axis=1)
    totals = np.array([float(r['total']) for r in origins])
    unmet = np.where(unmet <= 1e-9 * np.maximum(1.0, totals), 0.0, unmet)   # drop rounding residue
    cap = [str(r.get('capacity', '')).strip() for r in places]
    at_cap = [int(c != '' and x >= float(c) * (1 - 1e-9)) for x, c in zip(inflow, cap)]
    _write(f'{a.out}_places.csv', ['place_id', 'inflow', 'capacity', 'at_or_over_capacity'],
           [[r['place_id'], f'{x:.6g}', c, f] for r, x, c, f in zip(places, inflow, cap, at_cap)])
    _write(f'{a.out}_origins.csv', ['origin_id', 'total', 'allocated', 'unmet'],
           [[r['origin_id'], r['total'], f'{x:.6g}', f'{u:.6g}'] for r, x, u in zip(origins, allocated, unmet)])
    if a.flows:
        _write(f'{a.out}_flows.csv', ['origin_id', 'place_id', 'flow'],
               [[origins[i]['origin_id'], places[j]['place_id'], f'{T[i, j]:.6g}']
                for i, j in zip(*np.nonzero(T))])
    note = '' if a.model == 'capped' else ' (capacity not applied in this model)'
    print(f'{a.model}: allocated {allocated.sum():.6g} of {totals.sum():.6g}, unmet {unmet.sum():.6g}, '
          f'{sum(at_cap)} place(s) at or over capacity{note}; wrote {a.out}_places.csv, {a.out}_origins.csv'
          + (f', {a.out}_flows.csv' if a.flows else ''))


# ---------------------------------------------------------------- checks

def _self_test():
    rng = np.random.default_rng(3)
    w = weights([4.0, 1.0, 2.0], rng.random((5, 3)) * 10 + 0.5, alpha=1, beta=2)
    O = rng.random(5) * 10

    T = production_constrained(O, w)                  # rows = O, shares proportional to w
    assert np.allclose(T.sum(1), O) and np.allclose(T / T.sum(1, keepdims=True), w / w.sum(1, keepdims=True))

    D = rng.random(3); D *= O.sum() / D.sum()
    T = doubly_constrained(O, D, w)
    assert np.allclose(T.sum(1), O) and np.allclose(T.sum(0), D)
    T = attraction_constrained(D, w)
    assert np.allclose(T.sum(0), D)

    T, unmet = capped_production(O, w, [1e9] * 3)     # no cap binds: exactly production-constrained
    assert np.allclose(T, production_constrained(O, w)) and np.allclose(unmet, 0)

    # A capped place must keep the entropy form T = T0 a_i b_j (a simple "redistribute the overflow"
    # rule breaks it on this example).
    W = np.array([[9., 1., 1.], [1., 9., 1.]])
    T, unmet = capped_production([10, 10], W, [2, 100, 100])
    ratio = T / production_constrained([10, 10], W)
    assert np.allclose(ratio[0] / ratio[1], ratio[0, 0] / ratio[1, 0])
    assert np.isclose(T[:, 0].sum(), 2) and np.allclose(T.sum(1), 10) and np.allclose(unmet, 0)

    for trial in range(200):                          # optimality conditions on random problems
        n, m = rng.integers(1, 7), rng.integers(1, 7)
        w = rng.random((n, m)) + 1e-3
        O, cap = rng.random(n) * 10, rng.random(m) * (5 if trial % 2 else 30)
        T, unmet = capped_production(O, w, cap)
        T0 = production_constrained(O, w)
        rows, cols = T.sum(1), T.sum(0)
        assert np.isclose(rows.sum(), min(O.sum(), cap.sum()))          # maximal allocation
        assert (cols <= cap + 1e-8).all() and (rows <= O + 1e-8).all()
        assert np.allclose(rows + unmet, O)
        r = np.divide(T, T0, out=np.zeros_like(T), where=T0 > 0)
        assert np.allclose(r, np.outer(r[:, 0] / r[0, 0], r[0]) if r[0, 0] > 0 else r)  # T = T0 a b
        if O.sum() <= cap.sum():                       # case A: b <= 1, b < 1 only at full places
            b = r[0] / r[0].max() if r[0].max() > 0 else r[0]
            assert np.allclose(rows, O) and ((b > 1 - 1e-9) | np.isclose(cols, cap)).all()
            assert unmet.max() <= 1e-9 * max(1.0, O.max())
        else:
            assert np.allclose(cols, cap)

    T, unmet = capped_production([5e4, 3e4], [[9., 1., 1.], [1., 9., 1.]], [5.0, 1e7, 1e7])
    assert T[:, 0].sum() <= 5.0 * (1 + 1e-11) and unmet.max() <= 1e-6     # small cap respected
    assert np.allclose(capped_production([7], [[0, 0]], [2, 3])[1], [7])   # unreachable: all unmet
    try:
        capped_production([10, 10], [[1, 0], [0, 1]], [2, 30])
        raise AssertionError('partial reachability accepted')
    except ValueError:
        pass

    # Distances: 1 degree of latitude is ~111.2 km; the 0.1 km floor keeps zero distance finite.
    assert abs(distance_matrix([39.0], [-76.6], [40.0], [-76.6])[0, 0] - 111.195) < 0.01
    assert np.isclose(deterrence([0.0], 2)[0], 100.0)

    # End to end on tables: production totals are kept; a binding capacity is respected.
    origins = [dict(origin_id='a', lat='39.30', lon='-76.62', total='100'),
               dict(origin_id='b', lat='39.32', lon='-76.60', total='50')]
    places = [dict(place_id='x', lat='39.30', lon='-76.61', size='400', capacity='20'),
              dict(place_id='y', lat='39.31', lon='-76.60', size='100', capacity=''),
              dict(place_id='z', lat='39.33', lon='-76.63', size='900', capacity='')]
    T, unmet = run(origins, places, 'capped', beta=2)
    assert np.isclose(T.sum(), 150) and T[:, 0].sum() <= 20 + 1e-9 and np.allclose(unmet, 0)
    T, _ = run(origins, places, 'production', beta=2)
    assert np.allclose(T.sum(1), [100, 50]) and T[:, 0].sum() > 20      # without the cap, x overfills
    print('wilson_allocation self-tests passed')


if __name__ == '__main__':
    main()
