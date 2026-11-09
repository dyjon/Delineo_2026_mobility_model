import huff_model
import wilson_allocation
import csv

def parse_csv(path: str):
    pois = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        data = csv.DictReader(f)
        i = 1

        for row in data: 
            pois.append(huff_model.POI(i, float(row['poi_latitude']), float(row['poi_longitude']), row['poi_specific_category']))
            i += 1

    return pois


def huff_probs(people: list[huff_model.Person], pois: list[huff_model.POI]):

    #initialize a 2D array of probabilities: each row is a person, each column is a POI
    prob_matrix = [[0 for a in range(len(pois))] for b in range(len(people))]

    #instantiate the 2D array with all the person/POI probability combinations
    rownum = 0
    for person in people:
        places = [poi for poi in pois if poi.id != person.cur_loc.id and poi.loc_type in person.desires]

        if not places:
            raise ValueError("No eligible destinations for this person.")

        cdf = huff_model.probability(person, places)

        for i in range(len(cdf)):
            if i > 0:
                prob_matrix[rownum][i] = (cdf[i] - cdf[i-1])
            else:
                prob_matrix[rownum][i] = (cdf[i])

        rownum += 1

    return prob_matrix


#add more complex test cases later
def main():
    pois = parse_csv(r"C:\Users\10734\Desktop\POI.csv")

    if len(pois) < 5:
        raise ValueError("At least 5 POIs are required.")

    #get the grid of probabilities
    test_person = huff_model.Person(1, pois[4], [], ['restaurants','bars_breweries','urban_parks'])
    test_people = []
    test_people.append(test_person)
    prob_matrix = huff_probs(test_people, pois)

    #get the Wilson model's output using the grid of probabilities and an arbitrary capacity (ask how to select this)
    wilson_output = wilson_allocation.capped_production(len(test_people), prob_matrix, 100)

    #ask for clarification on how to output the Wilson model's results for testing
    person_count = 0
    for i in wilson_output:
        loc = huff_model.pick_location(i, pois)
        print(f"person {person_count} selects location {loc}")
        person_count += 1

    return 1


if __name__ == "__main__":
    main()