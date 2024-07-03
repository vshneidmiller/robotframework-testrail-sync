import re
from collections import Counter
from robotestrail.logging_config import *
from robotestrail.testrail_api_manager import TestRailApiManager
from robotestrail.robot_framework_utils import run_dryrun_and_get_tests_with_additional_info, parse_robot_output_xml, add_additional_info_to_parsed_robot_tests
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from datetime import datetime

class TestSyncManager:
    def __init__(self, config):
        self.logger = setup_logging()
        self.config = config
        self.tr_api = TestRailApiManager(config)
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

    def _get_type_id(self, test):
        """
        Get the type ID for a test.

        Args:
            test (dict): The test object.

        Returns:
            int: The type ID of the test.
        """
        type_id = self.config.get_default_type_id()
        if test.get("type_id"):
            type_id = test["type_id"]
        return type_id
    
    def _get_priority_id(self, test):
        priority_id = self.config.get_default_priority_id()
        if test.get("priority_id"):
            priority_id = test["priority_id"]
        return priority_id

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

        with ThreadPoolExecutor(max_workers=self.config.get_max_workers()) as executor:
            executor.map(self._sync_test_with_one_tr_id, robot_tests["tests_with_one_tr_id"])

        with ThreadPoolExecutor(max_workers=self.config.get_max_workers()) as executor:
            executor.map(self._sync_test_with_multiple_tr_ids, robot_tests["tests_with_multiple_tr_ids"])


    def set_results_by_id(self):
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
        test_run = self.tr_api.add_run_to_plan(plan_id=test_plan['id'], 
                                               suite_id=suite['id'],
                                               name=test_run_name,
                                               description="test_description", 
                                               case_ids=all_case_ids)

        results = []
        for test in robot_tests['tests']:

            for tr_id in test['tr_ids']:
                case_id = str(tr_id)[1:]
                status_id = self._get_testrail_status_by_robot_status(test['test_status'])
                comment = test.get('message') or None
                elapsed = test.get('elapsed') or None
                version = test.get('version') or None
                defects = test.get('defects') or None
                assignedto_id = test.get('assignedto_id') or None
                results.append({"case_id": case_id, "status_id": status_id, "comment": comment, "elapsed": elapsed, "version": version, "defects": defects, "assignedto_id": assignedto_id})

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

    def show_milestones(self):
        project_id = self.tr_api.get_project_id()
        project_name = self.config.get_project_name()
        milestones = self.tr_api.get_milestones(project_id)
        if not milestones:
            print("No milestones found.")
        else:
            print(f'Milestones for the project "{project_name}":\n')
            for milestone in milestones["milestones"]:
                print(f"{milestone['name']} - {milestone['id']}")

    def add_test_to_testrail(self, robot_test):
        self.logger.info(f"Adding new test to TestRail with ID {robot_test['id']}")
        # Logic to add new test to TestRail
        pass

    def _sync_tests_with_one_tr_id(self, tests):
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
            milestone_id=test["milestone_id"],
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
            