import ast

from flask import render_template
import requests
import numpy as np
from scipy.spatial import ConvexHull
import plotly.graph_objects as go

from utils import route_util as util
from utils import variables as var
from utils.database import database as db

import logging


def add_single_new_area_to_db(req, var_lang):
    typeofarea = req.form.get('typeofarea')
    date = req.form.get('date')
    description = db.clean(req.form.get('description'))

    # check if one argument is missing
    if not typeofarea or not date or not description:
        return _render_template_helper(var_lang, aoi=False)

    polygon_data = req.form.get('polygonData')
    cordpairs_list = ast.literal_eval(polygon_data)
    cordpairs_list[0][0].append(cordpairs_list[0][0][0])

    number_polygons = len(cordpairs_list)

    if number_polygons < 1:
        return _render_template_helper(var_lang, aoi=False)

    polygon_coordinates = []

    for polygon in cordpairs_list:
        myPolygon = polygon[0]
        mypolygon_coordinates = [[cordDict['lng'], cordDict['lat']] for cordDict in myPolygon]

        geom_str = db.convert_to_geostr(var.Geometry.POLYGON.name, mypolygon_coordinates)
        polygon_coordinates.append(geom_str)

    for polygon in polygon_coordinates:
        id_data = db.get_max_id(var.SCHEMA, var.AREA) + 1

        image_files = req.files.getlist("file")

        image_names = util.format_image_names(image_files, id_data)
        area_values = {
            'idx': str(id_data),
            'type': typeofarea,
            'date': date,
            'description': description,
            'image_path': image_names if image_names else None
        }
        db.add_row(var.SCHEMA, var.AREA, area_values)

        for file in image_files:
            if file.filename != '':
                file.save(var.IMG_PATH + file.filename)

        geom_values = {
            'idx': str(id_data),
            'geom': polygon
        }
        db.add_row(var.SCHEMA, var.GEO, geom_values)

    return _render_template_helper(var_lang, version=var.version, submit_response="Successfully added new area", aoi=False)


def visualize_areas_of_interest(request_dict, var_lang):
    aoi_result = f"<div></div>"

    # Check for input data
    if not request_dict['day'] or not request_dict['lake_query']:
        aoi_result = (f"Data is missing. Please provide day and lake query."
                      f"<div> {request_dict} </div>")
        return _render_template_helper(var_lang, aoi_result=aoi_result, aoi=True, submit_response=var_lang.NEW_AREA_SITE['input_data_missing'])

    request_str = 'http://estimate_areas_of_interest:10003/api/get_aois'

    data = requests.post(request_str, json=request_dict)

    if data.status_code == 200:
        apa_data = data.json()
        if len(apa_data.keys()) == 0:
            aoi_result = (f"For this date, no data is available \n\n "
                          f"Input: {request_dict} \n\n "
                          f"Output{apa_data}")
            return _render_template_helper(var_lang, aoi_result=aoi_result, aoi=True)

        date = list(apa_data.keys())[0]
        raw_apa = np.array(apa_data[date]['raw_apa'])
        cropped_apa = np.array(apa_data[date]['cropped_apa'])
        gps = np.array(apa_data[date]['gps'])
        area_of_interest = apa_data[date]['areas_of_interest']

        fig = _draw_area_of_interest(date, raw_apa, cropped_apa, gps, area_of_interest)
        aoi_result = fig.to_html(full_html=False)

        return _render_template_helper(var_lang, aoi_result=aoi_result, aoi=True, aois_to_save=apa_data[date]['areas_of_interest'], date_to_save=date, aoi_req=True, current_date=date, lake_query_value=request_dict['lake_query'], resolution_value=request_dict['resolution_in_m'], cloud_coverage_value=request_dict['cloud_coverage'], n_areas_value=request_dict['n_areas'])

    else:
        aoi_result = (f"Error code: {data.status_code} \n\n "
                      f"Input: {request_dict} \n\n "
                      f"Output {data.json()}")
        return _render_template_helper(var_lang, aoi_result=aoi_result, aoi=True)


def _draw_area_of_interest(date, raw_apa, cropped_apa, gps, areas_of_interest):
    # Create base figure
    fig = go.Figure()

    # Display raw_apa as a scattermapbox with color intensity based on the array values
    # Normalize raw_apa values to 0-1 range for color mapping
    if raw_apa.size > 0:
        # Flatten the array and normalize
        raw_apa_flat = cropped_apa[:,:,1].flatten()
        min_val = np.min(raw_apa_flat)
        max_val = np.max(raw_apa_flat)
        if min_val != max_val:  # Avoid division by zero
            normalized_values = (raw_apa_flat - min_val) / (max_val - min_val)
        else:
            normalized_values = np.zeros_like(raw_apa_flat)

        # Create a colorscale from blue to red
        colors = [f'rgba(0,{255*val},0,{val})' for val in normalized_values]

        # Add scattermapbox trace for each pixel in raw_apa
        fig.add_trace(go.Scattermapbox(
            lat=gps[:, 1],
            lon=gps[:, 0],
            mode='markers',
            marker={
                'size': 10,
                'color': colors,
                'opacity': 0.7
            },
            name='Raw APA Data'
        ))
        #todo: refine this and actually place apa index instead of markers


    for i, c in enumerate(areas_of_interest):
        hull = ConvexHull(c)
        c = np.array(c)
        for simplex in hull.simplices:
            # Add the polygon
            fig.add_trace(go.Scattermapbox(
                lat=c[simplex, 1],
                lon=c[simplex, 0],
                mode='lines',
                fill='toself',
                fillcolor='rgba(0, 255, 0, 0.1)',  # Semi-transparent green
                line={'width': 2, 'color': 'green'},
                name=f'Area of Interest {i+1}'
            ))

    # Update layout
    mean = gps.mean(0)
    fig.update_layout(mapbox={
        'center': {'lat': mean[1], 'lon': mean[0]},
        'zoom': 14},
        mapbox_style="open-street-map",
        margin={"r": 10, "t": 0, "l": 10, "b": 0}
    )
    return fig

def _render_template_helper(var_lang, **kwargs):
    return render_template("newarea.html",
                    new_area_lang=var_lang.NEW_AREA,
                    new_path_lang=var_lang.NEW_PATH,
                    tables_lang=var_lang.TABLES,
                    toa_lang=var_lang.TOA,
                    avoid_lang=var_lang.AVOID,
                    interest_lang=var_lang.INTEREST,
                    chose_lang=var_lang.CHOSE,
                    description_lang=var_lang.DESCRIPTION,
                    date_lang=var_lang.DATE,
                    images_lang=var_lang.IMAGES,
                    submit_lang=var_lang.SUBMIT,
                    version=var.version,
                    language_lang=var_lang.LANGUAGE,
                    english_lang=var_lang.ENGLISH,
                    german_lang=var_lang.GERMAN,
                    area_lang=var_lang.AREA,
                    add_area_lang=var_lang.ADD_AREA,
                    aoi_area_lang=var_lang.NEW_AREA_SITE['aoi_area'],
                    aoi_description_lang=var_lang.NEW_AREA_SITE['aoi_description'],
                    resolution_lang=var_lang.NEW_AREA_SITE['resolution'],
                    cloud_coverage_lang=var_lang.NEW_AREA_SITE['cloud_coverage'],
                    n_areas_lang=var_lang.NEW_AREA_SITE['n_areas'],
                    lake_query_lang=var_lang.NEW_AREA_SITE['lake_query'],
                    get_aoi_lang=var_lang.NEW_AREA_SITE['get_aoi'],
                    **kwargs
    )
