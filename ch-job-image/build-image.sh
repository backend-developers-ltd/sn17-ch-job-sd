#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <config_file> <docker_image_name>"
    exit 1
fi

MODEL_CONFIG_FILE=$1
DOCKER_IMAGE_NAME=$2

if [ -z "${MODEL_CONFIG_FILE}" ] || ! [ -f "${MODEL_CONFIG_FILE}" ]; then
    echo "$MODEL_CONFIG_FILE does not exist" >&2
    exit 1
fi

# Pass in additional files relevant to given model file
ADDITIONAL_CONTEXT="$(mktemp -d)"
cp "$MODEL_CONFIG_FILE" "$ADDITIONAL_CONTEXT/model_config.yml"

echo Building $DOCKER_IMAGE_NAME from $MODEL_CONFIG_FILE

docker build \
  --build-context codebase="$PWD/../sn17-image-generator" \
  --build-context additional_context="$ADDITIONAL_CONTEXT" \
  --file docker/Dockerfile \
  --tag "$DOCKER_IMAGE_NAME" \
  docker
