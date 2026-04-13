#!/usr/bin/env python3

import os
import subprocess
import argparse
import glob
import rosbag

def process_active_bag_files(bag_folder, orig_dir):
    """
    Processes active ROS bag files in the specified folder.

    Args:
        bag_folder (str): Path to the folder containing ROS bag files.
        orig_dir (str): Path to the folder where original files will be moved.

    Returns:
        None
    """
    # Find all active bag files in the specified folder
    bags = glob.glob(bag_folder + '*.bag.active')
    for bag_file in bags:
        try:
            # Try to open the bag file to check if it is valid
            with rosbag.Bag(bag_file, 'r') as bag:
                pass # Just to check if the file can be opened
        except rosbag.ROSBagException as e:
            # Handle different types of exceptions
            if "empty file" in str(e):
                print(f"Move bag file to folder orig: {bag_file}")
                move_bag_file_to_orig(bag_file, orig_dir)
            elif "Unindexed bag" in str(e):
                print(f"Unindexed bag found: {bag_file}")
                fix_active_bag_file(bag_file, bag_folder, orig_dir)
            else:
                print(f"Error processing {bag_file}: {e}")
            continue

        print(f"fix active bag file: {bag_file}")
        fix_active_bag_file(bag=bag_file, bag_folder=bag_folder, orig_dir=orig_dir)

def process_regular_bag_files(bag_folder, orig_dir):
    """
    Processes regular ROS bag files in the specified folder.

    Args:
        bag_folder (str): Path to the folder containing ROS bag files.
        orig_dir (str): Path to the folder where original files will be moved.

    Returns:
        None
    """
    # Find all regular bag files in the specified folder
    bags = glob.glob(bag_folder + '*.bag')
    for bag_file in bags:
        try:
            # Try to open the bag file to check if it contains messages
            with rosbag.Bag(bag_file, 'r') as bag:
                if not has_messages(bag):
                    print(f"Bag: {bag_file} has no Messages")
                    move_bag_file_to_orig(bag=bag_file,orig_dir=orig_dir)
        except rosbag.ROSBagException as e:
            # Handle different types of exceptions
            if "empty file" in str(e):
                print(f"Move bag file to folder orig: {bag}")
                move_bag_file_to_orig(bag=bag_file, orig_dir=orig_dir)
            elif "Unindexed bag" in str(e):
                print(f"Unindexed bag found: {bag_file}")
                base_name = get_base_name(bag_file)
                reindex_bag_file(bag=bag_file, bag_folder=bag_folder, base_name=base_name, orig_dir=orig_dir)
            else:
                print(f"Error processing {bag_file}: {e}")  
            continue

def fix_active_bag_file(bag, bag_folder, orig_dir):
    """
    Fixes an active ROS bag file by reindexing and moving it.

    Args:
        bag (str): Path to the active ROS bag file.
        bag_folder (str): Path to the folder containing ROS bag files.
        orig_dir (str): Path to the folder where original files will be moved.

    Returns:
        None
    """
    # Get the base name of the bag file
    base_name = get_base_name(bag)
    # Reindex the bag file
    reindex_bag_file(bag=bag, bag_folder=bag_folder, base_name=base_name, orig_dir=orig_dir)
    # Fix the bag file using rosbag fix
    fixed_bag_path = os.path.join(bag_folder, f"{base_name}.bag")
    subprocess.run(["rosbag", "fix", bag, fixed_bag_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Move the original bag file to the orig directory
    move_bag_file_to_orig(bag=bag, orig_dir=orig_dir)

def has_messages(bag):
    """
    Checks if the ROS bag file contains any messages.

    Args:
        bag (rosbag.Bag): The ROS bag file to check.

    Returns:
        bool: True if the bag contains messages, False otherwise.
    """
    message_count = bag.get_message_count()
    return message_count > 0
    
def move_bag_file_to_orig(bag, orig_dir):
    """
    Moves a ROS bag file to the original directory.

    Args:
        bag (str): Path to the ROS bag file.
        orig_dir (str): Path to the folder where original files will be moved.

    Returns:
        None
    """
    os.rename(bag, os.path.join(orig_dir, os.path.basename(bag)))

def get_base_name(file_path):
    """
    Extracts the base name from a file path.

    Args:
        file_path (str): The file path to extract the base name from.

    Returns:
        str: The base name of the file.
    """
    # Split the file path to get the base name
    filename, _ = os.path.splitext(os.path.basename(file_path))
    base_name = filename.split('.')[0]
    return base_name

def reindex_bag_file(bag, bag_folder, base_name, orig_dir):
    """
    Reindexes a ROS bag file and moves the original file.

    Args:
        bag (str): Path to the ROS bag file.
        bag_folder (str): Path to the folder containing ROS bag files.
        base_name (str): Base name of the ROS bag file.
        orig_dir (str): Path to the folder where original files will be moved.

    Returns:
        None
    """
    # Reindex the bag file using rosbag reindex
    subprocess.run(["rosbag", "reindex", bag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Determine the paths for the original active and regular bag files
    orig_active_path = os.path.join(bag_folder, f"{base_name}.bag.orig.active")
    orig_path = os.path.join(bag_folder, f"{base_name}.orig.bag")
    # Move the original bag file to the orig directory
    if os.path.exists(orig_active_path):
        move_bag_file_to_orig(bag=orig_active_path, orig_dir=orig_dir)
    else:
        move_bag_file_to_orig(bag=orig_path, orig_dir=orig_dir)
    
def process_bag_files(bag_folder):
    """
    Processes all ROS bag files in the specified folder.

    Args:
        bag_folder (str): Path to the folder containing ROS bag files.

    Returns:
        None
    """
    # Create the orig directory if it doesn't exist
    orig_dir = os.path.join(bag_folder, "orig")
    os.makedirs(orig_dir, exist_ok=True)

    # Process active and regular bag files
    process_active_bag_files(bag_folder=bag_folder, orig_dir=orig_dir)
    process_regular_bag_files(bag_folder=bag_folder, orig_dir=orig_dir)

    # Check if the orig directory is empty and remove it if it is
    if not os.listdir(orig_dir):
        print(f"Removing empty directory: {orig_dir}")
        os.rmdir(orig_dir)

    # Verify if the bags in the directory contain messages
    bags = glob.glob(bag_folder + '*.bag')
    for bag_file in bags:
        with rosbag.Bag(bag_file, 'r') as bag:
            if not has_messages(bag):
                print(f"Bag: {bag_file} has no Messages")
                move_bag_file_to_orig(bag=bag_file,orig_dir=orig_dir)

def main():
    """
    Main function to parse arguments and process the ROS bag files.

    This function sets up the argument parser to accept a single argument:
    - `bag_folder`: The path to the directory containing ROS bag files.

    It then validates the provided directory and initiates the processing
    of the ROS bag files.

    Args:
        None

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Process ROS bag files to check for errors, reindex, and move them as needed.")
    parser.add_argument('bag_folder', type=str, help='Path to the directory containing ROS bag files. This directory will be scanned for both active and regular ROS bag files.')
    args = parser.parse_args()

    bag_folder = args.bag_folder

    # Check if the provided path is a valid directory
    if not os.path.isdir(bag_folder):
        print(f"Error: {bag_folder} is not a valid directory.")
        return

    # Process the bag files in the specified directory
    process_bag_files(bag_folder)

if __name__ == '__main__':
    main()