import datetime
import glob
import os
import shutil
from pathlib import Path

import numpy as np
import osmnx as ox
import rasterio
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    WmsRequest,
    MimeType,
    MosaickingOrder,
    SentinelHubRequest,
    SentinelHubDownloadClient,
    bbox_to_dimensions,
)
from sentinelhub import SHConfig

from src.clustering import estimate_areas_of_interest, _get_lat_lon_from_tiff
from src.evalscripts import evalscript_apa
from src.sentinelhub_connector import get_config
from src.utils import save_areas_of_interests_to_json, get_request_dt


def get_satellite_data(config: SHConfig, data_dir: str,
                       time_frame: list, copernicus_data_service: str,
                       resolution_in_m: int = 10, max_cloud_coverage: float = 0.8,
                       lake_query: str = None, bbox_coordinates: str = None) -> list:
    """
    Download and process satellite data for the specified area and time frame.

    Args:
        config: SentinelHub configuration object
        data_dir: Directory path where downloaded data will be stored
        time_frame: List of [start_date, end_date] strings in format 'YYYY-MM-DD'
        copernicus_data_service: Name of the Copernicus data service layer
        resolution_in_m: Resolution in meters (default: 10)
        max_cloud_coverage: Maximum cloud coverage allowed in images (0.0-1.0, default: 0.8)
        lake_query: Optional query string for lake boundaries (e.g., "Maschsee, Hannover, Germany")
        bbox_coordinates: String containing comma-separated coordinates in format 'minLong, minLat, maxLong, maxLat'

    Returns:
        list: List of downloaded and processed satellite image data arrays
    """
    if bbox_coordinates is not None:
        bbox, size = _convert_box_coords_to_bbox(bbox_coordinates, resolution_in_m)
    elif lake_query is not None:
        bbox_coordinates = get_lake_box_boundaries(lake_query)
        bbox, size = _convert_box_coords_to_bbox(bbox_coordinates, resolution_in_m)
    else:
        raise ValueError(
            "Either bbox_coordinates or lake_query must be provided.\n" +
            "lake_query: Optional query string for lake boundaries (e.g., 'Maschsee, Hannover, Germany')\n" +
            "bbox_coordinates: String containing comma-separated coordinates in format 'minLong, minLat, maxLong, maxLat'"
        )

    time_slots = get_dates_with_images(config, copernicus_data_service, bbox, size, time_frame,
                                       resolution_in_m=resolution_in_m, max_cloud_coverage=max_cloud_coverage)

    def _get_sentinel_request(time_interval: tuple, evalscript: str, save_dir: str = None) -> SentinelHubRequest:
        # Helper function for handling multiple requests
        return SentinelHubRequest(
            evalscript=evalscript,
            data_folder=save_dir,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=time_interval,
                    mosaicking_order=MosaickingOrder.LEAST_CC,
                    maxcc=max_cloud_coverage
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=size,
            config=config,
        )

    # Download data from copernicus dataspace
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    else:
        try:
            shutil.rmtree(data_dir)
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))
            raise e

    # due to a bug, this needs later to be set for the dl-requests
    COPERNICUS_API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

    dict_of_requests = {slot[0].split('T')[0]: _get_sentinel_request(slot, evalscript=evalscript_apa, save_dir=data_dir)
                        for slot in
                        time_slots}
    dict_of_requests = {slot: request.download_list[0] for slot, request in
                        dict_of_requests.items()}  # download all images from time frame
    for slot, dl_item in dict_of_requests.items():
        dl_item.url = COPERNICUS_API_URL

    result_dict = dict()
    for slot, dl_item in dict_of_requests.items():
        result_dict[slot] = {
            "raw_apa": SentinelHubDownloadClient(config=config).download([dl_item], max_threads=1)[0]
        }
    result_dict = {k: d for k, d in result_dict.items() if
                   np.max(d["raw_apa"]) - np.min(d["raw_apa"]) > 0.0}  # filter empty data

    # post process the downloaded data
    _filter_empty_tiffs(data_dir)
    remaining_tiffs = glob.glob(os.path.join(data_dir, "*/*.tiff"))
    if len(remaining_tiffs) == 0:  # If no tiff left, return empty dict
        return dict()

    _rename_folders_to_dates(data_dir)

    shp_file = _get_lake_shp(lake_query)
    if shp_file is not None:
        _crop_images_to_lake_boundaries(data_dir, shp_file)

    cropped_tiffs = glob.glob(os.path.join(data_dir, "cropped/*.tiff"))
    for cropped_tif in cropped_tiffs:
        date = cropped_tif.split('/')[-1][:-5]
        result_dict[date]['cropped_apa'] = np.moveaxis(rasterio.open(cropped_tif).read(), 0, -1)

        result_dict[date]['gps'] = _get_lat_lon_from_tiff(cropped_tif)

    return result_dict


