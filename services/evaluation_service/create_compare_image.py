import numpy as np
import os
import tqdm
import cv2
import math
import datetime
from collections import deque
import logging

from shapely.geometry import Point as ShapelyPoint
from src.geo_utils import get_position_from_satelite_image, get_coordinats_by_image_name, haversine, create_mowed_pixel_array, define_water_pixels
from src.model_utils import get_prediction_model, get_harmony_matrix
from src.processing import get_syncronos_imag_list, detect_weed, get_folders, wrap_image, crop_image
from src.create_output import create_value_image_with_lake_form, create_leaflet_map, create_geojson, create_binary_image, create_value_image, create_num_pass_thrue_image, save_as_geotif, save_as_png


def create_compare_image(
    resolution_lat: int,
    resolution_lon: int,
    rectangle_cords: tuple,
    satellite_image_path: str,
    coordinates_sea: list,
    ann_model_path: str,
    harmony_matrix_path: str,
    data_folder_path: str,
    folder_uniq_name: str,
    rgb_folder_name: str,
    infra_folder_name: str,
    time_tolderance: float,
    imageCrop: tuple,
    output_path: str
):
    """
    Create a comparison image based on satellite data and other inputs.

    :param resolution_lat: Number of pixels along the latitude.
    :param resolution_lon: Number of pixels along the longitude.
    :param rectangle_cords: Tuple containing the top-left and bottom-right coordinates of the area.
    :param satellite_image_path: Path to the satellite image file.
    :param coordinates_sea: List of coordinates defining the sea polygon.
    :param ann_model_path: Path to the trained PyTorch model for weed detection.
    :param harmony_matrix_path: Path to the homography matrix file.
    :param data_folder_path: Path to the folder containing image data.
    :param folder_uniq_name: Unique name to filter folders in the data folder.
    :param rgb_folder_name: Name of the folder containing RGB images.
    :param infra_folder_name: Name of the folder containing infrared images.
    :param time_tolderance: Maximum allowed time difference for image synchronization.
    :param imageCrop: Tuple defining the crop region (x_start, y_start, x_width, y_height).
    :param output_path: Path to save the output files.
    """
    print("[main] starting")

    x_start, y_start, x_width, y_height = imageCrop

    start_lat = rectangle_cords[0][0]
    start_lon = rectangle_cords[0][1]
    end_lat = rectangle_cords[1][0]
    end_lon = rectangle_cords[1][1]

    dif_lat = (end_lat - start_lat) / resolution_lat
    dif_lon = (end_lon - start_lon) / resolution_lon

    # Get satellite image metadata
    satellite_img_available = os.path.exists(satellite_image_path)
    if not satellite_img_available:
        print(f"[main] Satellite image not found at {satellite_image_path}.")
    else:
        satellite_img_resolution, rectangle_cords_satallite, diff_cords_satallite = get_position_from_satelite_image(satellite_image_path)

        print(f"[main] satellite image resolution: {satellite_img_resolution}")
        print(f"[main] satellite image rectangle cords: {rectangle_cords_satallite}")
        print(f"[main] satellite image pixel diff cords: {diff_cords_satallite}")

    print(f"[main] output image resolution: {resolution_lat}, {resolution_lon}")
    print(f"[main] image rectangle cords: {rectangle_cords}")
    print(f"[main] image pixel diff cords: {dif_lat}, {dif_lon}")

    # Use satellite image resolution and coordinates if confirmed
    if satellite_img_available:
        user_input = 'y'  # For testing purposes, set to 'y'
    else:
        user_input = 'n'
    if user_input == 'y':
        resolution_lat = satellite_img_resolution[0]
        resolution_lon = satellite_img_resolution[1]

        start_lat = rectangle_cords_satallite[0][0]
        start_lon = rectangle_cords_satallite[0][1]
        end_lat = rectangle_cords_satallite[1][0]
        end_lon = rectangle_cords_satallite[1][1]

        dif_lat = diff_cords_satallite[0]
        dif_lon = diff_cords_satallite[1]

    # Calculate pixel distances
    distanz = haversine(start_lat, start_lon, start_lat + dif_lat, start_lon)
    print(f"[main] Pixel length in latitude direction: {round(distanz, 2)} meters.")

    distanz = haversine(start_lat, start_lon, start_lat, start_lon + dif_lon)
    print(f"[main] Pixel length in longitude direction: {round(distanz, 2)} meters.")

    # Create mowed pixel array and define water pixels
    mowed_pixel_array = create_mowed_pixel_array(resolution_lon, resolution_lat, start_lat, start_lon, end_lat, end_lon)
    mowed_pixel_array = define_water_pixels(mowed_pixel_array, coordinates_sea)

    #result_array = np.zeros((len(mowed_pixel_array), len((mowed_pixel_array[0]))))
    #result_array = []
    #for x in range(len(mowed_pixel_array)):
    #    for y in range(len(mowed_pixel_array[0])):
    #        new_ele = mowed_pixel_array[x][y].to_dict()
    #        result_array.append(new_ele)

    #result_array = np.array(result_array)
    #result_array.resize((len(mowed_pixel_array), len((mowed_pixel_array[0]))))


    # Get folders and load model and homography matrix
    folders = get_folders(data_folder_path, folder_uniq_name)
    model = get_prediction_model(ann_model_path)
    h_matrix = get_harmony_matrix(harmony_matrix_path)

    # Process images
    for folder in tqdm.tqdm(folders, desc="Folders"):
        files = os.listdir(data_folder_path + folder)
        csv_files = [filename for filename in files if filename.startswith("fix") and filename.endswith(".csv")]
        if rgb_folder_name in files and infra_folder_name in files and csv_files:
            synced_images = get_syncronos_imag_list(
                data_folder_path + folder + '/' + rgb_folder_name,
                data_folder_path + folder + '/' + infra_folder_name,
                time_tolderance
            )

            logging.log(logging.CRITICAL, synced_images)
            for rgb_image_path, infra_image_path in tqdm.tqdm(synced_images, desc='Images', leave=False):
                latitude, longitude = get_coordinats_by_image_name(rgb_image_path, data_folder_path + folder + '/' + csv_files[0])
                if latitude == 0 or longitude == 0:
                    continue

                rgb_image = cv2.imread(data_folder_path + folder + '/' + rgb_folder_name + '/' + rgb_image_path)
                infra_image = cv2.imread(data_folder_path + folder + '/' + infra_folder_name + '/' + infra_image_path)

                rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
                infra_image = cv2.cvtColor(infra_image, cv2.COLOR_BGR2GRAY)

                wraped_infra_image = wrap_image(infra_image, h_matrix)

                croped_rgb_image = crop_image(rgb_image, x_start, y_start, x_width, y_height)
                croped_infra_image = crop_image(wraped_infra_image, x_start, y_start, x_width, y_height)

                expanded_ir_image = np.expand_dims(croped_infra_image, axis=2)
                concated_image = np.concatenate((croped_rgb_image, expanded_ir_image), axis=2)

                pixel_dataset = concated_image.reshape(-1, concated_image.shape[2])
                pixel_dataset = pixel_dataset.astype(np.float32) / 255.0

                weed_percantage = detect_weed(model, pixel_dataset)

                ii = math.floor((start_lat - latitude) / abs(dif_lat))
                jj = math.floor((longitude - start_lon) / abs(dif_lon))

                if mowed_pixel_array[ii][jj].get_shapely_polygon().contains(ShapelyPoint((latitude, longitude))):
                    mowed_pixel_array[ii][jj].mowes_ammount += weed_percantage
                    mowed_pixel_array[ii][jj].number_pass_through += 1
                else:
                    print(f"[main] Warning: {ShapelyPoint((latitude, longitude))} is not in the pixel {mowed_pixel_array[ii][jj].get_shapely_polygon()}")

    print("[main] finished calculation of mowed pixel array")

    print("[main] starting to save outputs")

    result_array = []
    for x in range(len(mowed_pixel_array)):
        for y in range(len(mowed_pixel_array[0])):
            new_ele = mowed_pixel_array[x][y].to_dict()
            result_array.append(new_ele)

    result_array = np.array(result_array)
    result_array.resize((len(mowed_pixel_array), len((mowed_pixel_array[0]))))

    # Save outputs
    foldername = output_path + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f'result_{resolution_lat}x{resolution_lon}/'
    os.makedirs(foldername)

    create_binary_image(mowed_pixel_array, start_lat, start_lon, dif_lon, dif_lat, foldername + 'result.tif')
    create_value_image(mowed_pixel_array, start_lat, start_lon, dif_lon, dif_lat, foldername + 'result_value.tif')
    create_num_pass_thrue_image(mowed_pixel_array, start_lat, start_lon, dif_lon, dif_lat, foldername + 'result_num_pass.tif')
    create_value_image_with_lake_form(mowed_pixel_array, start_lat, start_lon, dif_lon, dif_lat, foldername + 'result_value_lake.tif')
    create_leaflet_map(mowed_pixel_array, resolution_lat, resolution_lon, foldername + 'resultmap.html')
    create_geojson(mowed_pixel_array, foldername + 'result.geojson', resolution_lat, resolution_lon)

    print("[main] done saving outputs")

    return {"resultarray":result_array.tolist(), "lat":resolution_lat, "lon":resolution_lon}

