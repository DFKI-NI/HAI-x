import os
import sys
import datetime

import pandas as pd
import numpy as np

import yaml
from tqdm import tqdm
import ffmpeg
import glob


def create_videos(chosen_date: str):
    oberpfad = "../../../haix_server/" + chosen_date + "/bag_files_extracted/color/"
    ordners = [ordner for ordner in os.listdir(oberpfad)]

    for ordner in tqdm(ordners):
        index = ordner.split("_")[7]

        path = oberpfad + ordner

        try:
            (
                ffmpeg
                .input(path + '/*.png', pattern_type='glob', framerate=20)
                .output('../static/video/maschsee-' + chosen_date + '/movie' + index + '.mp4', pix_fmt='yuv420p', loglevel="quiet")
                .run()
            )
        except ffmpeg.Error as e:
            print(ordner)
            print(e.stdout)
            sys.exit(1)


def create_video_info(chosen_date: str):
    path = "../../../haix_server/" + chosen_date + "/bag_files_extracted/color/"

    dates = []
    for x in tqdm(os.listdir(path)):
        yaml_files = [yaml_file for yaml_file in os.listdir(path + x) if
                      yaml_file.endswith(".yaml")]

        with open(path + x + "/fix_00000.yaml") as stream:
            try:
                data = yaml.safe_load(stream)

                first_lat = data['GPS']['lat']
                first_lon = data['GPS']['long']
            except yaml.YAMLError as exc:
                print(exc)

        if len(yaml_files) - 1 >= 1000:
            file_name = "/fix_0" + str(len(yaml_files) - 1)
        elif len(yaml_files) - 1 >= 100:
            file_name = "/fix_00" + str(len(yaml_files) - 1)
        else:
            file_name = "/fix_000" + str(len(yaml_files) - 1)

        with open(path + x + file_name + ".yaml") as stream:
            try:
                data = yaml.safe_load(stream)

                last_lat = data['GPS']['lat']
                last_lon = data['GPS']['long']
            except yaml.YAMLError as exc:
                print(exc)

        mystamp = datetime.datetime(int(x.split("_")[1]), int(x.split("_")[2]), int(x.split("_")[3]),
                                    int(x.split("_")[4]) + 2, int(x.split("_")[5]), int(x.split("_")[6]))
        dates.append([mystamp.timestamp(), x, first_lat, first_lon, last_lat, last_lon])

    dates.sort()
    pd.DataFrame(dates, columns=["Timestamp", "filename", "first_lat", "first_lon", "last_lat", "last_lon"]).to_csv(
        "../data/video_info/maschsee-" + chosen_date + ".csv", index=False)
            

def create_full_video(chosen_date: str, camera: str = "color"):
    output_path = "/home/ubuntu/haixInterface/videoDataOut/maschsee-" + chosen_date + "/" + camera + "_full.mp4"
    folder_path = "/home/ubuntu/haixInterface/videoData/" + chosen_date + "/files_extracted/"

    camera_folder = 'camera_' + camera

    camera_images = get_video_image_path_list(folder_path, camera_folder)

    print("[Vid] Creating full video with info for camera: ", camera)

    try:
        process = (
            ffmpeg
            .input('pipe:', format='image2pipe', framerate=20)
            .output(output_path, pix_fmt='yuv420p', loglevel="quiet")
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )

        for img in tqdm(camera_images):
            with open(img, 'rb') as f:
                process.stdin.write(f.read())

        process.stdin.close()
        process.wait()
    except ffmpeg.Error as e:
        print(e.stdout.decode('utf-8'))
        print(e.stderr.decode('utf-8'))
        sys.exit(1)


def create_full_video_info(chosen_date: str, camera: str = "color"):
    folder_path = "/home/ubuntu/haixInterface/videoData/" + chosen_date + "/files_extracted/"
    output_path = "/home/ubuntu/haixInterface/videoDataOut/maschsee-" + chosen_date + '/maschsee-' + chosen_date + "_" + camera + ".csv"

    camera_folder = 'camera_' + camera

    images = get_video_image_path_list(folder_path, camera_folder)

    csv_files = glob.glob(folder_path + "**/*.csv", recursive=True)
    csv_files.sort()

    print("[Info] Creating full video info for camera: ", camera)
    print("[Info] Reading csv files")
    # create one pd dataframe from all csv files
    pd_list = []
    for csv_file in tqdm(csv_files):
        pd_list.append(pd.read_csv(csv_file))

    full_pd = pd.concat(pd_list, ignore_index=True)

    print("[Info] Creating video info")

    video_info = []
    imageNumber = 0
    tolerance = 0.5 # seconds (+/-) image every second

    for image in tqdm(images):
        # get timestamp from image name
        timestamp = float(image.split("_")[-1].split(".")[0])

        # get video time
        video_time = round(imageNumber * (1 / 20), 2)
        imageNumber += 1

        lat_mean = full_pd.loc[(full_pd["timestamp"] >= timestamp - tolerance) & (full_pd["timestamp"] <= timestamp + tolerance), "latitude"].mean()
        lon_mean = full_pd.loc[(full_pd["timestamp"] >= timestamp - tolerance) & (full_pd["timestamp"] <= timestamp + tolerance), "longitude"].mean()

        if np.isnan(lat_mean) or np.isnan(lon_mean):
            print("[Warning] No GPS data found for timestamp: ", timestamp, "Using nearest timestamp instead")
            # find nearest timestamp
            nearest_timestamp = full_pd.loc[(full_pd["timestamp"] - timestamp).abs().argsort()[:1], "timestamp"].values[0]
            lat_mean = full_pd.loc[full_pd["timestamp"] == nearest_timestamp, "latitude"].values[0]
            lon_mean = full_pd.loc[full_pd["timestamp"] == nearest_timestamp, "longitude"].values[0]

        video_info.append([timestamp, lat_mean, lon_mean, video_time])


    video_info_df = pd.DataFrame(video_info, columns=["Timestamp", "Latitude", "Longitude", "VideoTime"])

    video_info_df.to_csv(output_path, index=False)


def get_video_image_path_list(folder_path: str, camera_folder: str):

    images = glob.glob(os.path.join(folder_path, '**/*.png'), recursive=True)

    camera_images = [image for image in images if camera_folder in image]
    camera_images.sort()

    return camera_images



if __name__ == "__main__":
    create_full_video('2024-08-15', 'infra1')