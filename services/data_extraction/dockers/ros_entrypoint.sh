#!/bin/bash
set -e

function ros_source_env() 
{
	if [ -f "$1" ]; then
		echo "sourcing   $1"
		source "$1"
	else
		echo "not found   $1"
	fi	
}

# setup ros environment
ros_source_env "/opt/ros/noetic/setup.bash"

# Check if CATKIN_WS is set and source it
if [ -n "$CATKIN_WS" ]; then
    ros_source_env "$CATKIN_WS/devel/setup.bash"
fi

# Execute any additional commands passed to the container
exec "$@"