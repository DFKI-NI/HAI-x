#!/usr/bin/env python3

"""
ROS Bag File Processor
======================

usage: extract_navsatfix.py [-h] -t TOPIC bag_folder

Extract NavSatFix messages from ROS bag files and save them as CSV.

positional arguments:
  bag_folder            Path to the directory containing ROS bag files.

optional arguments:
  -h, --help            show this help message and exit
  -t TOPIC, --topic TOPIC
                        ROS topic containing NavSatFix messages

Example:
    python3 extract_navsatfix.py /path/to/bag/files/ -t /fix
"""

import argparse
import os
import sys
import glob

import pandas as pd

import rosbag


def create_file_name(topic, timestamp):
    """
    Create a file name based on the ROS topic and timestamp.

    Args:
        topic (str): The ROS topic name.
        timestamp (float): The timestamp of the message.

    Returns:
        str: The generated file name.
    """
    base_name = '_'.join(topic.split('/')).strip('_')
    return f'{base_name}_{timestamp}'


def extract_navsatfix_messages(fix_msg):
    """
    Extract latitude, longitude, and timestamp from a NavSatFix message.

    Args:
        fix_msg (NavSatFix): The NavSatFix message.

    Returns:
        dict: A dictionary containing latitude, longitude, and timestamp.
    """
    return {
        'latitude': fix_msg.latitude,
        'longitude': fix_msg.longitude,
        'timestamp': fix_msg.header.stamp.to_sec()  # Convert ROS time to seconds
    }

def dump_buffer(buffer, save_prefix, bag_name):
    """
    Dump the buffered messages to a CSV file.

    Args:
        buffer (dict): The buffer containing messages.
        save_prefix (str): The prefix for the save path.
        bag_name (str): The name of the bag file.

    Returns:
        None
    """
    data = []
    for topic, messages in buffer.items():
        # Get the timestamp of the first message for the filename
        timestamp = messages[0][0].secs
        # Create the full path for the output CSV file
        filename = os.path.join(save_prefix, bag_name, create_file_name(topic, timestamp) + '.csv')
        for t, msg in messages:
            # Append each message's data to the list
            data.append({
                'timestamp': t.to_sec(),
                'latitude': msg['latitude'],
                'longitude': msg['longitude']
            })
    # Convert the list of dictionaries to a DataFrame and save as CSV
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)



def buffer_readout(bag, args):
    """
    Read messages from the ROS bag and buffer them.

    Args:
        bag (rosbag.Bag): The ROS bag object.
        args (argparse.Namespace): The command-line arguments.

    Returns:
        dict: A buffer containing the read messages.
    """
    buffer = {args.topic: [] }
    for topic, msg, t in bag.read_messages():
        if topic == args.topic:
            # Append the timestamp and extracted message data to the buffer
            buffer[topic].append((t, extract_navsatfix_messages(fix_msg=msg)))
    
    return buffer


def create_output_folder(save_path, bag_name):
    """
    Create the output folder if it does not exist.

    Args:
        save_path (str): The base path for saving files.
        bag_name (str): The name of the bag file.

    Returns:
        None
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
    Process a single ROS bag file.

    Args:
        bag_path (str): The path to the ROS bag file.
        save_prefix (str): The prefix for the save path.
        args (argparse.Namespace): The command-line arguments.

    Returns:
        None
    """
    try:
        # Generate a name for the bag file based on its path
        bag_name = '_'.join(bag_path.split('/')[-1].split('-'))[:-4]
        # Create the output directory for the current bag file
        create_output_folder(save_path=save_prefix, bag_name=bag_name)

        with rosbag.Bag(bag_path, 'r') as bag:
            # Read and buffer the messages from the bag file
            buffer = buffer_readout(bag, args)
            # Dump the buffered messages to a CSV file
            dump_buffer(buffer, save_prefix, bag_name)

        print(f'Bag finished: {bag_name}')

    except Exception as e:
        print(f'Failed to process {bag_path}: {e}')

def main():
    """
    Main function to parse arguments and process the ROS bag files.

    Args:
        None

    Returns:
        None
    """

    parser = argparse.ArgumentParser(description='Extract NavSatFix messages from ROS bag files and save them as CSV.')
    parser.add_argument('bag_folder', type=str, help='Path to the directory containing ROS bag files.')
    parser.add_argument('-t', '--topic', type=str, required=True, help='ROS topic containing NavSatFix messages')

    args = parser.parse_args()

    bag_folder = args.bag_folder

    if not os.path.isdir(bag_folder):
        print(f"Error: {bag_folder} is not a valid directory.")
        return

    save_prefix = os.path.join(bag_folder, 'files_extracted')
    bags = glob.glob(bag_folder + '*.bag')

    if not bags:
        print("No bag files found in the specified directory.")
        return 

    for bag_path in bags:
        process_bag_file(bag_path, save_prefix, args)

if __name__ == '__main__':
    main()
