# Estimate Weeding Areas from APA

This package uses satellite imagery to detect and estimate areas of interest (AOIs) based on plant intensity in lakes. It leverages the Sentinel Hub API to fetch satellite data and applies clustering techniques to identify potential weeding areas.

## Installation

This package is tested with Python 3.12

### Prerequisites

- Python 3.12
- Sentinel Hub account with API credentials

### Standard Installation

Install all the requirements:

```bash
pip install -r requirements.txt
```

### Sentinel Hub Configuration

To make the interface work with the Copernicus Dataspace, a modification is needed in the sentinelhub package:

1. Navigate to the sentinelhub package
2. Open the **constants.py** in **<ENVIRONMENT>/lib/python3.12/site-packages/sentinelhub**
3. Change the constant for "MAIN", see line 26, into **MAIN = "https://sh.dataspace.copernicus.eu"**

### Sentinel Hub Credentials

To use Sentinel Hub, you need an account and a plan (Exploration plan or free trial is enough for Process API and OGC API). Before using it, you must authenticate using your credentials (client ID and secret).

1. On the Sentinel Hub website, login with your credentials
2. Go to your account settings
3. Under OAuth clients, click on 'create new'
4. Enter a client name and create it
5. Note the client ID and client secret for later use

## Core Functionality

The package provides the following core functionalities:

1. **Satellite Data Retrieval**: Fetches satellite imagery for specified lakes and time periods
2. **Image Processing**: Crops images to lake boundaries and filters out empty or low-quality images
3. **Area of Interest Detection**: Uses clustering techniques to identify areas with medium to high plant intensity
4. **API Interface**: Provides a FastAPI application for easy access to the functionality

## API Documentation

The package includes a FastAPI application with the following endpoints:

### Root Endpoint (`GET /`)

Returns comprehensive documentation about all available API endpoints.

### Get Satellite Data (`POST /api/get_apa`)

Retrieves satellite data for a specified time period or day.

**Request Body Example (Date Range):**
```json
{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR"
}
```

**Request Body Example (Single Day):**
```json
{
  "day": "2025-01-08",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR"
}
```

### Get Areas of Interest (`POST /api/get_aois`)

Identifies areas of interest based on plant intensity in satellite images.

**Request Body Example:**
```json
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
```

## Docker Setup and Usage

The package includes a Dockerfile for easy deployment.

### Building the Docker Image

```bash
docker build -t weeding-areas-detector .
```

### Running the Docker Container

```bash
docker run -p 10003:10003 \
  -e sh_client_id=YOUR_CLIENT_ID \
  -e sh_client_secret=YOUR_CLIENT_SECRET \
  -e sh_instance_id=YOUR_INSTANCE_ID \
  weeding-areas-detector
```

Replace `YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, and `YOUR_INSTANCE_ID` with your Sentinel Hub credentials.

### Accessing the API

Once the container is running, you can access the API at:

```
http://localhost:10003/
```

The root endpoint provides comprehensive documentation about all available API endpoints.

## Example Usage

### Using the API

1. Start the API server (either directly or via Docker)
2. Send a POST request to `/api/get_aois` with appropriate parameters
3. Process the returned areas of interest for your application

### Using the Python Package Directly

```python
import estimate_weeding_areas_from_apa as aoi_apa_index

# Configure Sentinel Hub
config = aoi_apa_index.get_config(
    client_id,
    client_secret,
    instance_id
)

# Get satellite data
data = aoi_apa_index.get_satellite_data(
    config,
    './images/lake/',
    ['2025-01-01', '2025-01-31'],
    'ALL-BANDS-TRUE-COLOR',
    resolution_in_m=10,
    max_cloud_coverage=0.5,
    lake_query="Maschsee, Hannover, Germany"
)

# Estimate areas of interest
areas_of_interest = aoi_apa_index.estimate_areas_of_interest(
    data_path,
    ['medium', 'high'],
    n_areas=20,
    categories=['none', 'low', 'medium', 'high', 'vegetation']
)
```
