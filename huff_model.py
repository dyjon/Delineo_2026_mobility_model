#graph implementation of agent tracking
#infectivity represented by number of children in the graph

import math
import random
import poitype_filter_test as pft

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

#de facto pseudocode asince I have not integrated data

def desirability(subject: Person, location: POI, pois):
    all_types = pft.get_all_types(pois)
    type_groups = pft.get_type_groups(all_types)

    valid_groups = []
    for des in subject.desires:
        valid_groups.append(pft.get_best_group(des, all_types, type_groups))

    loc_num = all_types.index(location.loc_type)
    if type_groups[loc_num] not in valid_groups:
        return 0

    #return location's average similarity to all desires
    destotal = 0
    for des in subject.desires:
        destotal += pft.Levenshtein.ratio(des, location.loc_type)

    return (destotal / len(subject.desires))

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
