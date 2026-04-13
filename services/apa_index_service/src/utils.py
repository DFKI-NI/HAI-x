import datetime as dt
import json
from pathlib import Path
from typing import Dict, Any

import numpy as np
import rasterio

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

def get_lat_lon_from_tiff(path_to_tiff):
    """
    Extract latitude and longitude coordinates from a TIFF image.

    Args:
        path_to_tiff (str): Path to the TIFF image file

    Returns:
        numpy.ndarray: Array of GPS coordinates (longitude, latitude) for each pixel
    """
    image = rasterio.open(path_to_tiff)
    band1 = image.read(1)
    height, width = band1.shape
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    xs, ys = rasterio.transform.xy(image.transform, rows, cols)
    lons = np.array(xs)
    lats = np.array(ys)

    gps = np.array(list(zip(lons.ravel(), lats.ravel())))
    return gps


def _feature_collection_for_date(gps: np.ndarray, apa: np.ndarray, date: str, lake_query: str, full_apa: bool = False) -> Dict[str, Any]:
    """
    Build a GeoJSON FeatureCollection for a single date.

    Each pixel location becomes a Point feature with its corresponding APA value.

    Args:
        gps: numpy array of shape (N, 2) with lon/lat pairs flattened over the image
        apa: numpy array of shape (H, W, 3) or (H, W); APA composite values
        date: date string (YYYY-MM-DD)
        lake_query: lake description used (for naming/context)
        full_apa: If True, store all 3 APA values in the GeoJSON. Default is False.

    Returns:
        dict: GeoJSON FeatureCollection
    """
    # Select APA band: by convention we use the second channel (index 1) which corresponds
    # to water plants intensity in the current evalscript.
    if apa.ndim == 3:
        if full_apa:
            apa_vals = apa.reshape(-1, 3)
        else:
            apa_vals = apa[:, :, 1].ravel()
    else:
        apa_vals = apa.ravel()

    features = []
    # Ensure standard python types for JSON serialization
    for (lon, lat), val in zip(gps, apa_vals):
        if full_apa and isinstance(val, np.ndarray):
            v = [float(x) for x in val]
            if all(x == 0.0 for x in v):
                continue
        else:
            v = float(val)
            if v == 0.0:
                continue

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            },
            "properties": {
                "date": date,
                "lake": lake_query,
                "apa": v
            }
        })

    return {
        "type": "FeatureCollection",
        "name": f"APA_{lake_query}_{date}",
        "features": features
    }


def build_geojson_files(data: Dict[str, dict], lake_query: str, output_dir: str = ".", full_apa: bool = False) -> str:
    """
    Create GeoJSON files from processed APA data.

    For each available date in the input dict, a GeoJSON FeatureCollection is created
    where every pixel location is represented as a Point feature with its APA value.

    Args:
        data: dict mapping date -> { 'cropped_apa': np.ndarray, 'gps': np.ndarray, ... }
        lake_query: lake query string used; only the name part before a comma is used for filename
        output_dir: directory where the GeoJSON files will be written
        full_apa: If True, store all 3 APA values in the GeoJSON. Default is False.

    Returns:
        str: filename
    """
    # derive a short lake name for filenames
    lake_short = lake_query.split(',')[0].replace(' ', '_') if isinstance(lake_query, str) else 'lake'

    saved: Dict[str, str] = {}
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for date, payload in data.items():
        if 'cropped_apa' in payload.keys():
            apa = payload.get('cropped_apa')
        else:  # raw_apa
            apa = payload.get('raw_apa')
        gps = payload.get('gps')
        if apa is None or gps is None:
            # skip if required components are missing
            continue

        fc = _feature_collection_for_date(gps=np.asarray(gps), apa=np.asarray(apa), date=date, lake_query=lake_query, full_apa=full_apa)

        filename = f"{lake_short}_{date}.geojson"
        #filepath = output_path / filename
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(fc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        saved[date] = str(filename)

    return filename
