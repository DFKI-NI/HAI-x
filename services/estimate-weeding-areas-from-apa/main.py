"""
FastAPI application for retrieving satellite data and areas of interest.

This module provides endpoints for retrieving satellite data and identifying areas of interest
based on plant intensity in satellite images. It uses the estimate_weeding_areas_from_apa module
to fetch and process satellite data from Sentinel Hub.
"""
import glob
import json
import os
from ast import literal_eval
from pathlib import Path
from typing import Dict, List, Tuple, Any
import datetime

import numpy as np
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from scipy.spatial import ConvexHull

import estimate_weeding_areas_from_apa as aoi_apa_index

# Global constants
PROFILE_NAME = "cmanss"
DATA_DIR = './images/maschsee/'
CATEGORIES = ['none', 'low', 'medium', 'high', 'vegetation']

client_id = os.environ['sh_client_id']
client_secret = os.environ['sh_client_secret']
instance_id = os.environ['sh_instance_id']

config = aoi_apa_index.get_config(client_id, client_secret, instance_id, profile_name=PROFILE_NAME)

app = FastAPI()

# Pydantic models for request validation
class APARequest(BaseModel):
    day: str = None
    start: str = None
    stop: str = None
    resolution_in_m: int = 10
    max_cloud_coverage: float = 0.5
    lake_query: str = "Maschsee, Hannover, Germany"
    copernicus_data_service: str = "ALL-BANDS-TRUE-COLOR"

class AOIRequest(BaseModel):
    start: str = None
    stop: str = None
    day: str = None
    resolution_in_m: int = 10
    max_cloud_coverage: float = 0.5
    lake_query: str = "Maschsee, Hannover, Germany"
    copernicus_data_service: str = "ALL-BANDS-TRUE-COLOR"
    n_areas: int = 20
    
class DateCheckRequest(BaseModel):
    start: str = "2023-04-01"
    end: str = datetime.datetime.today().strftime('%Y-%m-%d')
    resolution_in_m: int = 10
    lake_query: str = "Maschsee, Hannover, Germany"
    copernicus_data_service: str = "ALL-BANDS-TRUE-COLOR"
    max_cloud_coverage: float = 0.5


def check_required_keys(data: Dict[str, Any], required_keys: List[List[str]]) -> bool:
    """
    Check if the input dictionary contains at least one set of required keys.

    Args:
        data: Dictionary containing input parameters
        required_keys: List of lists, where each inner list represents a set of required keys

    Returns:
        bool: True if at least one set of required keys is present

    Raises:
        HTTPException: If none of the required key sets are present
    """
    for key_set in required_keys:
        missing_keys = [key for key in key_set if key not in data]
        if not missing_keys:
            return True

    # If we get here, none of the key sets were complete
    flat_keys = [key for key_set in required_keys for key in key_set]
    unique_keys = list(set(flat_keys))
    raise HTTPException(
        status_code=400,
        detail=f"Missing required keys. Provide either {' and '.join(required_keys[0])} or {required_keys[1][0]}"
    )


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """
    Root endpoint that provides comprehensive information about all API functionalities.

    Returns:
        Dict[str, str]: A message with detailed information about all available API endpoints,
                       their parameters, and return values
    """
    api_docs = """    
    <html>
        <head>
            <title>Satellite Data Analysis API</title>
        </head>
        <body>
            <h1>FastAPI Application for Satellite Data Analysis</h1>
            <p>This API provides endpoints for retrieving and analyzing satellite data, specifically for identifying areas of interest based on plant intensity in satellite images.</p>

            <h2>Available Endpoints</h2>
            <ul>
                <li><strong>GET /</strong><br>
                    <em>Description:</em> Root endpoint that provides this documentation<br>
                    <em>Parameters:</em> None<br>
                    <em>Returns:</em> Documentation about all available API endpoints
                </li>
                <li><strong>POST /api/get_apa</strong><br>
                    <em>Description:</em> Retrieves satellite data for a specified time period or day using JSON body<br>
                    <em>Request Body:</em> JSON with either:
                    <ul>
                        <li>Date range format:
                            <pre>
{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR"
}
                            </pre>
                        </li>
                        <li>Single day format:
                            <pre>
{
  "day": "2025-01-08",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR"
}
                            </pre>
                        </li>
                    </ul>
                    <em>Returns:</em> Dictionary with dates as keys and JSON-encoded satellite data as values
                </li>
                <li><strong>POST /api/get_aois</strong><br>
                    <em>Description:</em> Identifies areas of interest based on plant intensity in satellite images using JSON body<br>
                    <em>Request Body:</em> JSON with either start/stop or day:
                    <pre>
{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "day": null,
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
  "n_areas": 20
}
                    </pre>
                    <em>Returns:</em> List of polygon coordinates representing areas of interest
                </li>
                <li><strong>POST /api/get_available_dates</strong><br>
                    <em>Description:</em> Checks for available dates with satellite images for a specified time frame<br>
                    <em>Request Body:</em> JSON with start and end dates:
                    <pre>
{
  "start": "2025-01-01",
  "end": "2025-01-31",
  "resolution_in_m": 10,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR"
}
                    </pre>
                    <em>Returns:</em> Dictionary with available dates and their time slots
                </li>
            </ul>

            <h2>Example Usage</h2>
            <h3>POST Endpoints (JSON Body)</h3>
            <pre>
POST /api/get_apa
Content-Type: application/json

{
  "day": "2025-01-08",
  "resolution_in_m": 20
}
            </pre>

            <pre>
POST /api/get_aois
Content-Type: application/json

{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "n_areas": 10
}
            </pre>
            
            <pre>
POST /api/get_available_dates
Content-Type: application/json

{
  "start": "2025-01-01",
  "end": "2025-01-31",
  "resolution_in_m": 10
}
            </pre>
        </body>
    </html>
    """

    return api_docs


