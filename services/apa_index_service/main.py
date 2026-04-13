"""
FastAPI application for retrieving satellite data and areas of interest.

This module provides endpoints for retrieving satellite data and identifying areas of interest
based on plant intensity in satellite images. It uses the estimate_weeding_areas_from_apa module
to fetch and process satellite data from Sentinel Hub.
"""
import datetime
import logging
from typing import Dict, List, Tuple

import numpy as np
from fastapi import FastAPI, HTTPException, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from pydantic import BaseModel

import apa_composite
from src.sentinelhub_connector import get_config
from src.utils import build_geojson_files

# Global constants
PROFILE_NAME = "cmanss"
DATA_DIR = './images/maschsee/'

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
    instance_id: str
    client_id: str
    client_secret: str
    geojson_file: bool = False
    full_apa: bool = False


class DateCheckRequest(BaseModel):
    start: str = "2023-04-01"
    end: str = datetime.datetime.today().strftime('%Y-%m-%d')
    resolution_in_m: int = 10
    lake_query: str = "Maschsee, Hannover, Germany"
    copernicus_data_service: str = "ALL-BANDS-TRUE-COLOR"
    max_cloud_coverage: float = 0.5
    instance_id: str
    client_id: str
    client_secret: str


class Creds(BaseModel):
    instance_id: str
    client_id: str
    client_secret: str


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """
    Root endpoint that provides comprehensive information about all API functionalities.

    Returns:
        Dict[str, str]: A message with detailed information about all available API endpoints,
                       their parameters, and return values
    """
    with open('./assets/api_functionality.html', 'r') as file:
        api_docs = file.readlines()
    api_docs = "".join(api_docs)

    return api_docs


@app.post("/api/set_credentials")
async def set_credentials(credentials: Creds):
    client_id = credentials.client_id
    client_secret = credentials.client_secret
    instance_id = credentials.instance_id

    config = get_config(client_id, client_secret, instance_id, profile_name=PROFILE_NAME)
    return JSONResponse({
        "status": "ok",
        "message": "Credentials received and configuration initialized.",
        "profile": PROFILE_NAME
    })


@app.get("/api/set_credentials")
async def set_credentials_via_query(instance_id: str, client_id: str, client_secret: str):
    """
    Helper endpoint to set credentials via URL query parameters.

    Example:
    /api/set_credentials?instance_id=YOUR_INSTANCE&client_id=YOUR_CLIENT&client_secret=YOUR_SECRET
    """
    config = get_config(client_id, client_secret, instance_id, profile_name=PROFILE_NAME)
    return JSONResponse({
        "status": "ok",
        "message": "Credentials received via URL and configuration initialized.",
        "profile": PROFILE_NAME
    })


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
    geojson = req.geojson_file
    full_apa = req.full_apa
    # logging.log(logging.CRITICAL, f"full_apa: {full_apa}")

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
    client_id = req.client_id
    client_secret = req.client_secret
    instance_id = req.instance_id

    time_frame = (start_time, end_time)

    data = _get_satellite_data(
        lake_query,
        time_frame,
        copernicus_data_service,
        resolution_in_m,
        max_cloud_coverage,
        client_id,
        client_secret,
        instance_id
    )

    if not data or len(data) == 0:
        return JSONResponse({"error": "No data found for the specified query. Probably the date has no satellite fly over"}, status_code=404)

    for k, v in data.items():
        for kk, vv in v.items():
            data[k][kk] = vv.tolist()

    if geojson:
        filename = build_geojson_files(data, lake_query=lake_query, output_dir=".", full_apa=full_apa)
        return FileResponse(filename, media_type="application/geo+json", filename=filename)
    else:
        data = jsonable_encoder(data)
        return JSONResponse(data)


def _get_satellite_data(
        lake_query: str,
        time_frame: Tuple[str, str],
        copernicus_data_service: str,
        resolution_in_m: int,
        max_cloud_coverage: float,
        client_id: str,
        client_secret: str,
        instance_id: str
) -> Dict[str, np.ndarray]:
    """
    Retrieve satellite data for a specified lake and time frame.

    Args:
        lake_query: Query string to identify the lake (e.g., "Maschsee, Hannover, Germany")
        time_frame: Tuple containing start and end dates (format: 'YYYY-MM-DD')
        copernicus_data_service: Type of Copernicus data service to use
        resolution_in_m: Resolution in meters
        max_cloud_coverage: Maximum cloud coverage (0.0 to 1.0)
        client_id: Sentinel Hub Client ID, str
        client_secret: Sentinel Hub Secret for Client ID, str
        instance_id: Service Instance ID at Sentinel Hub. Needs to be defined in the web interface, str

    Returns:
        Dict[str, np.ndarray]: Dictionary with dates as keys and satellite data as values
    """
    boundaries = apa_composite.get_lake_box_boundaries(lake_query, crs=apa_composite.CRS.WGS84)

    config = apa_composite.get_config(
        client_id,
        client_secret,
        instance_id,
        PROFILE_NAME
    )

    try:
        data = apa_composite.get_satellite_data(
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
    client_id = req.client_id
    client_secret = req.client_secret
    instance_id = req.instance_id

    config = apa_composite.get_config(
        client_id,
        client_secret,
        instance_id,
        PROFILE_NAME
    )

    # Get lake boundaries
    bbox_coordinates = apa_composite.get_lake_box_boundaries(req.lake_query, crs=apa_composite.CRS.WGS84)
    # Get bbox and size
    bbox, size = apa_composite._convert_box_coords_to_bbox(bbox_coordinates, req.resolution_in_m)

    # Get available dates
    time_frame = [req.start, req.end]

    try:
        slots = apa_composite.get_dates_with_images(
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
