import huffmodel
import csv


def parse_csv(path: str):
    pois = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        data = csv.DictReader(f)
        i = 1

        for row in data: 
            pois.append(huffmodel.POI(i, float(row['poi_latitude']), float(row['poi_longitude']), row['poi_specific_category']))
            i += 1

    return pois


def output_probs(people: list[huffmodel.Person], pois: list[huffmodel.POI]):
    rows = []

    for person in people:
        places = [poi for poi in pois if poi.id != person.cur_loc.id and poi.loc_type in person.desires]

        if not places:
            raise ValueError("No eligible destinations for this person.")

        cdf = huffmodel.probability(person, places)
        probabilities = []

        for i in range(len(cdf)):
            if i > 0:
                probabilities.append(cdf[i] - cdf[i-1])
            else:
                probabilities.append(cdf[i])

        for i in range(len(probabilities)):
            rows.append([person.id, places[i].id, probabilities[i]])

    with open('test_output.csv', 'w', newline="", encoding="utf-8") as g:
        fnames = ['person_id', 'place_id', 'prob']
        writer = csv.writer(g)
        writer.writerow(fnames)
        writer.writerows(rows)

    return 1


def main():
    pois = parse_csv(r"C:\Users\10734\Desktop\POI.csv")

    if len(pois) < 5:
        raise ValueError("At least 5 POIs are required.")

    test_person = huffmodel.Person(1, pois[4], [], ['restaurants','bars_breweries','urban_parks'])
    test_people = []
    test_people.append(test_person)
    output_probs(test_people, pois)

    return 1


if __name__ == "__main__":
    main()
