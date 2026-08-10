"""Routes for parent Flask app."""
import ast
import json
from ast import literal_eval
from datetime import datetime, timedelta
import logging
import os
import io
import numpy
import logging

import pandas as pd
import requests
from flask import render_template, make_response, request, current_app as app, session, jsonify, send_file

from utils import route_util as util
from utils import variables as var, dash_util as dutil, language_utils
from utils.database import database as db
from utils.geojson_processor import extract_bathymetry_fields, extract_apa_fields, geojson_to_json_string, build_volume_geojson
from .new_area import add_single_new_area_to_db, visualize_areas_of_interest, save_date_file, get_possible_satellite_fly_overs
from utils.evaluation_utils import draw_map, data_read, create_map

DATES_FILE_NAME_PREFIX = "./static/data/dates_of_fly_overs_for-"
DEFAULT_DATES_FILE_NAME = DATES_FILE_NAME_PREFIX + "Maschsee,Hannover,Germany"


def _get_capacitated_lake_date_options():
    """Query DB for lake+date combinations where volume data exists.
    Returns a list of dicts: [{'lake_name': ..., 'date': ...}, ...]
    """
    try:
        vol_df = db.open_table(var.SCHEMA, var.PLANT_VOLUME, var.PLANT_VOLUME_COLS)

        if vol_df.empty:
            return []

        if 'date' in vol_df.columns:
            if not pd.api.types.is_string_dtype(vol_df['date']):
                vol_df = vol_df.copy()
                vol_df['date'] = vol_df['date'].astype(str)
            combos = (
                vol_df[['lake_name', 'date']]
                .drop_duplicates()
                .sort_values(['lake_name', 'date'], ascending=[True, False])
            )
            return combos.to_dict(orient='records')
        return []
    except Exception:
        return []

TRAJ_OBJ = {
    'editable_cols': [],
    'hidden_cols': ['date'],
    'type': var.TRAJ,
    'max_rows': 100,
    'filter': 0
}


@app.route("/config", methods=["GET", "POST"])
def config():
    var_lang = language_utils.get_language_module()

    if request.method == "POST":
        instanceid = request.form.get('instanceid', '')
        clientid = request.form.get('clientid', '')
        clientsecret = request.form.get('clientsecret', '')
        default_lake = request.form.get('default_lake', 'Maschsee, Hannover, Germany')
        default_cloud_coverage = request.form.get('default_cloud_coverage', '0.5')
        default_resolution = request.form.get('default_resolution', '10')
        map_lat = request.form.get('map_lat', '52.353089')
        map_lon = request.form.get('map_lon', '9.745069')
        map_zoom = request.form.get('map_zoom', '14')
        default_hours = request.form.get('default_hours', '2')
        default_volume = request.form.get('default_volume', '20')
        default_n_areas = request.form.get('default_n_areas', '5')

        resp = make_response(render_template("config.html",
                           configuration_lang=var_lang.CONFIGURATION,
                           new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           clientid_from_cookie=clientid, instanceid_from_cookie=instanceid,
                           clientsecret_from_cookie=clientsecret,
                           default_lake=default_lake, default_cloud_coverage=default_cloud_coverage,
                           default_resolution=default_resolution,
                           map_lat=map_lat, map_lon=map_lon, map_zoom=map_zoom,
                           default_hours=default_hours, default_volume=default_volume,
                           default_n_areas=default_n_areas))
        resp.set_cookie("instance_id", instanceid)
        resp.set_cookie("client_id", clientid)
        resp.set_cookie("client_secret", clientsecret)
        resp.set_cookie("default_lake", default_lake)
        resp.set_cookie("default_cloud_coverage", default_cloud_coverage)
        resp.set_cookie("default_resolution", default_resolution)
        resp.set_cookie("map_lat", map_lat)
        resp.set_cookie("map_lon", map_lon)
        resp.set_cookie("map_zoom", map_zoom)
        resp.set_cookie("default_hours", default_hours)
        resp.set_cookie("default_volume", default_volume)
        resp.set_cookie("default_n_areas", default_n_areas)
    else:
        clientid = request.cookies.get('client_id', '')
        instanceid = request.cookies.get('instance_id', '')
        clientsecret = request.cookies.get('client_secret', '')
        default_lake = request.cookies.get('default_lake', 'Maschsee, Hannover, Germany')
        default_cloud_coverage = request.cookies.get('default_cloud_coverage', '0.5')
        default_resolution = request.cookies.get('default_resolution', '10')
        map_lat = request.cookies.get('map_lat', '52.353089')
        map_lon = request.cookies.get('map_lon', '9.745069')
        map_zoom = request.cookies.get('map_zoom', '14')
        default_hours = request.cookies.get('default_hours', '2')
        default_volume = request.cookies.get('default_volume', '20')
        default_n_areas = request.cookies.get('default_n_areas', '5')

        resp = render_template("config.html",
                           configuration_lang=var_lang.CONFIGURATION,
                           new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           clientid_from_cookie=clientid, instanceid_from_cookie=instanceid,
                           clientsecret_from_cookie=clientsecret,
                           default_lake=default_lake, default_cloud_coverage=default_cloud_coverage,
                           default_resolution=default_resolution,
                           map_lat=map_lat, map_lon=map_lon, map_zoom=map_zoom,
                           default_hours=default_hours, default_volume=default_volume,
                           default_n_areas=default_n_areas)

    return resp


@app.route("/newarea", methods=["GET"])
def new_area():
    """New Area"""
    var_lang = language_utils.get_language_module()

    default_lake = request.cookies.get('default_lake', 'Maschsee, Hannover, Germany')
    default_cloud_coverage = request.cookies.get('default_cloud_coverage', '0.5')
    default_resolution = request.cookies.get('default_resolution', '10')
    default_n_areas = request.cookies.get('default_n_areas', '5')

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           cap_lake_date_options=_get_capacitated_lake_date_options(),
                           aoi=False,
                           resolution_value=default_resolution,
                           cloud_coverage_value=default_cloud_coverage,
                           n_areas_value=default_n_areas,
                           lake_query_value=default_lake,
                           available_dates=[],
                           sentinel_lake_query=default_lake,
                           sentinel_cloud_coverage=default_cloud_coverage)

@app.route("/newarea/add", methods=["POST"])
def new_area_add():
    """Add New Area"""
    var_lang = language_utils.get_language_module()
    return add_single_new_area_to_db(request, var_lang)

@app.route("/evaluation_save", methods=["POST"])
def evaluation_save():
    var_lang = language_utils.get_language_module()

    df = pd.read_csv('result.csv')

    for row in df.itertuples():
        db.add_row(var.SCHEMA, var.EVALUATION, {"date":row.date, "lat1":row.lat1, "lon1":row.lon1, "lat2":row.lat2, "lon2":row.lon2, "weeding":row.weeding})

    response = requests.get("http://evaluation_service:10005/get_dates")
    result_string = "Dates: "

    for x in json.loads(response.text)["message"]:
        result_string += x
        result_string += " "

    return render_template("evaluation.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION, data_lang=var_lang.DATA,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           get_dates=result_string, evaluation_lang=var_lang.EVALUATION,
                           fig="",
                           approve_eval=False)


@app.route("/evaluation", methods=["POST", "GET"])
def evaluation():
    var_lang = language_utils.get_language_module()


    response = requests.get("http://evaluation_service:10005/get_dates")
    available_dates = json.loads(response.text)["message"]  # List of dates

    if request.method == "POST":

        date = request.form.get('evaluation_date')

        url = "http://evaluation_service:10005/create_comparison_image"

        payload = {
            'date': date,
            'output_path': './data/results/',
            'satellite_image_path': ""
        }

        json_data = json.loads(json.dumps(payload))
        response = requests.post(url, json=json_data)

        data_eval = json.loads(response.text)
        pda = data_read(data_eval)
        pda["date"] = date
        logging.log(logging.CRITICAL, pda)
        pda.to_csv('result.csv', index=False)
        fig = create_map(data_eval)
        fig = fig.to_html(full_html=False)

        return render_template("evaluation.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                               tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                               interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                               description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                               images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                               version=var.version, language_lang=var_lang.LANGUAGE,
                               english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                               configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                               data_lang=var_lang.DATA,
                               area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                               fig=fig,
                               approve_eval=True)

    # else:

    return render_template("evaluation.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                           data_lang=var_lang.DATA,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           available_dates=available_dates)

@app.route("/newarea/get_dates", methods=["POST"])
def new_area_get_dates():
    """Query available satellite dates for a given lake"""
    var_lang = language_utils.get_language_module()

    clientid = request.cookies.get('client_id')
    instanceid = request.cookies.get('instance_id')
    clientsecret = request.cookies.get('client_secret')

    lake_query = request.form.get('lake_query', '')
    cloud_coverage = request.form.get('cloud_coverage', '0.5')

    if not lake_query:
        return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           aoi=True,
                           resolution_value="10",
                           cloud_coverage_value=cloud_coverage,
                           n_areas_value="5",
                           lake_query_value=lake_query,
                           available_dates="Please enter a lake name.",
                           sentinel_lake_query=lake_query,
                           sentinel_cloud_coverage=cloud_coverage)

    if not clientid or not instanceid or not clientsecret:
        return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           aoi=True,
                           resolution_value="10",
                           cloud_coverage_value=cloud_coverage,
                           n_areas_value="5",
                           lake_query_value=lake_query,
                           available_dates="Please insert your credentials in the configuration page.",
                           sentinel_lake_query=lake_query,
                           sentinel_cloud_coverage=cloud_coverage)

    one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    request_dict = {"start": one_year_ago,
                    "end": datetime.today().strftime('%Y-%m-%d'),
                    "resolution_in_m": 10,
                    "lake_query": lake_query,
                    "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
                    "max_cloud_coverage": float(cloud_coverage),
                    "instance_id": instanceid,
                    "client_id": clientid,
                    "client_secret": clientsecret}

    available_dates = get_possible_satellite_fly_overs(request_dict)['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           aoi=True,
                           resolution_value="10",
                           cloud_coverage_value=cloud_coverage,
                           n_areas_value="5",
                           lake_query_value=lake_query,
                           available_dates=available_dates,
                           sentinel_lake_query=lake_query,
                           sentinel_cloud_coverage=cloud_coverage)


