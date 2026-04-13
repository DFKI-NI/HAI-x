# Density Based Clustering

This project provides an API for volume estimation and capacitated clustering for aquatic plant management.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Build and run with Docker:
   ```bash
   docker build -t density_based_clustering .
   docker run -p 10006:10006 density_based_clustering
   ```

## Configuration

### Credentials

To test services that require authentication (like the APA service), you should create a `credentials.json` file in the root directory. This file is used by `test.py` and can also be passed via the API.

Create `credentials.json` with the following structure:

```json
{
  "instance_id": "YOUR_INSTANCE_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

## API Documentation

The API is built with FastAPI. Once the server is running, you can access the interactive documentation at `http://localhost:10006/docs`.

### Endpoints

#### `POST /volume`

Estimates the volume of aquatic plants.

**Request Body (`VolumeEstimationRequest`):**
- `bathymetry_service_url`: (Optional) URL to fetch bathymetry GeoJSON.
- `apa_credentials_service_url`: (Optional) URL to set APA credentials.
- `apa_service_url`: (Optional) URL to fetch APA GeoJSON.
- `instance_id`: (Optional) Credentials instance ID.
- `client_id`: (Optional) Credentials client ID.
- `client_secret`: (Optional) Credentials client secret.
- `day`: Date in `YYYY-MM-DD` format (default: "2025-12-26").
- `lake_query`: Query string for the lake (default: "Maschsee,Hannover,Germany").
- `resolution_in_m`: Resolution in meters (default: 10).
- `max_cloud_coverage`: Max cloud coverage (default: 0.25).
- `copernicus_data_service`: Sentinel Hub service (default: "ALL-BANDS-TRUE-COLOR").
- `harvester_width`: Width of the harvester in meters (default: 20.0).
- `residual_height`: Residual height in meters (default: 0.2).
- `max_harvesting_depth`: Max harvesting depth in meters (default: 1.8).
- `output_file`: (Optional) Custom output filename.

#### `POST /get_capacitated_clustering`

Performs capacitated clustering on the volume data.

**Request Body (`CapacitatedClusteringRequest`):**
- `max_volume`: Maximum volume per cluster.
- `eps`: The maximum distance between two samples for one to be considered as in the neighborhood of the other.
- `min_volume`: (Optional) Minimum volume per cluster.
- `epsg`: EPSG code (default: 3857).
- `volume_geojson`: GeoJSON object containing volume data.
- `boundary_geojson`: (Optional) GeoJSON object for boundaries.
- `harvester_width`: Width of the harvester (default: 20.0).
- `residual_height`: Residual height (default: 0.2).
- `max_harvesting_depth`: Max harvesting depth (default: 1.8).
- `bathymetry_service_url`: (Optional) URL for bathymetry service.
- `apa_service_url`: (Optional) URL for APA service.
- `apa_request_body`: (Optional) Request body for APA service.
- `output_file`: (Optional) Custom output filename.
- `lake_query`: (Optional) Lake query (default: "Lake").
- `day`: (Optional) Date (default: "2026-01-26").

## Usage

You can use `test.py` to test the API or the local pipeline:
```bash
python test.py
```
