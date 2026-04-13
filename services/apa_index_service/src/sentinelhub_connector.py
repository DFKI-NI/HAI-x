import datetime

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
import logging

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
