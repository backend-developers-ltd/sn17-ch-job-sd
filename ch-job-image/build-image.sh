#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <config_file> <docker_image_name>"
    exit 1
fi

MODEL_CONFIG_FILE=$1
DOCKER_IMAGE_NAME=$2

if [ ! -d "$PWD/image-generator" ]; then
    echo "image-generator directory does not exist. Please check it out first." >&2
    exit 1
fi

if [ ! -f "$PWD/image-generator/preload.py" ] || [ ! -f "$PWD/image-generator/setup_env.sh" ]; then
    echo "image-generator directory content is incorrect. It should contain the image generation project code along with preload.py and setup_env.sh files." >&2
    exit 1
fi

if [ -z "${MODEL_CONFIG_FILE}" ] || ! [ -f "${MODEL_CONFIG_FILE}" ]; then
    echo "$MODEL_CONFIG_FILE does not exist" >&2
    exit 1
fi



# Pass in additional files relevant to given model file
ADDITIONAL_CONTEXT="$(mktemp -d)"
cp "$MODEL_CONFIG_FILE" "$ADDITIONAL_CONTEXT/model_config.yml"

echo Building $DOCKER_IMAGE_NAME from $MODEL_CONFIG_FILE

docker build \
  --build-context codebase="$PWD/image-generator" \
  --build-context additional_context="$ADDITIONAL_CONTEXT" \
  --file docker/Dockerfile \
  --tag "$DOCKER_IMAGE_NAME" \
  docker
