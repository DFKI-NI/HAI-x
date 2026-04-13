import numpy as np
import os
import torch
import cv2


def get_folders(folder_path: str, uniq_name: str) -> list:
    """
    Get all folders in the specified directory that contain a unique name.

    :param folder_path: Path to the directory containing folders.
    :param uniq_name: Unique name to filter folders.
    :return: List of folder names containing the unique name.
    """
    folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

    # Filter folders based on the unique name
    folders = [f for f in folders if uniq_name in f]
    folders.sort()

    return folders


def get_image_list(folder_path: str, image_format: str = '.png') -> list:
    """
    Get a list of image files in the specified folder.

    :param folder_path: Path to the folder containing images.
    :param image_format: File extension of the images (default is '.png').
    :return: List of image file names.
    """
    images = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    images = [f for f in images if f.endswith(image_format)]
    images.sort()

    return images


def get_timestamp_from_imagename(imageName: str) -> float:
    """
    Extract the timestamp from the image file name.
    Example image name format: 'image_raw_throttled_compressed_1723639444815586329.png'.

    :param imageName: Name of the image file.
    :return: Timestamp as a float (converted from nanoseconds to seconds).
    """
    imagenameWithoutEnding = imageName.split('.')[0]
    timestampString = imagenameWithoutEnding.split('_')[-1]

    # Convert nanoseconds to seconds
    timestemp = float(timestampString) / 1000000000

    return timestemp


def get_syncronos_imag_list(rgb_image_folder_path: str, infra_image_folder_path: str, time_tolderance: float) -> list:
    """
    Synchronize RGB and infrared images based on their timestamps.

    :param rgb_image_folder_path: Path to the folder containing RGB images.
    :param infra_image_folder_path: Path to the folder containing infrared images.
    :param time_tolderance: Maximum allowed time difference between timestamps (in seconds).
    :return: List of synchronized image pairs (RGB and infrared).
    """
    synced_images = []

    rgb_images = get_image_list(rgb_image_folder_path)
    infra_images = get_image_list(infra_image_folder_path)

    for rgb_image in rgb_images:
        rgb_timestamp = get_timestamp_from_imagename(rgb_image)
        
        for infra_image in infra_images:
            infra_timestamp = get_timestamp_from_imagename(infra_image)
            
            # Check if the timestamps are within the tolerance
            if abs(rgb_timestamp - infra_timestamp) < time_tolderance:
                synced_images.append([rgb_image, infra_image])
                break  # Stop searching once a match is found

    return synced_images 


def wrap_image(image: np.ndarray, h_matrix: np.ndarray) -> np.ndarray:
    """
    Apply a perspective transformation to an image using a homography matrix.

    :param image: Input image as a NumPy array.
    :param h_matrix: Homography matrix for the transformation.
    :return: Transformed image.
    """
    wrap_image = cv2.warpPerspective(image, h_matrix, (image.shape[1], image.shape[0]))

    return wrap_image


def crop_image(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """
    Crop a region from the image.

    :param image: Input image as a NumPy array.
    :param x: X-coordinate of the top-left corner of the crop region.
    :param y: Y-coordinate of the top-left corner of the crop region.
    :param w: Width of the crop region.
    :param h: Height of the crop region.
    :return: Cropped image.
    """
    crop_image = image[y:y+h, x:x+w]

    return crop_image


def detect_weed(model: torch.nn.Module, dataset: np.ndarray) -> float:
    """
    Detect the percentage of weed pixels in the dataset using a trained model.

    :param model: PyTorch model for weed detection.
    :param dataset: Input dataset as a NumPy array.
    :return: Percentage of weed pixels in the dataset.
    """
    tensor_dataset = torch.tensor(dataset, dtype=torch.float32)

    # Perform inference using the model
    output = model(tensor_dataset)
    predictions = output.detach().numpy()

    # Convert predictions to binary values (0 or 1)
    predictions = predictions > 0.5
    predictions = predictions.flatten()
    predictions = predictions.astype(np.uint8)

    # Count occurrences of each unique value in the predictions
    vals, counts = np.unique(predictions, return_counts=True)
    countDict = dict(zip(vals, counts))

    number_pixel = sum(value for key, value in countDict.items())

    if 1 not in countDict:
        # If no weed pixels are detected, return 0
        return 0.0

    # Calculate the percentage of weed pixels
    weed_percantage = countDict[1] / number_pixel
    weed_percantage = round(weed_percantage, 4)

    return weed_percantage



