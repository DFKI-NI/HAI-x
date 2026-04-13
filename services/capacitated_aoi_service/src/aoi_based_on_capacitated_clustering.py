import json
import logging
import tempfile
import warnings
from collections import deque
from typing import Optional, Union, Tuple, Dict, Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import unary_union
from tqdm import tqdm

from src.utils import ensure_polygon_geometry, clean_geometries

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)


class RegionGrowClusterOptimizer:
    """
    Clusters cells using an R-tree-driven region growing approach.
    Produces a GeoJSON of clustered polygons with per-feature and file-level explanations.

    Key parameters:
      - max_volume: maximum allowed cluster volume (same units as 'volume' column)
      - min_volume: minimum allowed volume (if None => 0.7 * max_volume)
      - eps: proximity threshold in projected CRS units (meters in EPSG:3857)
    """

    def __init__(self, max_volume: float = 1000.0, epsilon: float = 50.0, min_volume: Optional[float] = None,
                 project_epsg: int = 3857):
        self.max_volume = float(max_volume)
        self.eps = float(epsilon)
        self.min_volume = float(min_volume) if min_volume is not None else 0.7 * float(max_volume)
        self.project_epsg = int(project_epsg)

        self.gdf: Optional[gpd.GeoDataFrame] = None
        self.boundary: Optional[Polygon] = None
        self.original_crs = None
        self.next_cluster_id = 0

    def load_data(self, input_file: Union[str, Dict[str, Any], gpd.GeoDataFrame],
                  boundary_file: Optional[Union[str, Dict[str, Any], gpd.GeoDataFrame]] = None):
        logging.info("Loading input features...")
        self.input_files = []
        self.input_data = []
        if isinstance(input_file, gpd.GeoDataFrame):
            gdf = input_file.copy()
            self.input_files.append("in-memory-gdf")
        elif isinstance(input_file, dict):
            # Accept in-memory GeoJSON from API callers.
            gdf = gpd.GeoDataFrame.from_features(input_file.get("features", []))
            self.input_files.append("in-memory-geojson")
        else:
            gdf = gpd.read_file(input_file)
            self.input_files.append(input_file)
        if "volume" not in gdf.columns:
            raise ValueError("Input GeoJSON must contain a 'volume' column")

        # Remove rows with non-positive volumes
        gdf = gdf[gdf["volume"] > 0].copy()
        gdf = gdf[gdf["depth"] > 0.2].copy()
        if gdf.empty:
            raise ValueError("No features with positive 'volume' found.")

        self.original_crs = gdf.crs
        if self.original_crs is None:
            logging.warning("Input CRS missing; assuming EPSG:4326. Consider setting correct CRS.")
            gdf = gdf.set_crs(epsg=4326)
            self.original_crs = gdf.crs

        # load boundary if provided
        if boundary_file:
            if isinstance(boundary_file, gpd.GeoDataFrame):
                b = boundary_file.copy()
                self.input_files.append("in-memory-boundary-gdf")
            elif isinstance(boundary_file, dict):
                b = gpd.GeoDataFrame.from_features(boundary_file.get("features", []))
                self.input_files.append("in-memory-boundary-geojson")
            else:
                b = gpd.read_file(boundary_file)
                self.input_files.append(boundary_file)
            b = b.to_crs(epsg=self.project_epsg)
            self.boundary = unary_union(b.geometry)
            self.input_data.append("geometry")
        # print(self.boundary)

        else:
            self.boundary = None

        # project to working CRS
        gdf = gdf.to_crs(epsg=self.project_epsg)
        G2 = self.boundary

        gdf['centroid'] = gdf.geometry.centroid

        # Filter rows where centroid is inside G2 (if boundary provided)
        if G2 is not None:
            gdf = gdf[gdf['centroid'].apply(lambda c: G2.contains(c))]

        # Drop the centroid column if not needed
        # gdf = filtered_gdf.drop(columns=['centroid'])
        # create area_id if missing
        if "area_id" not in gdf.columns:
            gdf = gdf.reset_index(drop=True)
            gdf["area_id"] = gdf.index.astype(str)

        # centroids for quick access
        gdf["centroid"] = gdf.geometry.centroid
        gdf["x"] = gdf.centroid.x
        gdf["y"] = gdf.centroid.y
        self.input_data.append("volume")
        self.gdf = gdf
        self.next_cluster_id = 0
        logging.info(f"Loaded {len(self.gdf)} features into working CRS EPSG:{self.project_epsg}")
        return self.gdf

    def _candidate_neighbors(self, geom, buffer_dist):
        """
        Use GeoDataFrame sindex to find candidate neighbor indices within buffer_dist of geometry bbox.
        """
        if self.gdf is None:
            return []
        sindex = self.gdf.sindex
        minx, miny, maxx, maxy = geom.bounds
        bbox = (minx - buffer_dist, miny - buffer_dist, maxx + buffer_dist, maxy + buffer_dist)
        return list(sindex.intersection(bbox))

    def _within_eps(self, a_geom, b_geom, eps):
        """
        Check if two geometries are connectable within eps (true geometric distance).
        """
        if a_geom.intersects(b_geom) or a_geom.touches(b_geom):
            return True, 0.0, "intersect_or_touch"

        d = a_geom.distance(b_geom)
        if d > eps:
            return False, d, "distance_gt_eps"

        # optional: you could check boundary cross here, but region-growing keeps it simple
        return True, d, "within_eps"

    def region_grow(self):
        """
        Main region-growing clustering algorithm.
        Assigns cluster_id to self.gdf['cluster_id'].
        """
        if self.gdf is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        n = len(self.gdf)
        visited = np.zeros(n, dtype=bool)
        cluster_ids = np.full(n, -9999, dtype=int)
        volumes = self.gdf["volume"].values.astype(float)
        geoms = list(self.gdf.geometry)

        cluster_counter = 0
        idx_iter = range(n)

        logging.info("Starting region-growing clustering...")
        for i in tqdm(idx_iter, desc="Seeding clusters"):
            if visited[i]:
                continue

            seed_idx = i
            queue = deque([seed_idx])
            visited[seed_idx] = True
            members = [seed_idx]
            current_volume = float(volumes[seed_idx])

            # BFS-like growth
            while queue:
                cur = queue.popleft()
                cur_geom = geoms[cur]
                candidates = self._candidate_neighbors(cur_geom, self.eps)
                for cand in candidates:
                    if cand == cur or visited[cand]:
                        continue
                    within, dist, reason = self._within_eps(cur_geom, geoms[cand], self.eps)
                    if not within:
                        continue
                    cand_vol = float(volumes[cand])
                    if (current_volume + cand_vol) > self.max_volume:
                        continue
                    # accept
                    visited[cand] = True
                    queue.append(cand)
                    members.append(cand)
                    current_volume += cand_vol

            # assign cluster id
            cid = cluster_counter
            for idx in members:
                cluster_ids[idx] = cid
            cluster_counter += 1

        self.gdf["cluster_id"] = cluster_ids
        self.next_cluster_id = int(cluster_counter)
        logging.info(f"Region-growing produced {self.next_cluster_id} clusters")
        return

    def split_large_clusters(self):
        """
        Split clusters exceeding max_volume (greedy packing by volume).
        """
        logging.info("Splitting large clusters...")
        vols = self.gdf.groupby("cluster_id")["volume"].sum().to_dict()
        large = [cid for cid, v in vols.items() if v > self.max_volume and cid >= 0]
        if not large:
            logging.info("No large clusters to split.")
            return

        for cid in tqdm(large, desc="Splitting clusters"):
            members = self.gdf[self.gdf["cluster_id"] == cid].sort_values("volume", ascending=False)
            if members.empty:
                continue
            bins = []
            current_bin = []
            current_sum = 0.0
            for idx, row in members.iterrows():
                v = float(row["volume"])
                if current_sum + v <= self.max_volume:
                    current_bin.append(idx)
                    current_sum += v
                else:
                    if current_bin:
                        bins.append((current_bin.copy(), current_sum))
                    current_bin = [idx]
                    current_sum = v
            if current_bin:
                bins.append((current_bin.copy(), current_sum))

            if len(bins) > 1:
                # keep first bin as original cid
                first_bin, _ = bins[0]
                self.gdf.loc[first_bin, "cluster_id"] = cid
                for b in bins[1:]:
                    new_cid = self.next_cluster_id
                    self.gdf.loc[b[0], "cluster_id"] = new_cid
                    self.next_cluster_id += 1

    def reassign_or_merge_small_clusters(self):
        """
        Reassign small clusters to nearby valid clusters or merge several small clusters into one.
        """
        logging.info("Handling small clusters (reassign/merge)...")
        grouped = self.gdf.groupby("cluster_id")
        cluster_vols = grouped["volume"].sum().to_dict()
        centroids = grouped.geometry.apply(lambda g: g.unary_union.centroid)

        small_clusters = [cid for cid, v in cluster_vols.items() if (v < self.min_volume and cid >= 0)]
        if not small_clusters:
            logging.info("No small clusters found.")
            return

        cl_df = pd.DataFrame({"cluster_id": list(centroids.index), "centroid": list(centroids.values)})
        cl_df = cl_df.set_index("cluster_id")

        for scid in tqdm(small_clusters, desc="Small clusters"):
            if scid not in cluster_vols:
                continue
            s_vol = cluster_vols.get(scid, 0.0)
            if s_vol >= self.min_volume:
                continue
            s_cent = cl_df.loc[scid, "centroid"]

            # compute distances to other clusters
            dists = []
            for ocid, ocent in cl_df["centroid"].items():
                if ocid == scid:
                    continue
                d = s_cent.distance(ocent)
                dists.append((ocid, d))
            dists.sort(key=lambda x: x[1])

            reassigned = False
            for ocid, _ in dists:
                if ocid not in cluster_vols:
                    continue
                t_vol = cluster_vols[ocid]
                if t_vol + s_vol <= self.max_volume:
                    # reassign
                    idxs = self.gdf[self.gdf["cluster_id"] == scid].index
                    self.gdf.loc[idxs, "cluster_id"] = ocid
                    cluster_vols[ocid] = t_vol + s_vol
                    del cluster_vols[scid]
                    reassigned = True
                    break

            if reassigned:
                continue

            # otherwise try greedy merge with nearest small clusters
            merged_idxs = list(self.gdf[self.gdf["cluster_id"] == scid].index)
            merged_vol = s_vol
            merged_cids = {scid}
            for ocid, _ in dists:
                if merged_vol >= self.min_volume:
                    break
                if ocid in merged_cids:
                    continue
                o_vol = cluster_vols.get(ocid, 0.0)
                if o_vol == 0.0 or (merged_vol + o_vol) > self.max_volume:
                    continue
                idxs = list(self.gdf[self.gdf["cluster_id"] == ocid].index)
                merged_idxs.extend(idxs)
                merged_vol += o_vol
                merged_cids.add(ocid)

            if self.min_volume <= merged_vol <= self.max_volume and len(merged_cids) > 1:
                new_cid = self.next_cluster_id
                self.gdf.loc[merged_idxs, "cluster_id"] = new_cid
                for old in merged_cids:
                    if old in cluster_vols:
                        del cluster_vols[old]
                cluster_vols[new_cid] = merged_vol
                self.next_cluster_id += 1

    def make_cluster_explanations(self):
        """
        Build per-cluster explanation text and supporting facts.
        Returns dict keyed by cluster_id with explanation attributes.
        """
        grouped = self.gdf.groupby("cluster_id")
        volumes = grouped["volume"].sum().to_dict()
        explanations = {}
        for cid, vol in volumes.items():
            members = self.gdf[self.gdf["cluster_id"] == cid]
            valid = (self.min_volume <= vol <= self.max_volume)
            parts = []
            if valid:
                parts.append(
                    f"Cluster {cid}: VALID — total volume {vol:.2f} within range ({self.min_volume:.2f} - {self.max_volume:.2f}).")
            else:
                if vol < self.min_volume:
                    parts.append(
                        f"Cluster {cid}: INVALID — total volume {vol:.2f} is less than minimum {self.min_volume:.2f}.")
                else:
                    parts.append(
                        f"Cluster {cid}: INVALID — total volume {vol:.2f} exceeds maximum {self.max_volume:.2f}.")
            # add proximity metric: approximate max centroid distance
            if len(members) > 1:
                cents = list(members.centroid.values)
                maxd = 0.0
                for i in range(len(cents)):
                    for j in range(i + 1, len(cents)):
                        d = cents[i].distance(cents[j])
                        if d > maxd:
                            maxd = d
                parts.append(f"Max centroid distance (approx): {maxd:.1f} units.")
            else:
                parts.append("Single member cluster.")
            explanations[cid] = {
                "cluster_total_volume": float(vol),
                "cluster_valid": bool(valid),
                "explanation": " ".join(parts)
            }
        return explanations

    def save_clustered_geojson(self, out_geojson: str, out_summary_json: str):
        """
        Save polygons with diagnostic fields and file-level summary JSON.
        Ensures only one geometry column exists before writing.
        """
        if self.gdf is None:
            raise RuntimeError("No data to save. Run optimize pipeline first.")

        # build cluster explanations
        cluster_info = self.make_cluster_explanations()
        unwanted = ["density", "depth", "explanation", "tooltip",
                    "cell_area", "nearest_bathy_distance", "image_path"]

        # Drop unwanted columns
        save_gdf = self.gdf.drop(columns=unwanted, errors="ignore").copy()

        # Add diagnostic fields
        save_gdf = save_gdf.assign(
            cluster_total_volume=save_gdf["cluster_id"].map(
                lambda cid: cluster_info.get(cid, {}).get("cluster_total_volume")
            ),
            cluster_valid=save_gdf["cluster_id"].map(
                lambda cid: cluster_info.get(cid, {}).get("cluster_valid")
            ),
            explanation=save_gdf["cluster_id"].map(
                lambda cid: cluster_info.get(cid, {}).get("explanation", "")
            ),
        )

        # Normalize geometry
        save_gdf = clean_geometries(save_gdf, geom_col="geometry")
        save_gdf["geometry"] = save_gdf.geometry.apply(ensure_polygon_geometry)

        # Drop duplicate geometry-like columns
        geom_cols = [c for c in save_gdf.columns if c.lower().startswith("geometry") and c != "geometry"]
        save_gdf = save_gdf.drop(columns=geom_cols).set_geometry("geometry")

        # CRS handling
        if self.original_crs is not None:
            try:
                save_gdf = save_gdf.to_crs(self.original_crs)
            except Exception:
                logging.warning("Could not reproject to original CRS; saving in working CRS.")

        # File summary
        number_valid_clusters = sum(v.get("cluster_valid") for v in cluster_info.values())
        file_summary = {
            "total_features": len(save_gdf),
            "total_clusters": len(cluster_info),
            "valid_clusters": number_valid_clusters,
            "max_volume": self.max_volume,
            "min_volume": self.min_volume,
            "coordinate_system": "EPSG:4326 (WGS84)",
            "input files": self.input_files,
            "input data": self.input_data,
            "main_output": "cluster_id",
            "additional_outputs": [
                "explanation",
                "cluster_total_volume",
                "cluster_valid",
            ],
            "output files": [],
            "output data": [],
            "global Explanation": [
                f"The algorithm clusters cells based on proximity, volume and capacity of the harvester to {len(cluster_info)} clusters that can be harvested in a single trip."
                f"{number_valid_clusters} clusters with a total volume of plants in the range ({self.min_volume},{self.max_volume}), the harvester capacity is {self.max_volume} ."
            ],
        }

        # Build GeoJSON normally
        geojson_data = json.loads(save_gdf.to_json())

        # Append metadata at the top level (not per feature)
        geojson_data["metadata"] = file_summary

        # Save GeoJSON with metadata
        with open(out_geojson, "w") as f:
            json.dump(geojson_data, f, indent=2)

        logging.info(f"Saving clustered polygons with metadata to {out_geojson}")

        with open(out_summary_json, "w") as fh:
            json.dump(file_summary, fh, indent=2)

        return save_gdf, file_summary


