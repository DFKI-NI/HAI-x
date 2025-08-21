import enum

version = 0.17  # This need to be float, not string
# Default language setting (can be 'english' or 'german')
language = 'english'
IMG_PATH = 'static/img/'
DATA_FILE = 'data/data.csv'
PATH_FILE = 'data/path.csv'
TRAJ_PATH = 'data/Seekuh/'
GEO_FILE = 'data/geo.json'
VID_DATA_PATH = 'data/video_info/'
VID_FILE_PATH = 'static/video/'
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
VIDEO_FILE_NAME_RGB = 'color_full.mp4'
VIDEO_FILE_NAME_IR = 'infra1_full.mp4'
VIDEO_TIME_RGB_FILE_NAME = '_color.csv'
VIDEO_TIME_IR_FILE_NAME = '_infra1.csv'
SAVE = 'save'
DELETE = 'delete'
AREA = 'area'
PATH = 'path'
TRAJ = 'traj'
GEO = 'geo'
SCHEMA = 'interface'
AREA_COLS = ['idx', 'date', 'type', 'description', 'image_path']
GEO_COLS = ['idx', 'geom']
PATH_COLS = ['idx', 'path_id', 'date', 'lat', 'lon']
TRAJ_COLS = ['idx', 'timestamp', 'latitude', 'longitude', 'date', 'mowed_grass']

# available postgis geometries: https://postgis.net/workshops/postgis-intro/geometries.html
class Geometry(enum.Enum):
    POINT = 1
    LINESTRING = 2
    POLYGON = 3
    POLYGONWITHHOLE = 4
    COLLECTION = 5
