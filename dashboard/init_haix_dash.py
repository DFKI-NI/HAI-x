from flask import url_for
import dash
from dash import dcc, html, Output, Input, State, ctx
from dash.exceptions import PreventUpdate
import dash_player
import dash_bootstrap_components as dbc
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objs as go
import numpy as np
import os
import ast
from utils import variables as var, dash_util as util, language_utils
from utils.database import database as db
from .layout import init_layout
import pathlib
from flask.helpers import get_root_path

import logging
import geopy.distance

## Local imports:
from .sonar_ui import get_sonar_section
from .sonar_callbacks import register_sonar_callbacks


def init_haix_dash(dash_app):
    # create dash layout
    dash_app.index_string = init_layout(
        pathlib.Path(get_root_path(__name__)).joinpath("../templates").joinpath("dash.html")
    )

    var_lang = language_utils.get_language_module()

    date_choices = util.format_dates()

    dash_app.layout = dbc.Container([
        dcc.Store(id='click-storage'),
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(date_choices, id="dropdown-choice", placeholder="Select dates", multi=True),
                dcc.Location(id="url", refresh=True),
                dbc.Checklist(
                    [{"label":var_lang.AVOID, "value":var.AVOID}, {"label":var_lang.INTEREST, "value":var.INTEREST}, {"label":var_lang.TRAJECTORY, "value":var.TRAJECTORY}, {"label":var_lang.PATH, "value":var.PATH_PLANNING}],
                    [var.AVOID, var.INTEREST],
                    inline=True,
                    id="choices"
                ),
                dcc.Graph(figure={}, id='map-viz', style={'height': '60vh'}, config={'scrollZoom': True}),
            ], width=12, lg=6, className="g-0"),
            dbc.Col([
                html.B("Click area on map to see information below"),
                html.Div(id="click-info-output", className="mb-3"),
                html.Div(id="Test")
            ], width=12, lg=6)
        ]),
    ], fluid=True)


    init_callbacks(dash_app)

    return dash_app.server

