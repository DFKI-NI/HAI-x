import datetime
import glob
import os
from pathlib import Path


from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    WmsRequest,
    MimeType,
    MosaickingOrder,
    SentinelHubRequest,
    bbox_to_dimensions,
)
from sentinelhub import SHConfig

COPERNICUS_BASE_URL = "https://sh.dataspace.copernicus.eu/"
COPERNICUS_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
COPERNICUS_API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
COPERNICUS_AWS_METADATA_URL = "https://eodata.dataspace.copernicus.eu"
COPERNICUS_OPENSEARCH_URL = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2"
COPERNICUS_INSTANCE_URL = "https://sh.dataspace.copernicus.eu/configuration/v1/wms/instances"


def get_bbox_and_size(coords, resolution, crs=CRS.WGS84):
    bbox = BBox(bbox=coords, crs=crs)
    bbox_size = bbox_to_dimensions(bbox, resolution=resolution)
    return bbox, bbox_size


def get_wms_request(bbox, time_frame, width, config, image_format=MimeType.TIFF,
                    time_difference=datetime.timedelta(hours=2), data_collection=DataCollection.SENTINEL2_L2A,
                    layer='ALL-BANDS-TRUE-COLOR'):
    wms_request = WmsRequest(
        data_collection=data_collection,
        layer=layer,
        bbox=bbox,
        time=time_frame,
        width=width,
        image_format=image_format,
        time_difference=time_difference,
        config=config,
        maxcc=0.5
    )
    return wms_request


def get_img_request_for_given_date(eval_script,
                                   data_dir,
                                   bbox,
                                   bbox_size,
                                   date,
                                   config,
                                   data_collection=DataCollection.SENTINEL2_L2A,
                                   mime_type=MimeType.TIFF):
    img_request_for_given_date = C_SentinelHubRequest(
        evalscript=eval_script,
        data_folder=data_dir,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=data_collection,
                time_interval=[f'{date}T00:00:00+01:00', f'{date}T23:59:59+01:00'],
                mosaicking_order=MosaickingOrder.LEAST_CC,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", mime_type)],
        bbox=bbox,
        size=bbox_size,
        config=config,
    )
    return img_request_for_given_date


def download_all_images(data_dir,
                        img_dates,
                        eval_script,
                        bbox,
                        bbox_size,
                        config,
                        data_collection=DataCollection.SENTINEL2_L2A,
                        mime_type=MimeType.TIFF):
    print('Starting image download...')
    # Loop over the dates
    for dt in img_dates:
        # convert the datetime object to a string of the date
        dt = str(dt.date())
        img_request = get_img_request_for_given_date(eval_script=eval_script,
                                                     data_dir=data_dir,
                                                     bbox=bbox,
                                                     bbox_size=bbox_size,
                                                     date=dt,
                                                     config=config,
                                                     data_collection=data_collection,
                                                     mime_type=mime_type)
        all_bands_img = img_request.get_data(save_data=True)
    print('Finished.')
    return all_bands_img


def get_config(client_id, client_secret, instance_id, profile_name=None) -> SHConfig:
    if not client_id or not client_secret:
        print("Warning! To use Process API, please provide the credentials (OAuth client ID and client secret).")

    try:
        config = SHConfig(profile=profile_name)
    except:
        config = SHConfig()
        config.sh_client_id = client_id
        config.sh_client_secret = client_secret
        config.sh_base_url = COPERNICUS_BASE_URL
        config.sh_token_url = COPERNICUS_TOKEN_URL
        config.opensearch_url = COPERNICUS_OPENSEARCH_URL
        config.instance_id = instance_id
        config.save(profile_name)
    return config


class C_SentinelHubRequest(SentinelHubRequest):
    def __init__(self, **kwargs):
        super(C_SentinelHubRequest, self).__init__(**kwargs)

        # adjust the api URL. It is not adjusted from the Config
        for dl_item in self.download_list:
            dl_item.url = COPERNICUS_API_URL


if __name__ == '__main__':
    from osgeo import gdal  # todo: remove this package in future versions
    client_id = ""
    client_secret = ""
    instance_id = ""
    # If you have a profile in ~/.config/sentinelhub, you can just pass the profile name.
    profile_name = ""

    config = get_config(client_id, client_secret, instance_id, profile_name=profile_name)

    # define the bounding box corner coordinates (lower left, upper right) in WGS84
    maschsee_coords_wgs84 = (9.733200, 52.342366, 9.755344, 52.363231)
    resolution = 10  # in m
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=60)
    time_frame = (start, end)

    # Get bbox and bbox size
    bbox, size = get_bbox_and_size(coords=maschsee_coords_wgs84, resolution=resolution, crs=CRS.WGS84)

    # get the wms request to obtain dates with available images
    wms_request = get_wms_request(bbox=bbox,
                                  time_frame=time_frame,
                                  width=size[0],
                                  config=config,
                                  image_format=MimeType.TIFF,
                                  time_difference=datetime.timedelta(hours=2),
                                  data_collection=DataCollection.SENTINEL2_L2A,
                                  layer='ALL-BANDS-TRUE-COLOR')
    # obtain the dates
    img_dates = wms_request.get_dates()

    data_dir = '../images/maschsee/'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # download all images from time frame
    all_bands_images = download_all_images(data_dir=data_dir,
                                           img_dates=img_dates,
                                           eval_script=evalscripts.evalscript_all_bands,
                                           bbox=bbox,
                                           bbox_size=size,
                                           config=config,
                                           data_collection=DataCollection.SENTINEL2_L2A,
                                           mime_type=MimeType.TIFF)


    def crop_img_by_shapefile(img_in_path, img_out_path, shp_path, src_no_data=0, dst_no_data=0):
        """Crop a geotiff image by the outline of an ESRI shapefile and save it as a new geotiff image.

        Args:
            img_in_path : str
                path to the input geotiff image.
            img_out_path : str
                path to the output geotiff image.
            shp_path : str
                path to the ESRI shapefile (polygon) with extension '.shp' by which the geotiff file should be cut.
            src_no_data : int
                No data value of the input image.
            dst_no_data : int
                No data value of the output image.

        Returns:
            None
        """
        warp_opts = gdal.WarpOptions(cutlineDSName=shp_path,
                                     cropToCutline=True,
                                     srcNodata=src_no_data,
                                     dstNodata=dst_no_data,
                                     dstSRS='EPSG:4326')
        out_tile = gdal.Warp(destNameOrDestDS=img_out_path,
                             srcDSOrSrcDSTab=img_in_path,
                             format='GTiff',
                             options=warp_opts)
        # close file
        out_tile = None


    src_no_data = 0
    dst_no_data = 0
    maschsee_shp = '../assets/shapefiles/vector/00_NI_maschsee_shapefile/00_NI_maschsee_shapefile.shp'
    input_img_paths = glob.iglob('../images/maschsee/*/*.tiff')
    for img_path in input_img_paths:
        img_path = Path(img_path)
        img_id = Path(img_path).parent.name
        img_out_path = Path('../images/maschsee/cropped/') / (str(img_id) + '.tiff')
        command = f"gdalwarp -dstnodata NoData -cutline {maschsee_shp} {img_path} {img_out_path}"
        os.system(command)
