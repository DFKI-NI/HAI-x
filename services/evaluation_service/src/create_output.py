import numpy as np
import cv2
import rasterio as rio
from rasterio.transform import from_origin
from ipyleaflet import Map, Marker, Rectangle, Polygon, Polyline


def create_binary_image(mowed_pixel_array: list, start_lat: float, start_lon: float, dif_lon: float, dif_lat: float, output_path: str):
    """
    Create a binary image based on the mowed pixel array and save it as a GeoTIFF.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param start_lat: Starting latitude of the image.
    :param start_lon: Starting longitude of the image.
    :param dif_lon: Longitude difference per pixel.
    :param dif_lat: Latitude difference per pixel.
    :param output_path: Path to save the output GeoTIFF file.
    """
    resolution_lat = len(mowed_pixel_array)
    resolution_lon = len(mowed_pixel_array[0])

    # Initialize the image array
    image_array = np.zeros((resolution_lat, resolution_lon, 3))

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Get RGB color for each pixel
            image_array[i][j] = mowed_pixel_array[i][j].get_rgb_color()

    image_array = np.array(image_array, dtype=np.uint8)
    
    save_as_geotif(image_array, start_lat, start_lon, dif_lon, dif_lat, output_path)


def create_value_image(mowed_pixel_array: list, start_lat: float, start_lon: float, dif_lon: float, dif_lat: float, output_path: str, save_log_scale: bool = True):
    """
    Create a value image based on the mowed pixel array and save it as a GeoTIFF and PNG.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param start_lat: Starting latitude of the image.
    :param start_lon: Starting longitude of the image.
    :param dif_lon: Longitude difference per pixel.
    :param dif_lat: Latitude difference per pixel.
    :param output_path: Path to save the output GeoTIFF file.
    :param save_log_scale: Whether to save a log-scaled version of the image (default is True).
    """
    resolution_lat = len(mowed_pixel_array)
    resolution_lon = len(mowed_pixel_array[0])

    # Initialize the image array
    image_array = np.zeros((resolution_lat, resolution_lon, 3))

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Get the mowing amount for each pixel
            image_array[i][j] = mowed_pixel_array[i][j].mowes_ammount

    # Normalize and scale the image
    image_array = image_array / np.max(image_array)
    image_array = image_array * 255
    image_array = np.array(image_array, dtype=np.uint8)
    
    save_as_geotif(image_array, start_lat, start_lon, dif_lon, dif_lat, output_path)
    save_as_png(image_array, output_path.replace('.tif', '.png'))

    if not save_log_scale:
        return
    
    # Create a log-scaled version of the image
    epsilon = 1e-10
    log_scaled_image_array = image_array / 255.0
    log_scaled_image_array = np.log(log_scaled_image_array + epsilon)
    min_val = np.min(log_scaled_image_array)
    max_val = np.max(log_scaled_image_array)
    log_scaled_image_array = (log_scaled_image_array - min_val) / (max_val - min_val)
    log_scaled_image_array = log_scaled_image_array * 255
    log_scaled_image_array = np.array(log_scaled_image_array, dtype=np.uint8)
    save_as_geotif(log_scaled_image_array, start_lat, start_lon, dif_lon, dif_lat, output_path.replace('.tif', '_log.tif'))


def create_value_image_with_lake_form(mowed_pixel_array: list, start_lat: float, start_lon: float, dif_lon: float, dif_lat: float, output_path: str):
    """
    Create a value image with lake form adjustments and save it as a GeoTIFF.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param start_lat: Starting latitude of the image.
    :param start_lon: Starting longitude of the image.
    :param dif_lon: Longitude difference per pixel.
    :param dif_lat: Latitude difference per pixel.
    :param output_path: Path to save the output GeoTIFF file.
    """
    resolution_lat = len(mowed_pixel_array)
    resolution_lon = len(mowed_pixel_array[0])

    # Initialize the image array
    image_array = np.zeros((resolution_lat, resolution_lon, 3))

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Adjust pixel values for lake form
            image_array[i][j] = mowed_pixel_array[i][j].mowes_ammount
            if not mowed_pixel_array[i][j].in_sea and mowed_pixel_array[i][j].mowes_ammount == 0:
                image_array[i][j] = (1.5, 1.5, 1.5)

    # Normalize and scale the image
    image_array = image_array / np.max(image_array)
    image_array = image_array * 255
    image_array = np.array(image_array, dtype=np.uint8)
    
    save_as_geotif(image_array, start_lat, start_lon, dif_lon, dif_lat, output_path)


