#!/bin/bash
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel

# This a example of a environment file
# Make a copy og this file, the copy must be named "env.sh", 
# then change the configurations in your "env.sh" according to your environment

# original project directory
DIR_ORIGINAL_PROJECT=/path/to/project
DIR_ORIGINAL_PROJECT="${DIR_ORIGINAL_PROJECT%/}" # garante que nao tem um "/" no final

# mock shadow project directory
DIR_SHADOW_MOCKS=/path/to/mock/shadow/project
DIR_SHADOW_MOCKS="${DIR_SHADOW_MOCKS%/}" # garante que nao tem um "/" no final

DIR_SHADOW_MOCKS="$DIR_MOCK_SHADOW_PROJECT/MOCK_TREE"
DIR_SHADOW_MOCKS="${DIR_SHADOW_MOCKS%/}" # garante que nao tem um "/" no final

DIR_TEMP_PROJECT="$DIR_MOCK_SHADOW_PROJECT/TEMP_PROJECT"
DIR_TEMP_PROJECT="${DIR_TEMP_PROJECT%/}" # garante que nao tem um "/" no final
