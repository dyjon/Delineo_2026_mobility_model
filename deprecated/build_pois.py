import huffmodel
import csv
import sys

def parse_csv(path: str):
    pois = []
    with open(path, "r") as f:
        data = csv.DictReader(f)
        i = 1
        for row in data: 
            pois.append(huffmodel.POI(i,row['poi_latitude'],row['poi_longitude'],row['poi_specific_category']) )
            i += 1
    return pois

def output_probs(people: list[huffmodel.Person], pois: list[huffmodel.POI]):

    for person in people:
        probabilities = huffmodel.probability(person, pois)

        rows = []
        for i in probabilities:
            rows.append = [person.id, pois[i].id, probabilities[i]]

        with open('test_output.csv', 'w') as g:
            fnames = ['person_id,place_id,prob']
            writer = csv.dictWriter(g, fieldnames=fnames)
            writer.writeheader()
            writer.writerows(rows)

    return 1

def main():
    if len(sys.argv) > 1:
        pois = parse_csv(sys.argv[1])
        test_person = huffmodel.Person(1,pois[4],[],['restaurants','bars_breweries','urban_parks'])
        test_people = []
        test_people.append(test_person)
    else:
        print("Insufficient command line arguments\n")
    return 1

if __name__ == "__main__":
    main()