@app.route("/newarea/get_aois", methods=["POST"])
def new_area_get_aois():
    """Get Areas of Interest"""
    var_lang = language_utils.get_language_module()

    clientid = request.cookies.get('client_id')
    instanceid = request.cookies.get('instance_id')
    clientsecret = request.cookies.get('client_secret')

    logging.log(logging.CRITICAL, f" also wirklich {clientid}")
    request_dict = {
        'day': request.form.getlist('aoi_date')[0],
        'resolution_in_m': float(request.form.getlist('resolution')[0]),
        'cloud_coverage': float(request.form.getlist('cloud_coverage')[0]),
        'n_areas': int(request.form.getlist('n_areas')[0]),
        'lake_query': request.form.getlist('lake_query')[0],
        "instance_id": instanceid,
        "client_id": clientid,
        "client_secret": clientsecret
    }

    available_dates = get_possible_satellite_fly_overs(request_dict)['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    return visualize_areas_of_interest(request_dict, var_lang, available_dates=available_dates,
                                       sentinel_lake_query=request_dict['lake_query'],
                                       sentinel_cloud_coverage=str(request_dict['cloud_coverage']))


@app.route("/newarea/save_aois", methods=["POST"])
def new_area_save_aois():
    var_lang = language_utils.get_language_module()

    # available_dates = get_possible_satellite_fly_overs()['available_dates']
    # available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates
    date = request.form.getlist('date_to_save')

    dieliste = literal_eval(request.form.getlist('aois_ts')[0])

    for element in dieliste:
        id_data = db.get_max_id(var.SCHEMA, var.AREA) + 1

        element.append(element[0])

        polygon = db.convert_to_geostr(var.Geometry.POLYGON.name, element)

        area_values = {
            'idx': str(id_data),
            'type': "interest",
            'date': date[0],
            'description': "Automatic generated AOI from satellite pictures",
            'image_path': None
        }
        db.add_row(var.SCHEMA, var.AREA, area_values)

        geom_values = {
            'idx': str(id_data),
            'geom': polygon
        }
        db.add_row(var.SCHEMA, var.GEO, geom_values)

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                           data_lang=var_lang.DATA, capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           aoi=True)


def get_polygon(lons, lats, color='blue'):
    if len(lons) != len(lats):
        raise ValueError('the legth of longitude list  must coincide with that of latitude')
    geojd = {"type": "FeatureCollection"}
    geojd['features'] = []
    coords = []
    for lon, lat in zip(lons, lats):
        coords.append((lon, lat))
    coords.append((lons[0], lats[0]))  # close the polygon
    geojd['features'].append({"type": "Feature",
                              "geometry": {"type": "Polygon",
                                           "coordinates": [coords]}})
    layer = dict(sourcetype='geojson',
                 source=geojd,
                 below='',
                 type='fill',
                 color=color)
    return layer


@app.route("/newpath/<typ>", methods=["GET", "POST"])
def new_path(typ):
    var_lang = language_utils.get_language_module()
    add = True
    paths = {}
    approve_map = False
    fig = "<div></div>"
    show_error = False
    submit_manuell_path_response = ""
    pgd = var_lang.PATH_GENERATE_DESCRIPTION

    # Query database for distinct dates that have areas of interest
    try:
        aoi_date_rows = db.select_distinct(var.SCHEMA, var.AREA, 'date')
        aoi_dates = sorted([str(row[0]) for row in aoi_date_rows if row[0] is not None])
    except Exception:
        aoi_dates = []

    if typ == var.ADD:
        """New Path"""
        add = True
        if request.method == "POST":

            date = request.form.get('date')

            if not date:
                submit_manuell_path_response = "cannot submit, missing arguments. Please fill out all fields."
                return render_template("newpath.html", version=var.version, path=add, approve_map=approve_map, fig=fig,
                                       show_error=show_error, submit_manuell_path_response=submit_manuell_path_response,
                                       area_lang=var_lang.AREA, path_lang=var_lang.PATH, tables_lang=var_lang.TABLES,
                                       language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH,
                                       configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                                       data_lang=var_lang.DATA, capacitated_path_lang=var_lang.CAPACITATED_PATH,
                                       german_lang=var_lang.GERMAN, new_area_lang=var_lang.NEW_AREA,
                                       new_path_lang=var_lang.NEW_PATH, aoi_dates=aoi_dates)

            polyline_data = request.form.get('polylineData')
            cordpairs_list = ast.literal_eval(polyline_data)

            number_polyliness = len(cordpairs_list)

            if number_polyliness < 1:
                submit_manuell_path_response = "cannot submit, missing arguments. Please fill out all fields."
                return render_template("newpath.html", version=var.version, path=add, approve_map=approve_map, fig=fig,
                                       show_error=show_error, submit_manuell_path_response=submit_manuell_path_response,
                                       area_lang=var_lang.AREA, path_lang=var_lang.PATH, tables_lang=var_lang.TABLES,
                                       language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH,
                                       configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                                       data_lang=var_lang.DATA, capacitated_path_lang=var_lang.CAPACITATED_PATH,
                                       german_lang=var_lang.GERMAN, new_area_lang=var_lang.NEW_AREA,
                                       new_path_lang=var_lang.NEW_PATH, aoi_dates=aoi_dates)

            polyline_coordinates = []

            for polyline in cordpairs_list:
                mypolyline_coordinates = [[cordDict['lat'], cordDict['lng']] for cordDict in polyline]
                polyline_coordinates.append(mypolyline_coordinates)

            for polyline in polyline_coordinates:
                util.add_path_to_db(polyline, date)

            submit_manuell_path_response = "saved successfully"

    elif typ == var.GENERATE:
        """Generate path"""
        add = False

        if request.method == "POST":
            date = request.form.getlist("date")[0]
            date = datetime.strptime(date, '%Y-%m-%d').date()
            available_hours = request.form.getlist("hours")[0]
            dur = int(available_hours) * 60
            volume = request.form.getlist("volume")[0]
            aoi_dict = {}

            if request.form.getlist('submit_btn')[0] == 'view_paths':
                df = db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS)
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['type'].isin(['interest'])]

                df = df[df['date'].isin([date])]
                df = dutil.add_has_images_col(df)

                db.convert_to_geojson_file(var.SCHEMA, var.GEO, var.GEO_FILE)
                with open(var.GEO_FILE, 'r') as file:
                    geojson = json.load(file)

                filtered_data = [item for item in geojson["features"] if item["id"] in df["idx"].values.tolist()]

                i = 1
                for x in filtered_data:
                    cords = x['geometry']['coordinates'][0]
                    for row in cords:
                        row[1], row[0] = row[0], row[1]

                    aoi_dict[str(i)] = {'amount': 5, 'cords': cords}
                    i += 1

                url = 'http://path_planning_vrpy:10002/routePos/'
                myobj = {"vehicle_capacity": int(volume), "duration": dur, "aoi": aoi_dict}

                x = requests.post(url, json=json.loads(json.dumps(myobj)))

                output = x.json()
                paths = output['routes']

                if len(paths) > 0:
                    fig = json.dumps({"paths": paths, "aoi": {k: {"amount": v["amount"], "center": [sum(c[0] for c in v["cords"])/len(v["cords"]), sum(c[1] for c in v["cords"])/len(v["cords"])]} for k, v in aoi_dict.items()}})
                    approve_map = True
                else:
                    pgd = "There are no Areas of Interest for this date. Please choose another date."

            # paths = generate_path_script.get_paths(date, available_hours, volume)
            # r = requests.get(
            #    "http://127.0.0.1:8002/route/{'vc':" + volume + ", 'duration':" + str(dur) + ", 'aois':" + str(aoi_dict) + "}")
            # paths = literal_eval(r.text)
            # paths = paths["routes"]

            if request.form.getlist('submit_btn')[0] == 'approve':
                path_text = request.form.get('hidd')
                paths = literal_eval(path_text)
                # paths = paths["routes"]

                approve_map = True
                path_ids = request.form.getlist('map_id')[0]

                try:
                    path_ids = path_ids.split(',')
                    for path_id in path_ids:
                        # path_id = int(path_id)
                        path = paths[path_id]
                        util.add_path_to_db(path, date)
                except:
                    show_error = True
                    approve_map = False

            if request.form.getlist('submit_btn')[0] == 'approve_all':
                df = db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS)
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['type'].isin(['interest'])]

                df = df[df['date'].isin([date])]
                df = dutil.add_has_images_col(df)

                db.convert_to_geojson_file(var.SCHEMA, var.GEO, var.GEO_FILE)
                with open(var.GEO_FILE, 'r') as file:
                    geojson = json.load(file)

                filtered_data = [item for item in geojson["features"] if item["id"] in df["idx"].values.tolist()]

                i = 1
                for x in filtered_data:
                    cords = x['geometry']['coordinates'][0]
                    for row in cords:
                        row[1], row[0] = row[0], row[1]

                    aoi_dict[i] = {'amount': 5, 'cords': cords}
                    i += 1

                url = 'http://path_planning_vrpy:10002/routePos/'
                myobj = {"vehicle_capacity": int(volume), "duration": dur, "aoi": aoi_dict}

                x = requests.post(url, json=json.loads(json.dumps(myobj)))

                output = x.json()

                paths = output['routes']
                approve_map = True

                for path_id in range(1, len(paths) + 1):
                    util.add_path_to_db(paths[str(path_id)], date)
                if show_error == True:
                    approve_map = False


    if approve_map == True:
        hav = request.form['hours']
        svv = request.form['volume']
    else:
        hav = 2
        svv = 20

    return render_template("newpath.html", version=var.version, path=add, approve_map=approve_map, fig=fig,
                           show_error=show_error, path_var=paths,
                           submit_manuell_path_response=submit_manuell_path_response, add_path_lang=var_lang.ADD_PATH,
                           generate_path_lang=var_lang.GENERATE_PATH, submit_lang=var_lang.SUBMIT,
                           date_lang=var_lang.DATE, path_gen_description_lang=pgd,
                           approve_lang=var_lang.APPROVE, approve_all_lang=var_lang.APPROVE_ALL,
                           map_ids_lang=var_lang.MAP_IDS, view_paths_lang=var_lang.VIEW_PATH,
                           new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, storage_volume_lang=var_lang.STORAGE_VOLUME,
                           configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                           data_lang=var_lang.DATA, capacitated_path_lang=var_lang.CAPACITATED_PATH,
                           hours_available_lang=var_lang.HOURSE_AVAILABLE, hours_available_value=hav, storage_volume_value=svv, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN, aoi_dates=aoi_dates)


