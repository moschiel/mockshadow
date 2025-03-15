#!/bin/bash
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel

set -e

# Init submodules
echo "initializing submodules"
sudo git submodule update --init --recursive

# Make scripts executable
echo "Setting scripts execution permission"
sudo chmod +x mockshadow
sudo find . -type f -name "*.sh" | xargs sudo chmod +x

# Add Simbolyc Link to /usr/local/bin/
mockshadowpath="$(cd "$(dirname "$0")" && pwd -P)/mockshadow"
echo "Adding symbolic link for '$mockshadowpath' into '/usr/local/bin/mockshadow'"
sudo rm /usr/local/bin/mockshadow
sudo ln -s "$mockshadowpath" /usr/local/bin/mockshadow


# Build clang-code-extractor
echo "Building clang-code-extractor"
cd clang-code-extractor
sudo ./build.sh

echo "mockshadow setup complete!"