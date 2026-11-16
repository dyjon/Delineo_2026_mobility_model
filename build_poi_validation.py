import huff_model
import csv
import json

def parse_csv(path: str):
    pois = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        data = csv.DictReader(f)
        i = 1

        for row in data: 
            pois.append(huff_model.POI(i, float(row['poi_latitude']), float(row['poi_longitude']), row['poi_specific_category']))
            i += 1

    return pois

def parse_geojson(path: str):
    pois = []
    top_level_tags = ["aeroway","amenity","barrier","cemetery","club","craft","dark_store","education","emergency","healthcare","highway","historic","landuse","leisure","man_made","mooring","natural","office","power","public_transport","railway","shop","telecom","tourism","traffic_calming","tunnel","waterway"]

    with open(path,"r",encoding="utf-8-sig",newline="") as f:
        data = json.load(f)
        for row in data["features"]:
            loctype = ''
            for tag in top_level_tags:
                if(tag in row["properties"].keys()):
                    loctype += row["properties"][tag] + ' '
            
            pois.append(huff_model.POI(row["id"], row["geometry"]["coordinates"][1], row["geometry"]["coordinates"][0], loctype))

    return pois

def output_probs(people: list[huff_model.Person], pois: list[huff_model.POI]):
    rows = []

    for person in people:
        places = [poi for poi in pois if poi.id != person.cur_loc.id and poi.loc_type in person.desires]

        if not places:
            raise ValueError("No eligible destinations for this person.")

        cdf = huff_model.probability(person, places)
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
    pois = parse_csv("POI.csv")

    if len(pois) < 201:
        raise ValueError("At least 201 POIs are required.")

    test_people = [
        huff_model.Person(1, pois[4], [], ['restaurants', 'bars_breweries', 'urban_parks']),
        huff_model.Person(2, pois[100], [], ['restaurants', 'bars_breweries', 'urban_parks']),
        huff_model.Person(3, pois[200], [], ['restaurants', 'bars_breweries', 'urban_parks'])
    ]
    output_probs(test_people, pois)

    return 1

if __name__ == "__main__":
    main()
