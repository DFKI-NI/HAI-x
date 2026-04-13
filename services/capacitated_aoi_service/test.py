import os
import json
import logging
import warnings
from pathlib import Path

import requests

from main import _get_bathymetry, _get_apa
from src.volume_estimation import volume_estimation


warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)


def _is_server_running(base_url: str) -> bool:
    try:
        resp = requests.get(base_url.rstrip("/") + "/", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _save_file_response(resp: requests.Response, fallback_name: str) -> str:
    content_disposition = resp.headers.get("content-disposition") or resp.headers.get("Content-Disposition")
    if content_disposition and "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[1].strip('"')
    else:
        filename = fallback_name
    with open(filename, "wb") as f:
        f.write(resp.content)
    return filename


if __name__ == "__main__":
    # Optional API base URL (FastAPI app)
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:10006")

    # Parameters for APA request
    apa_request_body = {
        "day": "2025-12-26",
        "resolution_in_m": 10,
        "max_cloud_coverage": 0.25,
        "lake_query": "Maschsee,Hannover,Germany",
        "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
        "instance_id": "",
        "client_id": "",
        "client_secret": "",
        "geojson_file": True,
    }

    if os.path.exists('credentials.json'):
        with open('credentials.json', 'r') as f:
            credentials = json.load(f)
    apa_request_body.update(credentials)

    # Volume estimation parameters
    harvester_width = 20.0
    residual_height = 0.2
    max_harvesting_depth = 1.8

    if _is_server_running(API_BASE_URL):
        logging.info("API server detected at %s — using HTTP endpoints", API_BASE_URL)
        # Services
        # Here all services should be accessible from the host system. Hence, localhost as URL.
        apa_docker_service = {'name': "sentinel_2", 'port': 10003}
        bathymetry_service = {'name': "bathymetry", 'port': 10005}

        BATHYMETRY_SERVICE_URL = f"http://{bathymetry_service['name']}:{bathymetry_service['port']}/geojson"
        APA_CREDENTIALS_SERVICE_URL = f"http://{apa_docker_service['name']}:{apa_docker_service['port']}/api/set_credentials"
        APA_SERVICE_URL = f"http://{apa_docker_service['name']}:{apa_docker_service['port']}/api/get_apa"

        # 1) Call /volume (POST)
        volume_payload = {
            "bathymetry_service_url": BATHYMETRY_SERVICE_URL,
            "apa_credentials_service_url": APA_CREDENTIALS_SERVICE_URL,
            "apa_service_url": APA_SERVICE_URL,
            "instance_id": apa_request_body["instance_id"],
            "client_id": apa_request_body["client_id"],
            "client_secret": apa_request_body["client_secret"],
            "day": apa_request_body["day"],
            "lake_query": apa_request_body["lake_query"],
            "resolution_in_m": apa_request_body["resolution_in_m"],
            "max_cloud_coverage": apa_request_body["max_cloud_coverage"],
            "copernicus_data_service": apa_request_body["copernicus_data_service"],
            "harvester_width": harvester_width,
            "residual_height": residual_height,
            "max_harvesting_depth": max_harvesting_depth,
        }
        try:
            vol_resp = requests.post(API_BASE_URL.rstrip("/") + "/volume", json=volume_payload, timeout=600)
            if vol_resp.status_code == 200:
                volume_filename = _save_file_response(vol_resp, "volume.geojson")
                print("/volume response saved as:", volume_filename)
            else:
                print(f"/volume failed: {vol_resp.status_code} {vol_resp.text}")
                volume_filename = None
        except Exception as e:
            print("/volume request error:", e)
            volume_filename = None

        # 2) Call /get_capacitated_clustering
        volume_geojson_obj = None
        candidates = [
            volume_filename,
            "Maschsee_2025-12-26_volume_20m.geojson",
        ]
        if vol_resp.status_code == 200:
            with open(volume_filename, "r") as f:
                volume_geojson_obj = json.load(f)
        else:
            raise ConnectionError

        clustering_payload = {
            "max_volume": 100000.,
            "eps": 50.,
            "min_volume": 1000.,
            "epsg": 3857,
            "volume_geojson": volume_geojson_obj,
            "harvester_width": harvester_width,
            "residual_height": residual_height,
            "max_harvesting_depth": max_harvesting_depth,
            "bathymetry_service_url": BATHYMETRY_SERVICE_URL,
            "apa_service_url": APA_SERVICE_URL,
            "apa_request_body": apa_request_body,
        }

        # Try GET with body first (as defined), fall back to POST if server rejects it
        try:
            clust_resp = requests.post(
                API_BASE_URL.rstrip("/") + "/get_capacitated_clustering",
                json=clustering_payload,
                timeout=600,
            )
            if clust_resp.status_code == 200:
                clustered_file = _save_file_response(clust_resp, "clustered_aoi.geojson")
                print("/get_capacitated_clustering saved as:", clustered_file)
            else:
                print(f"/get_capacitated_clustering failed: {clust_resp.status_code} {clust_resp.text}")
        except Exception as e:
            print("Clustering request error:", e)

    # If the Server is not running, the calls to the other dockers are reached through the host system.
    else:
        logging.info("API server not detected — running local pipeline")
        # Services
        # Here all services should be accessible from the host system. Hence, localhost as URL.
        BATHYMETRY_SERVICE_URL = "http://localhost:10005/geojson"
        APA_CREDENTIALS_SERVICE_URL = "http://localhost:10003/api/set_credentials"
        APA_SERVICE_URL = "http://localhost:10003/api/get_apa"

        # Fetch bathymetry
        bathymetry_file = _get_bathymetry(BATHYMETRY_SERVICE_URL)
        print("bathymetry saved as:", bathymetry_file)

        # Set APA credentials
        cred_resp = requests.post(
            APA_CREDENTIALS_SERVICE_URL,
            json={
                "instance_id": apa_request_body["instance_id"],
                "client_id": apa_request_body["client_id"],
                "client_secret": apa_request_body["client_secret"],
            },
        )
        if cred_resp.status_code == 200:
            print("Credentials successfully set")
        else:
            print(f"Failed to set credentials: {cred_resp.status_code} {cred_resp.text}")

        # Fetch APA
        apa_file = _get_apa(APA_SERVICE_URL, apa_request_body)
        print("apa saved as:", apa_file)

        # Run volume estimation locally
        try:
            volume_file = volume_estimation(
                apa_file=apa_file,
                bathymetry_file=bathymetry_file,
                harvester_width=harvester_width,
                residual_height=residual_height,
                max_harvesting_depth=max_harvesting_depth,
            )
            print("volume saved as:", volume_file)
        except Exception as e:
            print("Volume estimation failed:", e)