if __name__ == "__main__":
    # Parameters
    coordinates_sea = [
        [52.347505, 9.751718], [52.347597, 9.750624], [52.348278, 9.750216],
        [52.353416, 9.746482], [52.354727, 9.745345], [52.356771, 9.743114],
        [52.360873, 9.740217], [52.362406, 9.739058], [52.362655, 9.738479],
        [52.362, 9.735947], [52.36141, 9.735324], [52.360951, 9.735281],
        [52.358737, 9.736633], [52.358147, 9.738479], [52.356863, 9.739165],
        [52.355028, 9.73968], [52.353023, 9.741611], [52.350926, 9.745603],
        [52.349183, 9.745774], [52.347466, 9.744594], [52.345067, 9.744895],
        [52.343808, 9.746912], [52.343022, 9.749594], [52.343284, 9.753091],
        [52.344057, 9.754465], [52.347505, 9.751718]
    ]

    resolution_lat = int(os.getenv("RESOLUTION_LAT"))
    resolution_lon = int(os.getenv("RESOLUTION_LON"))
    data_folder_path = os.getenv("DATA_FOLDER_PATH")
    folder_uniq_name = os.getenv("FOLDER_UNIQ_NAME")
    ann_model_path = os.getenv("ANN_MODEL_PATH")
    harmony_matrix_path = os.getenv("HARMONY_MATRIX_PATH")
    satelite_image_path = os.getenv("SATELITE_IMAGE_PATH")
    rgb_folder_name = os.getenv("RGB_FOLDER_NAME")
    infra_folder_name = os.getenv("INFRA_FOLDER_NAME")
    time_tolderance = float(os.getenv("TIME_TOLDERANCE"))
    x_start = int(os.getenv("X_START"))
    y_start = int(os.getenv("Y_START"))
    x_width = int(os.getenv("X_WIDTH"))
    y_height = int(os.getenv("Y_HEIGHT"))
    imageCrop = (x_start, y_start, x_width, y_height)
    top_left = (float(os.getenv("TOP_LEFT_LAT")), float(os.getenv("TOP_LEFT_LON")))
    bottom_right = (float(os.getenv("BOTTOM_RIGHT_LAT")), float(os.getenv("BOTTOM_RIGHT_LON")))
    rectangle_cords = (top_left, bottom_right)
    output_path = os.getenv("OUTPUT_PATH")

    create_compare_image(
        resolution_lat=resolution_lat,
        resolution_lon=resolution_lon,
        rectangle_cords=rectangle_cords,
        satelite_image_path=satelite_image_path,
        coordinates_sea=coordinates_sea,
        ann_model_path=ann_model_path,
        harmony_matrix_path=harmony_matrix_path,
        data_folder_path=data_folder_path,
        folder_uniq_name=folder_uniq_name,
        rgb_folder_name=rgb_folder_name,
        infra_folder_name=infra_folder_name,
        time_tolderance=time_tolderance,
        imageCrop=imageCrop,
        output_path=output_path
    )
