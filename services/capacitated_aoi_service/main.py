import json
import logging
import os.path
import tempfile
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.aoi_based_on_capacitated_clustering import (
    cluster_aoi_by_capacity,
)
from src.volume_estimation import volume_estimation

# FastAPI application
app = FastAPI()

# Static assets (usage docs)
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", include_in_schema=False)
def root_index():
    """Serve static usage information from assets/index.html at the root path."""
    index_path = ASSETS_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Usage page not found")
    return FileResponse(str(index_path), media_type="text/html")


class CapacitatedClusteringRequest(BaseModel):
    # Clustering params
    max_volume: float
    eps: float
    min_volume: Optional[float] = None
    epsg: int = 3857

    # Input data (inline GeoJSON dicts)
    volume_geojson: dict
    boundary_geojson: Optional[dict] = None

    # Volume estimation params
    harvester_width: float = 20.0
    residual_height: float = 0.2
    max_harvesting_depth: float = 1.8

    bathymetry_service_url: Optional[str] = None  # e.g., http://localhost:8000/geojson
    apa_service_url: Optional[str] = None  # e.g., http://localhost:8001/api/get_apa
    apa_request_body: Optional[dict] = None  # JSON body required by get_apa_post
    apa_geojson_path: Optional[str] = None  # Use a local APA GeoJSON file instead of the service

    # Optional explicit output filename and metadata
    output_file: Optional[str] = None
    lake_query: Optional[str] = "Lake"
    date: Optional[str] = "2026-01-26"


class VolumeEstimationRequest(BaseModel):
    # Services
    bathymetry_service_url: Optional[str] = "http://bathymetry_service:10005/geojson"
    apa_credentials_service_url: Optional[str] = "http://apa_index_service:10003/api/set_credentials"
    apa_service_url: Optional[str] = "http://apa_index_service:10003/api/get_apa"
    apa_geojson_path: Optional[str] = "None"  # Use a local APA GeoJSON file instead of the service

    # Credentials (optional but recommended for APA service)
    instance_id: Optional[str] = "None"
    client_id: Optional[str] = "None"
    client_secret: Optional[str] = "None"

    # APA request basics
    date: str = "2025-12-26"
    lake_query: str = "Maschsee,Hannover,Germany"
    resolution_in_m: int = 10
    max_cloud_coverage: float = 0.25
    copernicus_data_service: str = "ALL-BANDS-TRUE-COLOR"

    # Volume estimation params
    harvester_width: float = 20.0
    residual_height: float = 0.2
    max_harvesting_depth: float = 1.8

    # Optional explicit output filename
    output_file: Optional[str] = "None"


def _get_bathymetry(bathymetry_service_url: Optional[str]) -> str:
    """Fetch bathymetry GeoJSON file.

    - If a URL is provided, download it to a temporary file and return the path.
    """
    # todo: for bathymetry enable the functionality to cache the files and use them if the request is the same
    if not bathymetry_service_url:
        raise ValueError("bathymetry_service_url is required")

    response = requests.post(bathymetry_service_url, timeout=300)
    response.raise_for_status()

    content_disposition = response.headers.get("content-disposition")
    if content_disposition and "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[1].strip('"')
    else:
        filename = "downloaded_file"

    ordner = Path("data/output")
    ordner.mkdir(parents=True, exist_ok=True)

    with open(filename, "wb") as f:
        f.write(response.content)

    return filename


def _get_apa(
    apa_service_url: Optional[str],
    request_body: Optional[dict]
) -> str:
    """Fetch APA as GeoJSON.

    - If a local path is provided, use it directly.
    - If a URL is provided and a request body is given, POST it and parse the JSON response.
    - If a URL is provided without a body, GET it and parse the JSON response.
    - If no URL is provided, return an empty GeoJSON FeatureCollection.
    """

    # todo: for APA enable the functionality to cache the files and use them if the request is the same
    response = requests.post(apa_service_url, json=request_body, timeout=300)
    # response.raise_for_status()

    content_disposition = response.headers.get("content-disposition")
    if content_disposition and "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[1].strip('"')
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".geojson")
        filename = tmp.name

    with open(filename, "wb") as f:
        f.write(response.content)

    return filename


