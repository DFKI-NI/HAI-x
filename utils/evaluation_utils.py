import plotly.graph_objects as go
import numpy as np
import pandas as pd
import plotly.express as px
import logging
from utils.database import database as db
import utils.variables as var

def data_read(service_data):
    resultarray = service_data["resultarray"]

    rsltarr =  []
    for x in range(len(resultarray)):
        for y in range(len(resultarray[x])):
            ele = resultarray[x][y]
            if ele["in_sea"] == True:
                if ele["mowes_ammount"] != 0:
                    rsltarr.append([ele["corner_1"][0], ele["corner_1"][1], ele["corner_2"][0], ele["corner_2"][1], ele["mowes_ammount"]])

    rltDF = pd.DataFrame(rsltarr, columns=["lat1", "lon1", "lat2", "lon2", "weeding"])

    return pd.DataFrame(rltDF)

def db_to_geojson(arr):
    geojson = {"type": "FeatureCollection", "features": []}

    for row in arr.itertuples():
        p1 = [float(row.lon1), float(row.lat1)]
        p2 = [float(row.lon2), float(row.lat1)]
        p3 = [float(row.lon2), float(row.lat2)]
        p4 = [float(row.lon1), float(row.lat2)]

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[p1, p2, p3, p4, p1]]  # Polygon-Koordinaten
            },
            "id": row.id,  # Wichtig: Die ID verbindet GeoJSON mit dem DataFrame
            "properties": {
                "weeding": float(row.weeding)  # Der Wert
            }
        }
        geojson["features"].append(feature)

    return geojson

def df_to_geojson(arr):
    geojson = {"type": "FeatureCollection", "features": []}

    for row in arr.itertuples():
        p1 = [row.lon1, row.lat1]
        p2 = [row.lon2, row.lat1]
        p3 = [row.lon2, row.lat2]
        p4 = [row.lon1, row.lat2]

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[p1, p2, p3, p4, p1]]  # Polygon-Koordinaten
            },
            "id": row.Index,  # Wichtig: Die ID verbindet GeoJSON mit dem DataFrame
            "properties": {
                "weeding": row.weeding  # Der Wert
            }
        }
        geojson["features"].append(feature)

    return geojson


def create_map(service_data):
    rsltdata = data_read(service_data)
    fig = draw_map(rsltdata)

    return fig

def draw_map(rsltdata):
    geojson_data = df_to_geojson(rsltdata)

    #fig = px.choropleth_mapbox(
    #    rsltdata,
    #    geojson=geojson_data,  # Das GeoJSON mit den Rechteck-Formen
    #    locations=rsltdata.index,  # Spalte im DataFrame, die mit "id" im GeoJSON übereinstimmt
    #    color='weeding',  # Spalte im DataFrame für die Farbe
    #    color_continuous_scale="Viridis",  # Farbskala
    #    mapbox_style="carto-positron",  # Kartenhintergrund
    #    center={"lat": 52.35433447283137, "lon": 9.743009465842176},  # Kartenmitte
    #    zoom=12,
    #    opacity=0.7
    #)

    fig = go.Figure()
    fig.add_trace(go.Choroplethmapbox(
        geojson=geojson_data,  # Das GeoJSON-Objekt mit den Geometrien
        locations=rsltdata.index,  # Spalte im DataFrame mit den IDs
        featureidkey="id",  # Pfad zur ID in den GeoJSON-Properties
        z=rsltdata.weeding,  # Die Datenwerte, die die Farbe bestimmen
        colorscale="Viridis",  # Farbskala
        marker_opacity=0.7,
        marker_line_width=0.5,
        name="Mowing"
    ))

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=13,
        mapbox_center={"lat": 52.35433447283137, "lon": 9.743009465842176},
        margin=dict(l=0, r=0, b=0, t=0),
        height=450
    )

    return fig