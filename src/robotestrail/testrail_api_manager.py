import os
import requests
from robotestrail.logging_config import setup_logging


class TestRailApiManager:
    def __init__(self, config):
        self.logger =  setup_logging()
        self.config = config
        self.base_url = self.config.get_config()['testrail']['url']
        self.user = self.config.get_config()['testrail']['user']
        self.api_key = os.getenv(self.config.get_config()['testrail']['api_key_env_var'])
        self.logger.debug("TestRailApiManager initialized")

    def get_project_id(self):
        url = f"{self.base_url}/index.php?/api/v2/get_projects"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        projects = response.json()['projects']
        for project in projects:
            if project['name'] == self.config.get_config()['project']['name']:
                return project['id']
        return None
    
    def get_case_fields(self):
        url = f"{self.base_url}/index.php?/api/v2/get_case_fields"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_milestones(self, project_id):
        url = f"{self.base_url}/index.php?/api/v2/get_milestones/{project_id}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()

    def update_test_case(self, case_id, title=None, steps=None, custom_automation_type=None, section_id=None, preconditions=None, refs=None, priority_id=None, type_id=None, estimate=None, milestone_id=None):
        url = f"{self.base_url}/index.php?/api/v2/update_case/{case_id}"
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

        payload = {}
        for key, value in data.items():
            if value:
                payload[key] = value

        self.logger.info(f"Updating test case: {title} | Case ID: {case_id}")
        response = requests.post(
            url, json=payload, auth=(self.user, self.api_key), headers=headers
        )
        if response.status_code == 200:
            self.logger.debug(f"TC updated: {title} | Case ID: C{case_id}")
        else:
            self.logger.error(f"Failed to update test case: {title} | Case ID: C{case_id} | Status Code: {response.status_code} | Response: {response.text}")
            raise Exception(
                f"Failed to update test case: {response.status_code} {response.text}"
            )

    def get_test_plans(self, project_id):
        url = f"{self.base_url}/index.php?/api/v2/get_plans/{project_id}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()


    def get_tr_test_plan_by_name(self, project_id, name):
        test_plans = self.get_test_plans(project_id)["plans"]
        for test_plan in test_plans:
            if test_plan["name"] == name:
                return test_plan
        return None
    
    def get_tr_suite_by_name(self, project_id, suite_name):
        url = f"{self.base_url}/index.php?/api/v2/get_suites/{project_id}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        suites = response.json()
        for suite in suites:
            if suite['name'] == suite_name:
                return suite
        return None
    
    def add_run_to_plan(self, plan_id, suite_id, name, description=None, case_ids=None):
        url = f"{self.base_url}/index.php?/api/v2/add_plan_entry/{plan_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "suite_id": suite_id,
            "name": name,
            "description": description,
            "include_all": False,
            "case_ids": case_ids
        }
        self.logger.debug(f"Request Data: {data}")
        response = requests.post(url, auth=(self.user, self.api_key), headers=headers, json=data)
        #response.raise_for_status()
        if response.status_code == 200:
            self.logger.debug(f"Test run added to test plan: {name}")
            return response.json()
        else:
            self.logger.error(f"Failed to add test run to test plan: {name} | Status Code: {response.status_code} | Response: {response.text}")
            raise Exception(
                f"Failed to add test run to test plan: {response.status_code} {response.text}"
            )   
        
    def add_results_for_cases(self, run_id, payload):
        url = f"{self.base_url}/index.php?/api/v2/add_results_for_cases/{run_id}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, auth=(self.user, self.api_key), headers=headers, json=payload)
        if response.status_code == 200:
            self.logger.debug(f"Results added to test run: {run_id}")
        else:
            self.logger.error(f"Failed to add results to test run: {run_id} | Status Code: {response.status_code} | Response: {response.text}")
            raise Exception(
                f"Failed to add results to test run: {response.status_code} {response.text}"
            )