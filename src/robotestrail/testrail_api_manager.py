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
            if project['name'] == self.config.get_project_name():
                return project['id']
        return None
    
    def get_case_fields(self):
        url = f"{self.base_url}/index.php?/api/v2/get_case_fields"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_case_types(self):
        url = f"{self.base_url}/index.php?/api/v2/get_case_types"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_priorities(self):
        url = f"{self.base_url}/index.php?/api/v2/get_priorities"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_statuses(self):
        url = f"{self.base_url}/index.php?/api/v2/get_statuses"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_result_fields(self):
        url = f"{self.base_url}/index.php?/api/v2/get_result_fields"
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
    
    def get_projects(self):
        url = f"{self.base_url}/index.php?/api/v2/get_projects"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()

    def update_test_case(self, case_id, title=None, steps=None, custom_automation_type=None, custom_customer=None, custom_automatedby=None, section_id=None, preconditions=None, refs=None, priority_id=None, type_id=None, estimate=None, milestone_id=None):
        url = f"{self.base_url}/index.php?/api/v2/update_case/{case_id}"
        headers = {"Content-Type": "application/json"}
        
        data = {
            "title": title,
            "section_id": section_id,
            "custom_steps": steps,
            "custom_automation_type": custom_automation_type,
            "custom_customer": custom_customer,
            "custom_automatedby": custom_automatedby,
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

        self.logger.debug(f"Updating test case: {title} | Case ID: {case_id}")
        response = requests.post(
            url, json=payload, auth=(self.user, self.api_key), headers=headers
        )
        if response.status_code == 200:
            self.logger.info(f"TC updated: {title} | Case ID: C{case_id}")
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
    
    def add_run_to_plan(self, plan_id, suite_id, name, description=None, case_ids=None, milestone_id=None, assignedto_id=None, include_all=False, refs=None):
        url = f"{self.base_url}/index.php?/api/v2/add_plan_entry/{plan_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "suite_id": suite_id,
            "name": name,
            "description": description,
            "include_all": include_all,
            "case_ids": case_ids,
            "milestone_id": milestone_id,
            "assignedto_id": assignedto_id,
            "refs": refs
        }
        self.logger.info(f"Request Data: {data}")
        response = requests.post(url, auth=(self.user, self.api_key), headers=headers, json=data)
        #response.raise_for_status()
        if response.status_code == 200:
            self.logger.info(response.json())
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
            self.logger.info(f"Results added to test run: {run_id}")
            self.logger.debug(f"Response: {response.json()}")
        else:
            self.logger.error(f"Failed to add results to test run: {run_id} | Status Code: {response.status_code} | Response: {response.text}")
            raise Exception(
                f"Failed to add results to test run: {response.status_code} {response.text}"
            )
        
    def get_user_by_email(self, email):
        url = f"{self.base_url}/index.php?/api/v2/get_user_by_email&email={email}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_current_user(self):
        url = f"{self.base_url}/index.php?/api/v2/get_current_user/"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_cases(self, project_id, suite_id):
        url = f"{self.base_url}/index.php?/api/v2/get_cases/{project_id}&suite_id={suite_id}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
    
    def get_section_by_name(self, project_id, suite_id, name):
        sections = self.get_sections(project_id, suite_id)["sections"]
        for section in sections:
            if section["name"] == name:
                return section
        return None
    
    def get_sections(self, project_id, suite_id):
        url = f"{self.base_url}/index.php?/api/v2/get_sections/{project_id}&suite_id={suite_id}"
        response = requests.get(url, auth=(self.user, self.api_key))
        response.raise_for_status()
        self.logger.debug(response.json())
        return response.json()
        
    def add_section(self, project_id, suite_id, section_name, parent_id=None, description=None):
        url = f"{self.base_url}/index.php?/api/v2/add_section/{project_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "suite_id": suite_id,
            "name": section_name,
            "description": description,  # Optional: Add a description to the section
            "parent_id": parent_id,  # Optional: If adding a subsection, specify the parent section ID
        }
        response = requests.post(
            url, auth=(self.user, self.api_key), headers=headers, json=data
        )
        if response.status_code == 200:
            section = response.json()
            self.logger.info(f"Section added: '{section_name}' with ID {section['id']}")
            return section
        else:
            raise Exception(
                f"Failed to add section: {response.status_code} {response.text}"
            )
        
    def get_section_by_name_and_parent_id(self, project_id, suite_id, name, parent_id):
        sections = self.get_sections(project_id, suite_id)["sections"]
        for section in sections:
            if section["name"] == name and section["parent_id"] == parent_id:
                return section
        return None
    

    def update_section(self, section_id, section_name, description=None):
        url = f"{self.base_url}/index.php?/api/v2/update_section/{section_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "name": section_name,
            "description": description,
        }
        response = requests.post(
            url, auth=(self.user, self.api_key), headers=headers, json=data
        )
        if response.status_code == 200:
            section = response.json()
            self.logger.info(f"Section updated: '{section_name}' | S{section['id']} | {section['description']}")
            return section
        else:
            raise Exception(
                f"Failed to update section: {response.status_code} {response.text}"
            )
        
    def get_sections_with_formatted_path(self, project_id, suite_id):
        sections = self.get_sections(project_id, suite_id)["sections"]
        for section in sections:
            if section["parent_id"] is None:
                section["formatted_path"] = section["name"]
            else:
                parent_formatted_path = next(
                    (
                        s["formatted_path"]
                        for s in sections
                        if s["id"] == section["parent_id"]
                    ),
                    None,
                )
                section["formatted_path"] = f"{parent_formatted_path} > {section['name']}"
        return sections
    
    def add_test_case(self, section_id, title, steps, custom_automation_type, refs=None, priority_id=None, type_id=None, estimate=None, milestone_id=None, preconditions=None):
        url = f"{self.base_url}/index.php?/api/v2/add_case/{section_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "title": title,
            "custom_automation_type": custom_automation_type,
            "custom_steps": steps,
            "refs": refs,
            "priority_id": priority_id,
            "type_id": type_id,
            "estimate": estimate,
            "milestone_id": milestone_id,
            "custom_preconds": preconditions
        }
        response = requests.post(url, auth=(self.user, self.api_key), headers=headers, json=data)
        if response.status_code == 200:
            case = response.json()
            self.logger.info(f"Test case added: '{title}' | C{case['id']}")
            return case
        else:
            raise Exception(
                f"Failed to add test case: {response.status_code} {response.text}"
            )
        
    def delete_section(self, section_id):
        url = f"{self.base_url}/index.php?/api/v2/delete_section/{section_id}"
        response = requests.post(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            self.logger.info(f"Section deleted: S{section_id}")
        else:
            raise Exception(
                f"Failed to delete section: {response.status_code} {response.text}"
            )
    
    def move_cases_to_section(self, suite_id, section_id, case_ids):
        url = f"{self.base_url}/index.php?/api/v2/move_cases_to_section/{section_id}"
        headers = {"Content-Type": "application/json"}
        data = {
            "suite_id": suite_id,
            "case_ids": case_ids
        }
        response = requests.post(
            url, auth=(self.user, self.api_key), headers=headers, json=data
        )
        if response.status_code == 200:
            self.logger.info(f"Tests moved to ORPHAN: {case_ids}")
        else:
            raise Exception(
                f"Failed to move tests: {response.status_code} {response.text}"
            )
        