"""
@app.route("/switch_language/<language>", methods=["GET"])
def switch_language(language):
    if language in ['english', 'german']:
        var.language = language
        session['language'] = language

    # Redirect back to the referring page or home page
    referrer = request.referrer
    if referrer:
        return {'success': 200, 'redirect': referrer}
    return {'success': 200, 'redirect': '/'}
"""

@app.route("/changelog", methods=["GET"])
def changelog():
    var_lang = language_utils.get_language_module()
    return render_template("changelog.html", version=var.version, new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH, tables_lang=var_lang.TABLES, language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN)


# @app.route("/newarea/<request_msg>", methods=["GET"])
# def get_aois_api(request_msg):
#     """
#     API endpoint to get areas of interest from satellite data.
#
#     Args:
#         request_msg: A string representation of a dictionary containing request parameters.
#                     Must include 'day' date.
#
#     Returns:
#         JSON response with areas of interest
#     """
#
#     print(request_msg)
#
#     return render_template(
#         "new_area.html",
#         aoi_result=None,
#         approve_aois=False,
#         # approve_aois_lang=None,
#         # get_aoi_lang=None,
#         # lake_query_lang=None,
#         # n_areas_lang=None,
#         # cloud_coverage_lang=None,
#         # resolution_lang=None,
#         # date_lang=None,
#     )

@app.route("/tables/get/info", methods=["GET"])
def format_parameters():
    ''' formats url parameters before redirecting to table_view() '''
    parameters = '?'
    param_count = 0
    for key, value in request.args.items():
        if value is not None and key != 'type':
            param_count += 1
            if param_count > 1:
                parameters += '&'
            parameters += '{0}={1}'.format(key, str(value))

    req_typ = request.args.get('type', type=str)
    return {'success': 200, 'redirect': '/tables/view/' + req_typ + parameters}

@app.route("/traj/load", methods=["POST"])
def traj_load():
    payload = request.get_json(force=True) or {}
    date = payload.get("date")

    if not date:
        return {"success": 400, "redirect": request.referrer or "/"}

    bag_directory = f"/home/docker/rosbags/{date}/"

    cutoff = datetime(2025, 1, 1)
    date_obj = datetime.strptime(date, "%Y-%m-%d")

    if date_obj < cutoff:
        image_topics = [
            "/camera/color/image_raw_throttled/compressed", 
            "/camera/infra1/image_rect_raw_throttled/compressed",
        ]
    else:
        image_topics = [
            "/camera/color/image_raw_throttle/compressed", 
            "/camera/infra1/image_rect_raw_throttle/compressed",
        ]

    logging.info(image_topics)

    extract_navsatfix_payload = {
        "bag_directory": bag_directory,
        "topics": ["/fix"],
    }
    image_payload = {
        "bag_directory": bag_directory,
        "topics": image_topics,
    }
    mpeg_payload = {
        "bag_directory": bag_directory,
        "topics": image_topics,
    }
    trajectory_payload = {
        "bag_directory": bag_directory,
        "topics": [
           "/fix",
        ],
    }

    try:
        app.logger.info("Calling /rosbag/extract_navsatfix")
        resp = requests.post(
            "http://data_extraction:10006/rosbag/extract_navsatfix",
            json=extract_navsatfix_payload,
            timeout=2700,
        )
        app.logger.info("Finished /rosbag/extract_navsatfix")
        
        app.logger.info("Calling /rosbag/img")
        resp = requests.post(
            "http://data_extraction:10006/rosbag/img",
            json=image_payload,
            timeout=2700,
        )
        app.logger.info("Finished /rosbag/img with status %s", resp.status_code)
        # resp.raise_for_status()

        app.logger.info("Calling /rosbag/mpeg")
        resp = requests.post(
            "http://data_extraction:10006/rosbag/mpeg",
            json=mpeg_payload,
            timeout=2700,
        )
        app.logger.info("Finished /rosbag/mpeg with status %s", resp.status_code)

        # innerhalb von docker den Service-Namen aus compose.yaml benutzen
        app.logger.info("Calling /rosbag/trajectory")
        resp = requests.post(
            "http://data_extraction:10006/rosbag/trajectory",
            json=trajectory_payload,
            timeout=2700,
        )
        app.logger.info("Finished /rosbag/trajectory with status %s", resp.status_code)
        resp.raise_for_status()

        # Trajektorienpunkte aus der Response lesen und in die DB schreiben
        data = resp.json()
        trajectory = data.get("trajectory", [])

        if trajectory:
            start_idx = db.get_max_id(var.SCHEMA, var.traj) + 1
            for offset, point in enumerate(trajectory):
                values = {
                    "idx": start_idx + offset,
                    "timestamp": int(point["timestamp"]),
                    "latitude": float(point["latitude"]),
                    "longitude": float(point["longitude"]),
                    "date": point.get("date", date),
                    "mowed_grass": None,
                }
                db.add_row(var.SCHEMA, var.traj, values)

            # remove rosbags after saving the data to the database
            rosbag_folder_path = os.path.join(var.VID_FILE_PATH, date)
            files_in_folder = os.listdir(rosbag_folder_path)
            bagfiles_in_folder = [f for f in files_in_folder if f.endswith('.bag')]
            for filename in bagfiles_in_folder:
                full_path = os.path.join(rosbag_folder_path, filename)
                if os.path.isfile(full_path):
                    os.remove(full_path)

    except Exception as exc:
        app.logger.error("Error calling data_extraction: %s", exc)
        return {"success": 500, "redirect": request.referrer or "/"}

    # nach erfolgreichem Import zur Trajektorien-Tabelle für dieses Datum springen
    redirect_url = f"/tables/view/{var.TRAJ}?date={date}"
    return {"success": 200, "redirect": redirect_url}

def _get_volume_lakes():
    """Get lakes that have both bathymetry and APA data in the database."""
    try:
        return db.get_lakes_with_apa(var.SCHEMA, var.BATHYMETRY, var.APA_INDEX)
    except Exception as e:
        logging.log(logging.WARNING, f"Could not fetch lakes with APA data: {e}")
        return []

