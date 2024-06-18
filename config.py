import os
import yaml
import logging

# Global variables
TESTRAIL_URL = None
TESTRAIL_USER = None
TESTRAIL_API_KEY = None
PROJECT_NAME = None
TEST_SUITE_NAME = None
MAX_WORKERS = None
ROOT_TEST_SECTION_NAME = None
ROOT_TEST_SECTION_DISCLAIMER = None
ORPHAN_TEST_SECTION_NAME = None
ORPHAN_TEST_SECTION_DESCRIPTION = None
TEST_PLAN_NAME = None
TEST_PLAN_DESCRIPTION = None
TEST_RUN_NAME = None
TEST_RUN_DESCRIPTION = None
PATH_TO_ROBOT_TESTS_FOLDER = None
ROBOT_TEST_OUTPUT_XML_FILE_PATH = None
SOURCE_CONTROL_NAME = None
SOURCE_CONTROL_LINK = None
TESTRAIL_DEFAULT_TC_PRIORITY_ID = None
TESTRAIL_DEFAULT_TC_TYPE_ID = None

# Initialize the logger for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ConfigLogger')

def read_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def initialize_config(config):
    global TESTRAIL_URL, TESTRAIL_USER, TESTRAIL_API_KEY, PROJECT_NAME, TEST_SUITE_NAME
    global MAX_WORKERS, ROOT_TEST_SECTION_NAME, ROOT_TEST_SECTION_DISCLAIMER
    global ORPHAN_TEST_SECTION_NAME, ORPHAN_TEST_SECTION_DESCRIPTION, TEST_PLAN_NAME
    global TEST_PLAN_DESCRIPTION, TEST_RUN_NAME, TEST_RUN_DESCRIPTION
    global PATH_TO_ROBOT_TESTS_FOLDER, ROBOT_TEST_OUTPUT_XML_FILE_PATH
    global SOURCE_CONTROL_NAME, SOURCE_CONTROL_LINK, TESTRAIL_DEFAULT_TC_PRIORITY_ID
    global TESTRAIL_DEFAULT_TC_TYPE_ID

    TESTRAIL_URL = config.get('testrail', {}).get('url', 'not_set')
    TESTRAIL_USER = config.get('testrail', {}).get('user', 'not_set')
    TESTRAIL_API_KEY = os.getenv(config.get('testrail', {}).get('api_key_env_var', 'not_set'))
    PROJECT_NAME = config.get('project', {}).get('name', 'not_set')
    TEST_SUITE_NAME = config.get('project', {}).get('suite_name', 'not_set')
    MAX_WORKERS = config.get('testrail', {}).get('max_workers', -1)
    ROOT_TEST_SECTION_NAME = config.get('test_section', {}).get('root_name', 'not_set')
    ROOT_TEST_SECTION_DISCLAIMER = config.get('test_section', {}).get('root_disclaimer', 'not_set')
    ORPHAN_TEST_SECTION_NAME = config.get('test_section', {}).get('orphan_name', 'not_set')
    ORPHAN_TEST_SECTION_DESCRIPTION = config.get('test_section', {}).get('orphan_description', 'not_set')
    TEST_PLAN_NAME = config.get('test_plan', {}).get('name', 'not_set')
    TEST_PLAN_DESCRIPTION = config.get('test_plan', {}).get('description', 'not_set')
    TEST_RUN_NAME = config.get('test_run', {}).get('name', 'not_set')
    TEST_RUN_DESCRIPTION = config.get('test_run', {}).get('description', 'not_set')
    PATH_TO_ROBOT_TESTS_FOLDER = config.get('paths', {}).get('tests_folder', 'not_set')
    ROBOT_TEST_OUTPUT_XML_FILE_PATH = config.get('paths', {}).get('output_xml_file', 'not_set')
    SOURCE_CONTROL_NAME = config.get('source_control', {}).get('name', 'not_set')
    SOURCE_CONTROL_LINK = config.get('source_control', {}).get('link', 'not_set')
    TESTRAIL_DEFAULT_TC_PRIORITY_ID = config.get('testrail_defaults', {}).get('priority_id', -1)
    TESTRAIL_DEFAULT_TC_TYPE_ID = config.get('testrail_defaults', {}).get('type_id', -1)

    # Log the missing keys
    for key, value in config.items():
        if not value:
            logger.warning(f"Config is missing key: {key}")
