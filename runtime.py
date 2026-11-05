"""Project configuration for extractor flag resolution."""
import os
import mock_utils
DIR_MOCK_SHADOW_PROJECT = os.getcwd()
DIR_SHADOW_OUTPUT = os.path.join(DIR_MOCK_SHADOW_PROJECT, 'shadow_output')
USER_CONFIGS = mock_utils.get_user_configs()
USER_ENV = mock_utils.get_user_env()
DIR_SHADOW_MOCKS = os.path.join(DIR_MOCK_SHADOW_PROJECT, USER_CONFIGS['mocksDirectory'])
