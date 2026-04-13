import os
from pathlib import Path
from typing import Optional


from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from shapely.geometry import Point

from src.connectors import ClustersConnectors

app = FastAPI()

# Static assets (usage docs)
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Temporary directory for file storage
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
OUTPUT_FILE = "output_path.geojson"


class CVRPRequest(BaseModel):
    cluster_json: dict
    boundary_file: Optional[dict] = None
    start_x: Optional[float] = 9.741273233
    start_y: Optional[float] = 52.353144617
    end_x: Optional[float] = 9.741244433
    end_y: Optional[float] = 52.35319485
    row_spacing: float = 5.0
    mode: str = "serpentine"


@app.get("/")
async def get_index():
    return FileResponse(str(ASSETS_DIR / "index.html"), media_type="text/html")


@app.post("/cvrp")
async def process_geojson(req: CVRPRequest) -> FileResponse:
    cluster_json = req.cluster_json
    boundary_json = req.boundary_file if isinstance(req.boundary_file, dict) else None
    
    start = Point(req.start_x, req.start_y)
    end = Point(req.end_x, req.end_y)
    row_spacing = req.row_spacing
    mode = req.mode

    connector_builder = ClustersConnectors(start, end, row_spacing, mode)
    connector_builder.load_data(cluster_json, boundary_file=boundary_json)
    connector_builder.generate_Connectors(OUTPUT_FILE)

    return FileResponse(OUTPUT_FILE, media_type="application/geo+json", filename="output.geojson")

