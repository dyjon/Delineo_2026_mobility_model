#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().system('pip install overturemaps')


# In[3]:


get_ipython().system('pip install overturemaps')


# In[6]:


get_ipython().system('overturemaps download --bbox=-76.65,39.30,-76.59,39.36 -f geojson --type=place -o baltimore_places.geojson')


# In[7]:


import json
import csv

with open("baltimore_places.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("baltimore_places.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["poi_id", "name", "latitude", "longitude", "category"])

    for feature in data["features"]:
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}

        if geometry.get("type") != "Point":
            continue

        lon, lat = geometry["coordinates"][:2]
        name = (props.get("names") or {}).get("primary", "")
        category = props.get("basic_category") or (props.get("taxonomy") or {}).get("primary", "")
        writer.writerow([props.get("id", feature.get("id", "")), name, lat, lon, category])

print("CSV file created successfully.")


# In[8]:


import os
print(os.path.abspath("baltimore_places.csv"))


# In[9]:


get_ipython().system('pip install geopandas pyogrio overturemaps')


# In[11]:


get_ipython().system('pip install --upgrade fiona')


# In[1]:


get_ipython().run_line_magic('pip', 'install pyshp shapely')


# In[1]:


import zipfile
import shapefile
import io
from shapely.geometry import shape, Point

with zipfile.ZipFile("us_counties.zip") as z:
    shp_file = next(name for name in z.namelist() if name.endswith(".shp"))
    base = shp_file[:-4]

    reader = shapefile.Reader(
        shp=io.BytesIO(z.read(base + ".shp")),
        shx=io.BytesIO(z.read(base + ".shx")),
        dbf=io.BytesIO(z.read(base + ".dbf"))
    )

    baltimore_polygon = None

    for record in reader.iterShapeRecords():
        if record.record.as_dict()["GEOID"] == "24510":
            baltimore_polygon = shape(record.shape.__geo_interface__)
            break

if baltimore_polygon is None:
    raise ValueError("Baltimore City not found")

print("Baltimore City boundary loaded!")


# In[2]:


west, south, east, north = baltimore_polygon.bounds
bbox = f"{west},{south},{east},{north}"

print(bbox)


# In[3]:


get_ipython().system('overturemaps download --bbox="{bbox}" -f geojson --type=place -o baltimore_full_bbox.geojson')


# In[4]:


import json
import pandas as pd
from shapely.geometry import Point