def get_lake_box_boundaries(lake_query: str, crs='EPSG:4326') -> str:
    try:
        lake_gdf = ox.features_from_place(lake_query, tags={"natural": "water"})
        if lake_gdf.empty:
            lake_gdf = ox.features_from_address(lake_query.split(",")[0], tags={"natural": "water"})
        bounds = lake_gdf.bounds
        bounds_str = ", ".join([
            str(bounds['minx'].item()),
            str(bounds['miny'].item()),
            str(bounds['maxx'].item()),
            str(bounds['maxy'].item()),
        ])
        return bounds_str
    except Exception as e:
        print(f"OSM Error for {lake_query}: {e}")
        return e


def _filter_empty_tiffs(data_dir: str) -> None:
    """
    Remove directories containing empty TIFF files (with zero variance).

    Args:
        data_dir: Directory path containing downloaded satellite data

    Returns:
        None
    """
    dl_data = glob.iglob(data_dir + '*/*.tiff', recursive=True)
    for dl in dl_data:
        dl = Path(dl)
        img = rasterio.open(dl)
        if np.var(img.read()) == 0.0:
            shutil.rmtree(dl.parent)  # remove empty tiffs


def _rename_folders_to_dates(data_dir: str) -> None:
    """
    Rename downloaded data folders to their corresponding acquisition dates.

    Extracts dates from request.json files and renames folders to YYYY-MM-DD format.
    If a folder with the same date already exists, the duplicate folder is removed.

    Args:
        data_dir: Directory path containing downloaded satellite data

    Returns:
        None

    Reference:
        https://forum.sentinel-hub.com/t/translate-filename-of-downloaded-s2l2a-data-into-dates/2000/2
    """
    folders = glob.glob(data_dir + '/*[!cropped]*')
    dates = [get_request_dt(f'{folder}/request.json') for folder in folders]
    for folder, date in zip(folders, dates):
        new_folder = Path(folder).parent / date.strftime('%Y-%m-%d')
        if not os.path.exists(new_folder):
            os.rename(folder, new_folder)
        else:
            shutil.rmtree(folder, ignore_errors=True)


def _crop_images_to_lake_boundaries(data_dir: str, shp_file: str) -> None:
    """
    Crop satellite images to lake boundaries defined by a shapefile.

    Uses gdalwarp to clip images based on the lake shapefile boundaries.
    Creates a 'cropped' subdirectory to store the resulting images.

    Args:
        data_dir: Directory path containing downloaded satellite data
        shp_file: Path to the shapefile defining lake boundaries

    Returns:
        None
    """
    cropped_path = Path(data_dir + '/cropped/')
    if not os.path.exists(cropped_path):
        os.makedirs(cropped_path)

    # cut each image
    input_img_paths = [Path(img_path) for img_path in glob.iglob(data_dir + '/*/*.tiff')]
    for img_path in input_img_paths:
        img_id = img_path.parent.name
        img_out_path = cropped_path / (str(img_id) + '.tiff')
        command = f"gdalwarp -dstnodata NoData -cutline '{shp_file}' '{img_path}' '{img_out_path}'"
        os.system(command)


def _get_lake_shp(lake_query: str) -> str:
    """
    Retrieve lake boundaries from OpenStreetMap and save as a shapefile.

    Args:
        lake_query: A string containing the lake name and location (e.g., "Maschsee, Hannover, Germany")

    Returns:
        str: Path to the created shapefile, or None if the lake could not be found

    Raises:
        Various exceptions related to file operations are caught and logged
    """
    try:
        lake_gdf = ox.features_from_place(lake_query, tags={"natural": "water"})
        if lake_gdf.empty:
            lake_gdf = ox.features_from_address(lake_query.split(",")[0],
                                                tags={"natural": "water"})
    except Exception as e:
        print(f"OSM Error for {lake_query}: {e}")
        return None

    if not (lake_gdf is None):
        result = {"name": lake_query.split(",")[0], "found": True, "gdf": lake_gdf}
    else:
        return None

    folder_name = f"{result['name']}"
    if not os.path.exists(folder_name):
        try:
            os.makedirs(folder_name)
        except FileExistsError:
            print(f"One or more directories in '{folder_name}' already exist.")
        except PermissionError:
            print(f"Permission denied: Unable to create '{folder_name}'.")
        except Exception as e:
            print(f"An error occurred: {e}")
    file_name = f"{folder_name}/{result['name']}_boundaries.shp"
    result['gdf'].to_file(file_name)
    return file_name


