"""Check the Huff category matching against the 80 standardised categories in POI.csv.

    python test_category_matching.py [POI.csv]

Desires tested:
  category   each of the 80 categories, as written           -> must match only itself
  word       each word used in a category name ('retail')    -> whole-word matches, listed
  osm        common OpenStreetMap / AllThePlaces tag values   -> what a new dataset may ask for
For each desire: the categories matched by huff_model.py (whole word, else closest category) and
by the original matching (deprecated/huff_model_levenshtein.py). Writes
category_matching_report.csv; prints the cases to review.
"""
import csv
import importlib.util
import sys
import warnings
from pathlib import Path

import huff_model as new

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('huff_old', HERE / 'deprecated' / 'huff_model_levenshtein.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

OSM = ['restaurant', 'fast_food', 'cafe', 'bar', 'pub', 'nightclub', 'pharmacy', 'bank', 'atm', 'school',
       'kindergarten', 'college', 'university', 'hospital', 'clinic', 'doctors', 'dentist', 'place_of_worship',
       'fuel', 'parking', 'library', 'cinema', 'theatre', 'supermarket', 'convenience', 'clothes', 'fitness_centre',
       'gym', 'post_office', 'police', 'fire_station', 'townhall', 'marketplace', 'hotel', 'park', 'playground']


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else HERE / 'POI.csv'
    with open(path, encoding='utf-8-sig', newline='') as f:
        cats = sorted({r['poi_specific_category'] for r in csv.DictReader(f)})
    pois_new = [new.POI(k, 0.0, 0.0, c) for k, c in enumerate(cats)]
    pois_old = [old.POI(k, 0.0, 0.0, c) for k, c in enumerate(cats)]
    types = set(cats)
    home_new, home_old = new.POI(-1, 0.0, 0.0, 'home'), old.POI(-1, 0.0, 0.0, 'home')
    words = sorted({w for c in cats for w in c.split('_')})

    def match_new(d):
        person = new.Person(0, home_new, [], [d])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            hits = [p.loc_type for p in pois_new if new.desirability(person, p, pois_new, types) > 0]
        via = 'none' if not hits else 'word' if any(new.wants(d, t) for t in types) else 'fallback'
        return hits, via

    def match_old(d):
        person = old.Person(0, home_old, [], [d])
        pre = (old.pft.get_all_types(pois_old), None)
        if not any(x in pre[0] for x in person.desires):
            pre = (pre[0], old.pft.get_type_groups(pre[0]))
        return [p.loc_type for p in pois_old if old.desirability(person, p, pois_old, pre) > 0]

    rows = []
    for kind, desires in (('category', cats), ('word', words), ('osm', OSM)):
        for d in desires:
            hits, via = match_new(d)
            was = match_old(d)
            rows.append(dict(desire=d, kind=kind, matched_by=via, new_count=len(hits), new_matches='; '.join(hits),
                             original_count=len(was), original_matches='; '.join(was)))

    # every category, asked for by name, matches itself and nothing else
    for r in rows:
        if r['kind'] == 'category':
            assert r['new_matches'] == r['desire'], r
    by = {r['desire']: r['new_matches'] for r in rows}
    assert by['park'] == 'urban_parks' and by['parking'] == 'parking_facilities'      # whole words
    assert by['services'] == '' and by['other'] == ''                                 # generic words alone
    with open(HERE / 'category_matching_report.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f'{len(cats)} categories: each matches only itself (new); original: '
          f"{sum(r['original_matches'] == r['desire'] for r in rows if r['kind'] == 'category')} of {len(cats)} do")
    for kind in ('word', 'osm'):
        print(f'\n{kind} desires (desire -> new matches  |  original count):')
        for r in rows:
            if r['kind'] == kind:
                print(f"  {r['desire']:<18} {r['matched_by']:<8} {r['new_matches'][:90]:<90} | {r['original_count']}")


if __name__ == '__main__':
    main()
