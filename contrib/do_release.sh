#!/bin/sh

set -e

DOCKER_REPO=stv0g
DOCKER_IMAGE=${DOCKER_REPO}/withings-sync

VER=$(sed -n -e 's/.*version='\''\([0-9\.]*\)'\''.*/\1/p' < setup.py)

git tag v${VER} || true
git push --tags

docker build \
    -t ${DOCKER_IMAGE} \
    -t ${DOCKER_IMAGE}:${VER} .

docker push ${DOCKER_IMAGE}
docker push ${DOCKER_IMAGE}:${VER}

python3 setup.py sdist

twine upload dist/withings-sync-${VER}.tar.gz