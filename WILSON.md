# Wilson model code (`wilson_allocation.py`)

This file explains what `wilson_allocation.py` does, how to run it, and how the capacity-limited version is solved. The module is self-contained: it needs only Python 3 and numpy, and it does not depend on any other team code.

## 1. What it does

Given **where people start** (home areas, each with a total amount of time or trips to spend) and **where they can go** (places, each with a size and optionally a capacity), it works out how that total is split across places. The result is the flow `T_ij` from every home area `i` to every place `j`, and from it the total arriving at each place.

It uses A. G. Wilson's spatial interaction models. Wilson's idea: among all the ways of splitting the totals that agree with what you know, choose the **most probable** one, the split that can happen in the greatest number of ways. Formally this means maximising entropy under the known constraints. The answer is not a modelling choice; it follows from the constraints.

## 2. Quick start

```bash
pip install numpy
python wilson_allocation.py --self-test
python wilson_allocation.py --origins examples/origins.csv --places examples/places.csv --out examples/result --flows
```

The example has four Baltimore home areas spending 550 person-hours at five restaurants in one hour, with distance exponent β = 2. One diner can hold only 15 people.

| | Diner (capacity 15) | Café | Pub | Bistro | Food hall |
|---|---:|---:|---:|---:|---:|
| `--model production` (no capacity) | 85.5 | 188.4 | 150.5 | 101.5 | 24.1 |
| `--model capped` (default) | **15.0** | 194.5 | 154.2 | 146.4 | 39.9 |

With the capacity applied, the diner is held at 15. The other 70 people go to the other restaurants, in the proportions the model implies for the home areas that were sending them to the diner. Every home area's 120, 200, 150 or 80 person-hours are still fully placed.

## 3. Input files

Both files are CSV with a header row. Extra columns are ignored.

**Origins** (`--origins`):

| Column | Meaning |
|---|---|
| `origin_id` | any label |
| `lat`, `lon` | location in decimal degrees |
| `total` | amount leaving this origin (e.g. person-hours in this hour) |

**Places** (`--places`):

| Column | Needed by | Meaning |
|---|---|---|
| `place_id` | all | any label |
| `lat`, `lon` | all | location in decimal degrees |
| `size` | `production`, `capped` | attractiveness, e.g. floor area in m² (must be > 0) |
| `capacity` | `capped` (optional) | most it can hold; blank or missing = no limit |
| `total` | `attraction`, `doubly` | known amount arriving at this place |

If a needed value is missing, the program stops and names the file and column.

## 4. The four models

Each model is one function. Write `W_j` for a place's size, `d_ij` for distance and `f(d)` for the deterrence: how quickly willingness to travel falls with distance.

| `--model` | What is known | Formula | Function |
|---|---|---|---|
| `production` | how much leaves each origin, `O_i` | `T_ij = O_i · W_j^α f(d_ij) / Σ_k W_k^α f(d_ik)` | `production_constrained` |
| `capped` | `O_i` and a capacity `κ_j` per place | see §5 | `capped_production` |
| `attraction` | how much arrives at each place, `D_j` | `T_ij = D_j · O_i^α f(d_ij) / Σ_k O_k^α f(d_kj)` | `attraction_constrained` |
| `doubly` | both `O_i` and `D_j` (equal sums) | `T_ij = A_i B_j f(d_ij)`, with `A`, `B` found by iterative proportional fitting | `doubly_constrained` |

Use the one that matches what you actually know. For estimating how busy places are from population and time-use data, you know how much leaves each home area but not how much arrives at each place, because that is what you are trying to estimate. So `production` or `capped` is the right choice. `doubly` is for when both are known, for example when checking against observed visit counts.

**Deterrence** (`--form`):
- `power` (default): `f(d) = d^−β`. Doubling the distance always divides the pull by the same factor (2^β).
- `exponential`: `f(d) = exp(−β d)`. This is Wilson's original form, where cost equals distance; pull falls off faster at long range.

Distances are great-circle distances in km. Anything under 0.1 km is treated as 0.1 km, so a place at the same spot as a home area gets a large but finite pull.