@app.post("/api/get_apa")
async def get_apa_post(req: APARequest = Body(...)):
    """
    Get satellite data for a specified time period or day using POST request with JSON body.

    Args:
        req: JSON body containing date range parameters (start and stop dates)
        single_day_request: JSON body containing single day parameter

    Returns:
        Dict[str, str]: Satellite data with dates as keys and JSON-encoded numpy arrays as values

    Raises:
        HTTPException: If required parameters are missing
    """
    if (req.start is None or req.stop is None) and req.day is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters. Provide either start and stop dates or a single day date."
        )

    # Handle single day case
    if req.day is not None:
        day = req.day
        start_time = day + "T00:0:01"
        end_time = day + "T23:59:59"
    else:
        start_time = req.start
        end_time = req.stop

    resolution_in_m = req.resolution_in_m
    max_cloud_coverage = req.max_cloud_coverage
    lake_query = req.lake_query
    copernicus_data_service = req.copernicus_data_service

    time_frame = (start_time, end_time)

    data = _get_satellite_data(
        lake_query,
        time_frame,
        copernicus_data_service,
        resolution_in_m,
        max_cloud_coverage
    )

    for k, v in data.items():
        for kk, vv in v.items():
            data[k][kk] = vv.tolist()
    data = jsonable_encoder(data)

    return JSONResponse(data)


@app.post("/api/get_aois")
async def get_aois_post(req: AOIRequest = Body(...)): # -> List[List[List[float]]]:
    """
    Get areas of interest for a specified time period or day using POST request with JSON body.

    Args:
        req: JSON body containing request parameters (either start/stop or day)

    Returns:
        List[List[List[float]]]: List of polygon coordinates representing areas of interest

    Raises:
        HTTPException: If required parameters are missing
    """
    # Check for either start+stop or day
    if (req.start is None or req.stop is None) and req.day is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters. Provide either start and stop dates or a single day date."
        )


    # Handle single day case
    if req.day is not None:
        start_time = req.day + "T00:0:01"
        end_time = req.day + "T23:59:59"
    else:
        start_time = req.start
        end_time = req.stop

    time_frame = (start_time, end_time)

    data = _get_satellite_data(
        req.lake_query,
        time_frame,
        req.copernicus_data_service,
        req.resolution_in_m,
        req.max_cloud_coverage
    )

    dict_of_areas = _cluster_areas_in_satellite_data(req.n_areas)
    for date, areas_of_interest in dict_of_areas.items():
        data[date]['areas_of_interest'] = [a.points[a.vertices, :].tolist() for a in areas_of_interest]

    for k, v in data.items():
        for kk, vv in v.items():
            if kk != 'areas_of_interest':
                data[k][kk] = vv.tolist()
    data = jsonable_encoder(data)

    return data


