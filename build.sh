#!/bin/bash

# This script is very specific to my particular setup on my machine.
# It must be run after `flit publish` to update the package on PyPI.
# It uses `scripts/pyapp-runner.sh`, a simple CI script that runs via ssh,
# to build and sign the binaries for the package and then build the installer package.

# Get the current version of the package from the source
VERSION=$(grep __version__ applecrate/version.py | cut -d "\"" -f 2)

# Build the binaries and package them
# arm64 binary built on a remote M1 Mac
bash scripts/pyapp-runner.sh m1 applecrate $VERSION
bash scripts/pyapp-runner.sh macbook applecrate $VERSION