def cluster_aoi_by_capacity(
        volume_geojson: Union[Dict[str, Any], gpd.GeoDataFrame],
        max_volume: int,
        eps: int,
        output_polygons: Optional[str] = None,
        output_polygons_summary: Optional[str] = None,
        min_volume: Optional[int] = None,
        epsg: int = 3857,
        boundary_geojson: Optional[Union[Dict[str, Any], gpd.GeoDataFrame]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Cluster AOI features by capacity using region-growing with splitting and small-cluster handling.

    Parameters:
        volume_geojson: GeoJSON dict or GeoDataFrame containing polygon features with a 'volume' field.
        max_volume: maximum allowed total volume per cluster.
        eps: proximity threshold (in meters if EPSG:3857) for region-growing connectivity.
        min_volume: minimum desired cluster volume; if None, defaults to 0.7 * max_volume.
        epsg: working/projected CRS EPSG code (default 3857).
        boundary_geojson: optional boundary GeoJSON/GDF; features whose centroid lies outside are excluded.

    Returns:
        A tuple: (feature_collection_dict_with_metadata, summary_dict)
    """
    optimizer = RegionGrowClusterOptimizer(
        max_volume=max_volume,
        epsilon=eps,
        min_volume=min_volume,
        project_epsg=epsg,
    )

    # Load data from memory and run pipeline
    optimizer.load_data(volume_geojson, boundary_geojson)
    optimizer.region_grow()
    optimizer.split_large_clusters()
    optimizer.reassign_or_merge_small_clusters()

    # Use temp files if output paths not provided
    if output_polygons is None:
        output_polygons = tempfile.NamedTemporaryFile(delete=False, suffix=".geojson").name
    if output_polygons_summary is None:
        output_polygons_summary = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name

    polygons_gdf, summary = optimizer.save_clustered_geojson(output_polygons, output_polygons_summary)

    # Read back the saved GeoJSON as a dict (includes metadata)
    with open(output_polygons, "r") as f:
        feature_collection = json.load(f)

    return feature_collection, summary


if __name__ == '__main__':
    proximity_threshold = 50
    max_capacity = 100000
    min_capacity = 90000
    harvester_width = 20
    date = "2025-12-26"
    lake_name = "Maschsee"
    epsg_crs = "EPSG:3857"

    input_file = "../test_data/output/Maschsee_2025-12-26_volume_20m.geojson"
    output_file = f"{lake_name}_Clustered_Cap{max_capacity}_{harvester_width}m_{date}.geojson"
    summary_file = f"{lake_name}_Clustered_summary_Cap{max_capacity}_{harvester_width}m_{date}.geojson"
    # boundaries_file = f"lakes/boundaries/{lake_name}.geojson"

    cluster_aoi_by_capacity(
        input_file,
        max_capacity,
        proximity_threshold,
        output_file,
        summary_file,
        min_capacity,
        int(epsg_crs.split(':')[1]),
    )
