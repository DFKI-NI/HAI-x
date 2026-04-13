# CVRP with Capacity Clusters

This project provides a FastAPI-based service to generate connector paths for clustered geographical data, specifically designed for Capacitated Vehicle Routing Problems (CVRP). It supports various clustering modes and can handle both GeoJSON files and direct JSON input.

## Features

- **Multiple Clustering Modes**:
  - `unidirectional`: Generates paths in a single direction.
  - `serpentine`: Generates paths in a back-and-forth (boustrophedon) pattern.
  - `nearest_point`: Connects points using a greedy nearest-neighbor heuristic.
- **FastAPI Integration**: Provides a RESTful API for easy integration.
- **Flexible Input**: Accepts GeoJSON as a dictionary or via file upload.
- **Boundary Support**: Can use an explicit boundary or infer one from the data.
- **Dockerized**: Easy to build and deploy using Docker.

## Getting Started

### Prerequisites

- Python 3.12+
- System dependencies for GDAL/Proj (required for GeoPandas)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cvrp_with_capacity_clusters
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running Locally

Start the FastAPI server using uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 10011
```

### Docker

#### Build the Docker image:
```bash
docker build -t cvrp-clusters .
```

#### Run the Docker container:
```bash
docker run -p 10011:10011 cvrp-clusters
```

## API Documentation

The API documentation is automatically generated and can be accessed at:
- API description and test functionality: `http://localhost:10011/`
- CVRP for capacitated clustered regions: `http://localhost:10011/redoc`

### Endpoints

#### `POST /cvrp`
Processes clustered GeoJSON data and returns a GeoJSON file with generated connector paths.

**Request Body (`CVRPRequest`):**

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `cluster_json` | `dict` | **Required**. The GeoJSON data (as a dictionary) containing clusters. Must have a `cluster_id` column. | - |
| `boundary_file` | `dict` or `UploadFile` | Optional. GeoJSON representing the boundary. | `None` |
| `start_x` | `float` | X coordinate (longitude) of the start location. | `9.741273233` |
| `start_y` | `float` | Y coordinate (latitude) of the start location. | `52.353144617` |
| `end_x` | `float` | X coordinate (longitude) of the end location. | `9.741244433` |
| `end_y` | `float` | Y coordinate (latitude) of the end location. | `52.35319485` |
| `row_spacing` | `float` | Spacing between rows for boustrophedon paths. | `5.0` |
| `mode` | `string` | Clustering mode: `unidirectional`, `serpentine`, or `nearest_point`. | `"serpentine"` |

**Response**:
- A GeoJSON file (`output.geojson`) containing the generated paths and metadata.

## Testing

Run the included test suite to verify functionality:
```bash
python3 test.py
```

The tests cover various modes, input types, and error cases.