## 5. The capacity-limited model (`capped`)

### The problem it solves

Places can be full. The capped model adds a ceiling `κ_j` to each place and then:
1. places **as much as capacity allows**;
2. among all allocations that do this, picks the **most probable**: the one closest to the uncapped production-constrained solution `T0`, measured by relative entropy.

In symbols: maximise the allocated total, then minimise `Σ T_ij log(T_ij / T0_ij) − T_ij`, subject to `Σ_j T_ij ≤ O_i` and `Σ_i T_ij ≤ κ_j`.

The solution has Wilson's form `T_ij = T0_ij · a_i · b_j`: the uncapped flows, rescaled by one factor per origin (`a_i`) and one per place (`b_j`). If no place is full, `a = b = 1` and the answer is exactly the uncapped one.

### Two cases

| Case | Condition | What happens |
|---|---|---|
| A | total demand ≤ total capacity | Every origin's total is placed in full. Full places get `b_j < 1`, and the excess moves to places with room. |
| B | total demand > total capacity | Every place ends up exactly full. Origins get `a_i ≤ 1`, and what cannot be placed is reported as **unmet**. |

### How it is computed

Both cases use exact coordinate ascent on the dual problem. Each step solves one set of scaling factors in closed form, holding the other fixed:

- **Case A**, repeated until it stops changing:
  1. For each place, `b_j = min(1, κ_j / (flow it would receive))`. Full places are scaled down; others stay at 1.
  2. For each origin, `a_i = O_i / (what its flows sum to after step 1)`. Every origin's total is then exact.
- **Case B** is the mirror image: places are scaled to exactly `κ_j`, and origins are scaled down only if they would send more than `O_i`.

It stops when the optimality (Karush–Kuhn–Tucker) conditions hold to a relative tolerance of 10⁻¹²:
- no place over capacity;
- every place with `b_j < 1` exactly full;
- every origin total placed (case A), or every origin with `a_i < 1` fully used (case B).

Because these conditions are necessary and sufficient for this convex problem, the result is the exact optimum, not an approximation.

### Edge cases

- An origin with no reachable place (all weights zero) is reported entirely as unmet.
- Places with zero size are ignored (they attract nothing).
- **Partial reachability is refused.** Every origin that can reach any place must be able to reach all of them, which is always true with distance-based weights and positive sizes. If you zero out some origin–place pairs yourself (e.g. a travel-time cutoff), the function raises an error rather than guessing.

## 6. Choosing the parameters

| Parameter | Default | What it controls | Guidance |
|---|---|---|---|
| `--alpha` (α) | 1 | how strongly size attracts | 1 means pull proportional to size |
| `--beta` (β) | 2 | how strongly distance deters | see below |
| `--form` | power | shape of distance decay | power unless you have a reason |

For **visits to places** (shops, restaurants, gyms), **use β = 2**, the default. Two independent Baltimore checks agree:
- Observed visitor home areas (Advan weekly patterns via Dewey, July 2025) fit β ≈ 2 for restaurants, 1.75 for retail and 1.5 for gyms; β = 1 fits much worse.
- The universal visitation law (visitors per unit area fall as distance⁻²; Schläpfer et al. 2021) is reproduced at β ≈ 2–2.5.

For **commuting**, observed US Census flows (LODES) in Baltimore fit β ≈ 0.8. Work trips are longer, so do not use one β for both. Low values such as 0.5 spread visitors across most of a city.

## 7. Outputs

`--out PREFIX` writes:

| File | Columns |
|---|---|
| `PREFIX_places.csv` | `place_id, inflow` (total arriving), `capacity, at_or_over_capacity` |
| `PREFIX_origins.csv` | `origin_id, total, allocated, unmet` |
| `PREFIX_flows.csv` (with `--flows`) | `origin_id, place_id, flow`, every non-zero origin–place flow |

If the inputs are people present in one hour, `inflow` is the expected number of people at each place in that hour. In the non-capped models, `at_or_over_capacity` just flags places whose inflow exceeds the given capacity; capacity is not enforced there.

## 8. Using it as a library