def _get_satellite_data(
        lake_query: str,
        time_frame: Tuple[str, str],
        copernicus_data_service: str,
        resolution_in_m: int,
        max_cloud_coverage: float
) -> Dict[str, np.ndarray]:
    """
    Retrieve satellite data for a specified lake and time frame.

    Args:
        lake_query: Query string to identify the lake (e.g., "Maschsee, Hannover, Germany")
        time_frame: Tuple containing start and end dates (format: 'YYYY-MM-DD')
        copernicus_data_service: Type of Copernicus data service to use
        resolution_in_m: Resolution in meters
        max_cloud_coverage: Maximum cloud coverage (0.0 to 1.0)

    Returns:
        Dict[str, np.ndarray]: Dictionary with dates as keys and satellite data as values
    """
    boundaries = aoi_apa_index.get_lake_box_boundaries(lake_query, crs=aoi_apa_index.CRS.WGS84)

    config = aoi_apa_index.get_config(
        os.environ['sh_client_id'],
        os.environ['sh_client_secret'],
        os.environ['sh_instance_id'],
        PROFILE_NAME
    )

    try:
        data = aoi_apa_index.get_satellite_data(
            config,
            DATA_DIR,
            time_frame,
            copernicus_data_service,
            resolution_in_m=resolution_in_m,
            max_cloud_coverage=max_cloud_coverage,
            lake_query=lake_query
        )
    except ValueError as ve:
        print(f'ValueError: {ve}')
        return ve
    except OSError as oe:
        print(f'OSError: {oe}')
        return oe
    except Exception as e:
        print(f'OSM Error for {lake_query}: {e}')
        return e


    return data


def _cluster_areas_in_satellite_data(n_areas: int) -> List[ConvexHull]:
    """
    Cluster satellite data to identify areas of interest.

    Args:
        n_areas: Number of areas to identify

    Returns:
        List[ConvexHull]: List of ConvexHull objects representing areas of interest
        Dict[str, ConvexHull]: Dict of ConvexHull objects representing areas of interest addressed by a date
    """
    # Generate dictionary with data-dates key-value pairs
    dl_data = [Path(i) for i in glob.iglob(DATA_DIR + '/cropped/*[!cropped]*.tiff', recursive=True)]

    data_and_dates = dict()
    for dl in dl_data:
        request_file = dl.parent.parent / dl.stem / 'request.json'
        if os.path.exists(request_file):
            date = aoi_apa_index.get_request_dt(request_file)
            date = date.strftime('%Y-%m-%d')
            data_and_dates[date] = dl

    # Get the latest image (first key in the dictionary)
    # latest_key = list(data_and_dates.keys())[0]
    #
    # list_of_areas = aoi_apa_index.estimate_areas_of_interest(
    #     data_and_dates[latest_key],
    #     ['medium', 'high'],
    #     n_areas=n_areas,
    #     categories=CATEGORIES
    # )
    dict_of_areas = dict()
    for date, data in data_and_dates.items():
        dict_of_areas[date] = aoi_apa_index.estimate_areas_of_interest(
            data,
            ['medium', 'high'],
            n_areas=n_areas,
            categories=CATEGORIES
        )

    return dict_of_areas


@app.post("/api/get_available_dates")
async def get_available_dates(req: DateCheckRequest = Body(...)):
    """
    Get available dates with satellite images for a specified time frame.
    
    Args:
        req: JSON body containing start and end dates and other optional parameters
        
    Returns:
        Dict[str, List[Tuple[str, str]]]: Dictionary with available dates and their time slots
        
    Raises:
        HTTPException: If required parameters are missing
    """
    # Get lake boundaries
    bbox_coordinates = aoi_apa_index.get_lake_box_boundaries(req.lake_query, crs=aoi_apa_index.CRS.WGS84)
    # Get bbox and size
    bbox, size = aoi_apa_index._convert_box_coords_to_bbox(bbox_coordinates, req.resolution_in_m)
    
    # Get available dates
    time_frame = [req.start, req.end]
    
    try:
        slots = aoi_apa_index.get_dates_with_images(
            config,
            req.copernicus_data_service,
            bbox,
            size,
            time_frame,
            req.resolution_in_m,
            max_cloud_coverage=req.max_cloud_coverage
        )
        
        # Convert to dictionary format
        result = {
            "available_dates": [slot[0].split("T")[0] for slot in slots]
        }
        
        return JSONResponse(jsonable_encoder(result))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving available dates: {str(e)}"
        )