with open("baltimore_full_bbox.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

records = []

for feature in data["features"]:
    geometry = feature.get("geometry") or {}
    props = feature.get("properties") or {}

    if geometry.get("type") != "Point":
        continue

    lon, lat = geometry["coordinates"][:2]

    if not baltimore_polygon.covers(Point(lon, lat)):
        continue

    name = (props.get("names") or {}).get("primary", "")
    category = (props.get("basic_category") or (props.get("taxonomy") or {}).get("primary", ""))

    records.append({
        "poi_id": props.get("id", feature.get("id")),
        "name": name,
        "latitude": lat,
        "longitude": lon,
        "category": category
    })

df = pd.DataFrame(records)
df.to_csv("baltimore_city_places.csv", index=False)

print("Number of POIs:", len(df))
print("CSV saved successfully!")


# In[5]:


get_ipython().system('overturemaps releases check -o baltimore_full_bbox.geojson')


# In[4]:


get_ipython().system('overturemaps download --bbox=-76.711519,39.197207,-76.529453,39.372205 -f geojson --type=building -o baltimore_buildings.geojson')


# In[5]:


get_ipython().system('overturemaps releases check -o baltimore_buildings.geojson')


# In[9]:


import json
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely import transform
from pyproj import Transformer

# Load classified POIs
df = pd.read_csv("C:/Users/10734/Desktop/Baltimore_POI_31176_without_unclassified.csv", dtype={"poi_id": str})

# Load building footprints
with open("baltimore_buildings.geojson", encoding="utf-8") as f:
    data = json.load(f)

buildings = []
building_ids = []

for feature in data["features"]:
    geom = feature.get("geometry")

    if geom and geom["type"] in ("Polygon", "MultiPolygon"):
        buildings.append(shape(geom))
        building_ids.append(feature.get("properties", {}).get("id", feature.get("id")))

# Build spatial index
tree = STRtree(buildings)

# Project to meters (UTM Zone 18N)
project = Transformer.from_crs("EPSG:4326", "EPSG:26918", always_xy=True)

# Precompute building footprint areas
areas = [transform(building, project.transform, interleaved=False).area for building in buildings]

# Match POIs to buildings
poi_areas = []
match_status = []
matched_building_ids = []

for row in df.itertuples(index=False):
    point = Point(row.longitude, row.latitude)
    matches = tree.query(point, predicate="intersects")

    if len(matches) == 1:
        poi_areas.append(round(areas[int(matches[0])], 2))
        match_status.append("matched")
        matched_building_ids.append(building_ids[int(matches[0])])

    elif len(matches) == 0:
        poi_areas.append(float("nan"))
        match_status.append("no_building")
        matched_building_ids.append(None)

    else:
        poi_areas.append(float("nan"))
        match_status.append("multiple_buildings_review")
        matched_building_ids.append(None)

# Add new columns
df["building_footprint_m2"] = poi_areas
df["area_match_status"] = match_status
df["building_id"] = matched_building_ids
matched = df["building_footprint_m2"].notna().sum()

# Export simplified model input
columns = ["poi_id", "latitude", "longitude", "model_category", "building_footprint_m2", "area_match_status", "building_id"]
df[columns].to_csv("C:/Users/10734/Desktop/Baltimore_POI_31176_with_building_area.csv", index=False)

print("Matched POIs:", matched)
print("Matching rate:", round(matched / len(df) * 100, 2), "%")
print(df["area_match_status"].value_counts())
print("Total POIs:", len(df))
print("CSV saved successfully!")

assert len(df) == 31176
assert df["poi_id"].is_unique
assert len(poi_areas) == len(df)
assert len(matched_building_ids) == len(df)

print("Data validation passed!")


# In[15]:


unmatched = df[df["area_match_status"] == "no_building"]
print(unmatched["model_category"].value_counts().to_string())


# In[16]:


summary = df.groupby("model_category").agg(
    total_pois=("poi_id", "size"),
    unmatched_pois=("area_match_status", lambda x: (x == "no_building").sum())
)

summary["unmatched_rate_pct"] = summary["unmatched_pois"] / summary["total_pois"] * 100

print(summary.sort_values("unmatched_pois", ascending=False).to_string())


# In[17]:


# Project buildings to meters
buildings_m = [transform(building, project.transform, interleaved=False) for building in buildings]
tree_m = STRtree(buildings_m)
candidate_count = 0

for row in df[df["area_match_status"] == "no_building"].itertuples(index=False):
    point = Point(row.longitude, row.latitude)
    point_m = transform(point, project.transform, interleaved=False)
    candidates = tree_m.query(point_m.buffer(10))

    if any(buildings_m[int(i)].distance(point_m) <= 10 for i in candidates):
        candidate_count += 1

print("Previously unmatched POIs:", 8825)
print("POIs with a building within 10 m:", candidate_count)


# In[21]:


records = []

for row in df[df["area_match_status"] == "no_building"].itertuples(index=False):
    point = Point(row.longitude, row.latitude)
    point_m = transform(point, project.transform, interleaved=False)
    candidates = tree_m.query(point_m.buffer(10))
    nearby = []

    for i in candidates:
        i = int(i)
        distance = buildings_m[i].distance(point_m)

        if distance <= 10:
            nearby.append((distance, i))

    if not nearby:
        continue

    nearby.sort()
    distance, i = nearby[0]

    records.append({
        "poi_id": row.poi_id,
        "model_category": row.model_category,
        "building_id": building_ids[i],
        "building_footprint_m2": round(areas[i], 2),
        "distance_m": round(distance, 2),
        "candidate_count_10m": len(nearby)
    })

candidate_df = pd.DataFrame(records)
candidate_df.to_csv("C:/Users/10734/Desktop/Baltimore_POI_nearby_building_candidates.csv", index=False)

print("Candidate matches:", len(candidate_df))
print(candidate_df["candidate_count_10m"].value_counts().to_string())
print("CSV saved successfully!")


# In[23]:


single_candidates = candidate_df[candidate_df["candidate_count_10m"] == 1].copy()
print("Single-candidate POIs:", len(single_candidates))

# Distribution of POI categories
print(single_candidates["model_category"].value_counts())

# Distribution of distances to buildings
print(single_candidates["distance_m"].describe())

# Distance intervals
single_candidates["distance_group"] = pd.cut(single_candidates["distance_m"], bins=[-0.001, 2, 5, 10], labels=["0-2 m", "2-5 m", "5-10 m"])

print(single_candidates["distance_group"].value_counts().sort_index())


# In[24]:


# Indoor POI categories for preliminary testing
indoor_categories = [
    "restaurants",
    "worship_venues",
    "beauty_wellness_services",
    "specialty_outpatient_clinics",
    "specialty_retail",
    "grocery_food_retail",
    "apparel_personal_retail",
    "home_electronics_retail",
    "banks_branches",
    "primary_secondary_school"
]

# Filter nearby building candidates
selected = candidate_df[
    (candidate_df["candidate_count_10m"] == 1) &
    (candidate_df["distance_m"] <= 5) &
    (candidate_df["model_category"].isin(indoor_categories))
].copy()

print("Selected candidate POIs:", len(selected))
print(selected["model_category"].value_counts().to_string())
print(selected["distance_m"].describe())


# In[29]:


# Create an updated copy
df_updated = df.copy()

# Look up selected nearby matches
assert selected["poi_id"].is_unique
assert df_updated["poi_id"].is_unique

lookup = selected.set_index("poi_id")
mask = (df_updated["area_match_status"] == "no_building") & (df_updated["poi_id"].isin(lookup.index))

assert mask.sum() == len(selected)

ids = df_updated.loc[mask, "poi_id"]

# Add matching information
df_updated["building_distance_m"] = float("nan")
df_updated.loc[mask, "building_footprint_m2"] = ids.map(lookup["building_footprint_m2"]).to_numpy()
df_updated.loc[mask, "building_id"] = ids.map(lookup["building_id"]).to_numpy()
df_updated.loc[mask, "building_distance_m"] = ids.map(lookup["distance_m"]).to_numpy()
df_updated.loc[mask, "area_match_status"] = "nearby_5m_provisional"

# Export updated dataset
columns = ["poi_id", "latitude", "longitude", "model_category", "building_footprint_m2", "area_match_status", "building_id", "building_distance_m"]
df_updated[columns].to_csv("C:/Users/10734/Desktop/Baltimore_POI_31176_with_area_v2.csv", index=False)

print(df_updated["area_match_status"].value_counts())
print("Total POIs:", len(df_updated))
print("POIs with area:", df_updated["building_footprint_m2"].notna().sum())
print("CSV saved successfully!")


# In[30]:


remaining = candidate_df[
    (candidate_df["candidate_count_10m"] == 1) &
    (candidate_df["distance_m"] <= 5) &
    (~candidate_df["poi_id"].isin(selected["poi_id"]))
]

print("Remaining candidates:", len(remaining))
print(remaining["model_category"].value_counts().to_string())


# In[ ]:


additional_categories = [
    "mental_health_clinics",
    "bars_breweries",
    "convenience_retail",
    "cafes_beverages",
    "quick_service_food",
    "diagnostics_laboratories",
    "dental_care",
    "physical_alternative_therapy",
    "gyms_fitness_studios",
    "hotels_other_lodging",
    "libraries"
]

additional = remaining[remaining["model_category"].isin(additional_categories)].copy()

print("Additional candidate POIs:", len(additional))
print(additional["model_category"].value_counts())

# Add names and coordinates for review
review = additional.merge(df[["poi_id", "name", "latitude", "longitude"]], on="poi_id", how="left")
review.to_csv("C:/Users/10734/Desktop/Baltimore_POI_additional_candidates.csv", index=False)

print("Candidate file saved successfully!")


# In[31]:


additional_categories = [
    "mental_health_clinics",
    "bars_breweries",
    "convenience_retail",
    "cafes_beverages",
    "quick_service_food",
    "diagnostics_laboratories",
    "dental_care",
    "physical_alternative_therapy",
    "gyms_fitness_studios",
    "hotels_other_lodging",
    "libraries"
]

additional = remaining[remaining["model_category"].isin(additional_categories)].copy()

print("Additional candidate POIs:", len(additional))
print(additional["model_category"].value_counts())

# Add names and coordinates for review
review = additional.merge(df[["poi_id", "name", "latitude", "longitude"]], on="poi_id", how="left")
review.to_csv("C:/Users/10734/Desktop/Baltimore_POI_additional_candidates.csv",index=False)
print("Candidate file saved successfully!")

