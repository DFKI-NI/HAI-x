#!/usr/bin/env python3


"""
python3 bag_to_img.py -h
usage: bag_to_img.py [-h] -t TOPIC [TOPIC ...] [-f FORMAT] [-p PNG_COMPRESSION] [-j JPG_QUALITY] bag_folder

Extract images from ROS bag files.

positional arguments:
  bag_folder            Path to the directory containing ROS bag files.

optional arguments:
  -h, --help            show this help message and exit
  -t TOPIC [TOPIC ...], --topic TOPIC [TOPIC ...]
                        List of image topics to extract from the ROS bag files
  -f FORMAT, --format FORMAT
                        Image format ("png"/"jpg"), default: "png"
  -p PNG_COMPRESSION, --png-compression PNG_COMPRESSION
                        PNG compression (0-9, 0 = off, 1 = best speed (default), 9 = highest compression)
  -j JPG_QUALITY, --jpg-quality JPG_QUALITY
                        JPEG image quality (0-100, default: 95)

Example usage:
  python3 bag_to_img.py /path/to/bag/files/ -t /camera/color camera/infra1 -f png -p 3
"""
import rosbag

import argparse
import glob

import os

import cv2
import cv_bridge

# Initialize the CvBridge class to convert ROS image messages to OpenCV images
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
    # Split the topic name and create a base name
    split_topic = topic.split('/')
    base_name = '_'.join(split_topic[3:]).strip('_')
    return f'{base_name}_{timestamp}'

def buffer_readout(bag, args):
    """
    Reads messages from a ROS bag file and buffers them by topic.

    Args:
        bag: The ROS bag file.
        args: Command-line arguments containing the list of topics.

    Returns:
        dict: A dictionary with topics as keys and lists of (timestamp, image) tuples as values.
    """
    buffer = {name: [] for name in args.topic[:]}
    
    # Read messages from the bag file and buffer them
    for topic, msg, t in bag.read_messages():
        if topic in args.topic[:]: 
           buffer[topic].append((msg.header.stamp, to_cv_image(msg))) 
        
    return buffer

def dump_buffer(buffer, save_prefix, bag_name, args):
    """
    Dumps the buffered images to files.

    Args:
        buffer (dict): The buffered images.
        save_prefix (str): The prefix for saving the output.
        bag_name (str): The name of the bag file.
        args: Command-line arguments containing the image format and quality/compression settings.
    """
    # Iterate over the buffered images and save them to files
    for topic, images in buffer.items():
        for timestamp, image in images:
            filename = create_file_name(topic, timestamp)
            folder_name = f"{topic.split('/')[1]}_{topic.split('/')[2]}"
            create_output_folder(save_prefix, bag_name, folder_name)

            # Save the image in the specified format
            if args.format == 'png':
                cv2.imwrite(os.path.join(save_prefix, bag_name, folder_name, filename + '.png'), image, [cv2.IMWRITE_PNG_COMPRESSION, args.png_compression])
                
            elif args.format == 'jpg':
                cv2.imwrite(os.path.join(save_prefix, bag_name, folder_name, filename + '.jpg'), image, [cv2.IMWRITE_JPEG_QUALITY, args.jpg_quality])

            else:
                error_message = f'Unsupported file format: {args.format}. (Supported are: png, jpg).'
                print(error_message)  # print the error, because the exception will be silently swallowed by the executor
                raise RuntimeError(error_message)

def create_output_folder(save_path, bag_name, topic=None):
    """
    Creates the output folder in the main save path.

    Args:
        save_path (str): The path where the output should be saved.
        bag_name (str): The name of the bag.
        topic (str, optional): The topic name. Defaults to None.
    """
    # Determine the output directory path
    if topic:
        output_dir = os.path.join(save_path, bag_name, topic)
    else:
        output_dir = os.path.join(save_path, bag_name)

    # Create the output directory if it doesn't exist
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

        # Open the bag file and process its contents
        with rosbag.Bag(bag_path, 'r') as bag:
            buffer = buffer_readout(bag, args)
            dump_buffer(buffer, save_prefix, bag_name, args)

        print(f'Bag finished: {bag_name}')

    except Exception as e:
        print(f'Failed to process {bag_path}: {e}')


def main():
    """
    Main function to parse arguments and process the ROS bag files.
    """
    parser = argparse.ArgumentParser(description='Extract images from ROS bag files.')
    parser.add_argument('bag_folder', type=str, help='Path to the directory containing ROS bag files.')
    parser.add_argument('-t', '--topic', type=str, nargs='+', required=True, help='List of image topics to extract from the ROS bag files')
    parser.add_argument('-f', '--format', type=str, default='png', help='Image format ("png"/"jpg"), default: "png"')
    parser.add_argument('-p','--png-compression', type=int, default=1, help='PNG compression (0-9, 0 = off, 1 = best speed (default), 9 = highest compression)')
    parser.add_argument('-j', '--jpg-quality', type=int, default=95, help='JPEG image quality (0-100, default: 95)')

    args = parser.parse_args()

    bag_folder = args.bag_folder

    # Check if the specified bag folder is valid
    if not os.path.isdir(bag_folder):
        print(f"Error: {bag_folder} is not a valid directory.")
        return

    # Set up the save prefix for extracted files
    save_prefix = os.path.join(bag_folder, 'files_extracted')
    bags = glob.glob(bag_folder + '*.bag')

    # Check if any bag files are found in the specified directory
    if not bags:
        print("No bag files found in the specified directory.")
        return 

    # Process each bag file
    for bag_path in bags:
        process_bag_file(bag_path, save_prefix, args)

if __name__ == '__main__':
    main()