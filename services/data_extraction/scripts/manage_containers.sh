#!/bin/bash

compose_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && cd .. && pwd )"

# Set the default compose file
compose_file="compose.yml"

# Set the default profile
profile="ros-extractor"

# Set the build flag
build=""

# Set the action (up or down)
action="up"

# Set the base name of the ssh key pair
ssh_key="github"

# Set the no-cache flag
no_cache=""

# Set the detach flag
detach=""

# Function to print the usage instructions
print_usage() {
  echo "Usage: $0 [--profile|-p <profile>] [--build|-b] [--down|-d] [--ssh-key <key_name>] [--no-cache] [--detach|-D]"
  echo "Options:"
  echo "  --profile, -p <profile>    Specify the profile to use. Default: ros-bridge"
  echo "  --build, -b                Build the images before starting the containers"
  echo "  --down, -d                 Stop and remove the containers instead of starting"
  echo "  --ssh-key <key_name>       Specify the base name of the key pair"
  echo "  --no-cache                 Build the images without using cache"
  echo "  --detach, -D               Run containers in detached mode"
}

# Check if the script was called with --help or -h
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  print_usage
  exit 0
fi

# Check command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|-p)
      shift
      profile="$1"
      ;;
    --build|-b)
      build="--build"
      ;;
    --down|-d)
      action="down"
      ;;
    --ssh-key)
      shift
      ssh_key="$1"
      ;;
    --no-cache)
      no_cache="--no-cache"
      ;;
    --detach|-D)
      detach="-d"
      ;;
    *)
      echo "Unknown argument: $1"
      print_usage
      exit 1
      ;;
  esac
  shift
done

# Validate and export ssh_key
if [[ -n "$ssh_key" ]]; then
  export SSH_PRV_KEY=$(cat ~/.ssh/${ssh_key})
  export SSH_PUB_KEY=$(cat ~/.ssh/${ssh_key}.pub)
else
  echo "Error: Base name of the key pair not specified or does not exist."
  print_usage
  exit 1
fi


# Execute the docker compose command
if [[ "$action" == "up" ]]; then
  if [[ -n "$build" ]]; then
    docker compose -f "${compose_dir}/$compose_file" --profile "$profile" build $no_cache
  fi
  docker compose -f "${compose_dir}/$compose_file" --profile "$profile" up $detach
else
  docker compose -f "${compose_dir}/$compose_file" --profile "$profile" down
fi