#python3
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel

# This a example of a environment file
# Make a copy og this file, the copy must be named "env.sh", 
# then change the configurations in your "env.sh" according to your environment

import os

# Diretório original do projeto
DIR_ORIGINAL_PROJECT = os.path.expanduser("/path/to/project").rstrip("/")

# Diretório do projeto mock shadow
DIR_MOCK_SHADOW_PROJECT = os.path.expanduser("/path/to/mock/shadow/project").rstrip("/")

# Diretório para a árvore de mocks
DIR_SHADOW_MOCKS = os.path.join(DIR_MOCK_SHADOW_PROJECT, "MOCK_TREE").rstrip("/")

# Diretório do projeto temporário
DIR_TEMP_PROJECT = os.path.join(DIR_MOCK_SHADOW_PROJECT, "TEMP_PROJECT").rstrip("/")
