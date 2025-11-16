#!/bin/bash

set -e

# Find the user data directory
if [[ "$(uname)" == "Darwin" ]]; then
    DATA_DIR="$HOME/Library/Application Support/crsqlite"
elif [[ "$(uname)" == "Linux" ]]; then
    DATA_DIR="$HOME/.local/share/crsqlite"
else
    echo "Unsupported platform"
    exit 1
fi

# Fallback to project's lib directory if user data directory can't be created
if ! mkdir -p "$DATA_DIR"; then
    DATA_DIR="lib"
    mkdir -p "$DATA_DIR"
fi


# Detect the platform
if [[ "$(uname)" == "Darwin" ]]; then
    if [[ "$(uname -m)" == "arm64" ]]; then
        PLATFORM="darwin-arm64"
    else
        PLATFORM="darwin-x86_64"
    fi
elif [[ "$(uname)" == "Linux" ]]; then
    PLATFORM="linux-x86_64"
else
    echo "Unsupported platform"
    exit 1
fi

# Download and extract the binary
URL="https://github.com/vlcn-io/cr-sqlite/releases/download/v0.16.3/crsqlite-${PLATFORM}.zip"
echo "Downloading cr-sqlite for ${PLATFORM} from ${URL}"
curl -L -o "${DATA_DIR}/crsqlite.zip" "${URL}"
unzip "${DATA_DIR}/crsqlite.zip" -d "${DATA_DIR}"
rm "${DATA_DIR}/crsqlite.zip"

echo "cr-sqlite has been installed in the ${DATA_DIR} directory"