def init_callbacks(app):
    @app.callback(
        Output(component_id="dropdown-choice", component_property="options"),
        Input(component_id='dropdown-choice', component_property='value')
    )
    def update_choices(choice):
        return util.format_dates()


    @app.callback(
        Output(component_id='map-viz', component_property='figure'),
        Input(component_id='dropdown-choice', component_property='value'),
        Input(component_id='choices', component_property='value')
    )
    def update_graph(days_chosen, type_chosen):
        days_chosen = util.clean_dates(days_chosen)

        df = db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS)
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['type'].isin(type_chosen)]
        df = df[df['date'].isin(days_chosen)]
        df = util.add_has_images_col(df)
        df['idx'] = df['idx'].astype(str)

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
            range_color=[0, 6500],
            custom_data=['type', 'idx', 'date', 'description', 'has_images'])
        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig.update_traces(hovertemplate='<b>type</b>: %{customdata[0]}<br>' +
                                        '<b>id</b>: %{customdata[1]}<br>' +
                                        '<b>date</b>: %{customdata[2]}<br>' +
                                        '<b>description</b>: %{customdata[3]}<br>' +
                                        '<b>satellite images</b>: %{customdata[4]}')

        if var.TRAJECTORY in type_chosen:
            days = tuple([d.strftime('%Y-%m-%d') for d in days_chosen])

            if len(days) != 0:
                trajectory = db.open_table(var.SCHEMA, var.traj, var.TRAJ_COLS, filter=('date', days))
                trajectory['date'] = pd.to_datetime(trajectory['date'])
                trajec = trajectory.loc[trajectory['date'].isin(days_chosen)]
                for day_chosen in days:
                    dataname = var.maschsee + str(day_chosen)

                    try:
                        lats = trajec["latitude"]
                        lons = trajec["longitude"]

                        if os.path.exists(var.VID_DATA_PATH + dataname + "_color.csv"):
                            has_video = True
                        else:
                            has_video = False

                        trajec["mowed_grass"].fillna(value=0, inplace=True)
                        mow_amount = trajec["mowed_grass"].to_numpy()

                        customdataarray = np.full((len(lats), 3), [var.seekuh, day_chosen, has_video])
                        customdataarray = np.concatenate((customdataarray, trajec['timestamp'].values.reshape(-1, 1)), axis=1)

                        fig.add_scattermapbox(
                            lat=lats,
                            lon=lons,
                            text=trajec["timestamp"],
                            mode='markers',
                            marker=dict(
                                color=mow_amount,
                                colorscale='reds',
                                size=3
                            ),
                            customdata=customdataarray,
                            hovertemplate='%{lat},%{lon}<br>' +
                                        '<b>date</b>: %{customdata[1]}<br>' +
                                        '<b>video</b>: %{customdata[2]}'
                        )
                    except IOError:
                        print("No data for that day")

        if var.PATH_PLANNING in type_chosen:
            path = db.open_table(var.SCHEMA, var.PATH, var.PATH_COLS)
            path['date'] = pd.to_datetime(path['date'])
            path = path[path['date'].isin(days_chosen)]

            for x in path['path_id'].unique():
                subpath = path.loc[path['path_id'] == x]
                date = subpath['date'].values[0]
                data = np.full((len(subpath['lat']), 3), ['path', str(x), np.datetime_as_string(date, unit='D')])
                unique_ids = [[str(n)] for n in subpath.idx]
                data = np.concatenate((data, unique_ids), axis=1)

                subpath['idx'] = subpath['idx'].str.split('-').str[-1].astype(int)
                subpath.sort_values('idx', inplace=True)

                dist = 0
                for x in range(len(subpath) - 1):
                    #logging.info(subpath.iloc[x]['lat'])
                    #logging.info(subpath.iloc[x]['lon'])
                    dist += geopy.distance.geodesic([subpath.iloc[x]['lat'], subpath.iloc[x]['lon']], [subpath.iloc[x + 1]['lat'], subpath.iloc[x + 1]['lon']]).km

                data = np.insert(data, data.shape[1], dist, axis=1)


                fig.add_scattermapbox(
                    lat=subpath.lat,
                    lon=subpath.lon,
                    mode='markers+lines',
                    marker_size=10,
                    customdata=data,
                    hovertemplate='%{lat},%{lon}<br>' +
                                    '<b>path id</b>: %{customdata[1]}<br>' +
                                    '<b>date</b>: %{customdata[2]}<br>' +
                                    '<b>distance</b>: %{customdata[4]}<br>'
                )

        fig.add_scattermapbox(
            lat=[],
            lon=[],
            mode='lines'
        )

        fig.update_layout(showlegend=False)

        return fig
    
    @app.callback(
        Output(component_id='click-info-output', component_property='children', allow_duplicate=True),
        Output(component_id='click-storage', component_property='data'),
        Output(component_id='map-viz', component_property='figure', allow_duplicate=True),
        Input(component_id='map-viz', component_property='clickData'),
        State(component_id='map-viz', component_property='figure'),
        State(component_id='click-info-output', component_property='children'),
        prevent_initial_call=True
    )
    def show_information(clickData, fig, child):
        if clickData is not None:
            if 'customdata' in clickData['points'][0].keys():
                map_info = clickData['points'][0]["customdata"]
                if map_info[0] == var.seekuh:
                    logging.info(clickData['points'][0])
                    informations = util.get_index(float(map_info[3]), map_info[1])
                    lat = clickData['points'][0]['lat']
                    lon = clickData['points'][0]['lon']
                    block = None
                    figure = dash.no_update

                    if informations != 0:
                        area_string = 'Area: (' + str(informations[1]) + ', ' + str(informations[2]) + ', ' + str(
                            informations[3]) + ', ' + str(informations[4]) + ')'

                        if child is not None:
                            # children = child['props']['children']
                            try:
                                video_container = child['props']['children'][0]['props']['children'][1]['props']
                                if video_container['id'] == 'video-container':
                                    block = child
                                    child['props']['children'][0]['props']['children'][2]['props']['children'] = area_string
                            except:
                                block = None

                        if block == None:
                            block = html.Div([])
                            video = html.Div([

                                html.Div([
                                    dbc.Checklist(
                                        [var.VIDEO_RGB, var.VIDEO_IR],
                                        [var.VIDEO_RGB, var.VIDEO_IR],
                                        inline=True,
                                        id='video-choice'
                                    )
                                ]),

                                html.Div(id='video-container'),

                                html.P(area_string)
                            ])
                            block.children.append(video)

                        figure = go.Figure(fig)
                        figure = util.clear_map(figure)
                        data = {
                            'lat': lat,
                            'lon': lon
                        }
                    else:
                        block = html.Div([html.P('Coordinates: (' + str(lat) + ', ' + str(lon) + ')')])
                        data = {
                            'lat': lat,
                            'lon': lon
                        }
                    return block, json.dumps(data), figure
                elif map_info[0] == var.AVOID or map_info[0] == var.INTEREST:
                    # show area info
                    db.convert_to_geojson_file(var.SCHEMA, var.GEO, var.GEO_FILE)
                    with open(var.GEO_FILE, 'r') as file:
                        geojson = json.load(file)
                    id = clickData['points'][0]['location']
                    for area in geojson['features']:
                        if int(id) == area['id']:
                            block = html.Div([
                                html.P('Area: ' + str(id)),
                                html.Span(id="example-output", style={"verticalAlign": "middle"}),
                                html.P('Type: ' + map_info[0]),
                                html.P('Description: ' + map_info[3]),
                                html.P('Coordinates (lat,lon):')
                            ])
                            point_list = html.Ul(children=[])
                            for point in list(area['geometry']['coordinates'][0]):
                                point_list.children.append(html.Li('(' + str(point[1]) + ', ' + str(point[0]) + ')'))
                            block.children.append(point_list)
                            block.children.append(util.add_images(id))
                            
                            sonar_section = get_sonar_section(id)
                            block.children.append(sonar_section)

                            delete_block = html.Div([
                                html.Button('Delete Area',
                                    id='delete_area',
                                    className='btn btn-danger',
                                    **{
                                        'title': 'Permanently delete area from the map'
                                    }),
                                html.Button('Delete Point',
                                    id='delete_point',
                                    className='btn btn-danger mr-2',
                                    style={'display': 'none'}),
                                html.Button('Delete Path',
                                    id='delete_path',
                                    className='btn btn-danger',
                                    style={'display': 'none'})
                            ])
                            block.children.append(delete_block)
                            
                            data = {
                                'id': id,
                                'type': map_info[0]
                            }
                            return block, json.dumps(data), dash.no_update
                else:
                    # show path info
                    lat = clickData['points'][0]['lat']
                    lon = clickData['points'][0]['lon']
                    block = html.Div([
                        html.P('Path: ' + map_info[1]),
                        html.P('Point: ' + map_info[3]),
                        html.P('Coordinates: (' + str(lat) + ', ' + str(lon) + ')'),
                        html.Button('Delete Area',
                            id='delete_area',
                            className='btn btn-danger',
                            style={'display': 'none'}),
                        html.Button('Delete Point',
                            id='delete_point',
                            className='btn btn-danger',
                            style={'margin-right': '10px'},
                            **{
                                'title': 'Permanently delete this point from the path'
                            }),
                        html.Button('Delete Path',
                            id='delete_path',
                            className='btn btn-danger',
                            **{
                                'title': 'Permanently delete entire path from the map'
                            })
                    ])

                    data = {
                        'path_id': map_info[1],
                        'point_id': map_info[3],
                        'lat': lat,
                        'lon': lon
                    }
                    return block, json.dumps(data), dash.no_update
        return html.Div('Area not found')

    @app.callback(
        Output(component_id='click-info-output', component_property='children'),
        Input(component_id='delete_area', component_property='n_clicks'),
        Input(component_id='delete_point', component_property='n_clicks'),
        Input(component_id='delete_path', component_property='n_clicks'),
        Input(component_id='click-storage', component_property='data')
    )
    def delete(area_n_clicks, point_n_clicks, path_n_clicks, storage):
        if area_n_clicks is None and point_n_clicks is None and path_n_clicks is None: 
            # prevents method from calling on page load
            raise PreventUpdate
        else:
            storage = ast.literal_eval(storage)
            if ctx.triggered_id == 'delete_area':
                item = var.AREA.capitalize()
                id = int(storage['id'])
                db.delete_row(var.SCHEMA, var.GEO, ('idx', id))
                db.delete_row(var.SCHEMA, var.AREA, ('idx', id))
            else:
                if ctx.triggered_id == 'delete_point':
                    item = 'Point'
                    id = str(storage['point_id'])
                    db.delete_row(var.SCHEMA, var.PATH, ('idx', id))
                if ctx.triggered_id == 'delete_path':
                    item = 'Path'
                    id = int(storage['path_id'])
                    db.delete_row(var.SCHEMA, var.PATH, ('path_id', id))
            return html.Div('{} {} has been permanently deleted. Update the map or refresh the page to see the changes.'.format(item, str(id)))

    @app.callback(
        Output(component_id='video-container', component_property='children'),
        Input(component_id='video-choice', component_property='value'),
        Input(component_id='map-viz', component_property='clickData'),
        State(component_id='video-container', component_property='children'),
    )
    def videoChanged(videoModeChosen, clickData, children):
        if clickData is None:
            return f"Area not found"
        if 'customdata' not in clickData['points'][0].keys():
            return f"Error"
        
        map_info = clickData['points'][0]["customdata"]

        if map_info[0] != var.seekuh:
            return f"Error"

        information = util.get_index(float(map_info[3]), map_info[1])
        timeColor = util.get_time(float(map_info[3]), map_info[1], 'color')
        timeInfra = util.get_time(float(map_info[3]), map_info[1], 'infra1')

        if information == 0:
            return f"Error"

        # videoname = "movie" + str(information[0]) + ".mp4"
        # videoname = "color_full.mp4"

        video_path_rgb = url_for('static', filename='video/' + var.maschsee + map_info[1] + '/' + var.VIDEO_FILE_NAME_RGB)
        # videoname_ir = videoname.replace('.mp4', '_infra.mp4')
        # videoname_ir = "infra1_full.mp4"
        video_path_ir = url_for('static', filename='video/' + var.maschsee + map_info[1] + '/' + var.VIDEO_FILE_NAME_IR)

        video = None

        numberChosenVideoModes = len(videoModeChosen)

        if numberChosenVideoModes < 1:
            return f'No VideoMode Selected'

        if numberChosenVideoModes == 1:

            if videoModeChosen[0] == var.VIDEO_IR:
                video_path = video_path_ir
                video_time = timeInfra
            else:
                video_path = video_path_rgb
                video_time = timeColor

            video = html.Div([
                dash_player.DashPlayer(
                    id='main_player',
                    controls=True,
                    url=video_path,
                    width="100%",
                    height="auto",
                    intervalCurrentTime=5000,
                    seekTo=video_time
                )
            ])

        if numberChosenVideoModes == 2:
            video = html.Div([
                dbc.Row([
                    dbc.Col([
                        dash_player.DashPlayer(
                            id="main_player",
                            url=video_path_rgb,
                            controls=True,
                            width="100%",
                            height="auto",
                            intervalCurrentTime=5000,
                            seekTo=timeColor
                        ),
                    ]),
                    dbc.Col([
                        dash_player.DashPlayer(
                            id="secondary_player",
                            url=video_path_ir,
                            controls=True,
                            width="100%",
                            height="auto",
                            intervalCurrentTime=5000,
                            seekTo=timeInfra
                        ),
                    ]),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button('Play/Pause both',
                            id='playSyncBtn',
                            style={'margin-right': '10px', 'margin-bottom': '20px'}
                        ),
                        dbc.Button('sync time',
                            id='syncTimeBtn',
                            style={'margin-right': '10px', 'margin-bottom': '20px'}
                        )
                    ])
                ]),
            ])

        if video == None:
            return f'Error in selecting VideoMode. Max 2 Videos.'

        return video
    
    @app.callback(
        Output(component_id='main_player', component_property='playing'),
        Output(component_id='secondary_player', component_property='playing'),
        Input(component_id='playSyncBtn', component_property='n_clicks'),
        State(component_id='main_player', component_property='playing')
    )
    def play_video_sync(n_clicks, is_playing):

        if n_clicks is None:
            return dash.no_update

        outputPlaying = not is_playing

        return outputPlaying, outputPlaying
    
    @app.callback(
        Output(component_id='main_player', component_property='seekTo'),
        Output(component_id='secondary_player', component_property='seekTo'),
        Input(component_id='syncTimeBtn', component_property='n_clicks'),
        Input(component_id='map-viz', component_property='clickData'),
        State(component_id='main_player', component_property='currentTime')
    )
    def sync_current_viedeo_time(n_clicks, clickData, current_rgb_time):

        if n_clicks is None:
            return dash.no_update

        if current_rgb_time < 1:
            curr_rgb_time = 0
            curr_ir_time = 0
        else:
            map_info = clickData['points'][0]["customdata"][0]

            if map_info != var.seekuh:
                return current_rgb_time, current_rgb_time
        
            date = clickData['points'][0]["customdata"][1]
            curr_rgb_time = current_rgb_time
            curr_ir_time = util.get_ir_time_by_rgb_time(curr_rgb_time, date)

        return curr_rgb_time, curr_ir_time

    @app.callback(
        Output(component_id='map-viz', component_property='figure', allow_duplicate=True),
        Input(component_id='main_player', component_property='currentTime'),
        Input(component_id='map-viz', component_property='clickData'),
        Input(component_id='video-choice', component_property='value'),
        State(component_id='map-viz', component_property='figure'),
        prevent_initial_call=True
    )
    def update_map_video_time(currentTime, clickData, videoModeChosen, fig):
        if currentTime is None or currentTime < 1 or clickData is None:
            raise PreventUpdate

        date = clickData['points'][0]["customdata"][1]

        numberChosenVideoModes = len(videoModeChosen)
        if numberChosenVideoModes < 1:
            raise PreventUpdate
        if videoModeChosen[0] == var.VIDEO_IR:
            video_name = var.VIDEO_TIME_IR_FILE_NAME
        else:
            video_name = var.VIDEO_TIME_RGB_FILE_NAME

        figure = go.Figure(fig)
        figure = util.clear_boat(figure)
        figure = util.add_boat_positions(figure, round(currentTime, 1), date, video_name)

        return figure
    
    register_sonar_callbacks(app)

    # @app.callback(
    #     Output(component_id='map', component_property='figure', allow_duplicate=True),
    #     Input(component_id='map', component_property='clickData'),
    #     State(component_id='map', component_property='figure'),
    #     prevent_initial_call=True
    # )
    # def display_click_data(clickData, figure):
    #     if clickData is not None:
    #         if figure is None:
    #             print('figure is None')

    #         fig = go.Figure(figure)

    #         dataframe = figure.data[0]
    #         geojson = figure.data[1]

    #         # print(clickData)
    #         mylayers =[]
    #         mylayers.append(get_polygon(lons=[9.748, 9.749, 9.749, 9.748], lats=[52.35, 52.35, 52.353, 52.353],  color='red'))

    #         # add polygone to the map
    #         fig.add_scattermapbox(
    #             lat=[52.35, 52.35, 52.353, 52.353, 52.35],
    #             lon=[9.748, 9.749, 9.749, 9.748, 9.748],
    #             mode='lines',
    #             line=dict(width=2),
    #             name='New Area'
    #         )

    #         return fig   
        

    #         # Callback, um das Layout basierend auf der URL zu ändern
    # @app.callback(
    #     Output('page-content', 'children'),
    #     [Input('url', 'pathname')]
    # )
    # def display_page(pathname):
    #     if pathname == '/dash/newarea':
    #         return html.Div([
    #             dcc.Graph(id='map'),
    #             html.Div(id='output-div')
    #         ])
    #     else:
    #         return html.Div([
    #             html.H1("Hauptseite"),
    #             # Weitere Komponenten für die Hauptseite
    #         ])
