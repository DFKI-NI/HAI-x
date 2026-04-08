import enum

version = 0.19  # This need to be float, not string
# Default language setting (can be 'english' or 'german')
language = 'english'
IMG_PATH = 'static/img/'
DATA_FILE = 'data/data.csv'
PATH_FILE = 'data/path.csv'
TRAJ_PATH = 'data/Seekuh/'
GEO_FILE = 'data/geo.json'
VID_DATA_PATH = '/static/video/'
VID_FILE_PATH = '/static/video/'
neutral = 'neutral'
AVOID = 'avoid'
INTEREST = 'interest'
TRAJECTORY = 'Seekuh trajectory'
seekuh = 'seekuh'
traj = 'trajectory'
PATH_PLANNING = 'Path planning'
path = 'path'
maschsee = 'maschsee-'
ADD = 'add'
GENERATE = 'generate'
VIDEO_RGB = 'RGB'
VIDEO_IR = 'IR'
EXTRACTED_ROSBAGS_FOLDER_NAME = '/files_extracted/'
VIDEO_FILE_NAME_RGB = 'color_full.mp4'
VIDEO_FILE_NAME_IR = 'infra1_full.mp4'
VIDEO_TIME_RGB_FILE_NAME = 'color_full.csv'
VIDEO_TIME_IR_FILE_NAME = 'infra1_full.csv'
SAVE = 'save'
DELETE = 'delete'
AREA = 'area'
PATH = 'path' # each path
PATH_RAW = 'path_raw' # each point in each path
TRAJ = 'traj'
GEO = 'geo'
EVALUATION = 'evaluation'
SCHEMA = 'interface'
AREA_COLS = ['idx', 'date', 'type', 'description', 'image_path', 'is_capacitated', 'lake_name', 'cluster_id', 'cluster_total_volume', 'harvester_capacity']
GEO_COLS = ['idx', 'geom']
PATH_COLS = ['idx', 'path_id', 'date', 'lat', 'lon']
TRAJ_COLS = ['idx', 'timestamp', 'latitude', 'longitude', 'date', 'mowed_grass']
EVAL_COLS = ['id', 'date', 'lat1', 'lon1', 'lat2', 'lon2', 'weeding']
BATHYMETRY = 'bathymetry'
BATHYMETRY_COLS = ['idx', 'lake_name', 'date', 'lat', 'lon', 'depth', 'description']
APA_INDEX = 'apa_index'
APA_INDEX_COLS = ['idx', 'lake_name', 'date', 'lat', 'lon', 'apa_value', 'description']
PLANT_VOLUME = 'plant_volume'
PLANT_VOLUME_COLS = ['idx', 'lake_name', 'date', 'lat', 'lon', 'volume', 'apa_value', 'depth', 'description']
LAKE_APA_INDEX = 'lake_apa_index'
LAKE_APA_INDEX_COLS = ['idx', 'lake_name', 'geojson_data', 'created_at']

# available postgis geometries: https://postgis.net/workshops/postgis-intro/geometries.html
class Geometry(enum.Enum):
    POINT = 1
    LINESTRING = 2
    POLYGON = 3
    POLYGONWITHHOLE = 4
    COLLECTION = 5