def _render_data_template(var_lang, **kwargs):
    # Always provide volume_lakes for the volume tab dropdown
    if 'volume_lakes' not in kwargs:
        kwargs['volume_lakes'] = _get_volume_lakes()
    return render_template("data.html",
                           data_lang=var_lang.DATA,
                           new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, version=var.version,
                           language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH,
                           german_lang=var_lang.GERMAN, configuration_lang=var_lang.CONFIGURATION,
                           evaluation_lang=var_lang.EVALUATION,
                           bathymetry_lang=var_lang.BATHYMETRY,
                           apa_index_lang=var_lang.APA_INDEX,
                           plant_volume_lang=var_lang.PLANT_VOLUME,
                           date_lang=var_lang.DATE,
                           submit_lang=var_lang.SUBMIT,
                           bathymetry_description_lang=var_lang.DATA_SITE["bathymetry_description"],
                           apa_description_lang=var_lang.DATA_SITE["apa_description"],
                           plant_volume_description_lang=var_lang.DATA_SITE["plant_volume_description"],
                           lake_name_lang=var_lang.DATA_SITE["lake_name"],
                           get_bathymetry_lang=var_lang.DATA_SITE["get_bathymetry"],
                           get_apa_lang=var_lang.DATA_SITE["get_apa"],
                           calculate_volume_lang=var_lang.DATA_SITE["calculate_volume"],
                           save_to_db_lang=var_lang.DATA_SITE["save_to_db"],
                           **kwargs)


@app.route("/data", methods=["GET"])
def data_page():
    var_lang = language_utils.get_language_module()
    return _render_data_template(var_lang, active_tab='bathymetry')


@app.route("/data/bathymetry", methods=["POST"])
def data_bathymetry():
    var_lang = language_utils.get_language_module()
    osm_query = request.form.get('osm_query', '')

    try:
        payload = {}
        if osm_query:
            payload["osm_query"] = osm_query
        resp = requests.post("http://bathymetry_service:10005/geojson", json=payload, timeout=120)
        if resp.status_code == 200:
            geojson_data = resp.json()
            features = geojson_data.get('features', [])
            datei = open('textdatei.txt', 'w')
            datei.write(json.dumps(geojson_data))
            return _render_data_template(var_lang, active_tab='bathymetry',
                                         bathymetry_response=f"Retrieved {len(features)} bathymetry points.",
                                         bathymetry_geojson=json.dumps(geojson_data),
                                         bathymetry_save_data=json.dumps(geojson_data),
                                         bathymetry_lake_value=osm_query)
        else:
            return _render_data_template(var_lang, active_tab='bathymetry',
                                         bathymetry_response=f"Error: {resp.status_code} - {resp.text}",
                                         bathymetry_lake_value=osm_query)
    except (requests.ConnectionError, requests.Timeout) as e:
        return _render_data_template(var_lang, active_tab='bathymetry',
                                     bathymetry_response=f"Connection error: {str(e)}",
                                     bathymetry_lake_value=osm_query)


@app.route("/data/bathymetry/save", methods=["POST"])
def data_bathymetry_save():
    var_lang = language_utils.get_language_module()
    request.max_form_memory_size = 10 * 1024 * 1024
    lake_name = request.form.get('lake_name', '')
    save_data = request.form.get('save_data', '{}')

    try:
        geojson_data = json.loads(save_data)
        # Use geojson_processor to extract only depth and location data
        reduced_geojson = extract_bathymetry_fields(geojson_data)
        features_count = len(reduced_geojson.get('features', []))

        start_idx = db.get_max_id(var.SCHEMA, var.BATHYMETRY) + 1
        for offset, point in enumerate(reduced_geojson["features"]):
            values = {
                "idx": start_idx + offset,
                "lake_name": lake_name,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "lat": point["geometry"]["coordinates"][1],
                "lon": point["geometry"]["coordinates"][0], 
                "depth": point["properties"]["estimated_depth"],
            }
            db.add_row(var.SCHEMA, var.BATHYMETRY, values)
        
        return _render_data_template(var_lang, active_tab='bathymetry',
                                     bathymetry_response=f"Saved bathymetry data for {lake_name} with {features_count} points to database.")
    except Exception as e:
        logging.log(logging.CRITICAL, f"Error saving bathymetry data")
        return _render_data_template(var_lang, active_tab='bathymetry',
                                     bathymetry_response=f"Error saving data: {str(e)}")


@app.route("/data/apa/get_dates", methods=["POST"])
def data_apa_get_dates():
    """Query available satellite dates for APA data"""
    var_lang = language_utils.get_language_module()

    clientid = request.cookies.get('client_id')
    instanceid = request.cookies.get('instance_id')
    clientsecret = request.cookies.get('client_secret')

    lake_query = request.form.get('lake_query', '')
    cloud_coverage = request.form.get('cloud_coverage', '0.5')

    if not lake_query:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_available_dates="Please enter a lake name.",
                                     apa_lake_query_value=lake_query,
                                     apa_cloud_coverage_value=cloud_coverage)

    if not clientid or not instanceid or not clientsecret:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_available_dates="Please insert your credentials in the configuration page.",
                                     apa_lake_query_value=lake_query,
                                     apa_cloud_coverage_value=cloud_coverage)

    one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    request_dict = {"start": one_year_ago,
                    "end": datetime.today().strftime('%Y-%m-%d'),
                    "resolution_in_m": 10,
                    "lake_query": lake_query,
                    "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
                    "max_cloud_coverage": float(cloud_coverage),
                    "instance_id": instanceid,
                    "client_id": clientid,
                    "client_secret": clientsecret}

    available_dates = get_possible_satellite_fly_overs(request_dict)['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    return _render_data_template(var_lang, active_tab='apa',
                                 apa_available_dates=available_dates,
                                 apa_lake_query_value=lake_query,
                                 apa_cloud_coverage_value=cloud_coverage,
                                 apa_sentinel_lake_query=lake_query,
                                 apa_sentinel_cloud_coverage=cloud_coverage)


@app.route("/data/apa", methods=["POST"])
def data_apa():
    """Get APA index data - similar to /newarea/get_aois for sentinel data"""
    var_lang = language_utils.get_language_module()

    clientid = request.cookies.get('client_id')
    instanceid = request.cookies.get('instance_id')
    clientsecret = request.cookies.get('client_secret')

    lake_name = request.form.get('lake_query', '')
    date = request.form.get('date', '')
    cloud_coverage = request.form.get('cloud_coverage', '0.5')

    if not lake_name:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_response="Please enter a lake name.")

    # Get available dates for the response
    #todo: check if get dates is really needed here
    available_dates = []
    if clientid and instanceid and clientsecret:
        one_year_ago = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        request_dict = {"start": one_year_ago,
                        "end": datetime.today().strftime('%Y-%m-%d'),
                        "resolution_in_m": 10,
                        "lake_query": lake_name,
                        "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
                        "max_cloud_coverage": float(cloud_coverage),
                        "instance_id": instanceid,
                        "client_id": clientid,
                        "client_secret": clientsecret}
        available_dates = get_possible_satellite_fly_overs(request_dict)['available_dates']
        available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    try:
        payload = {
            "lake_query": lake_name,
            "day": date,
            "instance_id": instanceid,
            "client_id": clientid,
            "client_secret": clientsecret,
            "geojson_file": True,
            "full_apa": False
        }
        resp = requests.post("http://apa_index_service:10003/api/get_apa", json=payload, timeout=120)
        if resp.status_code == 200:
            geojson_data = resp.json()
            features = geojson_data.get('features', [])
            return _render_data_template(var_lang, active_tab='apa',
                                         apa_response=f"Retrieved {len(features)} APA index points.",
                                         apa_geojson=json.dumps(geojson_data),
                                         apa_save_data=json.dumps(geojson_data),
                                         apa_lake_value=lake_name,
                                         apa_date_value=date,
                                         apa_available_dates=available_dates,
                                         apa_sentinel_lake_query=lake_name,
                                         apa_sentinel_cloud_coverage=cloud_coverage)
        else:
            return _render_data_template(var_lang, active_tab='apa',
                                         apa_response=f"Error: {resp.status_code} - {resp.text}",
                                         apa_lake_value=lake_name,
                                         apa_date_value=date,
                                         apa_available_dates=available_dates,
                                         apa_sentinel_lake_query=lake_name,
                                         apa_sentinel_cloud_coverage=cloud_coverage)
    except (requests.ConnectionError, requests.Timeout) as e:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_response=f"Connection error: {str(e)}",
                                     apa_lake_value=lake_name,
                                     apa_date_value=date,
                                     apa_available_dates=available_dates,
                                     apa_sentinel_lake_query=lake_name,
                                     apa_sentinel_cloud_coverage=cloud_coverage)


