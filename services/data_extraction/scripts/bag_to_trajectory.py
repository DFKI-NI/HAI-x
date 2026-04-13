#!/usr/bin/env python3

"""
python3 bag_to_trajectory.py --help
usage: bag_to_trajectory.py [-h] -t TOPIC bag_folder

Extract a GPS/trajectory CSV from ROS bag files containing NavSatFix messages.

positional arguments:
    bag_folder                Path to the directory containing ROS bag files.

optional arguments:
    -h, --help                show this help message and exit
    -t TOPIC, --topic TOPIC   Topic from which to read NavSatFix messages
                                                        (e.g. /gps/fix).

Description:
    This script processes each ROS bag file in the specified bag_folder, reads
    NavSatFix messages from the given topic, and collects their timestamps and
    geographic coordinates. All trajectory points are written to a single
    CSV file named 'trajectory.csv' in a subdirectory called 'files_extracted'
    inside the bag_folder. The CSV contains the columns: timestamp, latitude,
    longitude, and date (local time, YYYY-MM-DD).
"""

import os
import sys
import argparse
import glob
from typing import List, Dict

import rosbag
from datetime import datetime
import pandas as pd


def unix_to_local_date(ts: int) -> str:
    """
    Converts a Unix timestamp to a local date string in the format 'YYYY-MM-DD'.
    
    Args:
        ts (int): The Unix timestamp.
    Returns:
        str: The formatted date string.
    """
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def create_output_folder(save_path: str) -> None:
    """Ensure that the given output directory exists.

    Args:
        save_path (str): Directory path to create if it does not exist.
    """
    os.makedirs(save_path, exist_ok=True)


def collect_trajectory_points(bags, topic: str):
    """Collect trajectory points from the given bag files.

    This function iterates over all provided ROS bag files and extracts
    NavSatFix messages from the specified topic.

    Args:
        bags (list[str]): Paths to ROS bag files.
        topic (str): NavSatFix topic to read (e.g. "/fix").

    Returns:
        list[dict]: A list of trajectory points with the keys
            ``timestamp``, ``latitude``, ``longitude``, and ``date``.
    """
    bags.sort()

    data = []

    for bag_path in bags:
        try:
            bag_name = '_'.join(bag_path.split('/')[-1].split('-'))[:-4]

            with rosbag.Bag(bag_path, 'r') as bag:
                for bag_topic, msg, t in bag.read_messages():
                    if bag_topic == topic:
                        data.append(
                            {
                                'timestamp': str(t.secs),
                                'latitude': msg.latitude,
                                'longitude': msg.longitude,
                                'date': unix_to_local_date(t.secs),
                            }
                        )

            print(f'Bag finished: {bag_name}')
        except Exception as e:
            print(f'Failed to process {bag_path}: {e}')

    return data


def save_timestamps_to_csv(save_prefix: str, filename: str, data: List[Dict]) -> None:
    """
    Save trajectory data to a CSV file.

    This function creates a CSV file containing the provided trajectory
    points (timestamps and coordinates).

    Args:
        save_prefix (str): Directory in which the CSV file will be stored.
        filename (str): The base name of the CSV file (without extension).
        data (list[dict]): Trajectory points with keys 'timestamp',
            'latitude', 'longitude', and 'date'.
    """
    if not data:
        return

    create_output_folder(save_prefix)
    df = pd.DataFrame(data)
    file_path = os.path.join(save_prefix, filename + '.csv')
    df.to_csv(file_path, index=False)


def extract_trajectory_data(
    bag_folder: str,
    topic: str,
    save_to_disk: bool = True,
) -> List[Dict]:
    """Extract trajectory data from a folder of ROS bag files.

    This helper is intended for both command-line and programmatic use
    (e.g. from the FastAPI service). It collects all NavSatFix messages
    from the given topic, optionally writes them to ``trajectory.csv`` and
    always returns the deduplicated trajectory in memory.

    Args:
        bag_folder (str): Directory containing ROS bag files.
        topic (str): NavSatFix topic to read (e.g. "/fix").
        save_to_disk (bool): If True (default), also write a CSV file named
            ``trajectory.csv`` into ``bag_folder/files_extracted``.

    Returns:
        list[dict]: A list of deduplicated trajectory points with the keys
            ``timestamp``, ``latitude``, ``longitude``, and ``date``.
    """
    if not os.path.isdir(bag_folder):
        raise FileNotFoundError(
            f"Bag folder does not exist or is not a directory: {bag_folder}"
        )

    bags = glob.glob(os.path.join(bag_folder, '*.bag'))
    if not bags:
        return []

    points = collect_trajectory_points(bags, topic)
    if not points:
        return []

    df = pd.DataFrame(points)
    if df.empty:
        return []

    # delete duplicate rows where all columns are the same
    df_no_duplicats = df.drop_duplicates(keep='first')
    # delete duplicate rows based on timestamp only
    df_no_duplicats = df_no_duplicats.drop_duplicates(subset=['timestamp'], keep='first')
    dedup_points = df_no_duplicats.to_dict(orient='records')

    if save_to_disk:
        save_prefix = os.path.join(bag_folder, 'files_extracted')
        filename = 'trajectory'
        save_timestamps_to_csv(save_prefix, filename, dedup_points)

    return dedup_points


def main():
    """
    Main entry point to parse arguments and process the ROS bag files.
    """
    parser = argparse.ArgumentParser(
        description=(
            'Extract a GPS/trajectory CSV from ROS bag files containing '
            'NavSatFix messages.'
        )
    )
    parser.add_argument('bag_folder', type=str, help='Path to the directory containing ROS bag files.')
    parser.add_argument(
        '-t',
        '--topic',
        type=str,
        required=True,
        help='Topic from which to read NavSatFix messages (e.g. /fix).',
    )

    args = parser.parse_args()

    try:
        trajectory_points = extract_trajectory_data(
            bag_folder=args.bag_folder,
            topic=args.topic,
            save_to_disk=True,
        )
    except FileNotFoundError as exc:
        print(str(exc))
        return

    if not trajectory_points:
        print("No trajectory points found in the specified directory.")
        return

    print(f"Extracted {len(trajectory_points)} trajectory points and wrote trajectory.csv.")


if __name__ == '__main__':
    main()