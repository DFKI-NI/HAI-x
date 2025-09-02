"""Routes for parent Flask app."""
import ast
import json
from ast import literal_eval
from datetime import datetime
import logging
import numpy

import pandas as pd
import requests
from flask import render_template, request, current_app as app, session, jsonify

from utils import route_util as util, generate_path_script
from utils import variables as var, dash_util as dutil, language_utils
from utils.database import database as db
from .new_area import add_single_new_area_to_db, visualize_areas_of_interest, save_date_file, get_possible_satellite_fly_overs

DATES_FILE_NAME_PREFIX = "./static/data/dates_of_fly_overs_for-"
DEFAULT_DATES_FILE_NAME = DATES_FILE_NAME_PREFIX + "Maschsee,Hannover,Germany"

TRAJ_OBJ = {
    'editable_cols': [],
    'hidden_cols': ['date'],
    'type': var.TRAJ,
    'max_rows': 100,
    'filter': 0
}


@app.route("/newarea", methods=["GET"])
def new_area():
    """New Area"""
    var_lang = language_utils.get_language_module()

    #available_dates_file = DEFAULT_DATES_FILE_NAME
    #save_date_file(available_dates_file)
    available_dates = get_possible_satellite_fly_overs()['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    # with open(available_dates_file, 'w') as f:
    #     available_dates = json.load(f)['available_dates']

    return render_template("newarea.html", new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                           tables_lang=var_lang.TABLES, toa_lang=var_lang.TOA, avoid_lang=var_lang.AVOID,
                           interest_lang=var_lang.INTEREST, chose_lang=var_lang.CHOSE,
                           description_lang=var_lang.DESCRIPTION, date_lang=var_lang.DATE,
                           images_lang=var_lang.IMAGES, submit_lang=var_lang.SUBMIT,
                           version=var.version, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN,
                           area_lang=var_lang.AREA, add_area_lang=var_lang.ADD_AREA,
                           aoi_area_lang=var_lang.NEW_AREA_SITE["aoi_area"],
                           aoi_description_lang=var_lang.NEW_AREA_SITE["aoi_description"],
                           resolution_lang=var_lang.NEW_AREA_SITE["resolution"],
                           cloud_coverage_lang=var_lang.NEW_AREA_SITE["cloud_coverage"],
                           n_areas_lang=var_lang.NEW_AREA_SITE["n_areas"],
                           lake_query_lang=var_lang.NEW_AREA_SITE["lake_query"],
                           get_aoi_lang=var_lang.NEW_AREA_SITE["get_aoi"],
                           aoi=False,
                           resolution_value="10",
                           cloud_coverage_value="0.1",
                           n_areas_value="5",
                           lake_query_value="",
                           available_dates=available_dates)

@app.route("/newarea/add", methods=["POST"])
def new_area_add():
    """Add New Area"""
    var_lang = language_utils.get_language_module()
    return add_single_new_area_to_db(request, var_lang)

@app.route("/newarea/get_aois", methods=["POST"])
def new_area_get_aois():
    """Get Areas of Interest"""
    var_lang = language_utils.get_language_module()

    request_dict = {
        'day': request.form.getlist('aoi_date')[0],
        'resolution_in_m': float(request.form.getlist('resolution')[0]),
        'cloud_coverage': float(request.form.getlist('cloud_coverage')[0]),
        'n_areas': int(request.form.getlist('n_areas')[0]),
        'lake_query': request.form.getlist('lake_query')[0],
    }

    # if request_dict['lake_query'] == "":
    # available_dates_file = DEFAULT_DATES_FILE_NAME
    # else:
    #     available_dates_file = DATES_FILE_NAME_PREFIX + request_dict['lake_query'].replace(" ", "")
    # save_date_file(available_dates_file)

    # with open(available_dates_file, 'r') as f:
    #     available_dates = json.load(f)['available_dates']

    available_dates = get_possible_satellite_fly_overs(request_dict)['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates

    return visualize_areas_of_interest(request_dict, var_lang, available_dates=available_dates)


@app.route("/newarea/save_aois", methods=["POST"])
def new_area_save_aois():
    var_lang = language_utils.get_language_module()
    available_dates = get_possible_satellite_fly_overs()['available_dates']
    available_dates = available_dates[-10:] if len(available_dates) >= 10 else available_dates
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
                                       german_lang=var_lang.GERMAN, new_area_lang=var_lang.NEW_AREA,
                                       new_path_lang=var_lang.NEW_PATH)

            polyline_data = request.form.get('polylineData')
            cordpairs_list = ast.literal_eval(polyline_data)

            number_polyliness = len(cordpairs_list)

            if number_polyliness < 1:
                submit_manuell_path_response = "cannot submit, missing arguments. Please fill out all fields."
                return render_template("newpath.html", version=var.version, path=add, approve_map=approve_map, fig=fig,
                                       show_error=show_error, submit_manuell_path_response=submit_manuell_path_response,
                                       area_lang=var_lang.AREA, path_lang=var_lang.PATH, tables_lang=var_lang.TABLES,
                                       language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH,
                                       german_lang=var_lang.GERMAN, new_area_lang=var_lang.NEW_AREA,
                                       new_path_lang=var_lang.NEW_PATH)

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
                    # fig = generate_path_script.pathplanning3(date.strftime('%Y-%m-%d'), available_hours, volume)
                    fig = generate_path_script.draw_map2(paths, aoi_dict)
                    fig = fig.to_html(full_html=False)
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
                           hours_available_lang=var_lang.HOURSE_AVAILABLE, hours_available_value=hav, storage_volume_value=svv, language_lang=var_lang.LANGUAGE,
                           english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN)


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

