import numpy as np
import math
import rasterio as rio
from collections import deque
from shapely.geometry.polygon import Polygon as ShapelyPolygon

from src.mowed_pixel import MowedPixel
from src.processing import get_timestamp_from_imagename


def get_position_from_satelite_image(image_name: str) -> tuple:
    """
    Get the position and resolution of the satellite image.

    :param image_name: Path to the satellite image file.
    :return: Tuple containing resolution, rectangle coordinates, and pixel size differences.
    """
    with rio.open(image_name) as src:
        # Get metadata from the image
        metadata = src.meta

    start_point_lon = metadata['transform'][2]
    start_point_lat = metadata['transform'][5]

    pixel_size_lon = metadata['transform'][0]  # Longitude pixel size
    pixel_size_lat = metadata['transform'][4]  # Latitude pixel size

    width = metadata['width']
    height = metadata['height']

    # Calculate the endpoint coordinates
    endpoint_lon = start_point_lon + pixel_size_lon * width
    endpoint_lat = start_point_lat + pixel_size_lat * height

    rectangle_cords = ((start_point_lat, start_point_lon), (endpoint_lat, endpoint_lon))
    diff_cords = (pixel_size_lat, pixel_size_lon)  # Pixel size differences
    resolution_image = (height, width)

    return resolution_image, rectangle_cords, diff_cords


def get_coordinats_by_image_name(image_name: str, fix_file_path: str) -> tuple:
    """
    Get the GPS coordinates for the given image name using a fix file, which contains GPS data and timestamps.

    :param image_name: Name of the image.
    :param fix_file_path: Path to the fix file containing GPS data.
    :return: Tuple of latitude and longitude.
    """
    last_coords = get_last_gps_coordinates(image_name, fix_file_path)

    try:
        direction_vector = get_direction_from_coordinates(last_coords)
    except ValueError:
        direction_vector = (0, 0)

    if sum(direction_vector) == 0:
        print("[get_coordinats_by_image_name] Warning: Direction vector is zero, cannot calculate new position.")

    new_lat, new_lon = calculat_new_gps_position(
        last_coords[-1][0],  # Last latitude
        last_coords[-1][1],  # Last longitude
        (direction_vector[1], direction_vector[0]),  # Swapped order for direction
        forward_m=11,  # Forward movement in meters
        transverse_m=-1  # Transverse movement in meters
    )

    return new_lat, new_lon


def get_last_gps_coordinates(image_name: str, fix_file_path: str, number_coordinates: int = 12) -> deque:
    """
    Retrieve the last GPS coordinates from the fix file.

    :param image_name: Name of the image.
    :param fix_file_path: Path to the fix file containing GPS data.
    :param number_coordinates: Maximum number of coordinates to retrieve.
    :return: Deque containing the last GPS coordinates.
    """
    timestamp = get_timestamp_from_imagename(image_name)
    last_coords = deque(maxlen=number_coordinates)

    with open(fix_file_path, 'r') as fix_file:
        for line in fix_file:
            line = line.strip().split(',')

            # Skip header lines or invalid data
            try:
                float(line[0])
            except ValueError:
                continue

            if len(line) == 3:
                last_coords.append((float(line[1]), float(line[2])))
                if float(line[0]) > timestamp:
                    break

    return last_coords


def get_direction_from_coordinates(coords):
    """
    Calculate the mean direction vector from a list of coordinates.

    :param coords: List of coordinates as tuples (latitude, longitude).
    :return: Mean direction vector as tuple (dx, dy).
    """
    direction_vectoren = []

    if len(coords) < 2:
        raise ValueError("Not enough coordinates to calculate direction.")
    
    for i in range(1, len(coords)):
        x1, y1 = coords[i - 1]
        x2, y2 = coords[i]
        vektor = (x2 - x1, y2 - y1)
        direction_vectoren.append(vektor)

    mean_vector = np.mean(direction_vectoren, axis=0)
    
    return mean_vector