@app.route("/data/apa/save", methods=["POST"])
def data_apa_save():
    var_lang = language_utils.get_language_module()
    lake_name = request.form.get('lake_name', '').split(',')[0]
    save_data = request.form.get('save_data', '{}')

    try:
        geojson_data = json.loads(save_data)

        # Parse date from geojson features for the filename
        geojson_date = ""
        features = geojson_data.get('features', [])
        if features and 'properties' in features[0]:
            geojson_date = features[0]['properties'].get('date', '')

        # Build filename from lake_name and date
        safe_lake = lake_name.replace(" ", "_").replace("/", "_") if lake_name else "unknown"
        safe_date = geojson_date.replace(" ", "_").replace("/", "-").replace(":", "-") if geojson_date else "nodate"
        filename = f"{safe_lake}_{safe_date}.geojson"

        os.makedirs("/geojsonfiles/APA", exist_ok=True)
        with open(f"/geojsonfiles/APA/{filename}", "w") as f:
            json.dump(geojson_data, f, indent=2)
        with open("/geojsonfiles/APA/newdata.geojson", "w") as f:
            json.dump(geojson_data, f, indent=2)

        json_data = json.dumps(geojson_data)
        buffer = io.BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)


        # Use geojson_processor to extract only APA value and location data
        reduced_geojson = extract_apa_fields(geojson_data)
        features_count = len(reduced_geojson.get('features', []))
        
        # Convert to compact JSON string for storage
        #geojson_string = geojson_to_json_string(reduced_geojson, compact=True)
        
        # Save to lake_apa_index table
        #idx = db.get_max_id(var.SCHEMA, var.LAKE_APA_INDEX) + 1
        #values = {
        #    'idx': str(idx),
        #    'lake_name': lake_name,
        #    'geojson_data': geojson_string
        #}

        daten = reduced_geojson['features']
        logging.log(logging.CRITICAL, daten[0])
        logging.log(logging.CRITICAL, daten[1])

        start_idx = db.get_max_id(var.SCHEMA, var.APA_INDEX) + 1
        for offset, point in enumerate(reduced_geojson['features']):
            values = {
                "idx": start_idx + offset,
                "lake_name": lake_name,
                "lat": float(point['geometry']["coordinates"][1]),
                "lon": float(point['geometry']["coordinates"][0]),
                "apa_value": float(point["properties"]["apa"]),
                "date": point["properties"]["date"],
                "description": None,
            }
            db.add_row(var.SCHEMA, var.APA_INDEX, values)
        
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_response=f"Saved APA index data for {lake_name} with {features_count} points to database.")
    except Exception as e:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_response=f"Error saving data: {str(e)}")


@app.route("/data/apa/download", methods=["POST"])
def data_apa_download():
    var_lang = language_utils.get_language_module()
    lake_name = request.form.get('lake_name', '').split(',')[0]
    save_data = request.form.get('save_data', '{}')

    try:
        geojson_data = json.loads(save_data)

        # Parse date from geojson features for the filename
        geojson_date = ""
        features = geojson_data.get('features', [])
        if features and 'properties' in features[0]:
            geojson_date = features[0]['properties'].get('date', '')

        # Build filename from lake_name and date
        safe_lake = lake_name.replace(" ", "_").replace("/", "_") if lake_name else "unknown"
        safe_date = geojson_date.replace(" ", "_").replace("/", "-").replace(":", "-") if geojson_date else "nodate"
        filename = f"{safe_lake}_{safe_date}.geojson"

        json_data = json.dumps(geojson_data)
        buffer = io.BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='daten.json',
            mimetype='application/json'
        )

    except Exception as e:
        return _render_data_template(var_lang, active_tab='apa',
                                     apa_response=f"Error saving data: {str(e)}")

@app.route("/data/volume/get_dates", methods=["POST"])
def data_volume_get_dates():
    """Return available APA dates from the database for a given lake as JSON"""
    lake_name = request.form.get('lake_name', '')
    if not lake_name:
        return jsonify([])
    try:
        dates = db.select_distinct_filtered(var.SCHEMA, var.APA_INDEX, 'date', 'lake_name', lake_name)
        # Convert date objects to strings
        date_strings = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in dates]
        return jsonify(date_strings)
    except Exception as e:
        logging.log(logging.WARNING, f"Could not fetch APA dates for {lake_name}: {e}")
        return jsonify([])

@app.route("/data/volume", methods=["POST"])
def data_volume():
    var_lang = language_utils.get_language_module()
    lake_name = request.form.get('lake_query', '')
    date = request.form.get('date', '')

    clientid = request.cookies.get('client_id')
    instanceid = request.cookies.get('instance_id')
    clientsecret = request.cookies.get('client_secret')

    if not lake_name:
        return _render_data_template(var_lang, active_tab='volume',
                                     volume_response="Please enter a lake name.")


    try:
        payload = {"lake_name": lake_name}
        if date:
            payload["date"] = date

        payload["instance_id"] = instanceid
        payload["client_id"] = clientid
        payload["client_secret"] = clientsecret

        resp = requests.post("http://capacitated_aoi_service:10010/volume", json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()

            return _render_data_template(var_lang, active_tab='volume',
                                         volume_response=f"Calculated plant volume points.",
                                         volume_result=json.dumps(data),
                                         volume_save_data=json.dumps(data),
                                         volume_lake_value=lake_name,
                                         volume_date_value=date)
        else:
            return _render_data_template(var_lang, active_tab='volume',
                                         volume_response=f"Error: {resp.status_code} - {resp.text}",
                                         volume_lake_value=lake_name,
                                         volume_date_value=date)
    except (requests.ConnectionError, requests.Timeout) as e:
        return _render_data_template(var_lang, active_tab='volume',
                                     volume_response=f"Connection error: {str(e)}",
                                     volume_lake_value=lake_name,
                                     volume_date_value=date)


@app.route("/data/volume/save", methods=["POST"])
def data_volume_save():
    var_lang = language_utils.get_language_module()
    lake_name = request.form.get('lake_name', '')
    form_date = request.form.get('date', '')
    save_data = request.form.get('save_data', '{}')

    try:
        data = json.loads(save_data)

        # The volume service returns GeoJSON with features
        features = data.get('features', [])

        start_idx = db.get_max_id(var.SCHEMA, var.PLANT_VOLUME) + 1
        for offset, feature in enumerate(features):
            props = feature.get('properties', {})
            coords = feature.get('geometry', {}).get('coordinates', [None, None])
            # coordinates may be a simple [lon, lat] or nested polygon coords
            if coords and isinstance(coords[0], list):
                # Polygon: use centroid of first ring
                ring = coords[0] if not isinstance(coords[0][0], list) else coords[0]
                lon = sum(c[0] for c in ring) / len(ring)
                lat = sum(c[1] for c in ring) / len(ring)
            else:
                lon = coords[0] if len(coords) > 0 else None
                lat = coords[1] if len(coords) > 1 else None

            # Use date from feature properties, fall back to form date
            feature_date = props.get('date', None) or form_date or None

            values = {
                'idx': start_idx + offset,
                'lake_name': lake_name,
                'date': feature_date,
                'lat': lat,
                'lon': lon,
                'volume': props.get('volume', None),
                'apa_value': props.get('apa_value') or props.get('apa', None),
                'depth': props.get('depth', None),
                'description': props.get('description', 'Plant volume data from remote service')
            }
            db.add_row(var.SCHEMA, var.PLANT_VOLUME, values)
        return _render_data_template(var_lang, active_tab='volume',
                                     volume_response=f"Saved {len(features)} plant volume points to database.")
    except Exception as e:
        return _render_data_template(var_lang, active_tab='volume',
                                     volume_response=f"Error saving data: {str(e)}")


@app.route("/newarea/capacitated_aoi", methods=["POST"])
def new_area_capacitated_aoi():
    var_lang = language_utils.get_language_module()

    lake_query = request.form.get('lake_query', '')
    date = request.form.get('date', '')
    harvester_capacity = request.form.get('harvester_capacity', '20')
    n_areas = request.form.get('n_areas', '5')

    if not lake_query or not date:
        return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                               tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                               interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                               description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                               images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                               version=var.version, language_lang=var_lang.LANGUAGE,
                               evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                               english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                               configuration_lang=var_lang.CONFIGURATION,
                               area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                               aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                               aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                               resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                               cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                               n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                               lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                               get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                               capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                               cap_lake_date_options=_get_capacitated_lake_date_options(),
                               aoi=False, capacitated=True,
                               capacitated_response="Please fill out all fields.",
                               cap_lake_value=lake_query, cap_date_value=date,
                               cap_capacity_value=harvester_capacity, cap_n_areas_value=n_areas)

    try:
        # Build volume GeoJSON from database
        volume_geojson = build_volume_geojson(lake_query, date)

        if not volume_geojson.get('features'):
            raise RuntimeError(f"No volume data found in database for {lake_query} on {date}")

        clientid = request.cookies.get('client_id', '')
        instanceid = request.cookies.get('instance_id', '')
        clientsecret = request.cookies.get('client_secret', '')

        payload = {
            "max_volume": float(harvester_capacity),
            "eps": 30,                                      # What ist eps?
            "volume_geojson": volume_geojson,
            "bathymetry_service_url": "http://bathymetry_service:10005/geojson",
            "apa_service_url": "http://apa_index_service:10003/api/get_apa",
            "apa_request_body": {
                "lake_query": lake_query,
                "day": date,
                "instance_id": instanceid,
                "client_id": clientid,
                "client_secret": clientsecret,
                "geojson_file": True,
                "full_apa": False
                },

        }
        resp = requests.post("http://capacitated_aoi_service:10010/get_capacitated_clustering", json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            aoi_result = json.dumps(data)
            # Count unique clusters from features (cluster_id property)
            if 'features' in data:
                cluster_ids = set()
                for feature in data['features']:
                    props = feature.get('properties', {})
                    cluster_id = props.get('cluster_id')
                    if cluster_id is not None:
                        cluster_ids.add(cluster_id)
                num_areas = len(cluster_ids) if cluster_ids else len(data['features'])
            else:
                num_areas = len(data.get('areas', []))
            capacitated_response = f"Found {num_areas} capacitated areas of interest."
        else:
            aoi_result = None
            capacitated_response = f"Error: {resp.status_code} - {resp.text}"
    except (requests.ConnectionError, requests.Timeout) as e:
        aoi_result = None
        capacitated_response = f"Connection error: {str(e)}"

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           cap_lake_date_options=_get_capacitated_lake_date_options(),
                           aoi=False, capacitated=True,
                           capacitated_response=capacitated_response,
                           capacitated_result=aoi_result,
                           capacitated_save_data=aoi_result,
                           cap_lake_value=lake_query, cap_date_value=date,
                           cap_capacity_value=harvester_capacity, cap_n_areas_value=n_areas)


