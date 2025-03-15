#!/bin/bash
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel


MAKE_ENTER_DIRECTORY=false

source "$SCRIPT_MOCKSHADOW_DIR/mock-utils.sh"
validate_file_exists "$SCRIPT_MOCKSHADOW_DIR/env.sh"
source "$SCRIPT_MOCKSHADOW_DIR/env.sh"
validate_directory_exists $DIR_ORIGINAL_PROJECT
