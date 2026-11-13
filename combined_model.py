"""Huff choice x Wilson capacity: final place selections for agents in one time slot.

    python combined_model.py --pois POI.csv --demo 200      # 200 random agents, prints a summary
    python combined_model.py --self-test

Pipeline:
  1. Huff: for each person, P[r, j] proportional to
         desirability(person, j)^gamma * size_j^ALPHA * BRAND^(branded j) / d(person, j)^BETA
     over the POIs whose type the person wants (huff_model.desirability, huff_model.gma).
  2. Wilson: wilson_allocation.capped_production(ones, P, capacity) adjusts P so that no POI holds
     more people than its capacity, changing Huff as little as possible (minimum KL divergence).
  3. dependent_rounding turns the adjusted flows into whole people, one POI each, never more
     than a POI's capacity; each person's chance of each POI is still the Wilson flow.

Defaults are fitted to Dewey/Advan visits in Baltimore (Baltimore, July 2025; checked on the team POI table):
  BETA = 1.75   distance exponent; best fit to observed visitor homes on the team's own POI table
  ALPHA = 0.25  exponent on the whole building area (visits rise slowly with size)
  BRAND = 1.85  branded places draw ~1.85x the visits at equal size (needs a `brand` column)
The team's earlier setting (no size, distance exponent 0.5) ranks observed visits negatively.

Capacity = building area / POIs in that building / occupant-load factor (IBC sq ft per person).
It counts people present at the same time, so run this once per time slot.
"""
import argparse
import csv
from collections import Counter

import numpy as np

import dependent_rounding as dr
import huff_model
import wilson_allocation as wa

ALPHA, BETA, BRAND = 0.25, 1.75, 1.85
SQFT_M2 = 0.09290304
NO_LIMIT = 1e12
# IBC occupant-load factors (sq ft per person) by POI.csv poi_specific_category
FACTOR_SQFT = {
    'restaurants': 15, 'bars_breweries': 15, 'cafes_beverages': 15,
    'apparel_personal_retail': 60, 'home_electronics_retail': 60, 'grocery_food_retail': 60,
    'convenience_retail': 60, 'specialty_retail': 60, 'general_merchandise_retail': 60,
    'worship_venues': 7, 'religious_organizations': 7,
    'health_services_unspecified': 150, 'specialty_outpatient_clinics': 150, 'mental_health_clinics': 150,
    'diagnostics_laboratories': 150, 'primary_family_clinics': 150, 'hospitals': 150,
    'gyms_fitness_studios': 50, 'primary_secondary_school': 20,
}


def load_pois(path):
    """POI.csv -> (list of huff_model.POI, size array, brand array, capacity array), aligned by index.

    size = whole building area (0 if no building); capacity = building area / POIs sharing the
    building / factor, NO_LIMIT where the category has no factor or the POI has no building.
    An optional `brand` column (non-empty = branded) turns on the brand multiplier."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    sharers = Counter(r['building_id'] for r in rows if r.get('building_id'))
    pois, size, brand, cap = [], [], [], []
    for i, r in enumerate(rows, start=1):
        pois.append(huff_model.POI(i, float(r['poi_latitude']), float(r['poi_longitude']), r['poi_specific_category']))
        area = float(r.get('building_area_square_meter') or 0)
        size.append(area)
        brand.append(bool((r.get('brand') or '').strip()))
        factor = FACTOR_SQFT.get(r['poi_specific_category'])
        cap.append(area / sharers[r['building_id']] / (factor * SQFT_M2) if factor and area > 0 else NO_LIMIT)
    return pois, np.array(size), np.array(brand), np.array(cap)


def huff_matrix(people, pois, size, brand, alpha=ALPHA, beta=BETA, brand_mult=BRAND, min_size=1.0):
    """People x POIs choice probabilities. Zero where the person does not want that POI type or is
    already there. POIs without a building get size min_size (1 m2), so they stay choosable but weak."""
    lat = np.array([p.lat for p in pois]); lon = np.array([p.long for p in pois])
    attract = np.maximum(size, min_size) ** alpha * np.where(brand, brand_mult, 1.0)
    types, first, tidx = np.unique([p.loc_type for p in pois], return_index=True, return_inverse=True)
    index = {p.id: k for k, p in enumerate(pois)}
    # people with the same start POI and desires share one row: compute each row once
    rows, row_of = {}, []
    for person in people:
        row_of.append(rows.setdefault((person.cur_loc.id, tuple(person.desires)), len(rows)))
    reps = {g: person for person, g in zip(people, row_of)}
    reps = [reps[g] for g in range(len(rows))]
    d = wa.distance_matrix([q.cur_loc.lat for q in reps], [q.cur_loc.long for q in reps], lat, lon)
    by_type = {}                                   # desires -> desirability per POI type
    U = np.zeros((len(reps), len(pois)))
    for g, person in enumerate(reps):
        key = tuple(person.desires)
        if key not in by_type:
            by_type[key] = np.array([huff_model.desirability(person, pois[k], pois) for k in first], float)
        want = by_type[key][tidx]
        if person.cur_loc.id in index:
            want[index[person.cur_loc.id]] = 0.0
        if not want.any():
            raise ValueError(f'No eligible destinations for person {person.id}')
        w = want ** huff_model.gma * attract * wa.deterrence(d[g], beta)
        U[g] = w / w.sum()
    P = U[row_of]
    return P


def select(people, pois, P, capacity, rng=None):
    """Wilson-adjusted probabilities, then whole-person assignments within capacity.

    People with identical Huff rows (same start place and desires) are pooled: Wilson runs on
    the pooled counts, dependent_rounding turns each pool's flows into whole people (capacity
    rounded down to whole people), and the pool's members are shuffled into those places.
    Returns (choices, P_final, unmet): choices[r] is a POI or None (unplaced), P_final[r] is
    person r's Wilson-adjusted probabilities, unmet[r] their chance of being unplaced."""
    rng = rng or np.random.default_rng()
    used = P.sum(axis=0) > 0                       # only POIs someone can choose
    rows, group, count = np.unique(P[:, used], axis=0, return_inverse=True, return_counts=True)
    group = group.ravel()
    cap = np.floor(capacity[used] + 1e-9)
    flows, unmet_g = wa.capped_production(count.astype(float), rows, cap)
    X = dr.dependent_round_fast(flows, cap, rng)
    final = np.zeros_like(P)
    final[:, used] = flows[group] / count[group, None]
    unmet = unmet_g[group] / count[group]
    idx = np.nonzero(used)[0]
    members = np.split(np.argsort(group, kind='stable'), np.cumsum(count)[:-1])
    choices = [None] * len(people)
    for g, mem in enumerate(members):
        for r, j in zip(rng.permutation(mem), np.repeat(idx, X[g])):
            choices[r] = pois[j]
    return choices, final, unmet