@app.post("/volume")
async def get_volume(req: VolumeEstimationRequest):
    """Return the volume GeoJSON. Uses cached file when available.

    Cache key convention: "<LakeName>_<YYYY-MM-DD>_volume_<width>m.geojson"
    where LakeName is inferred as the first token before a comma in `lake_query`.
    """

    # Infer expected cached filename
    lake_name = req.lake_query.split(",")[0].strip().replace(" ", "_")
    expected_stem = f"{lake_name}_{req.date}"
    expected_output = req.output_file or f"{expected_stem}_volume_{int(req.harvester_width)}m.geojson"

    # Check cache in current working directory
    #todo check if exists but also force to remove cached files
    # if os.path.exists(expected_output):
    #     return FileResponse(expected_output, media_type="application/geo+json", filename=expected_output)

    # Fetch bathymetry
    try:
        bathy_file = _get_bathymetry(req.bathymetry_service_url)
    except Exception as e:
        logging.exception("Failed to fetch bathymetry")
        raise HTTPException(status_code=502, detail=f"Failed to fetch bathymetry: {e}")

    # Set APA credentials if provided
    if req.instance_id and req.client_id and req.client_secret and req.apa_credentials_service_url:
        try:
            cred_resp = requests.post(
                req.apa_credentials_service_url,
                json={
                    "instance_id": req.instance_id,
                    "client_id": req.client_id,
                    "client_secret": req.client_secret,
                },
                timeout=300,
            )
            if cred_resp.status_code != 200:
                logging.warning(f"Setting APA credentials failed: {cred_resp.status_code}  {cred_resp.text}")
        except Exception as e:
            logging.warning(f"APA credentials request failed: {e}")

    # Build APA request body
    logging.log(logging.CRITICAL, req.client_id)
    apa_body = {
        "day": req.date,
        "resolution_in_m": req.resolution_in_m,
        "max_cloud_coverage": req.max_cloud_coverage,
        "lake_query": req.lake_query,
        "copernicus_data_service": req.copernicus_data_service,
        "instance_id": req.instance_id,
        "client_id": req.client_id,
        "client_secret": req.client_secret,
        "geojson_file": "True",
    }

    # Fetch APA , req.apa_geojson_path
    try:
        apa_file = _get_apa(req.apa_service_url, apa_body)
    except Exception as e:
        logging.exception("Failed to fetch APA")
        raise HTTPException(status_code=502, detail=f"Failed to fetch APA: {e}")

    # Compute volume
    out_path = volume_estimation(
        apa_file=apa_file,
        bathymetry_file=bathy_file,
        harvester_width=req.harvester_width,
        residual_height=req.residual_height,
        max_harvesting_depth=req.max_harvesting_depth,
        output_file=req.output_file,
        lake_name=lake_name,
        date=req.date,
    )

    return FileResponse(out_path, media_type="application/geo+json", filename=out_path)


@app.post("/get_capacitated_clustering")
async def get_capacitated_clustering(req: CapacitatedClusteringRequest):
    # Validate basic parameters
    if req.max_volume is None or req.eps is None:
        raise HTTPException(status_code=400, detail="eps and max_volume must be provided")
    if not req.bathymetry_service_url:
        raise HTTPException(status_code=400, detail="bathymetry_service_url must be provided")
    if not req.apa_geojson_path:
        if not req.apa_service_url:
            raise HTTPException(status_code=400, detail="apa_service_url must be provided")
        if req.apa_request_body is None:
            raise HTTPException(status_code=400, detail="apa_request_body must be provided")

    try:
        bathymetry_file = _get_bathymetry(bathymetry_service_url=req.bathymetry_service_url)
    except Exception as e:
        logging.exception("Failed to fetch bathymetry")
        raise HTTPException(status_code=502, detail=f"Failed to fetch bathymetry: {e}")

    try:
        apa_file = _get_apa(req.apa_service_url, req.apa_request_body)
    except Exception as e:
        logging.exception("Failed to fetch APA")
        raise HTTPException(status_code=502, detail=f"Failed to fetch APA: {e}")

    # Compute volume
    lake_name = req.lake_query.split(",")[0].strip().replace(" ", "_")
    expected_stem = f"{lake_name}_{req.date}"
    expected_output = req.output_file or f"{expected_stem}_volume_{int(req.harvester_width)}m.geojson"

    volume_estimation_file = volume_estimation(
        apa_file=apa_file,
        bathymetry_file=bathymetry_file,
        harvester_width=req.harvester_width,
        residual_height=req.residual_height,
        max_harvesting_depth=req.max_harvesting_depth,
        output_file=req.output_file or expected_output,
    )

    # Run clustering
    feature_collection, summary = cluster_aoi_by_capacity(
        volume_geojson=req.volume_geojson,
        max_volume=int(req.max_volume),
        eps=int(req.eps),
        min_volume=float(req.min_volume) if req.min_volume is not None else None,
        epsg=int(req.epsg),
        boundary_geojson=req.boundary_geojson,
    )

    # Infer output filename
    output_filename = f"{lake_name}_{req.date}_clustered_Cap{int(req.max_volume)}_{int(req.harvester_width)}m.geojson"

    # Save to file
    with open(output_filename, "w") as f:
        json.dump(feature_collection, f, indent=2)

    # Return as downloadable file
    return FileResponse(
        path=output_filename,
        media_type="application/geo+json",
        filename=output_filename,
    )
