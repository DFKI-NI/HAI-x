import json
from utils import variables as var
from os import listdir
from os.path import isfile, join
import pandas as pd
import plotly.express as px
from utils.database import database as db

def format_image_names(img_files, id):
    # rename the uploaded image if there is already an image with that name
    existing_files = [f for f in listdir(var.IMG_PATH) if isfile(join(var.IMG_PATH, f))]
    for f in img_files:
        if f.filename in existing_files:
            f.filename = str(id) + '_' + f.filename
    new_files = [file.filename for file in img_files]
    return ';'.join(new_files)

def add_path_to_db(line, date):
    id_data = db.get_max_id(var.SCHEMA, var.PATH) + 1

    point = 0
    point_data = str(id_data) + "-" + str(point)
    for points in line:
        values = {
            'path_id': id_data,
            'idx': point_data,
            'lat': float(points[0]),
            'lon': float(points[1]),
            'date': date
        }
        db.add_row(var.SCHEMA, var.PATH, values)
        point = point + 1
        point_data = str(id_data) + "-" + str(point)

def create_base_map(date):
    haix = db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS)
    df = haix[haix['date'] == date]

    db.convert_to_geojson_file(var.SCHEMA, var.GEO, var.GEO_FILE)
    with open(var.GEO_FILE, 'r') as file:
        geojson = json.load(file)

    fig = px.choropleth_mapbox(
            df, geojson=geojson, color="type",
            locations="idx",
            center={"lat": 52.35256085248966, "lon": 9.745146485688414},
            zoom=13,
            mapbox_style="carto-positron",
            opacity=0.2,
            color_discrete_map={
                var.AVOID: "red",
                var.INTEREST: "green",
                var.neutral: "grey"},
            range_color=[0, 6500])
    
    return fig

def contains_keys(possible_keys, object):
    return [key for key in possible_keys if key in object.keys()]