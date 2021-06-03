#!/bin/sh

set -e

DOCKER_REPO=stv0g
DOCKER_IMAGE=${DOCKER_REPO}/withings-sync
DOCKER_PLATFORMS=linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6

VER=$(sed -n -e 's/.*version='\''\([0-9\.]*\)'\''.*/\1/p' < setup.py)

git tag v${VER} || true
git push --tags

# Build Docker image

docker buildx create \
	--use \
	--platform ${DOCKER_PLATFORMS} \
	--name cross-platform-build

docker buildx build \
	--platform ${DOCKER_PLATFORMS} \
	--tag ${DOCKER_IMAGE}:${VER} \
	--push .

exit 0

# Publish to pypi.org
python3 setup.py sdist

twine upload dist/withings-sync-${VER}.tar.gz
