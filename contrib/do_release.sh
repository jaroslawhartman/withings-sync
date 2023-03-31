#!/bin/sh
# This script can be used to bypass github actions
# it deploys to pipy with api credentials
# (username=__token__, password=pypi-***)

set -e
# extract the version="x.y.z" from setup.py
VER=$(sed -n -e 's/.*version="\(.*\)".*/\1/p' < setup.py)

function tag_if_not_tagged {
  TAG=v$1
  if git rev-parse --verify --quiet "refs/tags/$TAG" >/dev/null; then
    echo "tag ${TAG} already exists"
  else
    git tag $TAG
    git push --tags
    echo "tagged ${TAG}"
  fi
}

function publish_to_pypi() {
  VERSION=$1
  echo "creating sdist.."
  python3 setup.py sdist > /dev/null
  ARTIFACT="dist/withings-sync-${VERSION}.tar.gz"
  # Publish to pypi.org
  twine check $ARTIFACT
  twine upload $ARTIFACT
}

tag_if_not_tagged $VER
publish_to_pypi $VER