def create_num_pass_thrue_image(mowed_pixel_array: list, start_lat: float, start_lon: float, dif_lon: float, dif_lat: float, output_path: str):
    """
    Create an image showing the number of passes through each pixel and save it as a GeoTIFF.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param start_lat: Starting latitude of the image.
    :param start_lon: Starting longitude of the image.
    :param dif_lon: Longitude difference per pixel.
    :param dif_lat: Latitude difference per pixel.
    :param output_path: Path to save the output GeoTIFF file.
    """
    resolution_lat = len(mowed_pixel_array)
    resolution_lon = len(mowed_pixel_array[0])

    # Initialize the image array
    image_array = np.zeros((resolution_lat, resolution_lon, 3))

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Get the number of passes through each pixel
            image_array[i][j] = mowed_pixel_array[i][j].number_pass_through

    image_array = np.array(image_array, dtype=np.uint8)
    
    save_as_geotif(image_array, start_lat, start_lon, dif_lon, dif_lat, output_path)


def save_as_geotif(image_array, start_lat, start_lon, dif_lon, dif_lat, output_path):
    """
    Save the image array as a GeoTIFF file.

    :param image_array: The image array to save.
    :param start_lat: Starting latitude of the image.
    :param start_lon: Starting longitude of the image.
    :param dif_lon: Longitude difference per pixel.
    :param dif_lat: Latitude difference per pixel.
    :param output_path: Path to save the GeoTIFF file.
    """

    # Die Funktion from_origin(west, north, xsize, ysize) erwartet:
    # west: Längengrad der linken oberen Ecke (also der westlichste Punkt),
    # north: Breitengrad der linken oberen Ecke (also der nördlichste Punkt),
    # xsize: Pixelbreite in Längengrad (positiv nach Osten),
    # ysize: Pixelhöhe in Breitengrad (positiv nach Süden, obwohl der Zahlenwert der koordinaten nach Süeden kleinder wird).
    dif_lat = abs(dif_lat)

    transform = from_origin(start_lon, start_lat, dif_lon, dif_lat)  # (west, north, xsize, ysize)

    with rio.open(
        output_path,
        'w',
        driver='GTiff',
        height=image_array.shape[0],
        width=image_array.shape[1],
        count=3,
        dtype=image_array.dtype,
        crs='+proj=latlong',
        transform=transform,
    ) as dst:
        for i in range(1, 4):
            dst.write(image_array[:, :, i-1], i)


def save_as_png(image_array: np.ndarray, output_path: str):
    """
    Save the image array as a PNG file.

    :param image_array: The image array to save.
    :param output_path: Path to save the PNG file.
    """
    cv2.imwrite(output_path, image_array)


def create_leaflet_map(mowed_pixel_array: list, resolution_lat: int, resolution_lon: int, output_path: str, only_mowed_areas: bool = True):
    """
    Create an interactive Leaflet map based on the mowed pixel array and save it as an HTML file.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param resolution_lat: Number of pixels along the latitude.
    :param resolution_lon: Number of pixels along the longitude.
    :param output_path: Path to save the Leaflet map HTML file.
    :param only_mowed_areas: If True, only include areas with mowing activity (default is True).
    """
    gps_coords = (52.353, 9.745)  # Default GPS coordinates for map center
    map = Map(center=gps_coords, zoom=14)

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Check if the pixel is in the sea
            if mowed_pixel_array[i][j].in_sea:
                if only_mowed_areas:
                    # Skip pixels with no mowing activity
                    if mowed_pixel_array[i][j].get_mowed_ammount() <= 0:
                        continue
                # Add the pixel as a rectangle to the map
                map.add(mowed_pixel_array[i][j].get_ipyleaflet_rectangle())

    # Save the map as an HTML file
    map.save(output_path)



def create_geojson(mowed_pixel_array: list, output_path: str, resolution_lat: int, resolution_lon: int, only_mowed_areas: bool = True, with_color_properties: bool = True):
    """
    Create a GeoJSON file based on the mowed pixel array.

    :param mowed_pixel_array: 2D array of MowedPixel objects.
    :param output_path: Path to save the GeoJSON file.
    :param resolution_lat: Number of pixels along the latitude.
    :param resolution_lon: Number of pixels along the longitude.
    :param only_mowed_areas: If True, only include areas with mowing activity (default is True).
    :param with_color_properties: If True, include color properties in the GeoJSON features (default is True).
    """
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for i in range(resolution_lat):
        for j in range(resolution_lon):
            # Check if the pixel is in the sea
            if mowed_pixel_array[i][j].in_sea:
                if only_mowed_areas:
                    # Skip pixels with no mowing activity
                    if mowed_pixel_array[i][j].get_mowed_ammount() <= 0:
                        continue
                # Add the pixel as a GeoJSON feature
                geojson["features"].append(mowed_pixel_array[i][j].get_geojson_rectangle(with_color_properties))

    # Convert the GeoJSON dictionary to a string and save it to a file
    geojson_string = str(geojson).replace("'", '"')
    with open(output_path, 'w') as geojson_file:
        geojson_file.write(geojson_string)

