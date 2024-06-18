import os
from robotestrail.logging_config import setup_logging
from robotestrail.robot_framework_utils import run_dryrun_and_get_tests, generate_csv_for_test_rail
from robotestrail.testrail_api import (
    tr_get_test_cases,
    tr_add_section,
    tr_add_run_to_plan,
    tr_get_milestones,
    tr_get_projects
)

from robotestrail.testrail_utils import (
    move_orphan_tests_to_orphan_folder,
    add_or_set_test_plan,
    set_test_results,
    get_project_by_name,
    get_test_suite_by_name,
    get_section_by_name,
    add_folders_to_testrail,
    add_tests_to_testrail,
    update_tests_in_testrail,
)

from robotestrail.config import (
    PROJECT_NAME,
    TEST_SUITE_NAME,
    ROOT_TEST_SECTION_NAME,
    TEST_RUN_NAME,
    TEST_RUN_DESCRIPTION,
    PATH_TO_ROBOT_TESTS_FOLDER,
    ROBOT_TEST_OUTPUT_XML_FILE_PATH,
    TESTRAIL_URL,
    TESTRAIL_USER,
    TESTRAIL_API_KEY,
    MAX_WORKERS,
    ROOT_TEST_SECTION_DISCLAIMER,
    ORPHAN_TEST_SECTION_NAME,
    ORPHAN_TEST_SECTION_DESCRIPTION,
    TEST_PLAN_NAME,
    TEST_PLAN_DESCRIPTION,
    SOURCE_CONTROL_NAME,
    SOURCE_CONTROL_LINK,
    TESTRAIL_DEFAULT_TC_PRIORITY_ID,
    TESTRAIL_DEFAULT_TC_TYPE_ID,
)

import concurrent.futures
from datetime import datetime

# Initialize the logger for this module
logger = setup_logging()


def sync_robot_tests_to_testrail():
    path = PATH_TO_ROBOT_TESTS_FOLDER
    # Get project and suite IDs
    project_id = get_project_by_name(PROJECT_NAME)["id"]
    suite_id = get_test_suite_by_name(project_id, TEST_SUITE_NAME)["id"]

    # Connect to the TestRail and get a list of existing test cases
    existing_tr_tests = tr_get_test_cases(project_id, suite_id)["cases"]

    # Add root TestRail section if it doesn't exist
    root_section = get_section_by_name(project_id, suite_id, ROOT_TEST_SECTION_NAME)
    if not root_section:
        tr_add_section(project_id, suite_id, ROOT_TEST_SECTION_NAME)

    # Run Robot Framework dry run and get all the existing tests
    robot_tests = run_dryrun_and_get_tests(path, "dryrun_output.xml")

    # If a folder (.robot file or dir with the .robot file) exists locally but NOT in TestRail, then it will be added as section
    add_folders_to_testrail(project_id, suite_id, robot_tests)

    # Add tests to TestRail if they are missing
    add_tests_to_testrail(project_id, suite_id, existing_tr_tests, robot_tests)

    # Update tests in TestRail if they are present
    update_tests_in_testrail(project_id, suite_id, existing_tr_tests, robot_tests)

    # Move orphan tests to ORPHAN folder
    move_orphan_tests_to_orphan_folder(project_id, suite_id, robot_tests)

    # TODO move empty folders to orphan folder


def add_new_test_results():
    # Get project and suite IDs
    project_id = get_project_by_name(PROJECT_NAME)["id"]
    suite_id = get_test_suite_by_name(project_id, TEST_SUITE_NAME)["id"]

    # Select test plan with specific name. Add new one if missing
    test_plan = add_or_set_test_plan(project_id)
    # Add new test run to the test plan

    test_run = tr_add_run_to_plan(
        test_plan["id"],
        suite_id,
        f"{TEST_RUN_NAME} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        TEST_RUN_DESCRIPTION,
    )

    # Set testrail test run results based on the robot output.xml file
    set_test_results(project_id, suite_id, test_run, ROBOT_TEST_OUTPUT_XML_FILE_PATH)

def generate_csv():
    generate_csv_for_test_rail(PATH_TO_ROBOT_TESTS_FOLDER)

