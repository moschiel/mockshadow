#!/usr/bin/env python3
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel
import os
import mock_utils

# Diretório do projeto mock shadow
DIR_MOCK_SHADOW_PROJECT = os.getcwd()

# Diretório para a árvore de mocks
DIR_SHADOW_MOCKS = os.path.join(DIR_MOCK_SHADOW_PROJECT, "MOCK_TREE").rstrip("/")

# Diretório do projeto temporário
DIR_TEMP_PROJECT = os.path.join(DIR_MOCK_SHADOW_PROJECT, "TEMP_PROJECT").rstrip("/")

USER_ENV = mock_utils.get_user_env()
USER_CONFIGS = mock_utils.get_user_configs()