import json
import huff_model
import csv

#convert legacy Delineo Person class to our Person class
def legacy_person_convert(oldperson):
    times = []
    if (oldperson.age < 18):
        times = [(9,15), (22,6)]
    else:
        times = [(9,17), (22,6)]

    newperson = huff_model.Person(oldperson.id, oldperson.location, times, [])
    return newperson 

#convert legacy Delineo Facility class to our POI class
#can only convert from legacy Facilities, not Households, as Households don't have fixed locations
def legacy_poi_convert(oldpoi):
    newpoi = huff_model.POI(oldpoi.id, oldpoi.latitude, oldpoi.longitude, oldpoi.top_category)
    return newpoi

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
    pois = parse_csv(r"C:\Users\10734\Desktop\POI.csv")

    if len(pois) < 5:
        raise ValueError("At least 5 POIs are required.")

    test_person = huff_model.Person(1, pois[4], [], ['restaurants','bars_breweries','urban_parks'])
    test_people = []
    test_people.append(test_person)
    output_probs(test_people, pois)

    return 1


if __name__ == "__main__":
    main()