@app.route("/changelog", methods=["GET"])
def changelog():
    var_lang = language_utils.get_language_module()
    return render_template("changelog.html", version=var.version, new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH, tables_lang=var_lang.TABLES, language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN)
"""


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


@app.route("/tables/<action>/<typ>", methods=["GET", "POST"])
def table_view(action, typ):
    var_lang = language_utils.get_language_module()

    area = {
        'df': db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS),
        'editable_cols': ['date', 'type', 'description'],
        'hidden_cols': [],
        'type': var.AREA
    }
    path = {
        'df': db.open_table(var.SCHEMA, var.PATH, var.PATH_COLS),
        'editable_cols': ['date'],
        'hidden_cols': ['path_id'],
        'type': var.PATH
    }
    TRAJ_OBJ = {
        'editable_cols': [],
        'hidden_cols': ['date'],
        'type': var.TRAJ,
        'max_rows': 100,
        'filter': 0
    }

    # read full trajectory database just once, then save to a pandas dataframe in a global variable
    if len(util.contains_keys(['dfs'], TRAJ_OBJ)) == 0:
        TRAJ_OBJ['dfs'] = db.open_table(var.SCHEMA, var.traj, var.TRAJ_COLS)
        TRAJ_OBJ['dfs']['date'] = TRAJ_OBJ['dfs']['date'].astype(str)
        TRAJ_OBJ['dates'] = [date[0].strftime('%Y-%m-%d') for date in db.select_distinct(var.SCHEMA, var.traj, 'date')]
    req_date = request.args.get('date', default=TRAJ_OBJ['dates'][0], type=str)
    try:
        dfs = TRAJ_OBJ['dfs']
        df = dfs[dfs['date'] == req_date]
    except KeyError:
        df = None
        req_date = TRAJ_OBJ['dates'][0]
    TRAJ_OBJ['df'] = df
    TRAJ_OBJ['req_date'] = req_date
    # if all rows in current dataframe have no values for the 'mowed_grass' column then hide that column
    if TRAJ_OBJ['df']['mowed_grass'].isna().sum() == len(df.index):
        TRAJ_OBJ['hidden_cols'].append('mowed_grass')

    if request.method == "GET":
        # view tables
        req_filter = request.args.get('filter', default=0, type=int)
        TRAJ_OBJ['filter'] = abs(req_filter) + 1
        return render_template("tables.html", version=var.version, area=area, path=path, traj=TRAJ_OBJ, tab=typ,
                               new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                               tables_lang=var_lang.TABLES, area_lang=var_lang.AREA, path_lang=var_lang.PATH,
                               trajectory_lang=var_lang.TRAJECTORY, save_all_lang=var_lang.SAVE_ALL,
                               add_area_lang=var_lang.ADD_AREA, delete_lang=var_lang.DELETE,
                               add_path_lang=var_lang.ADD_PATH, cells_double_clicked_lang=var_lang.CELLS_DOUBLE_CLICKED,
                               language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH,
                               german_lang=var_lang.GERMAN)

    if request.method == "POST":
        data = request.get_json()
        data_table = area['df'] if typ == var.AREA else path['df'] if typ == var.PATH else TRAJ_OBJ['dfs']
        current_table = var.AREA if typ == var.AREA else var.PATH if typ == var.PATH else var.traj
        identifier = 'idx'

        if action == var.SAVE:
            # update changed values in table
            for key, value in data.items():
                row = int(key)
                id_col = data_table.columns.get_loc(identifier)
                id = data_table.iloc[row, id_col]
                id = int(id) if typ == var.AREA or typ == var.traj else str(id)
                db.update_table(var.SCHEMA, current_table, value, (identifier, id))

        if action == var.DELETE:
            for row in data:
                # delete row from table
                row = int(row)
                id_col = data_table.columns.get_loc(identifier)
                id = str(data_table.iloc[row, id_col]) if typ == var.PATH else int(data_table.iloc[row, id_col])
                db.delete_row(var.SCHEMA, current_table, (identifier, id))
        page_url = '/tables/view/' + typ
        # return {'success': 200, 'redirect': page_url}
        return render_template('/tables/view/' + typ, version=var.version, area=area, path=path, traj=TRAJ_OBJ, tab=typ,
                               new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH,
                               tables_lang=var_lang.TABLES, area_lang=var_lang.AREA, path_lang=var_lang.PATH,
                               trajectory_lang=var_lang.TRAJECTORY, save_all_lang=var_lang.SAVE_ALL,
                               add_area_lang=var_lang.ADD_AREA, delete_lang=var_lang.DELETE,
                               add_path_lang=var_lang.ADD_PATH, cells_double_clicked_lang=var_lang.CELLS_DOUBLE_CLICKED)