@app.route("/newarea/capacitated_aoi/save", methods=["POST"])
def new_area_capacitated_aoi_save():
    """Save capacitated AOIs to the database."""
    var_lang = language_utils.get_language_module()

    save_data = request.form.get('save_data', '{}')
    lake_name = request.form.get('lake_name', '')
    form_date = request.form.get('date', '')
    harvester_capacity = request.form.get('harvester_capacity', '')

    try:
        data = json.loads(save_data)
        features = data.get('features', [])

        # Group features by cluster_id
        clusters = {}
        for feature in features:
            props = feature.get('properties', {})
            cluster_id = props.get('cluster_id')
            if cluster_id is not None:
                if cluster_id not in clusters:
                    clusters[cluster_id] = {
                        'features': [],
                        'total_volume': props.get('cluster_total_volume', 0),
                        'valid': props.get('cluster_valid', True)
                    }
                clusters[cluster_id]['features'].append(feature)

        saved_count = 0
        for cluster_id, cluster_data in clusters.items():
            # Skip invalid clusters
            if not cluster_data['valid']:
                continue

            # Collect all coordinates from cluster features to create a MultiPolygon
            all_coords = []
            for feature in cluster_data['features']:
                geom = feature.get('geometry', {})
                if geom.get('type') == 'MultiPolygon':
                    all_coords.extend(geom.get('coordinates', []))
                elif geom.get('type') == 'Polygon':
                    all_coords.append(geom.get('coordinates', []))

            if not all_coords:
                continue

            # Get next ID
            id_data = db.get_max_id(var.SCHEMA, var.AREA) + 1

            # Create a single polygon from the first feature's coordinates for simplicity
            # Or use the centroid approach
            first_feature = cluster_data['features'][0]
            first_geom = first_feature.get('geometry', {})
            coords = first_geom.get('coordinates', [[]])[0]
            if isinstance(coords[0][0], list):
                coords = coords[0]

            # Format coordinates for PostGIS
            polygon_coords = [(c[0], c[1]) for c in coords]
            polygon_coords.append(polygon_coords[0])  # Close polygon
            polygon = db.convert_to_geostr(var.Geometry.POLYGON.name, polygon_coords)

            # Add to area table with capacitated metadata
            area_values = {
                'idx': str(id_data),
                'type': "interest",
                'date': form_date,
                'description': f"Capacitated AOI Cluster {cluster_id}",
                'image_path': None,
                'is_capacitated': True,
                'lake_name': lake_name,
                'cluster_id': int(cluster_id),
                'cluster_total_volume': float(cluster_data['total_volume']) if cluster_data['total_volume'] else None,
                'harvester_capacity': float(harvester_capacity) if harvester_capacity else None
            }
            db.add_row(var.SCHEMA, var.AREA, area_values)

            # Add geometry
            geom_values = {
                'idx': str(id_data),
                'geom': polygon
            }
            db.add_row(var.SCHEMA, var.GEO, geom_values)
            saved_count += 1

        capacitated_response = f"Saved {saved_count} capacitated areas of interest to database."

    except Exception as e:
        capacitated_response = f"Error saving data: {str(e)}"

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           evaluation_lang=var_lang.EVALUATION, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           configuration_lang=var_lang.CONFIGURATION,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           capacitated_aoi_lang=var_lang.CAPACITATED_AOI,
                           cap_lake_date_options=_get_capacitated_lake_date_options(),
                           aoi=False, capacitated=True,
                           capacitated_response=capacitated_response)


@app.route("/newpath/capacitated", methods=["POST"])
def new_path_capacitated():
    var_lang = language_utils.get_language_module()

    date = request.form.get('date', '')
    hours = request.form.get('hours', '2')
    volume = request.form.get('volume', '20')
    harvester_capacity = request.form.get('harvester_capacity', '20')

    try:
        aoi_date_rows = db.select_distinct(var.SCHEMA, var.AREA, 'date')
        aoi_dates = sorted([str(row[0]) for row in aoi_date_rows if row[0] is not None])
    except Exception:
        aoi_dates = []

    if not date:
        return render_template("newpath.html", version=var.version, path=False, approve_map=False,
                               fig="<div></div>", show_error=False, path_var={},
                               submit_manuell_path_response="",
                               add_path_lang=var_lang.ADD_PATH,
                               generate_path_lang=var_lang.GENERATE_PATH, submit_lang=var_lang.SUBMIT,
                               date_lang=var_lang.DATE, path_gen_description_lang=var_lang.PATH_GENERATE_DESCRIPTION,
                               approve_lang=var_lang.APPROVE, approve_all_lang=var_lang.APPROVE_ALL,
                               map_ids_lang=var_lang.MAP_IDS, view_paths_lang=var_lang.VIEW_PATH,
                               new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                               tables_lang=var_lang.TABLES, storage_volume_lang=var_lang.STORAGE_VOLUME,
                               configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                               hours_available_lang=var_lang.HOURSE_AVAILABLE,
                               hours_available_value=hours, storage_volume_value=volume,
                               language_lang=var_lang.LANGUAGE, data_lang=var_lang.DATA,
                               english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                               aoi_dates=aoi_dates, capacitated=True,
                               capacitated_path_lang=var_lang.CAPACITATED_PATH,
                               cap_response="Please fill out all fields.",
                               cap_date_value=date, cap_hours_value=hours,
                               cap_volume_value=volume, cap_capacity_value=harvester_capacity)

    try:
        
        lake_query = "Maschsee, Hannover"
        payload = {
            "date": date,
            "lake_query": lake_query,
        }
        resp_volume = requests.post("http://capacitated_aoi_service:10010/volume", json=payload, timeout=30)


        if resp_volume.status_code != 200:
            raise RuntimeError(f"Volume error: {resp_volume.status_code} - {resp_volume.text}")

        volume_geojson = resp_volume.json()

        clientid = request.cookies.get('client_id', '')
        instanceid = request.cookies.get('instance_id', '')
        clientsecret = request.cookies.get('client_secret', '')
    
        payload = {
            "max_volume": float(harvester_capacity),
            "eps": 30,                                      # What ist eps?
            "volume_geojson": volume_geojson,
            "bathymetry_service_url": "http://bathymetry_service:10005/geojson",
            "apa_service_url": "http://apa_index_service:10003/api/get_apa",
            "apa_request_body": {
                "lake_query": lake_query,
                "day": date,
                "instance_id": instanceid,
                "client_id": clientid,
                "client_secret": clientsecret,
                "geojson_file": True,
                "full_apa": False
                },

        }
        resp_capacitated_clustering = requests.post("http://capacitated_aoi_service:10010/get_capacitated_clustering", json=payload, timeout=30)
        if resp_capacitated_clustering.status_code == 200:
            clustered_geojson = resp_capacitated_clustering.json()
        else:
            raise RuntimeError(f"Volume error: {resp_capacitated_clustering.status_code} - {resp_capacitated_clustering.text}")

        cvrp_payload = {
            "cluster_json": clustered_geojson,
            "mode": "serpentine",
            # "row_spacing": 5
        }

        resp = requests.post("http://capacitated_path_service:10011/cvrp", json=cvrp_payload, timeout=30)
        if resp.status_code == 200:
            try:
                data = resp.json()  # sollte klappen, obwohl FileResponse
            except ValueError:
                data = json.loads(resp.content.decode("utf-8"))

            features = data.get('features', [])
            meta = data.get('metadata', {}) or {}
            n_features = len(features)
            total_km = None
            if isinstance(meta.get('total_distance'), (int, float)):
                # dein Beispielwert sieht nach km aus – sonst hier evtl. Umrechnung ergänzen
                total_km = meta['total_distance']

            cap_result = json.dumps(data) if n_features > 0 else None
            if n_features > 0:
                if total_km is not None:
                    cap_response = f"Generated {n_features} path features (≈ {total_km:.2f} km)."
                else:
                    cap_response = f"Generated {n_features} path features."
            else:
                cap_response = "No paths could be generated for this configuration."

        else:
            cap_result = None
            cap_response = f"Error: {resp.status_code} - {resp.text}"

    except (requests.ConnectionError, requests.Timeout) as e:
        cap_result = None
        cap_response = f"Connection error: {str(e)}"


    return render_template("newpath.html", version=var.version, path=False, approve_map=False,
                           fig="<div></div>", show_error=False, path_var={},
                           submit_manuell_path_response="",
                           add_path_lang=var_lang.ADD_PATH,
                           generate_path_lang=var_lang.GENERATE_PATH, submit_lang=var_lang.SUBMIT,
                           date_lang=var_lang.DATE, path_gen_description_lang=var_lang.PATH_GENERATE_DESCRIPTION,
                           approve_lang=var_lang.APPROVE, approve_all_lang=var_lang.APPROVE_ALL,
                           map_ids_lang=var_lang.MAP_IDS, view_paths_lang=var_lang.VIEW_PATH,
                           new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, storage_volume_lang=var_lang.STORAGE_VOLUME,
                           configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
                           hours_available_lang=var_lang.HOURSE_AVAILABLE,
                           hours_available_value=hours, storage_volume_value=volume,
                           language_lang=var_lang.LANGUAGE, data_lang=var_lang.DATA,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           aoi_dates=aoi_dates, capacitated=True,
                           capacitated_path_lang=var_lang.CAPACITATED_PATH,
                           cap_response=cap_response,
                           cap_result=cap_result,
                        #    cap_result=cap_result,
                           cap_date_value=date, cap_hours_value=hours,
                           cap_volume_value=volume, cap_capacity_value=harvester_capacity)



