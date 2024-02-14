#!/bin/bash

# PyApp Runner -- Very simple CI for building/packaging python project via PyApp and AppleCrate
# This script is used to build and copy the PyApp executable from a remote server.
# It also packages the executable with applecrate, signs it, and copies it back to the local machine.

# See https://ofek.dev/pyapp/latest/how-to/ for more information on PyApp.
# The remote server must have PYAPP defined in the ~/.zshenv file
# to point to the install location of pyapp.
# echo 'export PYAPP="/Users/johndoe/code/pyapp-latest"' >> ~/.zshenv
# For code signing to work via ssh, you must first run this one time on the machine via GUI
# See https://developer.apple.com/forums/thread/712005 for more information on signing via ssh
# You must also have the following environment variables set in the ~/.zshenv of the remote server:
# export DEVELOPER_ID_APPLICATION="Developer ID Application: John Doe (XXXXXXXX)"
# export KEYCHAIN_PASSWORD="password"
# export CODE_DIR="/Users/johndoe/code" # the directory where the code is located
# This script assumes the code for the project is located in the directory $CODE_DIR/$PROJECT_NAME
# and that the project is configured for AppleCrate via the applecrate.toml file in the project directory.

# Usage: pyapp-runner.sh SERVER PROJECT_NAME PROJECT_VERSION
# SERVER is the nick name of the remote server and will be combined with $PYAPP_SERVER_ to get the actual server name
# In my case, I have the following values for the server in my ~/.zshrc file:
# export PYAPP_SERVER_INTEL="address of Intel Mac"
# export PYAPP_SERVER_ARM="address of Apple Silicon Mac"

# Check that all 3 arguments are provided
if [ $# -ne 3 ]; then
    echo "Usage: $0 SERVER PROJECT_NAME PROJECT_VERSION"
    exit 1
fi

SERVER=$1
PROJECT_NAME=$2
PROJECT_VERSION=$3

# define the remote server and user
# assumes ssh keys are setup for the user
# Set these directly or read from environment variables
USER=$PYAPP_USER

SERVER=$(echo $SERVER | tr '[:lower:]' '[:upper:]')
SERVER=PYAPP_SERVER_$SERVER
SERVER=${!SERVER}

if [ -z "$SERVER" ]; then
    echo "Server not found: $1"
    exit 1
fi

echo "Building on $SERVER"

# Connect to the remote server
ssh ${USER}@${SERVER} 'bash -l -s' << ENDSSH
# Commands to run on remote host
cd \$PYAPP

# clean the build directory
rm -f target/release/pyapp

# build the project
PYAPP_PROJECT_NAME=${PROJECT_NAME} PYAPP_PROJECT_VERSION=${PROJECT_VERSION} cargo build --release

if [ \$? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

# sign the binary
# For this to work via ssh, you must first run this one time on the machine via GUI
# Then click "Always Allow" when prompted to always allow codesign to access the key in the future

echo "Unlocking keychain"
security unlock-keychain -p \$KEYCHAIN_PASSWORD

if [ \$? -ne 0 ]; then
    echo "Failed to unlock keychain"
    exit 1
fi

echo "Signing the binary with \$DEVELOPER_ID_APPLICATION"
codesign --force -s "\$DEVELOPER_ID_APPLICATION" target/release/pyapp

if [ \$? -ne 0 ]; then
    echo "Codesign failed"
    exit 1
fi

# package the binary
mkdir -p "\${CODE_DIR}/${PROJECT_NAME}/build"
TARGET="\${CODE_DIR}/${PROJECT_NAME}/build/${PROJECT_NAME}-${PROJECT_VERSION}-\$(uname -m)"
echo "Copying target/release/pyapp to \$TARGET"
cp "target/release/pyapp" \$TARGET

echo "Changing to \${CODE_DIR}/${PROJECT_NAME}"
cd \${CODE_DIR}/${PROJECT_NAME}
echo "Pulling latest code and building package"
git pull
applecrate build

if [ \$? -ne 0 ]; then
    echo "Package build failed"
    exit 1
fi

echo "Done building $PROJECT_NAME"

ENDSSH

if [ $? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

# Copy the binary from the remote server
PYAPP_PATH=$(ssh ${USER}@${SERVER} 'echo $PYAPP')
PYAPP_ARCH=$(ssh ${USER}@${SERVER} 'uname -m')
CODE_DIR_SERVER=$(ssh ${USER}@${SERVER} 'echo "${CODE_DIR%/}"')
mkdir -p dist
PACKAGE="${PROJECT_NAME}-${PROJECT_VERSION}-${PYAPP_ARCH}-installer.pkg"
TARGET="dist/${PACKAGE}"
echo "Copying $PACKAGE from $SERVER to $TARGET"
scp ${USER}@${SERVER}:"${CODE_DIR_SERVER}/${PROJECT_NAME}/dist/$PACKAGE" $TARGET

echo "Done: ${TARGET}"
