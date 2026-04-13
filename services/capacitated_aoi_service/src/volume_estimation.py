import os
import json
from typing import Optional

import geopandas as gpd
import numpy as np
from shapely.geometry import box, mapping
from scipy.spatial import cKDTree


def _create_intersecting_grid(
    weed_gdf: gpd.GeoDataFrame,
    minx: float, miny: float, maxx: float, maxy: float,
    cell_size: float,
    crs: str = "EPSG:3857"
) -> gpd.GeoDataFrame:

    grid_cells = []
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cell = box(x, y, x + cell_size, y + cell_size)
            if weed_gdf.intersects(cell).any():
                grid_cells.append(cell)
            y += cell_size
        x += cell_size

    return gpd.GeoDataFrame(geometry=grid_cells, crs=crs)


def _write_output_geojson(
    grid_gdf: gpd.GeoDataFrame,
    depths: np.ndarray,
    harvesting_depths: np.ndarray,
    volumes: np.ndarray,
    distances: np.ndarray,
    cell_area: float,
    cell_size: float,
    harvester_width: float,
    residual_height: float,
    max_harvesting_depth: float,
    apa_file: str,
    bathymetry_file: str,
    output_file: Optional[str] = None,
    lake_name: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Create and write the output GeoJSON file from computed arrays and grid.

    Returns the path to the written file.
    """
    out_gdf = grid_gdf.copy()
    out_gdf = out_gdf.to_crs(epsg=4326)
    out_gdf["cell_id"] = range(1, len(out_gdf) + 1)
    out_gdf["depth"] = depths
    out_gdf["harvesting_depth"] = harvesting_depths
    out_gdf["volume"] = volumes
    out_gdf["cell_area"] = cell_area
    out_gdf["nearest_bathy_distance"] = distances
    # Standardize plant density column name
    if "apa" in out_gdf.columns:
        out_gdf = out_gdf.rename(columns={"apa": "plant_density"})

    features = []
    for _, row in out_gdf.iterrows():
        props = {
            "cell_id": int(row["cell_id"]),
            "plant_density": float(row.get("plant_density", 0.0)),
            "volume": float(row["volume"]),
            "depth": float(row["depth"]),
            "harvesting_depth": float(row["harvesting_depth"]),
            "cell_area": float(row["cell_area"]),
            "nearest_bathy_distance": float(row["nearest_bathy_distance"]),
        }
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(row["geometry"]),
        })

    metadata = {
        "lake_name": lake_name,
        "date": date,
        "cell_size": cell_size,
        "harvester_width": harvester_width,
        "plant_residual_height": residual_height,
        "max_harvesting_depth": max_harvesting_depth,
        "total_cells": int(len(out_gdf)),
        "total_volume_m3": float(np.sum(volumes)),
        "coordinate_system": "EPSG:4326 (WGS84)",
        "input files": [apa_file, bathymetry_file],
        "input data": ["plant_density", "estimated_depth"],
        "main_output": "volume",
        "additional_outputs": [
            "cell_id",
            "plant_density",
            "depth",
            "harvesting_depth",
            "cell_area",
            "nearest_bathy_distance",
        ],
    }

    geojson_data = {
        "type": "FeatureCollection",
        "features": features,
        "metadata": metadata,
    }

    if output_file is None:
        stem = os.path.splitext(os.path.basename(apa_file))[0]
        output_file = os.path.join(os.getcwd(), f"{stem}_volume_{int(cell_size)}m.geojson")

    with open(output_file, "w") as f:
        json.dump(geojson_data, f, indent=2)

    return output_file


def volume_estimation(
    apa_file: str,
    bathymetry_file: str,
    harvester_width: float = 20.0,
    residual_height: float = 0.2,
    max_harvesting_depth: float = 1.8,
    output_file: Optional[str] = None,
    crs = "EPSG:3857",
    lake_name: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """Estimate aquatic plant volume per grid cell and export a GeoJSON.

    Inputs are expected to contain:
      - APA (weed) GeoJSON with property 'plant_density'.
      - Bathymetry GeoJSON with property 'estimated_depth'.

    Processing is done in EPSG:3857 for metric calculations; output is EPSG:4326.

    Returns the path to the written GeoJSON.
    """

    # Load inputs and project to a metric CRS for area/distance
    weed_gdf = gpd.read_file(apa_file)
    bathy_gdf = gpd.read_file(bathymetry_file)

    weed_gdf = weed_gdf.to_crs(epsg=int(crs.split(':')[1]))
    weed_gdf['apa'] = weed_gdf['apa'] / 255.0  # normalize pixel values to 1.0
    bathy_gdf = bathy_gdf.to_crs(epsg=int(crs.split(':')[1]))

    # Build grid covering APA extent with cell size = harvester width
    minx, miny, maxx, maxy = weed_gdf.total_bounds
    cell_size = float(harvester_width)
    grid_gdf = _create_intersecting_grid(
        weed_gdf, minx, miny, maxx, maxy, cell_size, crs=crs
    )

    grid_gdf = gpd.sjoin(grid_gdf, weed_gdf[["geometry", "apa"]], how="left", predicate="intersects")
    grid_gdf["apa"] = grid_gdf["apa"].fillna(0.0)

    # Get nearest bathymetry depth for each grid centroid
    bathy_tree = cKDTree(np.array([[p.x, p.y] for p in bathy_gdf.geometry]))
    centroids = grid_gdf.geometry.centroid
    centroid_coords = np.array([[p.x, p.y] for p in centroids])
    distances, idxs = bathy_tree.query(centroid_coords, k=1)

    depths = bathy_gdf["estimated_depth"].iloc[idxs].to_numpy()

    # Compute harvesting depth and volume
    harvesting_depths = np.minimum(np.maximum(depths - float(residual_height), 0.0), float(max_harvesting_depth))
    cell_area = cell_size ** 2
    volumes = harvesting_depths * grid_gdf["apa"].to_numpy() * cell_area

    # Create output GeoJSON file
    return _write_output_geojson(
        grid_gdf=grid_gdf,
        depths=depths,
        harvesting_depths=harvesting_depths,
        volumes=volumes,
        distances=distances,
        cell_area=cell_area,
        cell_size=cell_size,
        harvester_width=harvester_width,
        residual_height=residual_height,
        max_harvesting_depth=max_harvesting_depth,
        apa_file=apa_file,
        bathymetry_file=bathymetry_file,
        output_file=output_file,
        lake_name=lake_name,
        date=date,
    )

if __name__ == "__main__":
    import argparse
    # CLI entrypoint to run volume estimation from the command line
    here = os.path.dirname(__file__)
    default_apa = os.path.abspath(os.path.join(here, "..", "Maschsee_2025-12-26.geojson"))
    default_bathy = os.path.abspath(os.path.join(here, "..", "maschsee_estimated_bathymetry_ex.geojson"))

    parser = argparse.ArgumentParser(description="Estimate aquatic plant volume per grid cell and export GeoJSON.")
    parser.add_argument("--apa", dest="apa_file", default=default_apa, help="Path to APA GeoJSON file (default: example file)")
    parser.add_argument("--bathymetry", dest="bathymetry_file", default=default_bathy, help="Path to bathymetry GeoJSON file (default: example file)")
    parser.add_argument("--harvester-width", type=float, default=20.0, help="Harvester width in meters (cell size)")
    parser.add_argument("--residual-height", type=float, default=0.2, help="Residual plant height in meters")
    parser.add_argument("--max-harvesting-depth", type=float, default=1.8, help="Maximum harvesting depth in meters")
    parser.add_argument("--output", dest="output_file", default=None, help="Output GeoJSON filepath (optional)")
    parser.add_argument("--lake-name", dest="lake_name", default=None, help="Lake name for the output filename (optional)")
    parser.add_argument("--date", dest="date", default=None, help="Date for the output filename (optional)")

    args = parser.parse_args()

    if not os.path.exists(args.apa_file):
        raise SystemExit(f"APA file not found: {args.apa_file}")
    if not os.path.exists(args.bathymetry_file):
        raise SystemExit(f"Bathymetry file not found: {args.bathymetry_file}")

    out = volume_estimation(
        apa_file=args.apa_file,
        bathymetry_file=args.bathymetry_file,
        harvester_width=args.harvester_width,
        residual_height=args.residual_height,
        max_harvesting_depth=args.max_harvesting_depth,
        output_file=args.output_file,
        lake_name=args.lake_name,
        date=args.date,
    )
    print(f"Volume GeoJSON written to: {out}")