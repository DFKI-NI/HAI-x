#!/usr/bin/env python3

"""
python3 bag_to_mpeg.py --help
usage: bag_to_mpeg.py [-h] -t TOPICS [TOPICS ...] [-f FPS] bag_folder

Convert a folder of ROS bagfiles into MPEG video files, extracting images from specified topics.

positional arguments:
  bag_folder                Path to the directory containing ROS bag files.

optional arguments:
  -h, --help                show this help message and exit
  -t TOPIC [TOPIC ...], --topics TOPICS [TOPICS ...] List of image topics
  -f FPS, --fps FPS         Frames per second for the output mpeg (default: 20)
  -c Codec, --codec Codec   Encoder Used for the output mpeg (default: avc1)
  --create-combined-video   Flag to create a combined video instad of the individual videos (default: False)

Description:
  This script processes each ROS bag file in the specified bag_folder, extracts images from the given topics, and converts them into individual MPEG video files. The output videos are saved in a subdirectory named 'files_extracted' within the bag_folder.
"""

import os
import sys
import argparse
import glob
import csv

import cv2
import cv_bridge
import rosbag
import rospy


try:
    from scripts.bag_to_trajectory import extract_trajectory_data
except ImportError:
    from bag_to_trajectory import extract_trajectory_data



# Initialize the CvBridge class
CVB = cv_bridge.CvBridge()

def to_cv_image(img_msg):
    """
    Converts a ROS image message into a BGR, 16-bit mono, or 8-bit mono OpenCV image.

    Args:
        img_msg: The ROS image message.

    Returns:
        The converted OpenCV image.
        
    Raises:
        RuntimeError: If the image format is unsupported.
    """
    if img_msg._type == 'sensor_msgs/Image':
        img_data = CVB.imgmsg_to_cv2(img_msg)
        if img_msg.encoding in ['16UC1', 'mono16', '8UC1', 'mono8', '8UC3', 'bgr8']:
            pass # # already in BGR format
        elif img_msg.encoding == 'rgb8':
            img_data = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
        elif img_msg.encoding == '8UC4' or img_msg.encoding == 'bgra8':
            img_data = cv2.cvtColor(img_data, cv2.COLOR_BGRA2BGR)
        elif img_msg.encoding == 'bayer_rggb8':
            img_data = cv2.cvtColor(img_data, cv2.COLOR_BAYER_BG2BGR)
        else:
            raise RuntimeError(f"Unsupported Image format '{img_msg.encoding}'")

    elif img_msg._type == 'sensor_msgs/CompressedImage':
        img_data = CVB.compressed_imgmsg_to_cv2(img_msg, desired_encoding="passthrough")
        if img_msg.format in ['mono8; jpeg compressed ']:
            img_data = cv2.cvtColor(img_data, cv2.COLOR_BAYER_BG2BGR)
    else:
        raise RuntimeError(f"Unsupported message format '{img_msg._type}'")

    return img_data


def create_file_name(topic, timestamp):
    """
    Creates a file name by combining the topic and the timestamp.

    Args:
        topic (str): The ROS topic name.
        timestamp (int): The timestamp of the first message.

    Returns:
        str: The generated file name.
    """
    base_name = '_'.join(topic.split('/')).strip('_')
    return f'{base_name}_{timestamp}'

def dump_buffer(buffer, save_prefix, bag_name, args):
    """
    Dumps the buffer to video files.

    Args:
        buffer (dict): Dictionary with topic data.
        save_prefix (str): Prefix for saving the output.
        bag_name (str): Name of the bag.
        args: Command-line arguments.
    """
    for topic, val in buffer.items():
        timestamp = val[0][0].secs
        file_name = os.path.join(save_prefix, bag_name, create_file_name(topic, timestamp) + '.mp4')
        height, width = val[0][1].shape[:2]
        mpeg = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*args.codec), args.fps, (width, height))

        for _, frame in val:
            mpeg.write(frame)

        mpeg.release()

def buffer_readout(bag, args):
    """
    Processes ROS bag messages and stores them in a buffer.

    Args:
        bag: The ROS bag object.
        args: Command-line arguments.

    Returns:
        dict: Buffer with processed messages.
    """
    buffer = {name: [] for name in args.topic[:]}
    first_timestamps = {}

    for topic, msg, t in bag.read_messages():
        if topic in args.topic[:]:            
            buffer[topic].append((t, to_cv_image(msg)))

    return buffer

def create_output_folder(save_path, bag_name):
    """
    Creates the output folder in the main save path.

    Args:
        save_path (str): The path where the output should be saved.
        bag_name (str): The name of the bag.
    """
    output_dir = os.path.join(save_path, bag_name)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"ERROR: {e.filename}: {e.strerror}")
            sys.exit(1)

def process_bag_file(bag_path, save_prefix, args):
    """
    Processes a single ROS bag file.

    Args:
        bag_path (str): Path to the ROS bag file.
        save_prefix (str): Prefix for saving the output.
        args: Command-line arguments.
    """
    try:
        bag_name = '_'.join(bag_path.split('/')[-1].split('-'))[:-4]
        create_output_folder(save_prefix, bag_name)

        with rosbag.Bag(bag_path, 'r') as bag:
            buffer = buffer_readout(bag, args)
            dump_buffer(buffer, save_prefix, bag_name, args)

        print(f'Bag finished: {bag_name}')
    except Exception as e:
        print(f'Failed to process {bag_path}: {e}')

