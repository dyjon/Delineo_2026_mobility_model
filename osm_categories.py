"""OpenStreetMap / AllThePlaces tags -> the team's 80 POI categories (osm_category_map.csv).

    import osm_categories
    cat = osm_categories.category_for(feature['properties'])   # e.g. 'convenience_retail', or None

Tags are checked in KEYS order, so a petrol station tagged amenity=fuel and shop=convenience
becomes fuel_ev_charging. A value missing from the table uses the key's '*' row if there is
one (any shop -> specialty_retail). Multi-valued tags ('convenience;alcohol') use the first value.

    python osm_categories.py [file.geojson ...]     # self-test, or report on GeoJSON files
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ('amenity', 'shop', 'healthcare', 'leisure', 'tourism', 'office', 'craft', 'education', 'emergency',
        'historic', 'cemetery', 'public_transport', 'railway', 'aeroway', 'club', 'dark_store', 'man_made',
        'natural', 'landuse', 'power', 'telecom', 'waterway', 'mooring')
_table = None


def table(path=HERE / 'osm_category_map.csv'):
    global _table
    if _table is None:
        with open(path, encoding='utf-8', newline='') as f:
            _table = {(r['osm_key'], r['osm_value']): r['poi_specific_category'] for r in csv.DictReader(f)}
    return _table


def category_for(properties):
    """Team category for a feature's tags, or None if no known key is present."""
    t = table()
    for key in KEYS:
        value = properties.get(key)
        if value:
            value = str(value).split(';')[0].strip()
            return t.get((key, value)) or t.get((key, '*'))
    return None


def _self_test():
    with open(HERE / 'POI.csv', encoding='utf-8-sig', newline='') as f:
        cats = {r['poi_specific_category'] for r in csv.DictReader(f)}
    bad = sorted({c for c in table().values() if c not in cats})
    assert not bad, f'not one of the POI.csv categories: {bad}'
    assert {k for k, _ in table()} <= set(KEYS)
    assert category_for({'amenity': 'restaurant'}) == 'restaurants'
    assert category_for({'amenity': 'fuel', 'shop': 'convenience'}) == 'fuel_ev_charging'
    assert category_for({'shop': 'convenience;alcohol'}) == 'convenience_retail'
    assert category_for({'shop': 'something_new'}) == 'specialty_retail'
    assert category_for({'name': 'no tags'}) is None
    print(f'osm_categories self-test passed ({len(table())} tag rows, {len(set(table().values()))} of {len(cats)} categories used)')


def report(paths):
    for p in paths:
        with open(p, encoding='utf-8-sig') as f:
            feats = json.load(f)['features']
        got = Counter(category_for(ft['properties']) for ft in feats)
        print(f'{Path(p).name}: {len(feats)} features ->', dict(got.most_common()))


if __name__ == '__main__':
    _self_test()
    if len(sys.argv) > 1:
        report(sys.argv[1:])
