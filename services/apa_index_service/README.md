# sentinel-2
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

Required credentials fields for all requests:
- instance_id
- client_id
- client_secret

**Request Body Example (Date Range):**
```json
{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
  "instance_id": "YOUR_INSTANCE_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

**Request Body Example (Single Day):**
```json
{
  "day": "2025-01-08",
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
  "instance_id": "YOUR_INSTANCE_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

### Get Available Dates (`POST /api/get_available_dates`)

Returns the list of dates with available satellite images for a specified time range.

**Request Body Example:**
```json
{
  "start": "2025-01-01",
  "end": "2025-01-31",
  "resolution_in_m": 10,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
  "max_cloud_coverage": 0.5,
  "instance_id": "YOUR_INSTANCE_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

**Response Example:**
```json
{
  "available_dates": ["2025-01-05", "2025-01-12", "2025-01-27"]
}
```

### Set Credentials (`POST /api/set_credentials`)

Optional endpoint to initialize Sentinel Hub configuration in the server. You can call it once after startup.

**Request Body Example:**
```json
{
  "instance_id": "YOUR_INSTANCE_ID",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
```

Note: Supplying credentials directly in request bodies of other endpoints is sufficient; calling this endpoint is optional.

## Docker Setup and Usage

The package includes a Dockerfile for easy deployment.

### Building the Docker Image

```bash
docker build -t sentinel-2 .
```

### Running the Docker Container

Credentials are supplied in the request body (see API examples), so no environment variables are needed.

```bash
docker run --rm -p 10003:10003 --network my_network --name sentinel_2 sentinel-2:latest
```

### Accessing the API

Once the container is running, you can access the API at:

```
http://localhost:10003/
```

The root endpoint provides comprehensive documentation about all available API endpoints.

## Example Usage

### Using the API

1. Start the API server (either directly or via Docker)
2. Send a POST request to `/api/get_apa` with appropriate parameters
3. Process the returned areas of interest for your application