import json
import os

import geopandas as gpd
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pykrige.ok import OrdinaryKriging
from scipy.interpolate import griddata

from src.utils import get_lake_shp
from src.xai import clipped_depth_to_geojson_features, save_to_geojson

# constants
OSM_QUERY = "Maschsee, Hannover, Germany"  # user input from gui
LAKE_DEPTH_FILE = "./data/maschsee_depth_complete.csv"  # user input from gui
OUTPUT_FILENAME = "data/output/maschsee_estimated_bathymetry_ex.geojson"  # user input from gui

# FastAPI app to serve the resulting GeoJSON
app = FastAPI(title="Bathymetry API")


class BathymetryRequest(BaseModel):
    osm_query: str | None = OSM_QUERY
    lake_depth_file: str | None = LAKE_DEPTH_FILE
    output_filename: str | None = OUTPUT_FILENAME


app.mount("/static", StaticFiles(directory="data"), name="static")


@app.post("/geojson")
def get_geojson(request: BathymetryRequest = BathymetryRequest()):
    """Generate (if needed) and return the bathymetry GeoJSON.

    This endpoint ensures a GeoJSON is available by running the processing
    pipeline on-demand and then returns it as a file response.

    Returns:
        fastapi.responses.FileResponse: The resulting GeoJSON file
        (`OUTPUT_FILENAME`) with media type `application/geo+json`.
    """
    _provide_geojson(
        osm_query=request.osm_query,
        lake_depth_file=request.lake_depth_file,
        output_filename=request.output_filename
    )
    return FileResponse(request.output_filename, media_type="application/geo+json", filename=request.output_filename)


@app.get("/")
def root():
    """Serve the HTML landing page describing the API and its images."""
    return FileResponse("assets/index.html", media_type="text/html")


def interpolate(df_depth):
    """Interpolate depth values on a grid from input measurements.

    Attempts Ordinary Kriging first, and falls back to cubic interpolation
    with post-scaling if Kriging fails.

    Args:
        df_depth (pandas.DataFrame): Input depth measurements with columns
            `longitude`, `latitude`, and `depth` (meters). Depth values <= 0
            are ignored for Kriging.

    Returns:
        tuple: `(grid_x, grid_y, grid_depth, valid_points, valid_depths)` where
            - `grid_x` (np.ndarray): Meshgrid X coordinates of shape (Ny, Nx).
            - `grid_y` (np.ndarray): Meshgrid Y coordinates of shape (Ny, Nx).
            - `grid_depth` (np.ndarray): Interpolated depths clipped to
              [0, max_depth].
            - `valid_points` (np.ndarray): Filtered input points with
              `depth > 0` used for Kriging.
            - `valid_depths` (np.ndarray): Corresponding depths to
              `valid_points`.

    Notes:
        - Grid resolution is fixed to 100x100 across the bounding box of the
          input points.
        - A broad exception handler is used to trigger the fallback method if
          Kriging raises any error.
    """
    points = df_depth[['longitude', 'latitude']].values
    depths = df_depth['depth'].values

    # Filter points with depth > 0.0
    valid_indices = np.where(depths > 0.0)[0]
    valid_points = points[valid_indices]
    valid_depths = depths[valid_indices]

    # Create grid
    grid_x = np.linspace(min(points[:, 0]), max(points[:, 0]), 100)
    grid_y = np.linspace(min(points[:, 1]), max(points[:, 1]), 100)

    max_depth = df_depth['depth'].max()

    try:
        results = kriging_interpolation(valid_points, valid_depths, grid_x, grid_y, max_depth)
        grid_x, grid_y, grid_depth, valid_points, valid_depths = results
    except:
        average_depth = depths.mean()
        grid_depth = interpolate_depth_fallback(points, grid_x, grid_y, depths, max_depth, average_depth)

    return grid_x, grid_y, grid_depth, valid_points, valid_depths