```python
import numpy as np
from wilson_allocation import distance_matrix, weights, capped_production

d = distance_matrix(origin_lat, origin_lon, place_lat, place_lon)     # km
w = weights(place_size, d, alpha=1.0, beta=2.0)                         # origins x places
flows, unmet = capped_production(origin_totals, w, place_capacity)      # use a large number for "no limit"
occupancy = flows.sum(axis=0)
```

| Function | Returns |
|---|---|
| `distance_matrix(olat, olon, plat, plon)` | km, origins × places |
| `deterrence(d, beta, form)` | `f(d)` with the 0.1 km floor |
| `weights(size, d, alpha, beta, form)` | `size^α · f(d)` |
| `production_constrained(O, w)` | flows |
| `attraction_constrained(D, w)` | flows, with `w` = origin mass × deterrence |
| `doubly_constrained(O, D, f)` | flows |
| `capped_production(O, w, capacity)` | `(flows, unmet per origin)` |
| `run(origin_rows, place_rows, model, alpha, beta, form)` | same as the CLI, on lists of dicts |

## 9. How it was checked

`python wilson_allocation.py --self-test` checks:
- the textbook identities: production rows sum to `O`; doubly constrained rows and columns sum to `O` and `D`; attraction columns sum to `D`;
- with no binding capacity, `capped` equals `production` exactly;
- a small case where a simple "redistribute the overflow" rule breaks Wilson's form, and this solver does not;
- 200 random problems, covering both cases, against the optimality conditions: maximal allocation, no limit exceeded, full places exactly full, and the `T0 · a · b` form;
- a very small capacity next to very large ones (each place is held to its own limit);
- unreachable origins, refusal of partial reachability, the distance formula (1° of latitude ≈ 111.2 km), and the end-to-end table interface.

Separately, the capped solver was compared with a general-purpose optimiser (scipy SLSQP) on 30 random problems. It was never worse: the largest difference was 3 × 10⁻¹⁴ in the objective.

### Against current data

These checks were run with the project's L1 pipeline and validation scripts, which are not in this repository; the results are summarised here.

- **Baltimore place occupancy:** run through its command line on the pipeline's real inputs, this tool reproduces the L1 pipeline to the 10th significant digit (12 category, day and hour combinations; up to 3,250 places each).
- **Observed commuting** (US Census LODES 2023, 219,842 Baltimore jobs, 618 × 2,369 block groups):
  - The production-constrained model matches an independently written implementation to 1.4 × 10⁻⁶ jobs.
  - It puts 47% of commuters in exactly the right home–work pair (Common Part of Commuters 0.466).
  - Given the true destination totals, the doubly constrained model reaches 49%.
- **Observed place visits** (Advan weekly patterns via Dewey, 21–27 July 2025; 566 Baltimore places matched by location and name):
  - **Where visitors come from:** the best β is about 2 for restaurants, 1.75 for retail and 1.5 for gyms (likelihood of observed visitor home block groups).
  - **How busy places are:** rank correlation with weekly visits is 0.30 for restaurants, 0.40 for retail and 0.52 for gyms. Floor area as size carries this; without size the correlation is about zero.
  - Places of worship, health facilities and parks are not in the visit data, so they are untested.

## 10. Limits

- The model gives **expected** flows: an average, not a sample of individuals.
- It is only as good as its inputs: sizes are proxies for attractiveness (floor area is not the same as appeal), and β must be chosen (see §6).
- Capacities are ceilings, not targets: a place below capacity is not pushed towards it.
- Partial reachability (some origins unable to reach some places) is not supported.

## 11. References

- Wilson, A. G. (1967). A statistical theory of spatial distribution models. *Transportation Research, 1*(3), 253–269.
- Wilson, A. G. (1971). A family of spatial interaction models, and associated developments. *Environment and Planning A, 3*(1), 1–32.
- Ortúzar, J. de D., & Willumsen, L. G. *Modelling Transport* (5th ed., 2024), ch. 5: trip distribution, gravity and entropy models.
- Schläpfer, M., et al. (2021). The universal visitation law of human mobility. *Nature, 593*, 522–527.
