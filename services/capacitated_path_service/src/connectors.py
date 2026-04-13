import json
import logging
import math
import warnings

import geopandas as gpd
import numpy as np
from shapely.affinity import rotate
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, triangulate

from .utils import shortest_path_length, analyze_linestring, order_points_nearest

warnings.filterwarnings("ignore")

from typing import Union


class ClustersConnectors:
    def __init__(self, start_location=[], end_location=[], row_spacing: float = 5.0, mode: str = "unidirectional", project_epsg: str ="EPSG:4326"):
        self.row_spacing = float(row_spacing)
        gdf = gpd.GeoDataFrame(geometry=[start_location, end_location], crs=project_epsg)
        gdf = gdf.to_crs(int(project_epsg.split(':')[-1]))
        self.start = gdf.geometry[0]
        self.end = gdf.geometry[1]
        if mode not in ("unidirectional", "serpentine", "nearest_point"):
            raise ValueError("mode must be 'unidirectional', 'serpentine' or 'nearest_point'")
        self.mode = mode

    def load_data(self, input_data: Union[str, dict], boundary_file: Union[str, dict] = None, project_epsg: str = "EPSG:4326"):
        self.input_files = []
        self.input_data_types = []
        logging.info("Loading areas...")
        if isinstance(input_data, dict):
            gdf = gpd.GeoDataFrame.from_features(input_data.get("features", []), crs=project_epsg)
            self.input_data_types.append("dict")
        else:
            gdf = gpd.read_file(input_data)
            self.input_files.append(input_data)
            self.input_data_types.append("file")

        if "cluster_id" not in gdf.columns:
            raise ValueError("Input GeoJSON must contain a 'cluster_id' column")

        if gdf.empty:
            raise ValueError("No features with valid cluster_id found")
        self.original_crs = gdf.crs
        if self.original_crs is None:
            logging.warning(f"Input CRS missing: assuming {project_epsg}; you should specify correct CRS.")
            gdf = gdf.set_crs(epsg=int(project_epsg.split(':')[-1]))

        if boundary_file:
            if isinstance(boundary_file, dict):
                b_gdf = gpd.GeoDataFrame.from_features(boundary_file.get("features", []), crs=project_epsg)
                self.input_data_types.append("boundary_dict")
            else:
                b_gdf = gpd.read_file(boundary_file)
                self.input_files.append(boundary_file)
                self.input_data_types.append("boundary_file")
            
            b_gdf = b_gdf.to_crs(epsg=int(project_epsg.split(':')[-1]))
            self.boundary = unary_union(b_gdf.geometry)
            if not (self.boundary.contains(self.start)) or not (self.boundary.contains(self.end)):
                raise ValueError("start and/or end location are/is outside boundary")
        else:  # use other geojson to infer the boundary
            # add start and end to the b_gdf geometry such that these variables are within the convex hull
            new_points = gpd.GeoDataFrame(geometry=[self.start, self.end], crs=project_epsg)
            b_gdf = gdf.to_crs(epsg=int(project_epsg.split(':')[-1]))
            b_gdf = gpd.pd.concat([b_gdf, new_points], ignore_index=True)
            self.boundary = unary_union(b_gdf.geometry).convex_hull
            self.input_data_types.append("geometry")

        gdf = gdf.to_crs(epsg=int(project_epsg.split(':')[-1]))
        self.clusters_gdf = gdf
        logging.info(f"Loaded {len(self.clusters_gdf)} features")
        return self.clusters_gdf, self.boundary, self.original_crs

    def boustrophedon_path(self, cluster_geom, points, row_tolerance=1):
        if not points:
            return [], {}

        best_result = None
        best_coverage = 0
        best_diagnostics = {}
        test_angles = [0, 45, 90, 135]

        for test_angle in test_angles:
            result, diagnostics = self._compute_path_with_angle(
                cluster_geom, points, row_tolerance, test_angle
            )
            if result:
                coverage = len(result) / len(points) if points else 0
                if coverage > best_coverage:
                    best_result = result
                    best_coverage = coverage
                    best_diagnostics = diagnostics
                    best_diagnostics['method'] = f'sweep_angle_{test_angle}'

        if best_coverage < 0.8 and hasattr(self, 'boundary') and self.boundary is not None:
            convex_result, convex_diagnostics = self._compute_path_convex_decomposition(
                cluster_geom, points, row_tolerance
            )
            if convex_result:
                convex_coverage = len(convex_result) / len(points) if points else 0
                if convex_coverage > best_coverage:
                    best_result = convex_result
                    best_coverage = convex_coverage
                    best_diagnostics = convex_diagnostics
                    best_diagnostics['method'] = 'convex_decomposition'

        if not best_result or best_coverage < 0.5:
            best_result, best_diagnostics = self._compute_path_original_mbr(
                cluster_geom, points, row_tolerance
            )
            best_diagnostics['method'] = 'mbr_fallback'
            if best_result:
                best_coverage = len(best_result) / len(points) if points else 0

        best_diagnostics['coverage_ratio'] = round(best_coverage, 3)
        return best_result or [], best_diagnostics

    def _compute_path_with_angle(self, cluster_geom, points, row_tolerance, fixed_angle):
        centroid = cluster_geom.centroid
        rotated = self._rotate_points(points, -fixed_angle, origin=centroid)

        if hasattr(self, 'boundary') and self.boundary is not None:
            boundary_rotated = self._rotate_geometry(self.boundary, -fixed_angle, origin=centroid)
            rotated = [p for p in rotated if boundary_rotated.contains(p) or boundary_rotated.touches(p)]
            if not rotated:
                return [], {"error": "No points within boundary", "sweep_angle": fixed_angle}

        pts = sorted(rotated, key=lambda p: (p.y, p.x))
        spacing = getattr(self, "row_spacing", row_tolerance)

        rows, current_row, current_y = [], [pts[0]], pts[0].y
        for p in pts[1:]:
            if abs(p.y - current_y) <= row_tolerance:
                current_row.append(p)
            else:
                rows.append(current_row)
                current_row = [p]
                current_y = p.y
        if current_row:
            rows.append(current_row)

        ordered_rot = []
        for i, row in enumerate(rows):
            row_sorted = sorted(row, key=lambda p: p.x)
            if getattr(self, 'mode', 'serpentine') == "serpentine" and i % 2 == 1:
                row_sorted = list(reversed(row_sorted))

            if hasattr(self, 'boundary') and self.boundary is not None:
                boundary_rotated = self._rotate_geometry(self.boundary, -fixed_angle, origin=centroid)
                validated_row = self._validate_row_boundary(row_sorted, boundary_rotated)
                ordered_rot.extend(validated_row)
            else:
                ordered_rot.extend(row_sorted)

        ordered = self._rotate_points(ordered_rot, fixed_angle, origin=centroid)
        if hasattr(self, 'boundary') and self.boundary is not None:
            ordered = self._validate_path_segments(ordered, self.boundary)

        if not ordered:
            return [], {"error": "No valid path within boundary", "sweep_angle": fixed_angle}

        path_line = LineString([p.coords[0] for p in ordered]) if len(ordered) > 1 else None
        diagnostics = {
            "sweep_angle": fixed_angle,
            "path_length": round(path_line.length, 2) if path_line else 0,
            "num_rows": len(rows),
            "num_turns": max(0, len(rows) - 1),
            "row_spacing": spacing,
            "mode": getattr(self, 'mode', 'serpentine'),
            "points_in_path": len(ordered)
        }
        return ordered, diagnostics

    def _compute_path_convex_decomposition(self, cluster_geom, points, row_tolerance):
        if not hasattr(self, 'boundary') or self.boundary is None:
            return [], {"error": "No boundary for convex decomposition"}
        convex_polygons = self._decompose_to_convex(self.boundary)
        all_ordered = []
        total_diagnostics = {
            "method": "convex_decomposition",
            "num_convex_parts": len(convex_polygons),
            "total_path_length": 0,
            "total_turns": 0,
            "parts": []
        }
        for i, convex_poly in enumerate(convex_polygons):
            part_points = [p for p in points if convex_poly.contains(p) or convex_poly.touches(p)]
            if not part_points: continue
            best_angle = self._find_optimal_sweep_angle(convex_poly, part_points)
            part_ordered, part_diag = self._compute_path_with_angle(convex_poly, part_points, row_tolerance, best_angle)
            if part_ordered:
                all_ordered.extend(part_ordered)
                total_diagnostics["total_path_length"] += part_diag.get("path_length", 0)
                total_diagnostics["total_turns"] += part_diag.get("num_turns", 0)
                total_diagnostics["parts"].append({
                    "part_id": i, "points": len(part_ordered), "angle": best_angle,
                    "path_length": part_diag.get("path_length", 0)
                })
        return all_ordered, total_diagnostics

    def _decompose_to_convex(self, polygon):
        if polygon.is_valid and len(polygon.exterior.coords) <= 4:
            return [polygon]
        try:
            triangles = list(triangulate([polygon]))
            valid_triangles = [tri for tri in triangles if polygon.contains(tri.centroid)]
            if not valid_triangles: return [polygon.convex_hull]
            return self._merge_adjacent_triangles(valid_triangles)
        except Exception:
            return [polygon.convex_hull]

    def _merge_adjacent_triangles(self, triangles):
        return triangles

    def _find_optimal_sweep_angle(self, polygon, points):
        test_angles = [0, 45, 90, 135]
        best_angle, best_score = 0, -1
        centroid = polygon.centroid
        for angle in test_angles:
            rotated_points = self._rotate_points(points, -angle, origin=centroid)
            pts = sorted(rotated_points, key=lambda p: (p.y, p.x))
            if len(pts) < 2: continue
            y_values = [p.y for p in pts]
            y_range = max(y_values) - min(y_values)
            score = 1000 if y_range == 0 else len(pts) / max(1, int(y_range / getattr(self, 'row_spacing', 1)))
            if score > best_score:
                best_score, best_angle = score, angle
        return best_angle

    def _compute_path_original_mbr(self, cluster_geom, points, row_tolerance):
        mrr = cluster_geom.minimum_rotated_rectangle
        coords = list(mrr.exterior.coords)
        edges = [(coords[i], coords[i + 1]) for i in range(4)]
        edge_lengths = [math.dist(e[0], e[1]) for e in edges]
        long_edge = edges[np.argmax(edge_lengths)]
        dx, dy = long_edge[1][0] - long_edge[0][0], long_edge[1][1] - long_edge[0][1]
        angle = math.degrees(math.atan2(dy, dx))
        return self._compute_path_with_angle(cluster_geom, points, row_tolerance, angle)

    def _validate_row_boundary(self, row_points, boundary):
        if len(row_points) <= 1: return row_points
        valid_points = [row_points[0]]
        for i in range(1, len(row_points)):
            line = LineString([row_points[i - 1].coords[0], row_points[i].coords[0]])
            if boundary.contains(line) or boundary.intersects(line):
                valid_points.append(row_points[i])
            else:
                break
        return valid_points

    def _validate_path_segments(self, ordered_points, boundary):
        if len(ordered_points) <= 1: return ordered_points
        valid_path = [ordered_points[0]]
        for i in range(1, len(ordered_points)):
            line = LineString([ordered_points[i - 1].coords[0], ordered_points[i].coords[0]])
            if boundary.contains(line) or boundary.crosses(line):
                valid_path.append(ordered_points[i])
            else:
                intersection = boundary.intersection(line)
                if hasattr(intersection, 'coords') and len(intersection.coords) > 0:
                    valid_path.append(Point(intersection.coords[0]))
        return valid_path

    def _rotate_points(self, points, angle, origin):
        return [rotate(p, angle, origin=origin, use_radians=False) for p in points]

    def _rotate_geometry(self, geom, angle_degrees, origin):
        return rotate(geom, angle_degrees, origin=(origin.x, origin.y))

    def connect_start_and_end_points(self, current_path):
        polygon = self.boundary
        if not current_path: return []
        path_start, path_end = current_path[0], current_path[-1]
        if not (polygon.contains(path_start) and polygon.contains(path_end)):
            raise ValueError("Start location and/or End location are/is not within boundary")

        start_start_len, start_start_path = shortest_path_length(polygon, self.start, path_start, [path_end, self.end])
        end_end_len, end_end_path = shortest_path_length(polygon, path_end, self.end, [path_start, self.start])
        start_end_total_len = start_start_len + end_end_len

        start_end_len, start_end_path = shortest_path_length(polygon, self.start, path_end, [path_start, self.end])
        end_start_len, end_start_path = shortest_path_length(polygon, path_start, self.end, [path_end, self.start])
        end_start_total_len = start_end_len + end_start_len

        if start_end_total_len < end_start_total_len:
            start_connection, end_connection, path_to_use = start_start_path, end_end_path, current_path.copy()
        else:
            start_connection, end_connection, path_to_use = start_end_path, end_start_path, current_path[::-1]

        new_path = start_connection.copy() if start_connection else []
        end_connection = end_connection or []

        if new_path and path_to_use:
            new_path.extend(path_to_use[1:] if new_path[-1] == path_to_use[0] else path_to_use)
        else:
            new_path.extend(path_to_use)

        if new_path and end_connection:
            new_path.extend(end_connection[1:] if new_path[-1] == end_connection[0] else end_connection)
        else:
            new_path.extend(end_connection)
        return new_path

    def generate_nearest(self):
        line_records, total_distance = [], 0
        for cid, members in self.clusters_gdf.groupby("cluster_id"):
            cents = list(members.centroid.values)
            if len(cents) < 2: continue
            ordered = self.connect_start_and_end_points(order_points_nearest(cents))
            line = LineString([p for p in ordered])
            total_distance += line.length
            exp_data = analyze_linestring(line)
            explanation = f"Cluster {cid} is covered by a path generated using {exp_data['mode']} with total length {exp_data['path_length']} with {exp_data['num_segments']} segments and {exp_data['num_turns']} angles."
            line_records.append({f"{self.mode}_id": cid, "geometry": line, **exp_data, "explanation": explanation})
        return line_records, total_distance

    def generate_boustrophedon(self):
        line_records, total_distance = [], 0
        for cid, members in self.clusters_gdf.groupby("cluster_id"):
            cluster_geom = members.unary_union
            cents = list(members.centroid.values)
            if len(cents) < 2: continue
            ordered, diag = self.boustrophedon_path(cluster_geom, cents, row_tolerance=self.row_spacing)
            ordered = self.connect_start_and_end_points(ordered)
            line = LineString([p for p in ordered])
            total_distance += line.length
            explanation = f"Cluster {cid} is covered by path {cid}: using {diag.get('mode', 'N/A')} with sweep angle {diag.get('sweep_angle', 'N/A')}°."
            line_records.append({f"{self.mode}_id": cid, "geometry": line, **diag, "explanation": explanation})
        return line_records, total_distance

    def generate_Connectors(self, cluster_lines_geojson: str = "nearest_cluster_lines_exp.geojson"):
        if self.mode == "nearest_point":
            line_records, total_distance = self.generate_nearest()
        else:
            line_records, total_distance = self.generate_boustrophedon()

        line_gdf = gpd.GeoDataFrame(line_records, crs=self.clusters_gdf.crs)
        gExplanation = "greedy nearest-neighbor heuristic..." if self.mode == "nearest_point" else "boustrophedon coverage..."

        data = {
            'no_paths': {len(line_records)}, 'total_distance': total_distance, 'coordinate_system': 'EPSG:4326 (WGS84)',
            'input files': self.input_files, 'input data': self.input_data_types, 'main_output': f'{self.mode}_id',
            'additional_outputs': ['explanation'], 'output files': [], 'output data': [],
            'global Explanation': [f" The algorithm covers area of each cluster ( cluster_id ) by {gExplanation} "]
        }
        if self.original_crs is not None:
            line_gdf = line_gdf.to_crs(self.original_crs)
        geojson_data = json.loads(line_gdf.to_json())
        geojson_data["metadata"] = data
        with open(cluster_lines_geojson, "w") as f:
            json.dump(geojson_data, f, indent=2, default=list)
        return geojson_data
