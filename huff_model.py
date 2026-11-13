#graph implementation of agent tracking
#infectivity represented by number of children in the graph

import math
import random

#global variables gamma, lambda for Huff calculation

gma = 0.5
lmb = 0.5

#definitions of classes

class POI:
    def __init__(self, id: int, lat: float, long: float, loc_type: str):
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

def wants(desire: str, loc_type: str):
    """True if a desire names this POI type: the exact category (e.g. 'restaurants'), or words
    that all appear in it ('retail' -> 'grocery_food_retail', 'parks' -> 'urban_parks').
    Whole words only, so 'park' does not pick up 'parking_facilities'."""
    d, t = desire.lower().replace(' ', '_'), loc_type.lower()
    return d == t or set(d.split('_')) <= set(t.split('_'))


def desirability(subject: Person, location: POI, pois=None):
    """1 if the location's type is one the person wants, else 0.

    POI.csv categories are already standardised, so matching is on the category name, not on
    string similarity between names (that grouped e.g. ATMs, museums and farms with
    restaurants). `pois` is unused; kept so existing calls still work."""
    return 1.0 if any(wants(d, location.loc_type) for d in subject.desires) else 0.0


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

    for i in range(len(locations)):
        desirabilities.append(desirability(subject, locations[i], locations))
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
    assert pick('parks') == ['urban_parks'] and pick('park') == []
    assert pick('restaurants', 'bars_breweries') == ['restaurants', 'bars_breweries']
    assert pick('food') == ['grocery_food_retail', 'quick_service_food']
    print('huff_model self-test passed')