@app.route("/newpath/save", methods=["POST"])
def new_path_save():
    """Save generated harvester paths as a .geojson file (no DB)."""

    var_lang = language_utils.get_language_module()

    save_data = request.form.get('save_data', '{}')
    form_date = request.form.get('date', '')
    harvester_capacity = request.form.get('harvester_capacity', '')

    try:
        data = json.loads(save_data)

        # file name
        date_str = form_date.replace(" ", "_").replace("/", "-")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        save_dir = "/geojsonfiles/paths"
        os.makedirs(save_dir, exist_ok=True)

        filename = f"paths_{date_str}_{ts}.geojson"
        filepath = os.path.join(save_dir, filename)

        # Save File
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        save_message = f"Saved {len(data.get('features', []))} paths to file: {filename}"

    except Exception as e:
        save_message = f"Error saving paths: {str(e)}"

    return render_template(
        "newpath.html",
        version=var.version,
        add_path_lang=var_lang.ADD_PATH,
        generate_path_lang=var_lang.GENERATE_PATH, submit_lang=var_lang.SUBMIT,
        date_lang=var_lang.DATE, path_gen_description_lang=var_lang.PATH_GENERATE_DESCRIPTION,
        approve_lang=var_lang.APPROVE, approve_all_lang=var_lang.APPROVE_ALL,
        map_ids_lang=var_lang.MAP_IDS, view_paths_lang=var_lang.VIEW_PATH,
        new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
        tables_lang=var_lang.TABLES, storage_volume_lang=var_lang.STORAGE_VOLUME,
        configuration_lang=var_lang.CONFIGURATION, evaluation_lang=var_lang.EVALUATION,
        hours_available_lang=var_lang.HOURSE_AVAILABLE,
        language_lang=var_lang.LANGUAGE, data_lang=var_lang.DATA,
        english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
        capacitated_path_lang=var_lang.CAPACITATED_PATH,
        path=False,
        capacitated=True,
        cap_response=save_message,
    )


@app.route("/newpath/download", methods=["POST"])
def new_path_download():
    """Save generated harvester paths as a .geojson file (no DB)."""

    var_lang = language_utils.get_language_module()

    save_data = request.form.get('save_data', '{}')
    form_date = request.form.get('date', '')
    harvester_capacity = request.form.get('harvester_capacity', '')

    try:
        data = json.loads(save_data)

        # file name
        date_str = form_date.replace(" ", "_").replace("/", "-")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        save_dir = "/geojsonfiles/paths"
        os.makedirs(save_dir, exist_ok=True)

        filename = f"paths_{date_str}_{ts}.geojson"
        filepath = os.path.join(save_dir, filename)

        save_message = f"Saved {len(data.get('features', []))} paths to file: {filename}"

        json_data = json.dumps(data)
        buffer = io.BytesIO()
        buffer.write(json_data.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='daten.json',
            mimetype='application/json'
        )

    except Exception as e:
        save_message = f"Error saving paths: {str(e)}"



