#graph implementation of agent tracking
#infectivity represented by number of children in the graph

import difflib
import math
import random
import re
import warnings

#global variables gamma, lambda for Huff calculation

gma = 0.5
lmb = 1.75   # distance exponent, fitted to observed visitor homes in POI-Dewey.csv (same as combined_model.BETA)

#definitions of classes

class POI:
    def __init__(self, id, lat: float, long: float, loc_type: str):
        self.id = id
        self.lat = lat
        self.long = long
        self.loc_type = loc_type

class Person:
    def __init__(self, id: int, start: POI, unavailable: list[tuple[float]], desires: list[str]):
        self.id = id
        self.cur_loc = start
        self.unavail_times = unavailable
        #arranged by most desired location type first
        self.desires = desires

GENERIC = {'other', 'unspecified', 'service', 'venue', 'facility',      # words that never match on their own
           'home', 'primary', 'personal', 'specialty', 'public', 'care'}


def _stem(word: str):
    """Singular form, so 'cafe' meets 'cafes' and 'library' meets 'libraries'."""
    if word.endswith('ies'):
        return word[:-3] + 'y'
    if word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def wants(desire: str, loc_type: str):
    """True if a desire names this POI type: the exact category (e.g. 'restaurants'), or words
    that all appear in it, singular or plural ('retail' -> 'grocery_food_retail', 'park' ->
    'urban_parks', 'cafe' -> 'cafes_beverages'). Whole words only, so 'park' does not pick up
    'parking_facilities'. Generic words alone ('services', 'other') match nothing."""
    d, t = desire.lower().replace(' ', '_'), loc_type.lower()
    if d == t:
        return True
    words = _words(d)
    return bool(words - GENERIC) and words <= _words(t)


def _words(name: str):
    """Singular words of a category name, split on anything but letters and digits, so
    'urban_parks' and Advan's 'Restaurants and Other Eating Places' both work."""
    return {_stem(w) for w in re.split(r'[^a-z0-9]+', name.lower()) if w and w not in ('and', 'of', 'the')}


FALLBACK_CUTOFF = 0.8   # minimum name similarity (0-1) for the closest-category fallback
_fallback = {}          # (desire, categories in the data) -> closest category or None


def closest_type(desire: str, types):
    """Fallback for a desire that names no category in the data: the single most similar
    category name, if it is at least FALLBACK_CUTOFF similar ('restaurant' -> 'restaurants').
    Warns once per desire, so mismatches are visible rather than silent."""
    key = (desire, tuple(sorted(types)))
    if key not in _fallback:
        d = desire.lower().replace(' ', '_')
        hit = difflib.get_close_matches(d, [t.lower() for t in key[1]], n=1, cutoff=FALLBACK_CUTOFF)
        _fallback[key] = next((t for t in key[1] if t.lower() == hit[0]), None) if hit else None
        warnings.warn(f"desire '{desire}' matches no category; "
                      + (f"using closest '{_fallback[key]}'" if _fallback[key] else 'nothing close enough, ignored'))
    return _fallback[key]


def desirability(subject: Person, location: POI, pois=None, types=None):
    """1 if the location's type is one the person wants, else 0.

    A desire matches a category if it names it exactly or all its words appear in it (see
    wants). A desire that matches no category in `pois` falls back to the single closest
    category name (closest_type), with a warning. Each desire is handled on its own, so one
    matching desire never hides another. `types` (the set of categories in `pois`) can be
    passed in to avoid rebuilding it on every call."""
    if types is None:
        types = {p.loc_type for p in pois} if pois else {location.loc_type}
    for d in subject.desires:
        if any(wants(d, t) for t in types):
            if wants(d, location.loc_type):
                return 1.0
        elif len(types) > 1 and closest_type(d, types) == location.loc_type:
            return 1.0
    return 0.0


def distance(subject: Person, location: POI):
    if subject.cur_loc == location:
        return 0

    lat_1 = math.radians(subject.cur_loc.lat)
    lon_1 = math.radians(subject.cur_loc.long)
    lat_2 = math.radians(location.lat)
    lon_2 = math.radians(location.long)

    a = math.sin((lat_2 - lat_1) / 2)**2 + math.cos(lat_1) * math.cos(lat_2) * math.sin((lon_2 - lon_1) / 2)**2

    return 2 * 6371 * math.asin(math.sqrt(min(1.0, max(0.0, a))))

def probability(subject: Person, locations: list[POI]):
    desirabilities = []
    distances = []
    types = {p.loc_type for p in locations}

    for i in range(len(locations)):
        desirabilities.append(desirability(subject, locations[i], locations, types))
        distances.append(max(distance(subject, locations[i]), 1e-10))

    sum_weight = 0.0

    for j in range(len(locations)):
        sum_weight += math.pow(desirabilities[j], gma) / math.pow(distances[j], lmb)

    if sum_weight <= 0:
        raise ValueError("No attractive destinations are available.")

    #we create a "list of maximums" eg 0.1, 0.2, 0.4, 0.8, 1 to linearly look through in pick_location
    probabilities = []
    for k in range(len(locations)):
        if k == 0:
            probabilities.append((math.pow(desirabilities[k], gma) / math.pow(distances[k], lmb)) / sum_weight)
        else:
            probabilities.append((math.pow(desirabilities[k], gma) / math.pow(distances[k], lmb)) / sum_weight + probabilities[k-1])

    return probabilities

def pick_location(probabilities: list[float], locations: list[POI]):
    #so we can linearly look through all probabilities like this
    rng = random.random()
    for l in range(len(probabilities)):
        if rng < probabilities[l]:
            return locations[l]

    return locations[-1]


if __name__ == "__main__":
    types = ['restaurants', 'atms', 'museums_art_culture', 'grocery_food_retail', 'urban_parks',
             'parking_facilities', 'bars_breweries', 'quick_service_food']
    home = POI(0, 39.29, -76.61, 'apartment_residential')
    pick = lambda *ds: [t for t in types if desirability(Person(1, home, [], list(ds)), POI(1, 0, 0, t)) > 0]
    assert pick('restaurants') == ['restaurants']
    assert pick('retail') == ['grocery_food_retail']
    assert pick('parks') == ['urban_parks'] and pick('park') == ['urban_parks']   # not parking_facilities
    assert pick('restaurants', 'bars_breweries') == ['restaurants', 'bars_breweries']
    assert pick('food') == ['grocery_food_retail', 'quick_service_food']
    pois = [POI(k, 0, 0, t) for k, t in enumerate(types)]
    pick2 = lambda *ds: [t for t in types if desirability(Person(1, home, [], list(ds)), POI(1, 0, 0, t), pois) > 0]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        assert pick2('restaurant') == ['restaurants']                       # singular
        assert pick2('services') == [] and pick2('other') == []             # generic words alone
        assert pick2('restaurants', 'bars') == ['restaurants', 'bars_breweries']   # one match does not hide the other
        assert pick2('cinema') == []                                         # nothing close: ignored
        assert pick2('restaurants') == ['restaurants']
    assert wants('restaurants', 'Restaurants and Other Eating Places')   # Advan / legacy Delineo names
    assert wants('grocery', 'Grocery Stores') and not wants('restaurants', 'Drinking Places (Alcoholic Beverages)')
    print('huff_model self-test passed')
