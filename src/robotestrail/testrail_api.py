import os
import requests
from collections import Counter
import concurrent.futures

import xml.etree.ElementTree as ET
from robotestrail.logging_config import setup_logging
from datetime import datetime
from enum import Enum
from robotestrail.robot_framework_utils import parse_robot_output_xml, get_rich_text_steps

from robotestrail.config import (
    TESTRAIL_URL, TESTRAIL_USER, TESTRAIL_API_KEY,
    MAX_WORKERS, ROOT_TEST_SECTION_NAME, ROOT_TEST_SECTION_DISCLAIMER, ORPHAN_TEST_SECTION_NAME, 
    ORPHAN_TEST_SECTION_DESCRIPTION, TEST_PLAN_NAME, TEST_PLAN_DESCRIPTION,
    SOURCE_CONTROL_NAME, SOURCE_CONTROL_LINK, TESTRAIL_DEFAULT_TC_PRIORITY_ID, TESTRAIL_DEFAULT_TC_TYPE_ID
)

# Initialize the logger for this module
logger = setup_logging()

# Define the statuses in Robot Framework
class RobotFrameworkStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"

# Define the statuses in TestRail
class TestRailStatus(Enum):
    PASSED = 1
    BLOCKED = 2
    UNTESTED = 3
    RETEST = 4
    FAILED = 5

# Map Robot Framework statuses to TestRail statuses
STATUS_MAPPING = {
    RobotFrameworkStatus.PASS: TestRailStatus.PASSED,
    RobotFrameworkStatus.FAIL: TestRailStatus.FAILED,
    RobotFrameworkStatus.SKIP: TestRailStatus.RETEST,
    RobotFrameworkStatus.NOT_RUN: TestRailStatus.UNTESTED,
}

def get_testrail_status_by_robot_status(robot_status):
    return STATUS_MAPPING.get(RobotFrameworkStatus(robot_status), TestRailStatus.UNTESTED).value


# API
# Function to send GET requests to TestRail API
def tr_get_testrail_data(endpoint):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/{endpoint}"
    response = requests.get(url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY))
    if response.status_code != 200:
        raise Exception(f"Failed to get data: {response.status_code} {response.text}")
    try:
        data = response.json()
    except ValueError:
        raise Exception(f"Failed to parse JSON response: {response.text}")
    return data

def tr_get_milestones(project_id):
    endpoint = f"get_milestones/{project_id}"
    milestones = tr_get_testrail_data(endpoint)
    logger.info(f"Retrieved {len(milestones)} milestones for project ID {project_id}")
    return milestones

def tr_get_projects():
    endpoint = f"get_projects"
    return tr_get_testrail_data(endpoint)


# Function to delete a test suite
def tr_delete_test_suite(suite_id):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/delete_suite/{suite_id}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers
    )
    if response.status_code == 200:
        logger.info(f"Successfully deleted suite with ID {suite_id}")
    else:
        raise Exception(
            f"Failed to delete suite: {response.status_code} {response.text}"
        )


# Function to get details of a test suite
def tr_get_test_suite(suite_id):
    endpoint = f"get_suite/{suite_id}"
    return tr_get_testrail_data(endpoint)


def tr_get_test_suites(project_id):
    endpoint = f"get_suites/{project_id}"
    return tr_get_testrail_data(endpoint)

def tr_move_cases_to_section(suite_id, section_id, case_ids):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/move_cases_to_section/{section_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "suite_id": suite_id,
        "case_ids": case_ids
    }
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data
    )
    if response.status_code == 200:
        logger.info(f"Tests moved to ORPHAN: {case_ids}")
    else:
        raise Exception(
            f"Failed to move tests: {response.status_code} {response.text}"
        )


# Function to get sections in a test suite
def tr_get_sections(project_id, suite_id):
    endpoint = f"get_sections/{project_id}&suite_id={suite_id}"
    return tr_get_testrail_data(endpoint)


# Function to get test cases in a section
def tr_get_test_cases(project_id, suite_id):
    endpoint = f"get_cases/{project_id}&suite_id={suite_id}"
    return tr_get_testrail_data(endpoint)


def tr_add_section(project_id, suite_id, section_name, parent_id=None, description=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_section/{project_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "suite_id": suite_id,
        "name": section_name,
        "description": description,  # Optional: Add a description to the section
        "parent_id": parent_id,  # Optional: If adding a subsection, specify the parent section ID
    }
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data
    )
    if response.status_code == 200:
        section = response.json()
        logger.info(f"Section added: '{section_name}' with ID {section['id']}")
        return section
    else:
        raise Exception(
            f"Failed to add section: {response.status_code} {response.text}"
        )


def tr_update_section(section_id, section_name, description=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/update_section/{section_id}"
    headers = {"Content-Type": "application/json"}
    data = {"name": section_name,
            "description": description,
            }
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data
    )
    if response.status_code == 200:
        section = response.json()
        logger.info(f"Section updated: '{section_name}' | S{section['id']} | {section['description']}")
        return section
    else:
        raise Exception(
            f"Failed to update section: {response.status_code} {response.text}"
        )


def tr_delete_section(section_id):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/delete_section/{section_id}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers
    )
    if response.status_code == 200:
        logger.info(f"Successfully deleted section with ID {section_id}")
    else:
        raise Exception(
            f"Failed to delete section: {response.status_code} {response.text}"
        )