def fullVideoTopics(bags,save_prefix, gps_data, args):
    """
    Process ROS bag files to extract video frames and timestamps, and save them as one video file.

    This function sorts the provided ROS bag files, extracts frames from the specified topic, and compiles them into one video file.

    Args:
        bags (list): A list of paths to the ROS bag files.
        save_prefix (str): Prefix for saving the output.
        args: Command-line arguments.
    """
    bags.sort()

    for myTopic in args.topic[:]:

        firstBag = True
        timestamps = []

        filename = myTopic.split('/')[2]
    
        for bag_path in bags:

            try:
                bag_name = '_'.join(bag_path.split('/')[-1].split('-'))[:-4]

                create_output_folder(save_prefix, bag_name)

                with rosbag.Bag(bag_path, 'r') as bag:

                    buffer = {myTopic: []}
                    for topic, msg, t in bag.read_messages():
                        if topic == myTopic:
                            buffer[topic].append((t, to_cv_image(msg)))
                            timestamps.append(str(t.secs))

                    for topic, val in buffer.items():
                        timestamp = val[0][0].secs
                        if firstBag:
                            file_name = os.path.join(save_prefix, filename + '_full.mp4')
                            height, width = val[0][1].shape[:2]
                            mpeg = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*args.codec), args.fps, (width, height))
                            firstBag = False

                        for _, frame in val:
                            mpeg.write(frame)

                print(f'Bag finished: {bag_name}')
            except Exception as e:
                print(f'Failed to process {bag_path}: {e}')

        mpeg.release()
        save_timestamps_with_gps(save_prefix, filename, timestamps, gps_data, args.fps)

# def save_timestamps_to_csv(save_prefix, filename, timestamps, args):
#     """
#     Save timestamps to a CSV file.

#     This function creates a CSV file containing the provided timestamps and their corresponding video times.
#     The video time is calculated based on the frame rate (fps) specified in the arguments (args).

#     Args:
#         save_prefix (str): Prefix for saving the output.
#         filename (str): The name of the CSV file (without extension).
#         timestamps (list): A list of timestamps to be saved.
#         args: Command-line arguments.
#     """
#     videoTime = 0
#     file_path = os.path.join(save_prefix, filename + '_full.csv')
#     try:
#         with open(file_path, mode='w', newline='') as file:
#             writer = csv.writer(file)
#             writer.writerow([filename + '-timestamps', 'videoTime'])

#             for timestamp in timestamps:
#                 writer.writerow([timestamp, videoTime])
#                 videoTime = round(videoTime + 1 / args.fps, 2)
#     except Exception as e:
#         print(f"An error occurred while saving the file: {e}")


def save_timestamps_with_gps(save_prefix, filename, timestamps, gps_data, fps):
    """
    Save frame timestamps together with GPS data and video time.
    """

    # GPS dictionary: { timestamp(int): (lat, lon) }
    gps_lookup = {
        int(item['timestamp']): (item['latitude'], item['longitude'])
        for item in gps_data
    }

    file_path = os.path.join(save_prefix, filename + "_full.csv")

    videoTime = 0.0

    try:

        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Latitude", "Longitude", "VideoTime"])

            for t in timestamps:
                ts = int(t)

                # get gps or fill with None
                if ts in gps_lookup:
                    lat, lon = gps_lookup[ts]
                else:
                    lat, lon = None, None  # oder Interpolation möglich

                writer.writerow([ts, lat, lon, round(videoTime, 2)])

                videoTime += 1.0 / fps

    except Exception as e:
        print(f"An error occurred while saving the file: {e}")

def main():
    """
    Main function to parse arguments and process the ROS bag files.
    """
    parser = argparse.ArgumentParser(description='Convert a folder of ROS bagfiles into MPEG video files, extracting images from specified topics.')
    parser.add_argument('bag_folder', type=str, help='Path to the directory containing ROS bag files.')
    parser.add_argument('-t', '--topic', type=str, nargs='+', required=True, help='List of image topics to extract from the ROS bag files')
    parser.add_argument('--gps-topic', type=str, default='/fix')
    parser.add_argument('-f', '--fps', type=int, default=20, help='Frames per second for the output mpeg (default: 20)') 
    parser.add_argument('-c', '--codec', type=str, default='avc1', help='Encoder Used for the output mpeg (default: avc1)')
    parser.add_argument('--create-combined-video', action='store_true', help='Flag to create a combined video instad of the individual videos (default: False)')

    args = parser.parse_args()

    bag_folder = args.bag_folder

    if not os.path.isdir(bag_folder):
        print(f"Error: {bag_folder} is not a valid directory.")
        return

    save_prefix = os.path.join(bag_folder, 'files_extracted')
    bags = glob.glob(bag_folder + '*.bag')

    gps_data = extract_trajectory_data(bag_folder, args.gps_topic, save_to_disk=False)

    if not bags:
        print("No bag files found in the specified directory.")
        return 

    if args.create_combined_video:
        fullVideoTopics(bags, save_prefix, gps_data, args)
    else:
        for bag_path in bags:
            process_bag_file(bag_path, save_prefix, args)

if __name__ == '__main__':
    main()