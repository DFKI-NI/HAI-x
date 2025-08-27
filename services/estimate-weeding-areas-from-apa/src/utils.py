import datetime as dt
import json

import yaml
from sentinelhub import (
    CRS,
    BBox,
    bbox_to_dimensions,
)


def read_lake_data(config_file: str) -> dict:
    with open(config_file) as file:
        config = yaml.safe_load(file)
    config['lake_bbox'] = BBox(bbox=config['coordinates_wgs84'], crs=CRS.WGS84)
    config['output_resolution'] = bbox_to_dimensions(config['lake_bbox'], resolution=config['resolution'])
    return config

def save_areas_of_interests_to_json(areas_of_interests: list, filename: str) -> None:
    payload = {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'geometry': 'Polygon',
            'coordinates': polygon,
            'id': id
        } for id, polygon in enumerate(areas_of_interests)]
    }
    with open(filename, 'w') as file:
        json.dump(areas_of_interests, file)

def get_request_dt(request_file):
    """
    Given a request file (usually a Json file), this function returns a datetime object.
    :param request_file: str
    :return: datetime object
    """
    with open(request_file, 'r') as req:
        request = json.load(req)
        start_time = request['request']['payload']['input']['data'][0]['dataFilter']['timeRange']['from']
        start_time = dt.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S%z')
        # url = unquote(request['url'])
        # time_parameter = [t for t in url.split('&') if t.startswith('TIME=')][0]
        # time = time_parameter.split('TIME=')[1].split('/')[0]
        return start_time