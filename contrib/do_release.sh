#!/bin/sh
# This script can be used to bypass github actions
# it deploys to pipy with api credentials
# (username=__token__, password=pypi-***)

set -e
# extract the version="x.y.z" from pyproject.toml
VER=$(sed -n -e 's/.*version = "\(.*\)".*/\1/p' < pyproject.toml)

function tag_if_not_tagged {
  TAG=v$VER
  if git rev-parse --verify --quiet "refs/tags/$TAG" >/dev/null; then
    echo "tag ${TAG} already exists"
  else
    git tag $TAG
    git push --tags
    echo "tagged ${TAG}"
  fi
}

function publish_to_pypi() {
  echo "creating sdist.."
  poetry build
  # Publish to pypi.org
  poetry publish
}

tag_if_not_tagged $VER
publish_to_pypi $VER