def _convert_box_coords_to_bbox(bbox_coordinates: str, resolution_in_m: int) -> tuple:
    """
    Convert bounding box coordinates string to BBox object and calculate dimensions.

    Args:
        bbox_coordinates: String containing comma-separated coordinates in format 'minLong, minLat, maxLong, maxLat'
        resolution_in_m: Resolution in meters for calculating image dimensions

    Returns:
        tuple: A tuple containing (BBox object, size dimensions tuple)

    Raises:
        AssertionError: If bbox_coordinates doesn't contain exactly 4 values
    """
    bbox_coordinates = [float(i.strip()) for i in bbox_coordinates.split(',')]
    assert len(bbox_coordinates) == 4
    bbox_coordinates = tuple(bbox_coordinates)
    bbox = BBox(bbox=bbox_coordinates, crs=CRS.WGS84)
    size = bbox_to_dimensions(bbox, resolution=resolution_in_m)
    return bbox, size


def get_dates_with_images(config: SHConfig, copernicus_data_service: str, bbox: BBox,
                          size: tuple, time_frame: list, resolution_in_m: int = 10, max_cloud_coverage: float = 0.5) -> list:
    """
    Get dates with available satellite images for the specified area and time frame.

    Args:
        config: SentinelHub configuration object
        copernicus_data_service: Name of the Copernicus data service layer
        bbox: BBox object defining the area of interest
        size: Tuple of (width, height) dimensions for the image
        time_frame: List of [start_date, end_date] strings in format 'YYYY-MM-DD'
        resolution_in_m: Resolution in meters (default: 10)

    Returns:
        list: List of time slots as tuples (start_time, end_time) for each available date
    """
    # get the wms request to obtain dates with available images
    wms_request = WmsRequest(
        data_collection=DataCollection.SENTINEL2_L2A,
        layer=copernicus_data_service,
        bbox=bbox,
        time=time_frame,
        width=size[0],
        image_format=MimeType.TIFF,
        time_difference=datetime.timedelta(hours=2),
        config=config,
        maxcc=max_cloud_coverage
    )

    # obtain the dates
    edges = wms_request.get_dates()
    slots = [(f'{dt.date()}T00:00:00+01:00', f'{dt.date()}T23:59:59+01:00') for dt in edges]

    return slots


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True)
    parser.add_argument('--bbox_coordinates', type=str, required=True,
                        help="Please provide as str, e.g.,'minLong, minLat, maxLong, minLat'")
    parser.add_argument('--resolution', type=int, required=False, default=10)
    parser.add_argument('--start-time', type=str, required=True,
                        help="Start time in the format yyyy-mm-dd, e.g. '2024-05-13'")
    parser.add_argument('--end-time', type=str, required=True,
                        help="End time in the format yyyy-mm-dd, e.g. '2024-05-14'")
    parser.add_argument('--service', type=str, required=False,
                        help="Service as defined in the Copernicus Dashboard, e.g., 'ALL-BANDS-TRUE-COLOR'",
                        default='ALL-BANDS-TRUE-COLOR')

    args = parser.parse_args()
    config_profile = args.config
    bbox_coordinates = args.bbox_coordinates  # [float(i.strip()) for i in args.bbox_coordinates.split(',')]
    # bbox_coordinates = tuple(bbox_coordinates)
    resolution_in_m = args.resolution
    time_frame = [args.start_time, args.end_time]
    copernicus_data_service = args.service
    max_cloud_coverage = 0.8  # currently hardcoded
    data_dir = './images/maschsee/'
    lake_query = "Maschsee, Hannover, Germany"

    try:
        config = SHConfig(config_profile)
    except:
        client_id = input("Please provide OAuth Client ID: ")
        client_secret = input("Please provide OAuth Client Secret: ")
        instance_id = input("Please provide Instance ID: ")
        config = get_config(
            client_id,
            client_secret,
            instance_id
        )

    data = get_satellite_data(
        config,
        data_dir,
        time_frame,
        copernicus_data_service,
        resolution_in_m=resolution_in_m,
        max_cloud_coverage=max_cloud_coverage,
        lake_query=lake_query
    )

    # generate dictionary with data-dates key-value pairs
    dl_data = [Path(i) for i in glob.iglob(data_dir + '/cropped/*[!cropped]*.tiff', recursive=True)]
    data_and_dates = dict()
    for dl in dl_data:
        request_file = dl.parent.parent / dl.stem / 'request.json'
        date = get_request_dt(request_file)
        data_and_dates[date] = dl

    ## Clustering and AI Part
    latest_key = list(data_and_dates.keys())[0]  # latest image

    categories = ['none', 'low', 'medium', 'high', 'vegetation']
    list_of_areas = estimate_areas_of_interest(data_and_dates[latest_key], ['medium', 'high'], n_areas=20,
                                               categories=categories)

    areas_of_interests = [a.points[a.vertices, :].tolist() for a in list_of_areas]
    save_areas_of_interests_to_json(areas_of_interests, 'areas_of_interests.json')