def tr_add_test_case(section_id, title, steps, custom_automation_type=1, preconditions=None, refs=None, priority_id=TESTRAIL_DEFAULT_TC_PRIORITY_ID, type_id=TESTRAIL_DEFAULT_TC_TYPE_ID, estimate=None, milestone_id=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_case/{section_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "custom_steps": steps,
        "custom_automation_type": custom_automation_type,
        "custom_preconds": preconditions,
        "refs": refs,
        "priority_id": priority_id,
        "type_id": type_id,
        "estimate": estimate,
        "milestone_id": milestone_id
    }

    response = requests.post(
        url, json=data, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers
    )
    if response.status_code == 200:
        logger.info(f"TC added: {title} | C{response.json()['id']}")
    else:
        raise Exception(
            f"Failed to add test case: {response.status_code} {response.text}"
        )


def tr_update_test_case(case_id, section_id, title, steps, custom_automation_type=1, preconditions=None, refs=None, priority_id=None, type_id=None, estimate=None, milestone_id=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/update_case/{case_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "title": title,
        "section_id": section_id,
        "custom_steps": steps,
        "custom_automation_type": custom_automation_type,
        "custom_preconds": preconditions,
        "refs": refs,
        "priority_id": priority_id,
        "type_id": type_id,
        "estimate": estimate,
        "milestone_id": milestone_id
    }

    logger.info(f"Updating test case: {title} | Case ID: {case_id}")
    response = requests.post(
        url, json=data, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers
    )
    if response.status_code == 200:
        logger.info(f"TC updated: {title} | Case ID: C{case_id}")
    else:
        logger.error(f"Failed to update test case: {title} | Case ID: C{case_id} | Status Code: {response.status_code} | Response: {response.text}")
        raise Exception(
            f"Failed to update test case: {response.status_code} {response.text}"
        )


# TR API - Run
def tr_add_run(project_id, suite_id, name, description=None, case_ids=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_run/{project_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "suite_id": suite_id,
        "name": name,
        "description": description,
        "case_ids": case_ids
    }
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data
    )
    if response.status_code == 200:
        run = response.json()
        logger.info(f"Run added: '{name}' with ID {run['id']}")
        return run
    else:
        raise Exception(
            f"Failed to add run: {response.status_code} {response.text}"
        )

def tr_update_run(run_id, name, description):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/update_run/{run_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "name": name,
        "description": description
    }
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data
    )
    if response.status_code == 200:
        run = response.json()
        logger.info(f"Run updated: '{name}' with ID {run['id']}")
        return run
    else:
        raise Exception(
            f"Failed to update run: {response.status_code} {response.text}"
        )

def tr_delete_run(run_id):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/delete_run/{run_id}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers
    )
    if response.status_code == 200:
        logger.info(f"Successfully deleted run with ID {run_id}")
    else:
        raise Exception(
            f"Failed to delete run: {response.status_code} {response.text}"
        )

def tr_get_runs(project_id, suite_id=None):
    endpoint = f"get_runs/{project_id}"
    if suite_id:
        endpoint += f"&suite_id={suite_id}"
    return tr_get_testrail_data(endpoint)

def tr_get_run(run_id):
    endpoint = f"get_run/{run_id}"
    return tr_get_testrail_data(endpoint)

def tr_get_results_for_run(run_id):
    endpoint = f"get_results_for_run/{run_id}"
    return tr_get_testrail_data(endpoint)


# TR API - Test Plan
def tr_get_test_plans(project_id):
    endpoint = f"get_plans/{project_id}"
    url = f"{TESTRAIL_URL}/index.php?/api/v2/{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    response = requests.get(url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get test plans: {response.status_code} {response.text}")
    
    plans = response.json()
    return plans

def tr_add_test_plan(project_id, name, description=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_plan/{project_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "name": name,
        "description": description
    }
    response = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data)
    if response.status_code == 200:
        plan = response.json()
        logger.info(f"Test Plan added: '{name}' with ID {plan['id']}")
        return plan
    else:
        raise Exception(f"Failed to add test plan: {response.status_code} {response.text}")

def tr_add_run_to_plan(plan_id, suite_id, name, description=None, case_ids=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_plan_entry/{plan_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "suite_id": suite_id,
        "name": name,
        "description": description,
        "case_ids": case_ids
    }
    response = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data)
    if response.status_code == 200:
        run = response.json()
        logger.info(f"Run added to Plan ID {plan_id}: '{name}' with ID {run['runs'][0]['id']}")
        return run['runs'][0]
    else:
        raise Exception(f"Failed to add run to plan: {response.status_code} {response.text}")

def tr_add_result_for_case(run_id, case_id, status_id, comment=None, version=None, elapsed=None, defects=None, assignedto_id=None):
    url = f"{TESTRAIL_URL}/index.php?/api/v2/add_result_for_case/{run_id}/{case_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "status_id": status_id,
        "comment": comment,
        "version": version,
        "elapsed": elapsed,
        "defects": defects,
        "assignedto_id": assignedto_id
    }
    response = requests.post(url, auth=(TESTRAIL_USER, TESTRAIL_API_KEY), headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Testrail TC status set: Case ID C{case_id}, Status ID {status_id}")
        return result
    else:
        raise Exception(f"Failed to update test run result: {response.status_code} {response.text}")

