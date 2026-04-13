#!/bin/bash
set -e

# Get a list of image IDs with the "none" tag
image_ids=($(docker images -f "dangling=true" -q))

# Check if there are any images with the "none" tag
if [ ${#image_ids[@]} -eq 0 ]; then
  echo "No images with the 'none' tag found."
  exit 0
fi

# List the images with the "none" tag
echo "Images with the 'none' tag:"
docker images --format "{{.ID}}\t{{.Repository}}:{{.Tag}}" -f "dangling=true"

# Prompt the user for confirmation
read -r -p "Are you sure you want to delete these images? (y/n) " confirm

if [ "$confirm" != "y" ]; then
  echo "Deletion canceled."
  exit 0
fi

# Delete the images with the "none" tag
echo "${image_ids[@]}" | xargs docker rmi

# Check if the image deletion was successful
echo "Successfully deleted images with the 'none' tag."