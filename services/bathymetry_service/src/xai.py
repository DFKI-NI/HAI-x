import json

import numpy as np
from geopy.distance import geodesic
from scipy.spatial import cKDTree
from shapely.geometry import Point, mapping
from tqdm import tqdm


def clipped_depth_to_geojson_features(grid_x, grid_y, grid_depth, lake_boundary, depth_points, depth_values):
    """
    Create GeoJSON features with visual explanations
    """
    # Create output directory for images
    # os.makedirs(output_dir, exist_ok=True)

    # Create KDTree for nearest neighbor search
    depth_tree = cKDTree(depth_points)

    features = []
    no_points = 0
    grid_points = np.vstack([grid_x.ravel(), grid_y.ravel()]).T  # (N, 2)
    # idx = np.where([lake_boundary.contains(Point(p)) for p in grid_points])
    with tqdm(total=grid_points.shape[0]) as pbar:
        for p, depth in zip(grid_points, grid_depth.ravel()):
            pt = Point(p)
            if lake_boundary.contains(pt) and not np.isnan(depth):
                # Find nearest two measured points with depth > 0.0
                distances, indices = depth_tree.query(p, k=2)

                # Get coordinates and depths of nearest two points
                nearest_point1 = depth_points[indices[0]]
                nearest_depth1 = depth_values[indices[0]]
                nearest_point2 = depth_points[indices[1]]
                nearest_depth2 = depth_values[indices[1]]

                # Calculate distances in meters
                nearest_coord1 = (nearest_point1[1], nearest_point1[0])  # (lat, lon)
                nearest_coord2 = (nearest_point2[1], nearest_point2[0])  # (lat, lon)

                distance_meters1 = geodesic(p, nearest_coord1).meters
                distance_meters2 = geodesic(p, nearest_coord2).meters

                # Create visualization
                point_id = f"point_{no_points:04d}"

                feature = {
                    "type": "Feature",
                    "geometry": mapping(pt),
                    "properties": {
                        "point_id": point_id,
                        "estimated_depth": float(f"{depth:.2f}"),
                        "depth_of_nearest_point_1": float(f"{nearest_depth1:.2f}"),
                        "depth_of_nearest_point_2": float(f"{nearest_depth2:.2f}"),
                        "nearest_point_location_1": f"{nearest_point1[0]:.6f}, {nearest_point1[1]:.6f}",
                        "nearest_point_location_2": f"{nearest_point2[0]:.6f}, {nearest_point2[1]:.6f}",
                        "distance_to_nearest_point_1_m": float(f"{distance_meters1:.2f}"),
                        "distance_to_nearest_point_2_m": float(f"{distance_meters2:.2f}"),
                        "interpolation_method": "kriging"
                    }
                }
                features.append(feature)
                no_points = no_points + 1
            pbar.update(1)

    return no_points, features


def save_to_geojson(no_points, features, lake_boundaries_file, lake_depth_file, average_depth, max_depth, file_name):
    """Save results to GeoJSON file with metadata"""
    geojson_data = {
        "type": "FeatureCollection",
        "features": features,
        'metadata': {
            'no_depth_points': no_points,
            'input files': [lake_boundaries_file, lake_depth_file],
            'average_depth': average_depth,
            'max_depth': max_depth,
            'input data': ["geometry", "depth"],
            'main_output': "estimated_depth",
            'additional_outputs': [
                "depth_of_nearest_point_1",
                "depth_of_nearest_point_2",
                "nearest_point_location_1",
                "nearest_point_location_2",
                "distance_to_nearest_point_1_m",
                "distance_to_nearest_point_2_m",
                "interpolation_method",
                "visual_explanation_filename",
                "point_id"
            ],
            'output files': [],
            'coordinate_system': 'EPSG:4326 (WGS84)',
            'distance_unit': 'meters',
            'interpolation_method': 'kriging_with_fallback',
            'global Explanation': f"Measured depth values were interpolated using Kriging to estimate depth of {no_points} points. "
                                  f"Average depth: {average_depth}m, Maximum depth: {max_depth}m. "
                                  f"The interpolation is done using the geometry shape of {lake_boundaries_file} and depth from {lake_depth_file}"
            ,

        }
    }

    with open(file_name, "w") as f:
        json.dump(geojson_data, f, indent=2)
        print(f"Bathymetry with explanations saved to '{file_name}'.")