def show_milestones():
    project_id = get_project_by_name(PROJECT_NAME)["id"]
    milestones = tr_get_milestones(project_id)
    if not milestones:
        print("No milestones found.")
    else:
        print(f'Milestones for the project "{PROJECT_NAME}":\n')
        for milestone in milestones["milestones"]:
            print(f"{milestone['name']} - {milestone['id']}")

def create_config():
    print("Creating a new config file with the default values...")
    pass

def check():
    errors = []
    warnings = []

    def check_required_config_field(field_name, field, error, description):
        if not field:
            errors.append(
                {
                    "error": f"Required field is missing: {field}",
                    "description": description,
                }
            )

    print(
        "Checking the config file, Robot Framework tests, and the TestRail connection... \n"
    )
    # check_required_config_field(TESTRAIL_URL, "TESTRAIL_URL", "TestRail URL is missing", "URL to the TestRail instance")

    if TESTRAIL_URL == "not_set":
        errors.append(
            {
                "error": "Required config field is missing: TESTRAIL_URL",
                "description": "It should be something like: https://your-organization.testrail.com",
            }
        )

    if TESTRAIL_USER == "not_set":
        errors.append(
            {
                "error": "Required config field is missing: TESTRAIL_USER",
                "description": "TestRail user name. Usually it's an email address. You can find it in your TestRail profile: Username > My Settings > Email Address. https://your-organization.testrail.com/index.php?/mysettings",
            }
        )

    if TESTRAIL_API_KEY == "not_set" or TESTRAIL_API_KEY ==None:
        errors.append(
            {
                "error": "Required config field is missing: TESTRAIL_API_KEY",
                "description": "TestRail API key. You can create it in your TestRail profile: Username > My Settings > API Keys. https://your-organization.testrail.com/index.php?/mysettings . Then you have to export it as an environment variable. For example: export TESTRAIL_API_KEY=your_api_key (for Linux and MacOS). DON'T ADD THE API KEY DIRECTLY TO THE CONFIG FILE! Config file should contain only the name of the environment variable.",
            }
        )
    
    if PROJECT_NAME == "not_set":
        errors.append(
            {
                "error": "Required config field is missing: PROJECT_NAME",
                "description": "Name of the project in TestRail. The projects are listed on the main TestRail page: https://your-organization.testrail.com/",
            }
        )
    
    if TEST_SUITE_NAME == "not_set":
        errors.append(
            {
                "error": "Required config field is missing: TEST_SUITE_NAME",
                "description": "Name of the test suite in TestRail. The test suites are listed in the project",
            }
        )
    
    if MAX_WORKERS == -1:
        errors.append(
            {
                "error": "Required config field is missing: MAX_WORKERS",
                "description": "It is the number of max concurrent requests to the TestRail. It should be a positive integer. If you are not sure, set it to 1 or check with your TestRail admin.",
            }
        )

    if ROOT_TEST_SECTION_NAME == "not_set":
        errors.append(
            {
                "error": "Required config field is missing: ROOT_TEST_SECTION_NAME",
                "description": "Name of the root test section in TestRail. It is the parent of all the test cases.",
            }
        )

    

    # required_fields = [TESTRAIL_URL, TESTRAIL_USER, TESTRAIL_API_KEY, PROJECT_NAME, TEST_SUITE_NAME, MAX_WORKERS, ROOT_TEST_SECTION_NAME, ROOT_TEST_SECTION_DISCLAIMER, ORPHAN_TEST_SECTION_NAME, ORPHAN_TEST_SECTION_DESCRIPTION, TEST_PLAN_NAME, TEST_PLAN_DESCRIPTION, TEST_RUN_NAME, TEST_RUN_DESCRIPTION, PATH_TO_ROBOT_TESTS_FOLDER, ROBOT_TEST_OUTPUT_XML_FILE_PATH, SOURCE_CONTROL_NAME, SOURCE_CONTROL_LINK, TESTRAIL_DEFAULT_TC_PRIORITY_ID, TESTRAIL_DEFAULT_TC_TYPE_ID]


    #check connection to TestRail
    try:
        tr_get_projects()
        print("Successfully connected to TestRail.")
    except Exception as e:
        errors.append(
            {
                "error": "Can't connect to TestRail. Make sure the TestRail URL, user, and API key are correct.",
                "description": f"Error: {e}",
            }
        )
    

    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"- {error['error']} - {error['description']}")
    else:
        print("No errors found.")