def calculat_new_gps_position(lat: float, lon: float, direction: tuple, forward_m: float, transverse_m: float) -> tuple:
    """
    Calculate a new GPS position based on a starting position, direction vector, and movement.

    :param lat: Current latitude in degrees.
    :param lon: Current longitude in degrees.
    :param direction: Tuple (dx, dy) representing the direction vector (ΔLat, ΔLon).
    :param forward_m: Forward movement in meters.
    :param transverse_m: Transverse movement in meters (positive = right, negative = left).
    :return: New GPS position as tuple (new_lat, new_lon).
    """
    # Conversion factors for small distances
    meter_per_degree_lat = 111320  # Approximate meters per degree latitude
    meter_per_degree_lon = 40075000 * math.cos(math.radians(lat)) / 360  # Longitude depends on latitude

    # Normalize the direction vector
    dx, dy = direction
    length = math.hypot(dx, dy)
    if length == 0:
        print("[calculat_new_gps_position] Warning: Direction vector is zero, using (0, 0) as default.")
        return lat, lon  # No movement if the vector is zero
    dx_norm, dy_norm = dx / length, dy / length

    # Orthogonal vector (right of the direction)
    dx_orth, dy_orth = dy_norm, -dx_norm

    # Total shift in x/y direction (meters)
    shift_x = dx_norm * forward_m + dx_orth * transverse_m
    shift_y = dy_norm * forward_m + dy_orth * transverse_m

    # Convert shifts to degrees
    delta_lat = shift_y / meter_per_degree_lat
    delta_lon = shift_x / meter_per_degree_lon

    new_lat = lat + delta_lat
    new_lon = lon + delta_lon

    return new_lat, new_lon


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two GPS coordinates using the Haversine formula.

    :param lat1: Latitude of the first point in degrees.
    :param lon1: Longitude of the first point in degrees.
    :param lat2: Latitude of the second point in degrees.
    :param lon2: Longitude of the second point in degrees.
    :return: Distance between the two points in meters.
    """
    R = 6371000  # Radius of the Earth in meters

    # Convert degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in meters
    distance = R * c

    return distance


def define_water_pixels(mowed_pixel_array: list, coordinates_sea: list) -> list:
    """
    Mark pixels as water pixels based on their coordinates.

    :param mowed_pixel_array: Array of MowedPixel objects.
    :param coordinates_sea: List of coordinates defining the sea polygon.
    :return: Updated mowed_pixel_array with water pixels marked.
    """
    sea_polygone = ShapelyPolygon(coordinates_sea)

    for i in range(len(mowed_pixel_array)):
        for j in range(len(mowed_pixel_array[i])):
            # Check if the pixel is within the sea polygon
            if sea_polygone.contains(mowed_pixel_array[i][j].get_shapely_point()):
                mowed_pixel_array[i][j].in_sea = True

    return mowed_pixel_array


def create_mowed_pixel_array(resolution_lon: int, resolution_lat: int, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> list:
    """
    Create an array of MowedPixel objects based on the specified resolution and coordinates.

    :param resolution_lon: Number of pixels along the longitude.
    :param resolution_lat: Number of pixels along the latitude.
    :param start_lat: Starting latitude.
    :param start_lon: Starting longitude.
    :param end_lat: Ending latitude.
    :param end_lon: Ending longitude.
    :return: 2D array of MowedPixel objects.
    """
    dif_lat = (end_lat - start_lat) / resolution_lat
    dif_lon = (end_lon - start_lon) / resolution_lon

    # Initialize the array
    rectangle_array = [[None for _ in range(resolution_lon)] for _ in range(resolution_lat)]

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Calculate the start and end coordinates for each pixel
            start_coords = (start_lat + i * dif_lat, start_lon + j * dif_lon)
            end_coords = (start_lat + (i + 1) * dif_lat, start_lon + (j + 1) * dif_lon)

            # Create a MowedPixel object
            rectangle_array[i][j] = MowedPixel(start_coords, end_coords)

    return rectangle_array

