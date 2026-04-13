import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
import logging

from create_compare_image import create_compare_image


class InputParameter(BaseModel):
    data_folder_path: str
    output_path: str
    satellite_image_path: str

class InputDate(BaseModel):
    date: str
    output_path: str
    satellite_image_path: str


app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """
    Root endpoint that provides comprehensive information about all API functionalities.

    Returns:
        Dict[str, str]: A message with detailed information about all available API endpoints,
                       their parameters, and return values
    """
    api_docs = """
    <html>
        <head>
            <title>API Documentation</title>
        </head>
        <body>
            <h1>API Documentation</h1>
            <h2>Endpoints</h2>
            <ul>
                <li><a href="/hello_world">/hello_world</a> - Returns a simple greeting message.</li>
                <li><a href="/create_comparison_image">/create_comparison_image</a> - Creates a comparison image based on the provided parameters.</li>
            </ul>
            <h2>Parameters for /create_comparison_image</h2>
            <ul>
                <li><strong>data_folder_path</strong>: Path to the data folder containing the necessary images and data.</li>
                <li><strong>output_path</strong>: Path where the output comparison image will be saved.</li>
            </ul>
            <h2>Return Values</h2>
            <ul>
                <li><strong>/hello_world</strong>: Returns a JSON object with a greeting message.</li>
                <li><strong>/create_comparison_image</strong>: Returns a JSON object with a message indicating the success of the image creation process.</li>
            </ul>
        </body>
    </html>
    """
    return HTMLResponse(content=api_docs)


@app.get("/get_dates")
async def get_dates() -> dict:
    destination = Path("data/rosbags/")

    results = []

    for eintrag in destination.iterdir():
        if eintrag.is_dir():
            results.append(eintrag.name)

    return {"message": results}


@app.post("/create_comparison_image")
async def create_comparison_image(args: InputDate) -> dict:
    """
    Endpoint to create a comparison image based on the provided input parameters.

    :param args: Input parameters containing the data folder path and output path.
    :return: A dictionary with a message indicating the success of the image creation process.
    """
    # Extract parameters from the request body
    #data_folder_path = args.data_folder_path
    data_folder_path = "data/rosbags/" + args.date + "/files_extracted/"
    output_path = args.output_path
    satellite_image_path = args.satellite_image_path

    # Define coordinates for the sea polygon
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

    # Retrieve parameters from environment variables
    resolution_lat = int(os.getenv("RESOLUTION_LAT"))
    resolution_lon = int(os.getenv("RESOLUTION_LON"))

    folder_uniq_name = os.getenv("FOLDER_UNIQ_NAME")
    ann_model_path = os.getenv("ANN_MODEL_PATH")
    harmony_matrix_path = os.getenv("HARMONY_MATRIX_PATH")
    # satelite_image_path = os.getenv("SATELITE_IMAGE_PATH")

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

    # Call the function to create the comparison image
    data_array = create_compare_image(
        resolution_lat=resolution_lat, 
        resolution_lon=resolution_lon, 
        rectangle_cords=rectangle_cords,
        satellite_image_path=satellite_image_path,
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

    for x in range(len(data_array["resultarray"])):
        for y in range(len(data_array["resultarray"][0])):
            if data_array["resultarray"][x][y]["mowes_ammount"] != 0.0:
                logging.log(logging.CRITICAL, data_array["resultarray"][x][y])

    #html_file_path = "data/results/2025-11-10_17-41-55result_223x129/resultmap.html"
    #return FileResponse(html_file_path, media_type="text/html")
    return data_array