def _self_test():
    pois = [huff_model.POI(1, 39.30, -76.62, 'restaurants'), huff_model.POI(2, 39.31, -76.61, 'restaurants'),
            huff_model.POI(3, 39.30, -76.60, 'urban_parks'), huff_model.POI(4, 39.32, -76.62, 'restaurants')]
    size, brand = np.array([400.0, 100.0, 0.0, 900.0]), np.array([False, True, False, False])
    people = [huff_model.Person(k, pois[k % 4], [], ['restaurants']) for k in range(40)]
    P = huff_matrix(people, pois, size, brand)
    assert np.allclose(P.sum(1), 1) and (P[:, 2] == 0).all()                         # park not wanted
    assert all(P[r, pois.index(q.cur_loc)] == 0 for r, q in enumerate(people))        # current place excluded
    cap = np.array([5.0, NO_LIMIT, NO_LIMIT, 8.0])
    choices, final, unmet = select(people, pois, P, cap, np.random.default_rng(1))
    assert (final.sum(0) <= cap * (1 + 1e-9)).all() and np.allclose(final.sum(1) + unmet, 1)
    assert all(c is not None and P[r, pois.index(c)] > 0 for r, c in enumerate(choices))   # only wanted POIs
    # many people, tight capacity: realised counts never exceed it, expected counts match Wilson
    crowd = [huff_model.Person(k, pois[2], [], ['restaurants']) for k in range(30)]
    Pc = huff_matrix(crowd, pois, size, brand)
    capc = np.array([4.0, 6.5, NO_LIMIT, 9.0])
    hits = np.zeros(4)
    for s in range(300):
        ch, fin, _ = select(crowd, pois, Pc, capc, np.random.default_rng(s))
        n = np.bincount([pois.index(c) for c in ch if c is not None], minlength=4)
        assert (n <= np.floor(capc)).all()
        hits += n
    assert np.allclose(hits / 300, fin.sum(0), atol=0.3)
    # without binding capacity the final probabilities are exactly Huff's
    _, same, _ = select(people, pois, P, np.full(4, NO_LIMIT))
    assert np.allclose(same, P)
    print('combined_model self-tests passed')


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--pois', default='POI.csv')
    p.add_argument('--demo', type=int, default=0, help='run N random agents wanting restaurants and bars')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test or not a.demo:
        _self_test()
        return
    rng = np.random.default_rng(a.seed)
    pois, size, brand, cap = load_pois(a.pois)
    starts = rng.choice(len(pois), a.demo, replace=False)
    people = [huff_model.Person(k, pois[s], [], ['restaurants', 'bars_breweries']) for k, s in enumerate(starts)]
    P = huff_matrix(people, pois, size, brand)
    choices, final, unmet = select(people, pois, P, cap, rng)
    d = wa.distance_matrix([q.cur_loc.lat for q in people], [q.cur_loc.long for q in people],
                           [c.lat for c in choices], [c.long for c in choices]).diagonal()
    print(f'{a.demo} agents: median trip {np.median(d):.2f} km; {len({c.id for c in choices})} distinct POIs; '
          f'{int((final.sum(0) >= cap * (1 - 1e-9)).sum())} POIs at capacity; unmet {unmet.sum():.3g}')


if __name__ == '__main__':
    main()
