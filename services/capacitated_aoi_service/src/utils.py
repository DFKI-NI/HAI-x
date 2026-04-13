import math

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


def clean_geometries(gdf: gpd.GeoDataFrame, geom_col: str = "geometry") -> gpd.GeoDataFrame:
    # Find all columns with shapely geometries
    geom_cols = [
        c for c in gdf.columns
        if c != geom_col and gdf[c].apply(lambda x: hasattr(x, "geom_type")).all()
    ]

    if geom_cols:
        gdf = gdf.drop(columns=geom_cols)

    # Ensure single active geometry column
    gdf = gdf.set_geometry(geom_col)

    return gdf


def ensure_polygon_geometry(geom):
    """
    Normalize geometry to a MultiPolygon (or a safe Polygon placeholder) so
    writing to GeoJSON won't fail due to mixed geometry types.
    - fixes invalid geometries with buffer(0)
    - extracts polygonal parts from GeometryCollection
    - converts lines/points to small polygon via buffer (relative buffer size)
    - returns a MultiPolygon (or empty Polygon if nothing valid)
    """
    if geom is None:
        return Polygon()  # placeholder empty polygon

    try:
        # Quick validity fix
        if not getattr(geom, "is_valid", True):
            geom = geom.buffer(0)
    except Exception:
        # ignore buffer errors, continue with original geom
        pass

    if geom is None or geom.is_empty:
        return Polygon()

    gtype = geom.geom_type

    if gtype in ("Polygon", "MultiPolygon"):
        # ensure MultiPolygon for homogeneity
        if gtype == "Polygon":
            return MultiPolygon([geom])
        return geom

    if gtype == "GeometryCollection":
        # collect polygonal parts
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if polys:
            union = unary_union(polys)
            if union.geom_type == "Polygon":
                return MultiPolygon([union])
            return union  # likely MultiPolygon
        # fallback to convex_hull
        ch = geom.convex_hull
        if ch.geom_type == "Polygon":
            return MultiPolygon([ch])
        return ch

    # For Point/LineString/LinearRing/etc - create a small polygon by buffering.
    try:
        minx, miny, maxx, maxy = geom.bounds
        diag = math.hypot(maxx - minx, maxy - miny)
        # buffer size relative to feature extent (avoid absolute tiny values)
        buf = max(diag * 1e-3, 0.1)
        buffered = geom.buffer(buf)
        if buffered.is_empty:
            # Last resort: convex hull
            ch = geom.convex_hull
            if ch.geom_type == "Polygon":
                return MultiPolygon([ch])
            return ch
        if buffered.geom_type == "Polygon":
            return MultiPolygon([buffered])
        return buffered
    except Exception:
        return Polygon()
