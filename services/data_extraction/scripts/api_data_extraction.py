
import os
import sys
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from loguru import logger

import scripts.downsample_rosbag as downsample_rosbag_module
import scripts.extract_navsatfix as extract_navsatfix_module
import scripts.fix_rosbag as fix_rosbag_module
import scripts.bag_to_img as img_rosbag_module
import scripts.bag_to_mpeg as mpeg_rosbag_module
import scripts.bag_to_trajectory as bag_to_trajectory_module


class InputParameter(BaseModel):
    """Common request body for rosbag API endpoints.

    Attributes:
        bag_directory: Directory containing ROS bag files.
        topic: Optional single topic (used by downsample, navsatfix,
            trajectory). If omitted, a sensible default is used.
        topics: Optional list of topics (used by img/mpeg). If omitted,
            sensible defaults are used.
    """

    bag_directory: str
    topic: Optional[str] = None
    topics: Optional[List[str]] = None


app = FastAPI()

# docker compose --profile api-data-extraction up --build

def normalize_and_validate_bag_directory(raw_path: str) -> str:
    """Validate and normalize the incoming bag directory.

    - Ensures the path is provided
    - Ensures the directory exists and is a directory
    - Ensures there is exactly one trailing path separator
    """

    if not raw_path or not raw_path.strip():
        raise HTTPException(status_code=400, detail="bag_directory must not be empty")

    path = os.path.expanduser(raw_path.strip())

    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"bag_directory does not exist: {path}")

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"bag_directory is not a directory: {path}")

    if not path.endswith(os.sep):
        path = path + os.sep

    logger.debug(f"Using bag_directory: {path}")
    return path

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
                <li><a href="/hello_world">GET /hello_world</a> - Returns a simple greeting message.</li>
                <li>POST /rosbag/downsample_rosbags - Downsamples rosbags for a given directory.</li>
                <li>POST /rosbag/extract_navsatfix - Extracts NavSatFix data from rosbags.</li>
                <li>POST /rosbag/fix - Fixes rosbags in the given directory.</li>
                <li>POST /rosbag/img - Extracts images from rosbags.</li>
                <li>POST /rosbag/mpeg - Converts rosbags to MPEG videos.</li>
                <li>POST /rosbag/trajectory - Extracts trajectory (GPS) data from rosbags and returns it as JSON.</li>
            </ul>
            <h2>Request Body (for all POST /rosbag/* endpoints)</h2>
            <pre>{"bag_directory": "/path/to/rosbags", "topic": "/fix"}</pre>
            <pre>{"bag_directory": "/path/to/rosbags", "topics": ["/camera/color/...", "/camera/infra1/..."]}</pre>
            <p>
                <strong>bag_directory</strong> must be an existing directory inside the container. It is validated by the API
                (must exist, be a directory, and will be normalized to have a trailing path separator).
            </p>
            <h2>Return Values</h2>
            <ul>
                <li><strong>/hello_world</strong>: Returns a JSON object with a greeting message.</li>
                <li><strong>POST /rosbag/*</strong>: Returns a JSON object with a short status message. On validation errors, an HTTP 400 is returned.</li>
            </ul>
        </body>
    </html>
    """
    return HTMLResponse(content=api_docs)


@app.get("/hello_world")
async def hello_world() -> dict:
    """
    Endpoint that returns a simple greeting message.

    :return: A dictionary containing a greeting message.
    """
    return {"message": "Hello from HaixTools in Docker :)  !"}


# curl -X POST "http://localhost:10006/rosbag/downsample_rosbags" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags", "topic": "/fix"}'
@app.post("/rosbag/downsample_rosbags")
async def create_comparison_image(params: InputParameter) -> dict:
    """
    Endpoint that creates a comparison image based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary indicating the success of the image creation process.
    """

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    # Allow overriding the topic per request; fall back to a default that
    # matches the CLI/docker usage.
    topic = params.topic or os.getenv("ROS_TOPIC_FIX", "/fix")

    sys.argv = [
        "downsample_rosbag.py",  # script name
        "-t",
        topic,
        bag_directory,
    ]

    logger.debug(f"sys.argv set to: {sys.argv}. Calling downsample_rosbag.main()")

    downsample_rosbag_module.main()

    logger.debug(f"downsample_rosbag.main() finished")

    return {"message": f"Downsampled rosbags saved to "}


# curl -X POST "http://localhost:10006/rosbag/extract_navsatfix" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags", "topic": "/fix"}'
@app.post("/rosbag/extract_navsatfix")
async def extract_navsatfix(params: InputParameter) -> dict:
    """
    Endpoint that extracts NavSatFix data from rosbags based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary indicating the success of the extraction process.
    """
    logger.debug("Starting extract_navsatfix with params: {params}")

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    topic = params.topic or os.getenv("ROS_TOPIC_FIX", "/fix")

    sys.argv = [
        "extract_navsatfix.py",  # script name
        "-t",
        topic,
        bag_directory,
    ]

    logger.debug(f"sys.argv set to: {sys.argv}. Calling extract_navsatfix.main()")

    extract_navsatfix_module.main()

    logger.debug(f"extract_navsatfix.main() finished")
    return {"message": f"Extracted NavSatFix data "}

# curl -X POST "http://localhost:10006/rosbag/fix" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags/"}'
@app.post("/rosbag/fix")
async def fix_rosbag(params: InputParameter) -> dict:
    """
    Endpoint that fixes rosbags based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary indicating the success of the fixing process.
    """
    logger.debug("Starting fix_rosbag with params: {params}")

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    sys.argv = [
        "fix_rosbag.py",  # script name
        bag_directory,
    ]

    logger.debug(f"sys.argv set to: {sys.argv}. Calling fix_rosbag.main()")

    fix_rosbag_module.main()

    logger.debug(f"fix_rosbag.main() finished")
    return {"message": f"Fixed rosbags "}

# curl -X POST "http://localhost:10006/rosbag/img" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags/", "topics": ["/camera/color/image_raw_throttled/compressed", "/camera/infra1/image_rect_raw_throttled/compressed"]}'
@app.post("/rosbag/img")
async def img_rosbag(params: InputParameter) -> dict:
    """
    Endpoint that processes image rosbags based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary indicating the success of the image processing.
    """
    logger.debug("Starting img_rosbag with params: {params}")

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    default_img_topics = [
        "/camera/color/image_raw_throttled/compressed",
        "/camera/infra1/image_rect_raw_throttled/compressed",
    ]
    topics = params.topics or default_img_topics

    sys.argv = [
        "bag_to_img.py",  # script name
        bag_directory,
        "-t",
        *topics, # star does unpacking, that means in this case each topic is a separate argument
    ]

    logger.debug(f"sys.argv set to: {sys.argv}. Calling img_rosbag.main()")

    img_rosbag_module.main()

    logger.debug(f"img_rosbag.main() finished")
    return {"message": f"Processed image rosbags "}

# curl -X POST "http://localhost:10006/rosbag/mpeg" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags/", "topics": ["/camera/color/image_raw_throttled/compressed", "/camera/infra1/image_rect_raw_throttled/compressed"]}'
@app.post("/rosbag/mpeg")
async def mpeg_rosbag(params: InputParameter) -> dict:
    """
    Endpoint that converts rosbags to MPEG videos based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary indicating the success of the MPEG conversion.
    """
    logger.debug("Starting mpeg_rosbag with params: {params}")

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    default_mpeg_topics = [
        "/camera/color/image_raw_throttled/compressed",
        "/camera/infra1/image_rect_raw_throttled/compressed",
        # "/pixelwise_nn_node/camera/prediction",  # example additional topic
    ]
    topics = params.topics or default_mpeg_topics

    sys.argv = [
        "bag_to_mpeg.py",  # script name
        bag_directory,
        "--create-combined-video",
        "-t",
        *topics,
    ]

    logger.debug(f"sys.argv set to: {sys.argv}. Calling mpeg_rosbag.main()")

    mpeg_rosbag_module.main()

    logger.debug(f"mpeg_rosbag.main() finished")
    return {"message": f"Converted MPEG videos "}


# curl -X POST "http://localhost:10006/rosbag/trajectory" -H "Content-Type: application/json" -d '{"bag_directory": "/home/docker/rosbags/", "topic": "/fix"}'
@app.post("/rosbag/trajectory")
async def trajectory_rosbag(params: InputParameter) -> dict:
    """
    Endpoint that extracts trajectory data from rosbags based on the provided parameters.

    :param params: InputParameter object containing bag_directory.
    :return: A dictionary containing a status message and the extracted
             trajectory points.
    """
    logger.debug("Starting trajectory_rosbag with params: {params}")

    bag_directory = normalize_and_validate_bag_directory(params.bag_directory)

    # Reuse the shared helper from bag_to_trajectory so that the same logic
    # works both for the CLI and the API.
    topic = params.topic or os.getenv("ROS_TOPIC_FIX", "/fix")
    logger.debug(f"Calling bag_to_trajectory.extract_trajectory_data() for topic {topic}")

    trajectory_points = bag_to_trajectory_module.extract_trajectory_data(
        bag_directory,
        topic=topic,
    )
    # TODO: add the topic " /pixelwise_nn_node/weed_percentage" 

    logger.debug("bag_to_trajectory.extract_trajectory_data() finished")
    return {
        "message": "Extracted trajectory data",
        "topic": topic,
        "count": len(trajectory_points),
        "trajectory": trajectory_points,
    }