def kriging_interpolation(valid_points, valid_depths, grid_x, grid_y, max_depth):
    """Perform Ordinary Kriging interpolation for bathymetry estimation.

    Args:
        valid_points (np.ndarray): Nx2 array of `[lon, lat]` with depth > 0.
        valid_depths (np.ndarray): N array of depth values for `valid_points`.
        grid_x (np.ndarray): 1D array of grid X coordinates (longitudes).
        grid_y (np.ndarray): 1D array of grid Y coordinates (latitudes).
        max_depth (float): Maximum depth used to clip interpolated values.

    Returns:
        tuple: `(grid_x_mesh, grid_y_mesh, grid_depth, valid_points, valid_depths)`
            suitable for downstream clipping and export.
    """
    OK = OrdinaryKriging(
        valid_points[:, 0], valid_points[:, 1], valid_depths,
        variogram_model='spherical',
        nlags=20,
        weight=True,
        verbose=False,
        enable_plotting=False
    )

    grid_depth, ss = OK.execute('grid', grid_x, grid_y)

    # Scale to desired depth range if needed
    grid_depth = np.clip(grid_depth, 0, max_depth)

    # Create meshgrid for consistency with previous function
    grid_x_mesh, grid_y_mesh = np.meshgrid(grid_x, grid_y)

    return grid_x_mesh, grid_y_mesh, grid_depth, valid_points, valid_depths


def interpolate_depth_fallback(points, grid_x, grid_y, depth, max_depth, average_depth):
    """Fallback cubic interpolation with scaling when Kriging is unavailable.

    Performs cubic interpolation over the target grid and scales the resulting
    values so that their mean roughly matches the observed average depth,
    then clips to `[0, max_depth]`.

    Args:
        points (np.ndarray): Nx2 array of `[lon, lat]` coordinates.
        grid_x (np.ndarray): 1D array of grid X coordinates (longitudes).
        grid_y (np.ndarray): 1D array of grid Y coordinates (latitudes).
        depth (np.ndarray): N array of observed depth values.
        max_depth (float): Maximum depth used to clip values.
        average_depth (float): Mean depth of the observations used for scaling.

    Returns:
        np.ndarray: Interpolated and scaled grid depths with shape (Ny, Nx).
    """
    # Interpolate using cubic method
    grid_depth = griddata(points, depth, (grid_x, grid_y), method='cubic')

    # Scale the interpolated depth values
    valid_mask = ~np.isnan(grid_depth)
    original = grid_depth[valid_mask]
    scaled = (original - np.min(original)) / (np.max(original) - np.min(original))
    scaled = scaled + (max_depth - 1.0)
    scale_factor = average_depth / np.mean(scaled)
    scaled *= scale_factor
    scaled = np.clip(scaled, 0, max_depth)

    grid_depth[valid_mask] = scaled

    return grid_depth


def _provide_geojson(
        osm_query: str,
        lake_depth_file: str,
        output_filename: str
):
    """Run the processing pipeline and materialize the GeoJSON if needed.

    Side effects:
        - Reads the input CSV defined by `lake_depth_file`.
        - Downloads/reads the lake polygon via `get_lake_shp`.
        - Interpolates depths and clips to the lake boundary.
        - Writes the final GeoJSON to `output_filename`.

    Returns:
        None
    """
    if not os.path.exists(output_filename):
        df_depth = pd.read_csv(lake_depth_file, sep=';')
        lake_boundaries_file = get_lake_shp(osm_query)

        lake_average_depth = df_depth['depth'].mean()
        lake_max_depth = df_depth['depth'].max()

        x_coordinates, y_coordinates, depths, depth_points, depth_values = interpolate(df_depth)

        print(f"Kriging completed. Found {len(depth_points)} valid depth points.")

        lake_boundary = gpd.read_file(lake_boundaries_file).geometry.iloc[0]
        no_points, features = clipped_depth_to_geojson_features(
            x_coordinates, y_coordinates, depths, lake_boundary,
            depth_points, depth_values)

        # Save to GeoJSON
        save_to_geojson(
            no_points, features, lake_boundaries_file, lake_depth_file,
            lake_average_depth, lake_max_depth, output_filename)
    else:
        # Extract number of points from existing GeoJSON
        try:
            with open(output_filename, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                no_points = len(data['features'])
        except Exception:
            no_points = 0

    print(f"Process completed. {no_points} points with visual explanations saved.")
    print(f"GeoJSON: {output_filename}")
