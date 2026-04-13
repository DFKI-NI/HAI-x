#!/bin/bash

# Set the target registry
TARGET_REGISTRY="git.ni.dfki.de:5050"

# Function to display usage instructions
display_usage() {
  echo "Usage: $0 [namespace]"
  echo "Push Docker images from the specified namespace to the target registry."
  echo "If no namespace is provided, the script will identify the namespace automatically."
  echo "Options:"
  echo "  -h, --help    Display this help and exit."
}

# Check if the help option is specified
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  display_usage
  exit 0
fi

# Get the namespace from the command-line argument or set it to empty
NAMESPACE="$1"

# Get a list of available namespaces
AVAILABLE_NAMESPACES=$(docker image ls --format "{{.Repository}}" | awk -F '/' '{print $2}' | uniq)

# Check if no namespace is provided
if [ -z "$NAMESPACE" ]; then
  # Check if no available namespaces found
  if [ -z "$AVAILABLE_NAMESPACES" ]; then
    echo "No namespaces found."
    exit 1
  fi

  echo "Available namespaces:"
  echo "$AVAILABLE_NAMESPACES"
  read -p "Enter the namespace to push images: " NAMESPACE

  # Check if the entered namespace is valid
  if ! echo "$AVAILABLE_NAMESPACES" | grep -q "^$NAMESPACE$"; then
    echo "Invalid namespace."
    exit 1
  fi
fi

# Get a list of image IDs from 'docker image ls' for the specified namespace
IMAGE_IDS=$(docker image ls --format "{{.ID}} {{.Repository}}" | awk -v namespace="$NAMESPACE" '$2 ~ namespace {print $1}')

# List the images for confirmation
echo "Images to be pushed:"
for IMAGE_ID in $IMAGE_IDS; do
  REPO_TAG=$(docker image inspect --format='{{index .RepoTags 0}}' $IMAGE_ID)
  echo "$REPO_TAG"
done

# Prompt for confirmation
read -p "Confirm pushing the above images to the target registry? (y/n) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "Pushing images aborted."
  exit 1
fi

# Prompt the user for the registry username
read -p "Enter registry username: " REGISTRY_USERNAME

# Prompt the user for the registry password
read -sp "Enter registry password: " REGISTRY_PASSWORD
echo

# Log in to the target registry using --password-stdin
echo "$REGISTRY_PASSWORD" | docker login -u $REGISTRY_USERNAME --password-stdin $TARGET_REGISTRY

# Push the images for the specified namespace to the target registry
for IMAGE_ID in $IMAGE_IDS; do
  REPO_TAG=$(docker image inspect --format='{{index .RepoTags 0}}' $IMAGE_ID)
  docker push $REPO_TAG
done

# Log out from the target registry
docker logout $TARGET_REGISTRY