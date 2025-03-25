#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 3 ]; then
    echo "Usage: $0 <config_file> <docker_repo> <docker_image_prefix> [docker_image_version=latest]"
    exit 1
fi

MODEL_CONFIG_FILE=$1
DOCKER_REPO=$2
DOCKER_IMAGE_PREFIX=$3
DOCKER_IMAGE_VERSION=${4:-latest}
IMAGE_SUFFIX=$(basename "$1" ".${1##*.}")

if [ -z "${MODEL_CONFIG_FILE}" ] || ! [ -f "${MODEL_CONFIG_FILE}" ]; then
    echo "$MODEL_CONFIG_FILE does not exist" >&2
    exit 1
fi

FULL_IMAGE_NAME=$DOCKER_REPO/$DOCKER_IMAGE_PREFIX-$IMAGE_SUFFIX:$DOCKER_IMAGE_VERSION

echo Building $FULL_IMAGE_NAME from $MODEL_CONFIG_FILE

# Pass in additional files relevant to given model file
ADDITIONAL_CONTEXT="$(mktemp -d)"
cp "$MODEL_CONFIG_FILE" "$ADDITIONAL_CONTEXT/model_config.yml"

docker build \
  --build-context codebase="$PWD/sn17-image-generator" \
  --build-context additional_context="$ADDITIONAL_CONTEXT" \
  --file docker/Dockerfile \
  --tag sn17-$IMAGE_SUFFIX \
  docker
