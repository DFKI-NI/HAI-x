#!/bin/bash

# Define the device as a variable
device="/dev/ttyACM0"

# Create a filename with the current date and time
filename="data_$(date +'%Y-%m-%d_%H-%M-%S').txt"

# Use the tee command to display the output on the screen and write it to the file
cat -v <"$device" | tee "$filename"