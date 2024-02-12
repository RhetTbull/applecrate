#!/bin/bash

# This script is specific to my particular setup on my machine.
# It must be run after `flit publish` to update the package on PyPI.
# It will build and sign the binaries for the package and
# then build the installer package.

# Get the current version of the package from the source
VERSION=$(grep __version__ applecrate/version.py | cut -d "\"" -f 2)

# Build the binaries
# arm64 binary built on a remote M1 Mac
bash scripts/pyapp-runner.sh m1 applecrate $VERSION
bash scripts/pyapp-runner.sh macbook applecrate $VERSION

# Sign the binaries
echo "Signing the binaries with Developer ID Application certificate: $DEVELOPER_ID_APPLICATION"
codesign --force --deep --sign "$DEVELOPER_ID_APPLICATION" applecrate-${VERSION}-x86_64
codesign --force --deep --sign "$DEVELOPER_ID_APPLICATION" applecrate-${VERSION}-arm64

# Build the installer
applecrate build
