#!/usr/bin/env python3

import argparse
import rosbag
import rospy
import os
import sys


def downcample_bag(input_bag_path, output_bag_path, target_frequency, topic):

    target_interval = rospy.Duration(1.0 / target_frequency)
    last_timestamp = None

    with rosbag.Bag(output_bag_path, 'w') as outbag:
        for input_topic, msg, timestamp in rosbag.Bag(input_bag_path).read_messages():
            if input_topic == topic:
                if last_timestamp is None or (timestamp - last_timestamp) >= target_interval:
                    outbag.write(topic, msg, timestamp)
                    last_timestamp = timestamp

            else:
                outbag.write(input_topic, msg, timestamp)
            
def main():
    parser = argparse.ArgumentParser(description="Downsample a ROS bag file.")
    parser.add_argument('bag_directory', type=str, help='Path to directory containing bag files')
    parser.add_argument("-f", "--frequency", type=float, default=1.0, help="Desired output frequency in Hz.")
    parser.add_argument('-t', '--topic', type=str, required=True, help='Topic to Downsample')

    args = parser.parse_args()

    bag_directory = args.bag_directory
    output_directory = os.path.join(bag_directory, 'downsampled_bags')

    target_frequency = args.frequency
    topic = args.topic

    # make output folder
    if not os.path.isdir(output_directory):
        try:
            os.makedirs(output_directory)
        except OSError as e:
            print(f"ERROR: {e.filename}: {e.strerror}")
            sys.exit(1)

    for filename in os.listdir(bag_directory):
        if filename.endswith('.bag'):
            input_bag_path = os.path.join(bag_directory, filename)
            output_bag_path = os.path.join(output_directory, filename.replace('.bag', '-downsampled.bag'))
            
            downcample_bag(input_bag_path, output_bag_path, target_frequency, topic)


if __name__ == '__main__':
    main()