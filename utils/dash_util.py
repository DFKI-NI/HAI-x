from flask import url_for
import os
from collections import defaultdict
from utils import variables as var
from dash import html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objs as go
from os import listdir
from utils import variables as var
from flask.helpers import get_root_path
from datetime import datetime
from utils.database import database as db

def get_index(own_timestamp: float, date: str):
    if os.path.exists(var.VID_DATA_PATH + var.maschsee + date + ".csv"):
        data = pd.read_csv(var.VID_DATA_PATH + var.maschsee + date + ".csv")

        for index, row in data.iterrows():
            if own_timestamp <= row['Timestamp']:
                result_index = index - 1
                break

        return [result_index, data.loc[result_index, 'first_lat'], data.loc[result_index, 'first_lon'], data.loc[result_index, 'last_lat'], data.loc[result_index, 'last_lon']]
    else:
        return 0
    
def get_time(own_timestamp: float, date: str, topic: str):
    if os.path.exists(var.VID_DATA_PATH + var.maschsee + date + "_" + topic + ".csv"):
        data = pd.read_csv(var.VID_DATA_PATH + var.maschsee + date +  "_" + topic + ".csv")

        for index, row in data.iterrows():
            if own_timestamp < row['Timestamp']:
                # result_index = index - 1
                videoTime = row['VideoTime'] - 1
                break

        if videoTime < 0:
            videoTime = 0
        return videoTime
    else:
        return 0
    
def get_ir_time_by_rgb_time(rgb_time: float, date: str):
    if os.path.exists(var.VID_DATA_PATH + var.maschsee + date + var.VIDEO_TIME_RGB_FILE_NAME) and \
        os.path.exists(var.VID_DATA_PATH + var.maschsee + date + var.VIDEO_TIME_IR_FILE_NAME):
        data = pd.read_csv(var.VID_DATA_PATH + var.maschsee + date + var.VIDEO_TIME_RGB_FILE_NAME)

        for index, row in data.iterrows():
            if rgb_time <= row['VideoTime']:
                rgb_timestamp = row['Timestamp']
                break
        
        data = pd.read_csv(var.VID_DATA_PATH + var.maschsee + date + var.VIDEO_TIME_IR_FILE_NAME)
        for index, row in data.iterrows():
            if rgb_timestamp <= row['Timestamp']:
                ir_time = row['VideoTime']
                break

        return ir_time
    else:
        return 0

def format_dates():
    haix = db.select_distinct(var.SCHEMA, var.AREA, 'date')
    pathplanning = db.select_distinct(var.SCHEMA, var.PATH, 'date')
    traj = db.select_distinct(var.SCHEMA, var.traj, 'date')
    date_choices = append_type_to_dates(haix, pathplanning, traj)
    return date_choices

def append_type_to_dates(haix, pathplanning, traj):
    dates = defaultdict(list)
    dates = build_dates_dict(dates, haix, var.AREA)
    dates = build_dates_dict(dates, traj, var.traj)
    dates = build_dates_dict(dates, pathplanning, var.PATH)
    date_choices = []
    for key, value in dates.items():
        date = key + ': '
        types = ', '.join(sorted(value))
        date += types
        date_choices.append(date)
    date_choices = sorted(date_choices, reverse=True)
    return date_choices

def build_dates_dict(dates, list_of_dates, typ):
    for date in list_of_dates:
        date = date[0].strftime('%Y-%m-%d')
        if typ not in dates[date]:
            dates[date].append(typ)
    return dates

def add_has_images_col(df):
    has_images = []
    for i, row in df.iterrows():
        if type(row['image_path']) == str:
            has_images.append(True)
        else:
            has_images.append(False)
    df['has_images'] = has_images
    return df

def add_images(id):
    parent_style_dict = {
        'display': 'flex',
        'justify-content': 'flex-start',
        'flex-wrap': 'wrap',
        'align-items': 'flex-start'
    }
    child_style_dict = {
        'max-width': '50%',
        'height': 'auto'
    }
    df = db.open_table(var.SCHEMA, var.AREA, var.AREA_COLS)
    image_paths = df.loc[df['idx'] == int(id)]['image_path'].values[0]
    if type(image_paths) == str:
        image_block = html.Div([html.P('Images:')], className='mb-3')
        images = html.Div(children=[], style=parent_style_dict)
        image_paths = image_paths.split(';')
        for file in image_paths:
            path = url_for('static', filename='img/' + file)
            image = html.Img(src=path, style=child_style_dict, width='50%')
            images.children.append(image)
        image_block.children.append(images)
        return image_block
    return None

def clear_map(fig):
    data = list(fig.data)
    for i, chart in enumerate(data):
        try:
            if len(chart['lat']) == 2:
                del data[i]
                break
        except Exception:
            print("fehler")

    fig.data = data
    return fig

def add_start_stop(fig, start, stop):
    df = pd.DataFrame([[start[0], start[1], "start"], [stop[0], stop[1], "stop"]], columns=['lat', 'lon', 'type'])

    fig.add_scattermapbox(
        lat=df["lat"],
        lon=df["lon"],
        text=df["type"],
        marker={
            'color': ['green', 'red'],
            'size': 8
        }
    )

    return fig

def clear_boat(fig):
    data = list(fig.data)
    for i, chart in enumerate(data):
        try:
            if len(chart['lat']) == 1:
                del data[i]
                break
        except Exception:
            print("fehler")

    fig.data = data
    return fig

def add_boat_positions(fig, curentRgbTime, date, video_name):

    if os.path.exists(var.VID_DATA_PATH + var.maschsee + date + video_name):
        data = pd.read_csv(var.VID_DATA_PATH + var.maschsee + date + video_name)

        for _, row in data.iterrows():
            if curentRgbTime <= row['VideoTime']:
                rgb_timestamp = row['Timestamp']
                boat_lat = row['Latitude']
                boat_lon = row['Longitude']
                break
            
    fig.add_scattermapbox(
        lat=[boat_lat],
        lon=[boat_lon],
        text='data["type"]',
        name='boat',
        marker={
            'color': 'blue',
            'size': 8
        }
    )

    return fig

def clean_dates(dates):
    clean_dates = []
    if dates is not None:
        for date in dates:
            d = date.split(":")[0]
            dt = datetime.strptime(d, '%Y-%m-%d')
            clean_dates.append(dt)
    return clean_dates
