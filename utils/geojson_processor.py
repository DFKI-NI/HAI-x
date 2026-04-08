"""
GeoJSON Processor Utility

This module provides functions to extract specific fields from GeoJSON data
while preserving mandatory location information. This reduces the amount of
data stored in the database.

Example usage with bathymetry data:
    from utils.geojson_processor import extract_geojson_fields
    
    # Extract only depth field from bathymetry GeoJSON
    reduced_geojson = extract_geojson_fields(
        geojson_data,
        fields_to_extract=['estimated_depth', 'depth']
    )
"""

import json
from typing import Union


def extract_geojson_fields(
    geojson_data: Union[dict, str],
    fields_to_extract: list[str],
    include_all_if_missing: bool = False
) -> dict:
    """
    Extract specific fields from GeoJSON features while preserving location information.
    
    Location information (geometry) is always mandatory and included in the output.
    
    Args:
        geojson_data: GeoJSON data as a dictionary or JSON string.
        fields_to_extract: List of property field names to extract from each feature.
                          Only these fields will be kept in the properties.
        include_all_if_missing: If True, include all properties when none of the
                               specified fields are found. If False, return empty
                               properties dict.
    
    Returns:
        A new GeoJSON dictionary with reduced data containing only:
        - type: The GeoJSON type (e.g., "FeatureCollection")
        - features: List of features with:
            - type: "Feature"
            - geometry: Full geometry object (mandatory location info)
            - properties: Only the specified fields that exist
    
    Example:
        >>> geojson = {
        ...     "type": "FeatureCollection",
        ...     "features": [{
        ...         "type": "Feature",
        ...         "geometry": {"type": "Point", "coordinates": [9.745, 52.353]},
        ...         "properties": {
        ...             "estimated_depth": 2.5,
        ...             "temperature": 18.0,
        ...             "timestamp": "2024-01-01",
        ...             "sensor_id": "ABC123"
        ...         }
        ...     }]
        ... }
        >>> result = extract_geojson_fields(geojson, ['estimated_depth'])
        >>> # Result will only contain geometry and estimated_depth property
    """
    # Parse JSON string if necessary
    if isinstance(geojson_data, str):
        geojson_data = json.loads(geojson_data)
    
    # Handle single feature
    if geojson_data.get('type') == 'Feature':
        return _extract_from_feature(geojson_data, fields_to_extract, include_all_if_missing)
    
    # Handle FeatureCollection
    if geojson_data.get('type') == 'FeatureCollection':
        reduced_features = []
        for feature in geojson_data.get('features', []):
            reduced_feature = _extract_from_feature(feature, fields_to_extract, include_all_if_missing)
            reduced_features.append(reduced_feature)
        
        return {
            'type': 'FeatureCollection',
            'features': reduced_features
        }
    
    # Return as-is if not a recognized GeoJSON type
    return geojson_data


def _extract_from_feature(
    feature: dict,
    fields_to_extract: list[str],
    include_all_if_missing: bool
) -> dict:
    """
    Extract specific fields from a single GeoJSON feature.
    
    Args:
        feature: A GeoJSON Feature object.
        fields_to_extract: List of property field names to extract.
        include_all_if_missing: Include all properties if none of the specified fields exist.
    
    Returns:
        A new Feature dict with only the specified properties and full geometry.
    """
    properties = feature.get('properties', {}) or {}
    
    # Extract only the specified fields
    extracted_properties = {}
    for field in fields_to_extract:
        if field in properties:
            extracted_properties[field] = properties[field]
    
    # If no fields were found and include_all_if_missing is True, keep all
    if not extracted_properties and include_all_if_missing:
        extracted_properties = properties
    
    return {
        'type': 'Feature',
        'geometry': feature.get('geometry'),  # Always include full geometry (location)
        'properties': extracted_properties
    }


def extract_bathymetry_fields(geojson_data: Union[dict, str]) -> dict:
    """
    Convenience function to extract bathymetry-specific fields.
    
    Extracts depth-related fields: 'estimated_depth', 'depth'
    
    Args:
        geojson_data: Bathymetry GeoJSON data.
    
    Returns:
        Reduced GeoJSON with only depth and location information.
    """
    return extract_geojson_fields(
        geojson_data,
        fields_to_extract=['estimated_depth', 'depth'],
        include_all_if_missing=False
    )


def extract_apa_fields(geojson_data: Union[dict, str]) -> dict:
    """
    Convenience function to extract APA index-specific fields.
    
    Extracts APA-related fields: 'apa_value', 'apa', 'index'
    
    Args:
        geojson_data: APA index GeoJSON data.
    
    Returns:
        Reduced GeoJSON with only APA value and location information.
    """
    return extract_geojson_fields(
        geojson_data,
        fields_to_extract=['apa_value', 'apa', 'index', 'date'],
        include_all_if_missing=False
    )


def build_volume_geojson(lake_name: str, date: str) -> dict:
    """
    Build a GeoJSON FeatureCollection from plant_volume data in the database.

    Queries the plant_volume table for the given lake_name and date, and
    returns a FeatureCollection where each row becomes a Feature with a
    Polygon geometry (small square around lat/lon) and volume properties.

    Args:
        lake_name: Name of the lake to query.
        date: Date string (e.g. '2025-12-26') to filter by.

    Returns:
        A GeoJSON FeatureCollection dict with volume features.
    """
    from utils.database import database as db
    from utils import variables as var

    # Query plant_volume rows for the given lake and date
    df = db.open_table(
        var.SCHEMA, var.PLANT_VOLUME, var.PLANT_VOLUME_COLS,
        filter=None, order_by='idx'
    )

    # Filter by lake_name and date
    if not df.empty:
        df = df[df['lake_name'] == lake_name]
    if not df.empty:
        df = df[df['date'].astype(str) == str(date)]

    features = []
    # Small offset for creating a square polygon around each point (~20m)
    dlat = 0.0001  # approx 11m
    dlon = 0.00015  # approx 10m at ~52° latitude

    for _, row in df.iterrows():
        lat = float(row['lat']) if row['lat'] is not None else 0.0
        lon = float(row['lon']) if row['lon'] is not None else 0.0
        volume = float(row['volume']) if row['volume'] is not None else 0.0
        apa_value = float(row['apa_value']) if row['apa_value'] is not None else None
        depth = float(row['depth']) if row['depth'] is not None else None

        # Create a small polygon around the point
        coords = [[
            [lon - dlon, lat - dlat],
            [lon + dlon, lat - dlat],
            [lon + dlon, lat + dlat],
            [lon - dlon, lat + dlat],
            [lon - dlon, lat - dlat],
        ]]

        properties = {
            'volume': volume,
            'date': str(date),
            'lake_name': lake_name,
        }
        if apa_value is not None:
            properties['apa_value'] = apa_value
        if depth is not None:
            properties['depth'] = depth

        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': coords,
            },
            'properties': properties,
        }
        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features,
    }


def geojson_to_json_string(geojson_data: dict, compact: bool = True) -> str:
    """
    Convert GeoJSON dict to JSON string.
    
    Args:
        geojson_data: GeoJSON dictionary.
        compact: If True, produce compact JSON without extra whitespace.
    
    Returns:
        JSON string representation.
    """
    if compact:
        return json.dumps(geojson_data, separators=(',', ':'))
    return json.dumps(geojson_data, indent=2)
