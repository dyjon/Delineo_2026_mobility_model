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

    test_people = [
        huffmodel.Person(1, pois[4], [], ['restaurants', 'bars_breweries', 'urban_parks']),
        huffmodel.Person(2, pois[100], [], ['restaurants', 'bars_breweries', 'urban_parks']),
        huffmodel.Person(3, pois[200], [], ['restaurants', 'bars_breweries', 'urban_parks'])
    ]
    output_probs(test_people, pois)

    return 1

if __name__ == "__main__":
    main()


import pandas as pd

df = pd.read_csv("test_output.csv")

print("Number of unique persons:", df["person_id"].nunique())
print("Number of unique destinations:", df["place_id"].nunique())
print("Missing values:", df.isna().sum().sum())
print("Duplicate person-place pairs:", df.duplicated(["person_id", "place_id"]).sum())
print("Probability sum by person:")
print(df.groupby("person_id")["prob"].sum())


print(df.head())
print("Number of destinations:", len(df))
print("Probability sum:", df["prob"].sum())
print("Minimum probability:", df["prob"].min())
print("Maximum probability:", df["prob"].max())


import numpy as np

print("Total output rows:", len(df))
print("Destinations per person:")
print(df.groupby("person_id")["place_id"].nunique())
print("All probabilities nonnegative:", (df["prob"] >= 0).all())
print("All persons normalized:", np.allclose(df.groupby("person_id")["prob"].sum().to_numpy(), 1.0, atol=1e-8))


pivot = df.pivot(index="place_id", columns="person_id", values="prob").fillna(0)

print("Agent 1 vs Agent 2:")
print(np.abs(pivot[1] - pivot[2]).sum())
print("Agent 1 vs Agent 3:")
print(np.abs(pivot[1] - pivot[3]).sum())
