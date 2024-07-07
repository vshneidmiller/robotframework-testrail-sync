import re
from collections import Counter
from robotestrail.logging_config import *
from robotestrail.testrail_api_manager import TestRailApiManager
from robotestrail.robot_framework_utils import run_dryrun_and_get_tests_with_additional_info, parse_robot_output_xml, add_additional_info_to_parsed_robot_tests
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from datetime import datetime
import json

class TestSyncManager:
    def __init__(self, config):
        self.logger = setup_logging()
        self.config = config
        self.tr_api = TestRailApiManager(config)
        self.case_types = self.tr_api.get_case_types()
        self.case_fields = self.tr_api.get_case_fields()
        self.max_workers = self.config.get_max_workers()
        self.priorities = self.tr_api.get_priorities()


        self.logger.debug("TestSyncManager initialized")

    def _log_tests_without_tr_id(self, tests):
        """
        Logs the tests that do not have a TestRail ID.

        Args:
            tests (list): A list of tests without TestRail ID.

        Returns:
            None
        """
        if tests:
            message = "The robot tests without TestRail ID will not be synced to the TestRail.\nThe following robot tests have no TestRail ID:"
            for test in tests:
                message += f"\n - {test['title']} - {test['formatted_path']}"
            self.logger.warning(message)
        else:
            self.logger.info("All robot tests have TestRail IDs.")
    
    def _log_tests_with_multiple_tr_ids(self, tests):
        """
        Logs the tests that have multiple TestRail IDs.

        Args:
            tests (list): A list of tests with multiple TestRail IDs.

        Returns:
            None
        """
        if tests:
            message = "Robot tests with more than one TestRail IDs will not be synced with the TestRail (only automation type will be updated to the default automation type from the config)\nThe following tests have multiple TestRail IDs:"
            for test in tests:
                message += f"\n - {test['title']} - {test['formatted_path']}"
            self.logger.info(message)

    def _log_tests_with_duplicate_tr_ids(self, all_tr_ids):
        """
        Logs all duplicate transaction IDs from the provided list.
        
        :param all_tr_ids: List of all transaction IDs.
        """
        # Count occurrences of each tr_id
        tr_id_counts = Counter(all_tr_ids)
        
        # Find duplicates (tr_ids with more than one occurrence)
        duplicates = [tr_id for tr_id, count in tr_id_counts.items() if count > 1]
        
        if duplicates:
            message = "The following TestRail IDs are present several times\n"
            for tr_id in duplicates:
                message += (f" - TestRail ID: {tr_id} - Count: {tr_id_counts[tr_id]}\n")
            self.logger.warning(message)
        else:
            self.logger.info("No duplicate TestRail IDs found.")

    def _get_custom_automation_type(self, test):
        if test.get("custom_automation_type"):
            custom_automation_type_id = self._get_custom_automation_type_id_by_name(test["custom_automation_type"])

        if test.get("custom_automation_type_id"):
            custom_automation_type_id = test["custom_automation_type_id"]
        return custom_automation_type_id

    def _get_type_id(self, test):
        """
        Get the type ID for a test case.

        Args:
            test (dict): The test case.

        Returns:
            int or None: The type ID of the test case, or None if not found.
        """
        if test.get("type_id"):
            return test["type_id"]

        if test.get("type"):
            return self._get_case_type_id_by_name(test["type"])

        if self.config.get_default_type_id():
            return self.config.get_default_type_id()
        
        if self.config.get_default_type():
            return self._get_case_type_id_by_name(self.config.get_default_type())

        return None
        
    
    def _get_priority_id(self, test):
        if test.get("priority_id"):
            return test["priority_id"]
        
        if test.get("priority"):
            return self._get_priority_id_by_name(test["priority"])

        if self.config.get_default_priority_id():
            return self.config.get_default_priority_id()
        
        if self.config.get_default_priority():
            return self._get_priority_id_by_name(self.config.get_default_priority())
        
        return None

    def _get_custom_automation_type(self, test):
        custom_automation_type = self.config.get_default_custom_automation_type()
        if test.get("custom_automation_type"):
            custom_automation_type = test["custom_automation_type"]
        return custom_automation_type


    def sync_tests_by_id(self):
        self.logger.info("Starting test sync process")
        self.logger.info(f"Project ID: {self.tr_api.get_project_id()}")

        # Get all robot tests by running robot dry-run and parsing the output.xml
        path_to_tests = self.config.get_robot_tests_folder_path()
        robot_tests = run_dryrun_and_get_tests_with_additional_info(path_to_tests, 'dry_run_output.xml')
        
        self._log_tests_without_tr_id(robot_tests["tests_without_tr_id"])
        self._log_tests_with_multiple_tr_ids(robot_tests["tests_with_multiple_tr_ids"])
        self._log_tests_with_duplicate_tr_ids(robot_tests["all_tr_ids"])


        if self.max_workers:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.logger.info(f"Syncing tests with one TestRail ID\nThe following number of tests with single TestRail ID will be synced: {len(robot_tests['tests_with_one_tr_id'])}")
                executor.map(self._sync_test_with_one_tr_id, robot_tests["tests_with_one_tr_id"])
        else:
            self._sync_tests_with_one_tr_id(robot_tests["tests_with_one_tr_id"])

        if self.max_workers:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.logger.info(f"Syncing tests with multiple TestRail IDs\nThe following number of tests with multiple TestRail IDs will be synced: {len(robot_tests['tests_with_multiple_tr_ids'])}")
                executor.map(self._sync_test_with_multiple_tr_ids, robot_tests["tests_with_multiple_tr_ids"])
        else:
            self._sync_tests_with_multiple_tr_ids(robot_tests["tests_with_multiple_tr_ids"])


    def set_results_by_id(self):
        resp = self.tr_api.get_case_fields()
        self.logger.info("Starting sety tests rusults by id process")
        project_id = self.tr_api.get_project_id()
        self.logger.info(f"Project ID: {project_id}")
        path_to_tests = self.config.get_robot_tests_folder_path()
        
        dry_run_tests = run_dryrun_and_get_tests_with_additional_info(path_to_tests, "dry_run_output.xml")
        all_case_ids = [t[1:] for t in dry_run_tests['all_tr_ids']] 
        output_file_path= self.config.get_robot_output_xml_file_path()
        robot_tests = parse_robot_output_xml(output_file_path)
        robot_tests = add_additional_info_to_parsed_robot_tests(robot_tests)
        test_plan = self.tr_api.get_tr_test_plan_by_name(project_id, self.config.get_test_plan_name())

        #add test run to test plan
        suite = self.tr_api.get_tr_suite_by_name(project_id, self.config.get_test_suite())
        test_run_name = f"{self.config.get_test_run_name()} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        assignedto_id = None
        if self.config.get_test_run_assignedto_email():
            user = self.tr_api.get_user_by_email(self.config.get_test_run_assignedto_email())
            assignedto_id = user['id']

        try:
            test_run = self.tr_api.add_run_to_plan(plan_id=test_plan['id'],
                                                   suite_id=suite['id'],
                                                   name=test_run_name,
                                                   #milestone_id=386,    #self.config.get_test_run_milestone_id(),
                                                   #refs='TC-1',    #self.config.get_test_run_refs(),
                                                   description=self.config.get_test_run_description(),
                                                   assignedto_id=assignedto_id,
                                                   include_all=False,
                                                   case_ids=all_case_ids)
        except Exception as e:
            self.logger.error(f"Project '{self.config.get_project_name()}' does not have test plan with name '{self.config.get_test_plan_name()}'\nError adding test run to test plan: {e}")
            return

        results = []
        self.logger.info(f"Adding results to test run '{test_run_name}'")

        for test in robot_tests['tests']:

            for tr_id in test['tr_ids']:
                formatted_elapsed = f"{str(round(test.get('elapsedtime', 0)/1000))}s"
                if formatted_elapsed == '0s':
                    formatted_elapsed = 0
                #milestone_id = self.config.get_test_run_milestone_id()
                
                case_id = str(tr_id)[1:]
                status_id = self._get_testrail_status_by_robot_status(test['test_status'])
                comment = test.get('status_message') or None
                elapsed = formatted_elapsed or None
                version = test.get('version') or None
                defects = test.get('defects') or None
                assignedto_id = assignedto_id or None
                #milestone_id = milestone_id
                results.append({"case_id": case_id, "status_id": status_id, "comment": comment, "elapsed": elapsed, "version": version, "defects": defects})

        self.tr_api.add_results_for_cases(test_run['runs'][0]['id'], {"results": results})
                


    def _get_testrail_status_by_robot_status(self, robot_status):
        """
        Get the TestRail status ID based on the Robot Framework status.

        Args:
            robot_status (str): The Robot Framework status.

        Returns:
            int: The TestRail status ID.
        """
        status_map = {
            "PASS": 1,
            "NOT RUN": 3,
            "SKIP": 4,
            "FAIL": 5,
        }
        return status_map.get(robot_status, 0)

    def show_info(self):
        project_id = self.tr_api.get_project_id()
        project_name = self.config.get_project_name()

        #projects
        projects = self.tr_api.get_projects()
        print(f"\nPROJECTS:\n{projects}\n")

        #milestones
        milestones = self.tr_api.get_milestones(project_id)
        print(f'MILESTONES FOR PROJECT "{project_name}":\n{milestones}\n')

        #current user
        current_user = self.tr_api.get_current_user()
        print(f"CURRENT USER INFO:\n{current_user}\n")

        #case fields
        case_fields = self.tr_api.get_case_fields()
        print(f"CASE FIELDS:\n{case_fields}\n")

        #case types
        case_types = self.tr_api.get_case_types()
        print(f"CASE TYPES:\n{case_types}\n")

        #priorities
        priorities = self.tr_api.get_priorities()
        print(f"PRIORITIES:\n{priorities}\n")

        #statuses
        statuses = self.tr_api.get_statuses()
        print(f"STATUSES:\n{statuses}\n")

        #result fields
        result_fields = self.tr_api.get_result_fields()
        print(f"RESULT FIELDS:\n{result_fields}\n")

        json_with_results = {
            "projects": projects,
            "milestones": milestones,
            "current_user": current_user,
            "case_fields": case_fields,
            "case_types": case_types,
            "priorities": priorities,
            "statuses": statuses,
            "result_fields": result_fields
        }

        #dump to file
        with open('testrail_info.json', 'w') as json_file:
            json.dump(json_with_results, json_file, indent=4)
        

    def add_test_to_testrail(self, robot_test):
        self.logger.info(f"Adding new test to TestRail with ID {robot_test['id']}")
        # Logic to add new test to TestRail
        pass

    def _sync_tests_with_one_tr_id(self, tests):
        self.logger.info(f"Syncing tests with one TestRail ID\n The following number of tests will be synced: {len(tests)}")
        for test in tests:
            self._sync_test_with_one_tr_id(test)

    def _sync_test_with_one_tr_id(self, test):
        tr_case_id = str(test["tr_ids"][0])[1:]
        
        self.tr_api.update_test_case(
            case_id=tr_case_id,
            title=test["title"],
            steps=test["rich_text_steps"],
            preconditions=test["formatted_tags"],
            estimate=test["estimate"],
            refs=test["refs"],
            custom_customer=test.get("custom_customer"),
            custom_automation_type=self._get_custom_automation_type(test),
            custom_automatedby=self._get_automatedby_id(test),
            milestone_id=test.get("milestone_id"),
            type_id=self._get_type_id(test),
            priority_id=self._get_priority_id(test),
        )
        
    def _sync_tests_with_multiple_tr_ids(self, tests):
        if tests:
            self.logger.info("Syncing tests with multiple TestRail IDs")
            for test in tests:
                self._sync_test_with_multiple_tr_ids(test)

    def _sync_test_with_multiple_tr_ids(self, test):
        for tr_id in test["tr_ids"]:
            tr_case_id = str(tr_id)[1:]
            self.tr_api.update_test_case(
                case_id=tr_case_id,
                custom_automation_type=self._get_custom_automation_type(test),
                type_id=self._get_type_id(test),
                priority_id=self._get_priority_id(test)
            )
            
    def _get_case_type_id_by_name(self, case_type_name):
        for case_type in self.case_types:
            if case_type["name"] == case_type_name:
                return case_type["id"]
        return None
    
    def _get_custom_automation_type(self, test):
        if test.get("custom_automation_type"):
            return self._get_custom_automation_type_id_by_name(test["custom_automation_type"])

        if test.get("custom_automation_type_id"):
            return test["custom_automation_type_id"]
        
        if self.config.get_default_custom_automation_type_id():
            return self.config.get_default_custom_automation_type_id()
        
        if self.config.get_default_custom_automation_type():
            return self._get_custom_automation_type_id_by_name(self.config.get_default_custom_automation_type())

        return None
    
    def _get_automatedby_id(self, test):
        if test.get("custom_automatedby_id"):
            return test["custom_automatedby_id"]
        
        if test.get("custom_automatedby"):
            email = test["custom_automatedby"]
            user = self.tr_api.get_user_by_email(email)
            return user['id']
        
        if self.config.get_default_automatedby_id():
            return self.config.get_default_automatedby_id()
        
        if self.config.get_default_automatedby():
            email = self.config.get_default_automatedby()
            user = self.tr_api.get_user_by_email(email)
            return user['id']
        
        return None
        
    
    def _get_custom_automation_type_id_by_name(self, custom_automation_type_name):
        custom_field = "custom_automation_type"
        result = self._get_custom_field_id_by_name_from_tr(custom_field, custom_automation_type_name, self.case_fields)
        return result
    
    def _get_priority_id_by_name(self, priority_name):
        for priority in self.priorities:
            if priority["name"] == priority_name:
                return priority["id"]
        return None

    def _get_custom_field_id_by_name_from_tr(self, custom_field, custom_field_name, case_fields):
        for case_field in case_fields:
            if case_field['system_name'] == custom_field:
                custom_fields_list = (case_field['configs'][0]['options']['items']).split('\n')
                
                custom_fields_dict_list = []
                for field in custom_fields_list:
                    key_value_list = field.split(', ')
                    custom_fields_dict_list.append({"id": key_value_list[0], "name": key_value_list[1]})
                break

        for field in custom_fields_dict_list:
            if field["name"] == custom_field_name:
                return field["id"]
        return None
    