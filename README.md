# Delineo 2026 — Global Mobility Model

Part of the [Delineo Disease Modeling](https://github.com/Delineo-Disease-Modeling) project at Johns Hopkins. The goal is to estimate, from publicly available data, **how many people are at each place (point of interest) at each hour**. Those numbers become the mobility input for Delineo's disease-spread simulations.

Team: Liam Perez, Jingcheng Shi, Qianli Ning.

## What is in this repository

| Path | What it is | Status |
|---|---|---|
| [`wilson_allocation.py`](wilson_allocation.py) | **Population model.** Wilson's entropy-maximising spatial interaction models: how a population's time or trips from home areas split across places, optionally with a capacity limit per place. Library and command-line tool. | Working, tested. Explained in [WILSON.md](WILSON.md) |
| [`WILSON.md`](WILSON.md) | Full explanation of the Wilson code: inputs, the four model versions, how the capacity-limited version is solved, parameter guidance, checks and validation results. | — |
| [`examples/`](examples/) | Small example inputs for `wilson_allocation.py`: four Baltimore home areas and five restaurants. | — |
| [`huffmodel.py`](huffmodel.py) | **Individual choice model.** Huff model for one agent: `Person` and `POI` classes, probability of choosing each POI from desirability and great-circle distance, and `pick_location` to sample one. | In progress |
| [`build_pois.py`](build_pois.py) | Loads `POI.csv` into `POI` objects for `huffmodel.py` and writes choice probabilities for test agents. | In progress |
| [`poitype_filter_test.py`](poitype_filter_test.py) | Interactive helper: type a keyword and it lists the matching general and specific POI categories in the data files (used to decide which categories count as e.g. bars). | Utility |
| [`POI.csv`](POI.csv) | Baltimore points of interest (see Data). | Data |
| [`POI-Dewey.csv`](POI-Dewey.csv) | Observed visits to places, one week (see Data). | Data |

### How the two models fit together

- **Huff** (`huffmodel.py`) answers *which place one person chooses*: the chance of choosing a place rises with how attractive it is and falls with distance.
- **Wilson** (`wilson_allocation.py`) answers *how a whole population's time is shared out*: given how much time leaves each home area, it gives the expected number of people at every place, and can respect each place's capacity.

Without capacity limits the two agree on average. An agent simulation using the Huff choice rule should reproduce the Wilson occupancy numbers.

## Quick start

Python 3.9 or later. `wilson_allocation.py` needs numpy; the other scripts use only the standard library.

```bash
pip install numpy
python wilson_allocation.py --self-test
python wilson_allocation.py --origins examples/origins.csv --places examples/places.csv --out examples/result --flows
python poitype_filter_test.py POI.csv POI-Dewey.csv
```

## Data

### `POI.csv`: Baltimore points of interest

About 31,000 places in Baltimore from Overture Maps (release 2026-09-23.1), each matched to an Overture building footprint where possible.

| Column | Meaning |
|---|---|
| `poi_id`, `poi_name` | Overture place ID and name |
| `poi_latitude`, `poi_longitude` | location |
| `poi_original_category` | Overture category |
| `poi_specific_category` | team's standardised category |
| `building_id`, `building_area_square_meter` | matched Overture building and its footprint area |
| `poi_building_match_status`, `poi_building_distance_meter` | `matched` (inside a building), `within_5_meters_nearby`, `multiple_buildings` or `no_building`; distance for nearby matches |

Known issues to handle before modelling:
- **Closed places:** about 1,300 rows are places Overture marks as permanently closed.
- **Shared buildings:** when several businesses share a building, each row carries the whole building's footprint. Divide the footprint by the number of places in the building when using it as a size.

### `POI-Dewey.csv`: observed visits

Advan weekly patterns obtained through Dewey for **21–27 July 2025**: about 10,000 places, mostly Baltimore, Maryland. A few hundred rows are other places with "Baltimore" in the name (Michigan, Ohio and others), so filter on `REGION == "MD"`. Use is subject to Dewey's data terms.

The columns used for validation:
- `VISIT_COUNTS`, `VISITOR_COUNTS`: weekly visits and visitors;
- `VISITS_BY_EACH_HOUR`: 168 hourly counts, Monday first;
- `MEDIAN_DWELL`: minutes;
- `VISITOR_HOME_CBGS`: visitors by home census block group;
- `NAICS_CODE`, `TOP_CATEGORY`, `SUB_CATEGORY`: categories;
- `LATITUDE`, `LONGITUDE`: location.

Many rows carry a generic name (the category) instead of a business name. The file contains no places of worship or health facilities.

## Key results so far

These come from the Wilson model, run on this data in the project's place-occupancy pipeline (details in [WILSON.md](WILSON.md)):

- **Distance parameter β = 2 for visits to places.** Observed visitor home areas in `POI-Dewey.csv` fit β ≈ 2 for restaurants, 1.75 for retail and 1.5 for gyms; β = 1 fits much worse. Commuting is different: census work flows fit β ≈ 0.8.
- **Floor area is a real but moderate measure of attractiveness:**
  - It ranks places by observed weekly visits with correlation of about 0.3 for restaurants, 0.4 for retail and 0.5 for gyms.
  - Without it, the ranking is no better than chance.
- **Hourly patterns:** national time-use survey profiles match observed weekday visits well (retail r = 0.95, restaurants 0.79), and weekends less well.
