import time
from datetime import date, timedelta

import src.evalscripts as evalscripts
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

COPERNICUS_TOKEN_URL = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'


def get_api_access_token(client_id, client_secret):
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(token_url=COPERNICUS_TOKEN_URL, client_secret=client_secret, include_client_id=True)
    return token, oauth


def _gen_request_sentinel2_data(bbox, start, stop, resolution, evalscript):
    request = {
        "input": {
            "bounds": {
                "properties": { "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84" },
                "bbox": bbox, },
            "data": [{
                "type": "sentinel-2-l1c",
                "dataFilter": { "timeRange": { "from": start, "to": stop, } },
            }],
        },
        "output": { "height": resolution[0], "width": resolution[1], },
        "evalscript": evalscript,
    }
    return request


def get_sentinel2_data(data_collection, ft, start, stop, token):
    if token['expires_at'] - time.time() <= 0.0:
        raise Exception('Token expired')

    request = {
        "input": {
            "bounds": {
                "properties": { "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84" },
                "bbox": [
                    13.822174072265625,
                    45.85080395917834,
                    14.55963134765625,
                    46.29191774991382,
                ],
            },
            "data": [
                {
                    "type": "sentinel-2-l1c",
                    "dataFilter": {
                        "timeRange": {
                            "from": "2022-10-01T00:00:00Z",
                            "to": "2022-10-31T00:00:00Z",
                        }
                    },
                }
            ],
        },
        "output": {
            "width": 512,
            "height": 512,
        },
        "evalscript": evalscripts.evalscript_true_color,
    }

    url = "https://sh.dataspace.copernicus.eu/api/v1/process"
    response = oauth.post(url, json=request)
    return response


if __name__ == '__main__':
    client_id = ""
    client_secret = ""
    token, session = get_api_access_token(client_id, client_secret)
    print(token)

    ft = ("POLYGON ((9.728411992798499 52.365124853249085, 9.728411992798499 52.342100158630956, 9.755825281904066 "
          "52.342100158630956, 9.755825281904066 52.365124853249085, 9.728411992798499 52.365124853249085))")  # WKT Representation of BBOX
    data_collection = "SENTINEL-2"
    today = date.today()
    stop = today.strftime("%Y-%m-%d") + 'T00:00:00Z'
    yesterday = today - timedelta(days=5)
    start = yesterday.strftime("%Y-%m-%d") + 'T00:00:00Z'

    bbox = [13.822174072265625, 45.85080395917834, 14.55963134765625, 46.29191774991382]
    resolution = [512, 512]
    request = _gen_request_sentinel2_data(bbox, start, stop, resolution, evalscripts.evalscript_true_color)
    url = "https://sh.dataspace.copernicus.eu/api/v1/process"

    json_response = session.post(url, json=request)

    print(json_response.headers)
    print(json_response.content[:100])  # Fetch available dataset
