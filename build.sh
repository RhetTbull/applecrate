#!/bin/bash

# This script is very specific to my particular setup on my machine.
# It must be run after `flit publish` to update the package on PyPI.
# It uses `scripts/pyapp-runner.sh`, a simple CI script that runs via ssh,
# to build and sign the binaries for the package and then build the installer package.

# Get the current version of the package from the source
VERSION=$(grep __version__ applecrate/version.py | cut -d "\"" -f 2)

# verify VERSION is valid
# PyApp will happily build with an invalid version number
# get directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYPI_VERSION=$(python $DIR/scripts/get_latest_pypi_version.py applecrate)
if [ "$PYPI_VERSION" != "$VERSION" ]; then
    echo "Invalid version number: $VERSION"
    echo "Latest version on PyPI: $PYPI_VERSION"
    echo "Did you forget to run 'flit publish'?"
    exit 1
fi

# Build the binaries and package them
# arm64 binary built on a remote M1 Mac
echo "Building version $VERSION for Apple Silicon"
bash scripts/pyapp-runner.sh m1 applecrate $VERSION

echo "Building version $VERSION for Intel"
bash scripts/pyapp-runner.sh macbook applecrate $VERSION