@app.route("/tables/<action>/<typ>", methods=["GET", "POST"])
def table_view(action, typ):
    var_lang = language_utils.get_language_module()

    # ---- Area ----
    area = {
        'df': db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS),
        'editable_cols': ['date', 'type', 'description'],
        'hidden_cols': [],
        'type': var.AREA
    }

    # ---- PATH RAW (alle Punkte, editierbar) ----
    path_raw_df = db.open_table(var.SCHEMA, var.PATH, var.PATH_COLS)

    # Datum in Strings umwandeln (robust)
    if 'date' in path_raw_df.columns and not pd.api.types.is_string_dtype(path_raw_df['date']):
        path_raw_df['date'] = path_raw_df['date'].astype(str)

    path_raw = {
        'df': path_raw_df,
        'editable_cols': ['date'],      # Nur RAW ist editierbar!
        'hidden_cols': ['path_id'],     # Pfad-ID hier verstecken
        'type': var.PATH_RAW            # Wichtig: neuer Typ!
    }

    # ---- PATH SUMMARY (eine Zeile pro path_id) ----
    if not path_raw_df.empty:
        path_summary_df = (
            path_raw_df.groupby('path_id', as_index=False)
                    .agg(points=('idx', 'count'),
                            date=('date', 'first'))
        )
    else:
        path_summary_df = pd.DataFrame(columns=['path_id', 'points', 'date'])

    path = {
        'df': path_summary_df,
        'editable_cols': [],   # Summary ist NICHT editierbar
        'hidden_cols': [],
        'type': var.PATH       # Der Typ bleibt var.PATH
    }

    # ---- Trajectory: nur noch Tages-Übersicht (date + start_ts + end_ts) ----

    TRAJ_OBJ = {
        'editable_cols': [],  
        'hidden_cols': [],     # keine Spalten verstecken
        'type': var.TRAJ,
        'max_rows': 100,
        'filter': 0
    }

    # komplette Tabelle laden
    dfs = db.open_table(var.SCHEMA, var.traj, var.TRAJ_COLS)

    # defensive Normalisierung
    if 'date' in dfs.columns:
        dfs['date'] = dfs['date'].astype(str)
    else:
        dfs['date'] = pd.Series(dtype=str)

    # wenn Daten vorhanden → Gruppierung nach Datum
    if 'timestamp' in dfs.columns and not dfs.empty:
        grouped = (
            dfs.groupby('date', as_index=False)['timestamp']
            .agg(start_ts='min', end_ts='max')
        )
        grouped = grouped.sort_values('date', ascending=False, ignore_index=True)
    else:
        grouped = pd.DataFrame(columns=['date', 'start_ts', 'end_ts'])

    # Ausgabeobjekt
    TRAJ_OBJ['dfs'] = grouped      # nur diese Übersichtstabelle anzeigen
    TRAJ_OBJ['df'] = grouped       # build_table(traj) benutzt dieses Feld
    TRAJ_OBJ['dates'] = grouped.to_dict(orient='records')  # optional verfügbar

    # verfügbare Importdaten bleiben
    try:
        folder_names = sorted([
            o for o in os.listdir(var.VID_FILE_PATH)
            if os.path.isdir(os.path.join(var.VID_FILE_PATH, o))
        ])
        bag_folder_names = []
        for folder_name in folder_names:
            folder_path = os.path.join(var.VID_FILE_PATH, folder_name)
            files_in_folder = os.listdir(folder_path)
            bag_files = [f for f in files_in_folder if f.endswith('.bag')]
            if bag_files:
                bag_folder_names.append(folder_name)
        TRAJ_OBJ['available_dates'] = bag_folder_names
    except Exception:
        TRAJ_OBJ['available_dates'] = []

    # ---- APA Data (summary per date) ----
    apa_raw_df = db.open_table(var.SCHEMA, var.APA_INDEX, var.APA_INDEX_COLS)

    if not apa_raw_df.empty and 'date' in apa_raw_df.columns:
        if not pd.api.types.is_string_dtype(apa_raw_df['date']):
            apa_raw_df['date'] = apa_raw_df['date'].astype(str)
        if 'apa_value' in apa_raw_df.columns:
            apa_raw_df['apa_value'] = pd.to_numeric(apa_raw_df['apa_value'], errors='coerce')
        apa_summary_df = (
            apa_raw_df.groupby(['lake_name', 'date'], as_index=False)
                      .agg(
                          data_points=('apa_value', 'count'),
                          mean_apa=('apa_value', 'mean'),
                          min_apa=('apa_value', 'min'),
                          max_apa=('apa_value', 'max')
                      )
        )
        apa_summary_df['mean_apa'] = apa_summary_df['mean_apa'].round(4)
        apa_summary_df['min_apa'] = apa_summary_df['min_apa'].round(4)
        apa_summary_df['max_apa'] = apa_summary_df['max_apa'].round(4)
        apa_summary_df = apa_summary_df.sort_values('date', ascending=False, ignore_index=True)
    else:
        apa_summary_df = pd.DataFrame(columns=['lake_name', 'date', 'data_points', 'mean_apa', 'min_apa', 'max_apa'])

    apa_data = {
        'df': apa_summary_df,
        'editable_cols': [],
        'hidden_cols': [],
        'type': var.APA_INDEX
    }

    # ---- Bathymetry Data (summary per lake) ----
    bathy_raw_df = db.open_table(var.SCHEMA, var.BATHYMETRY, var.BATHYMETRY_COLS)

    if not bathy_raw_df.empty and 'lake_name' in bathy_raw_df.columns:
        if 'date' in bathy_raw_df.columns and not pd.api.types.is_string_dtype(bathy_raw_df['date']):
            bathy_raw_df['date'] = bathy_raw_df['date'].astype(str)
        if 'depth' in bathy_raw_df.columns:
            bathy_raw_df['depth'] = pd.to_numeric(bathy_raw_df['depth'], errors='coerce')
        bathy_summary_df = (
            bathy_raw_df.groupby('lake_name', as_index=False)
                        .agg(
                            data_points=('depth', 'count'),
                            mean_depth=('depth', 'mean'),
                            min_depth=('depth', 'min'),
                            max_depth=('depth', 'max')
                        )
        )
        bathy_summary_df['mean_depth'] = bathy_summary_df['mean_depth'].round(4)
        bathy_summary_df['min_depth'] = bathy_summary_df['min_depth'].round(4)
        bathy_summary_df['max_depth'] = bathy_summary_df['max_depth'].round(4)
    else:
        bathy_summary_df = pd.DataFrame(columns=['lake_name', 'data_points', 'mean_depth', 'min_depth', 'max_depth'])

    bathymetry_data = {
        'df': bathy_summary_df,
        'editable_cols': [],
        'hidden_cols': [],
        'type': var.BATHYMETRY
    }

    # ---- Volume Data (summary per lake+date) ----
    vol_raw_df = db.open_table(var.SCHEMA, var.PLANT_VOLUME, var.PLANT_VOLUME_COLS)

    if not vol_raw_df.empty and 'lake_name' in vol_raw_df.columns:
        if 'date' in vol_raw_df.columns and not pd.api.types.is_string_dtype(vol_raw_df['date']):
            vol_raw_df['date'] = vol_raw_df['date'].astype(str)
        if 'volume' in vol_raw_df.columns:
            vol_raw_df['volume'] = pd.to_numeric(vol_raw_df['volume'], errors='coerce')
        if 'apa_value' in vol_raw_df.columns:
            vol_raw_df['apa_value'] = pd.to_numeric(vol_raw_df['apa_value'], errors='coerce')
        if 'depth' in vol_raw_df.columns:
            vol_raw_df['depth'] = pd.to_numeric(vol_raw_df['depth'], errors='coerce')
        vol_summary_df = (
            vol_raw_df.groupby(['lake_name', 'date'], as_index=False)
                      .agg(
                          data_points=('volume', 'count'),
                          total_volume=('volume', 'sum'),
                          mean_volume=('volume', 'mean'),
                          mean_apa=('apa_value', 'mean'),
                          mean_depth=('depth', 'mean')
                      )
        )
        vol_summary_df['total_volume'] = vol_summary_df['total_volume'].round(4)
        vol_summary_df['mean_volume'] = vol_summary_df['mean_volume'].round(4)
        vol_summary_df['mean_apa'] = vol_summary_df['mean_apa'].round(4)
        vol_summary_df['mean_depth'] = vol_summary_df['mean_depth'].round(4)
        vol_summary_df = vol_summary_df.sort_values('date', ascending=False, ignore_index=True)
    else:
        vol_summary_df = pd.DataFrame(columns=['lake_name', 'date', 'data_points', 'total_volume', 'mean_volume', 'mean_apa', 'mean_depth'])

    volume_data = {
        'df': vol_summary_df,
        'editable_cols': [],
        'hidden_cols': [],
        'type': var.PLANT_VOLUME
    }

    # ---- GET → Ansicht rendern ----
    if request.method == "GET":
        req_filter = request.args.get('filter', default=0, type=int)
        TRAJ_OBJ['filter'] = abs(req_filter) + 1

        return render_template(
            "tables.html",
            version=var.version,
            area=area,
            path=path,
            path_raw=path_raw,
            traj=TRAJ_OBJ,
            apa_data=apa_data,
            bathymetry_data=bathymetry_data,
            volume_data=volume_data,
            tab=typ,
            new_area_lang=var_lang.NEW_AREA,
            new_path_lang=var_lang.NEW_PATH,
            tables_lang=var_lang.TABLES,
            area_lang=var_lang.AREA,
            path_lang=var_lang.PATH,
            path_raw_lang=var_lang.PATH_RAW,
            trajectory_lang=var_lang.TRAJECTORY,
            apa_data_lang=var_lang.APA_DATA,
            bathymetry_data_lang=var_lang.BATHYMETRY_DATA,
            volume_data_lang=var_lang.PLANT_VOLUME_DATA,
            save_all_lang=var_lang.SAVE_ALL,
            add_area_lang=var_lang.ADD_AREA,
            delete_lang=var_lang.DELETE,
            evaluation_lang=var_lang.EVALUATION,
            data_lang=var_lang.DATA,
            add_path_lang=var_lang.ADD_PATH,
            cells_double_clicked_lang=var_lang.CELLS_DOUBLE_CLICKED,
            language_lang=var_lang.LANGUAGE,
            english_lang=var_lang.ENGLISH,
            configuration_lang=var_lang.CONFIGURATION,
            german_lang=var_lang.GERMAN
        )

    # ---- POST → Speichern/Löschen ----
    if request.method == "POST":
        data = request.get_json()
        # Richtige Tabelle anhand von 'typ' wählen
        if typ == var.AREA:
            data_table = area['df']
            current_table = var.AREA

        elif typ == var.PATH:
            data_table = path['df']         # SUMMARY
            current_table = var.PATH

        elif typ == var.PATH_RAW:
            data_table = path_raw['df']     # RAW POINTS
            current_table = var.PATH

        elif typ == var.TRAJ:
            data_table = TRAJ_OBJ['df']     # SUMMARY
            current_table = var.traj

        elif typ == var.APA_INDEX:
            data_table = apa_data['df']
            current_table = var.APA_INDEX

        elif typ == var.BATHYMETRY:
            data_table = bathymetry_data['df']
            current_table = var.BATHYMETRY

        elif typ == var.PLANT_VOLUME:
            data_table = volume_data['df']
            current_table = var.PLANT_VOLUME

        identifier = 'idx'

        if action == var.SAVE:
            if typ == var.AREA or typ == var.PATH_RAW:
                # update changed values in table
                for key, value in data.items():
                    row = int(key)
                    id_col = data_table.columns.get_loc(identifier)
                    id_val = data_table.iloc[row, id_col]
                    id_val = int(id_val) if (typ == var.AREA or typ == var.traj) else str(id_val)
                    db.update_table(var.SCHEMA, current_table, value, (identifier, id_val))

        if action == var.DELETE:
            for row in data:
                row = int(row)

                # --- Special case: Trajectory summary (delete by date) ---
                if typ == var.TRAJ:
                    # date aus der angezeigten Tabelle holen
                    date_val = data_table.iloc[row]['date']
                    db.delete_row(var.SCHEMA, current_table, ('date', date_val))

                # --- PATH SUMMARY: delete all points with this path_id ---
                elif typ == var.PATH:
                    path_id_val = int(data_table.iloc[row]['path_id'])
                    db.delete_row(var.SCHEMA, current_table, ('path_id', path_id_val))

                # --- APA/Bathymetry/Volume: delete by lake_name + date ---
                elif typ in (var.APA_INDEX, var.BATHYMETRY, var.PLANT_VOLUME):
                    lake_name = data_table.iloc[row]['lake_name']
                    date_val = data_table.iloc[row].get('date', None)
                    # Convert string "None" to actual None (from pandas .astype(str))
                    if date_val in (None, 'None', 'NaT', ''):
                        date_val = None
                    # Delete all rows matching lake_name (and date if available)
                    if date_val:
                        db.delete_rows_by_lake_date(var.SCHEMA, current_table, lake_name, date_val)
                    else:
                        db.delete_rows_by_lake(var.SCHEMA, current_table, lake_name)

                else:
                    # --- Default case for AREA and PATH unchanged ---
                    id_col = data_table.columns.get_loc(identifier)
                    id_val = (
                        str(data_table.iloc[row, id_col])
                        if typ == var.PATH_RAW
                        else int(data_table.iloc[row, id_col])
                    )
                    db.delete_row(var.SCHEMA, current_table, (identifier, id_val))


        # Better: Redirect back to the view URL (otherwise F5 -> Form Resubmission)
        page_url = f"/tables/view/{typ}"
        return {'success': 200, 'redirect': page_url}
