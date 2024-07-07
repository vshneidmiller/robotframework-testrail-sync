import os
import csv
from collections import Counter
from robotestrail.logging_config import *
from robotestrail.testrail_api_manager import TestRailApiManager
from robotestrail.robot_framework_utils import run_dryrun_and_get_tests_with_additional_info, parse_robot_output_xml, add_additional_info_to_parsed_robot_tests
from concurrent.futures import ThreadPoolExecutor
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

    def add_new_test_results_by_name(self):
        self.logger.info("Adding new test results to TestRail by name")
        project_id = self.tr_api.get_project_id()
        suite_id = self.tr_api.get_tr_suite_by_name(project_id, self.config.get_test_suite())['id']
        test_plan = self.tr_api.get_tr_test_plan_by_name(project_id, self.config.get_test_plan_name())
        test_run_name = f"{self.config.get_test_run_name()} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        test_run = self.tr_api.add_run_to_plan(plan_id=test_plan['id'],
                                               suite_id=suite_id,
                                               name=test_run_name,
                                               description=self.config.get_test_run_description(),
                                               include_all=True)

        # Set testrail test run results based on the robot output.xml file
        self.set_test_results(project_id, suite_id, test_run['runs'][0]['id'], self.config.get_robot_output_xml_file_path())




    def sync_robot_test_by_name(self):
        self.logger.info("Syncing robot tests with the TestRail by name")
        path_to_tests = self.config.get_robot_tests_folder_path()
        root_section_name = self.config.get_root_test_section_name()
        project_id = self.tr_api.get_project_id()
        suite_id = self.tr_api.get_tr_suite_by_name(project_id, self.config.get_test_suite())['id']
        existing_tr_tests = self.tr_api.get_cases(project_id, suite_id)['cases']
        root_section = self.tr_api.get_section_by_name(project_id, suite_id, root_section_name)
        if not root_section:
            self.tr_api.add_section(project_id, suite_id, root_section_name)
        robot_tests = run_dryrun_and_get_tests_with_additional_info(path_to_tests, 'dry_run_output.xml')
        self.add_folders_to_testrail(project_id, suite_id, robot_tests, self.config.get_source_control_link())
        self.add_tests_to_testrail(project_id, suite_id, existing_tr_tests, robot_tests)
        self.update_tests_in_testrail(project_id, suite_id, existing_tr_tests, robot_tests)
        self.move_orphan_tests_to_orphan_folder(project_id, suite_id, robot_tests)

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

    
    def generate_csv(self):
        self.logger.info("Generating CSV file with test cases")
        path_to_tests = self.config.get_robot_tests_folder_path()
        robot_tests = run_dryrun_and_get_tests_with_additional_info(path_to_tests, 'dry_run_output.xml')
        self.create_csv_file_for_tests(robot_tests['tests'])


    def check(self):
        self.logger.info("Checking the configuration, Robot Framework tests, and the TestRail connection")
        pass

#def check():
#    errors = []
#    warnings = []
#
#    def check_required_config_field(field_name, field, error, description):
#        if not field:
#            errors.append(
#                {
#                    "error": f"Required field is missing: {field}",
#                    "description": description,
#                }
#            )
#
#    print(
#        "Checking the config file, Robot Framework tests, and the TestRail connection... \n"
#    )
#    # check_required_config_field(TESTRAIL_URL, "TESTRAIL_URL", "TestRail URL is missing", "URL to the TestRail instance")
#
#    if TESTRAIL_URL == "not_set":
#        errors.append(
#            {
#                "error": "Required config field is missing: TESTRAIL_URL",
#                "description": "It should be something like: https://your-organization.testrail.com",
#            }
#        )
#
#    if TESTRAIL_USER == "not_set":
#        errors.append(
#            {
#                "error": "Required config field is missing: TESTRAIL_USER",
#                "description": "TestRail user name. Usually it's an email address. You can find it in your TestRail profile: Username > My Settings > Email Address. https://your-organization.testrail.com/index.php?/mysettings",
#            }
#        )
#
#    if TESTRAIL_API_KEY == "not_set" or TESTRAIL_API_KEY ==None:
#        errors.append(
#            {
#                "error": "Required config field is missing: TESTRAIL_API_KEY",
#                "description": "TestRail API key. You can create it in your TestRail profile: Username > My Settings > API Keys. https://your-organization.testrail.com/index.php?/mysettings . Then you have to export it as an environment variable. For example: export TESTRAIL_API_KEY=your_api_key (for Linux and MacOS). DON'T ADD THE API KEY DIRECTLY TO THE CONFIG FILE! Config file should contain only the name of the environment variable.",
#            }
#        )
#    
#    if PROJECT_NAME == "not_set":
#        errors.append(
#            {
#                "error": "Required config field is missing: PROJECT_NAME",
#                "description": "Name of the project in TestRail. The projects are listed on the main TestRail page: https://your-organization.testrail.com/",
#            }
#        )
#    
#    if TEST_SUITE_NAME == "not_set":
#        errors.append(
#            {
#                "error": "Required config field is missing: TEST_SUITE_NAME",
#                "description": "Name of the test suite in TestRail. The test suites are listed in the project",
#            }
#        )
#    
#    if MAX_WORKERS == -1:
#        errors.append(
#            {
#                "error": "Required config field is missing: MAX_WORKERS",
#                "description": "It is the number of max concurrent requests to the TestRail. It should be a positive integer. If you are not sure, set it to 1 or check with your TestRail admin.",
#            }
#        )
#
#    if ROOT_TEST_SECTION_NAME == "not_set":
#        errors.append(
#            {
#                "error": "Required config field is missing: ROOT_TEST_SECTION_NAME",
#                "description": "Name of the root test section in TestRail. It is the parent of all the test cases.",
#            }
#        )
#
#    
#
##    # required_fields = [TESTRAIL_URL, TESTRAIL_USER, TESTRAIL_API_KEY, PROJECT_NAME, TEST_SUITE_NAME, MAX_WORKERS, ROOT_TEST_SECTION_NAME, ROOT_TEST_SECTION_DISCLAIMER, ORPHAN_TEST_SECTION_NAME, ORPHAN_TEST_SECTION_DESCRIPTION, TEST_PLAN_NAME, TEST_PLAN_DESCRIPTION, TEST_RUN_NAME, TEST_RUN_DESCRIPTION, PATH_TO_ROBOT_TESTS_FOLDER, ROBOT_TEST_OUTPUT_XML_FILE_PATH, SOURCE_CONTROL_NAME, SOURCE_CONTROL_LINK, TESTRAIL_DEFAULT_TC_PRIORITY_ID, TESTRAIL_DEFAULT_TC_TYPE_ID]
##



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
    
    def add_folders_to_testrail(self, project_id, suite_id, robot_tests, source_control_link_root):
        # Function to add all intermediate paths
        def add_intermediate_paths(path, all_paths):
            parts = path.split(" > ")
            for i in range(1, len(parts)):
                intermediate_path = " > ".join(parts[:i])
                if intermediate_path not in all_paths:
                    all_paths.append(intermediate_path)

        def get_github_link_to_folder_file(formatted_path, formatted_pathes):
            count = str(formatted_pathes).count(formatted_path)
            if count > 1:
                source_control_link = (
                    f"{source_control_link_root}/{str(formatted_path).replace(' > ', os.sep)}"
                )
            else:
                source_control_link = f"{source_control_link_root}/{str(formatted_path).replace(' > ', os.sep)}.robot"
            return source_control_link

        def get_parent_id_by_formatted_path(formatted_path):
            sections = self.tr_api.get_sections(project_id, suite_id)["sections"]
            local_path_list = formatted_path.split(" > ")
            parent_id = None
            for local_path in local_path_list:
                matching_sections = [
                    s
                    for s in sections
                    if s["name"] == local_path
                    and (s["parent_id"] == parent_id or parent_id is None)
                ]
                if not matching_sections:
                    return None
                parent_id = matching_sections[0]["id"]
            return parent_id

        def create_sections(sections):
            source_control_name = self.config.get_source_control_name()
            for missing_path in sections:
                parent_id = get_parent_id_by_formatted_path(
                    missing_path.rsplit(" > ", 1)[0]
                )
                source_control_link = get_github_link_to_folder_file(
                    missing_path, sorted_formatted_local_pathes
                )
                description = (
                    f"Link to the {source_control_name}:\n{source_control_link}"
                )
                section_name = missing_path.split(">")[-1].strip()
                self.tr_api.add_section(project_id, suite_id, section_name, parent_id, description)


        def create_missing_sections():
            missing_sections_pathes = []
            for path in sorted_formatted_local_pathes:
                if path not in [
                    s["formatted_path"] for s in existing_sections_with_formatted_path
                ]:
                    missing_sections_pathes.append(path)
            self.logger.info("Missing sections:\n%s", missing_sections_pathes)

            levels = [[] for _ in range(6)]
            for path in missing_sections_pathes:
                levels[min(path.count(" > "), 5)].append(path)

            for i, level in enumerate(levels):
                if level:
                    self.logger.info(f"Creating sections for level {i}:\n{level}")
                    create_sections(level)

        def update_existing_sections():
            source_control_name = self.config.get_source_control_name()
            root_test_section_name = self.config.get_root_test_section_name()
            def update_section(existing_section_path):
                try:
                    parent_id = get_parent_id_by_formatted_path(
                        existing_section_path.rsplit(" > ", 1)[0]
                    )
                    source_control_link = get_github_link_to_folder_file(
                        existing_section_path, sorted_formatted_local_pathes
                    )
                    description = (
                        f"Link to the {source_control_name}:\n{source_control_link}"
                    )
                    section_name = existing_section_path.split(">")[-1].strip()
                    if existing_section_path == root_test_section_name:
                        root_description = (
                            f"{root_test_section_name}\n\n{description}"
                        )
                        section = self.tr_api.get_section_by_name(
                            project_id, suite_id, root_test_section_name
                        )
                        self.logger.info(
                            f"Updating root section: {section_name} with description: {root_description}"
                        )
                        self.tr_api.update_section(
                            section["id"], section_name, description=root_description
                        )
                    else:
                        section = self.tr_api.get_section_by_name_and_parent_id(
                            project_id, suite_id, section_name, parent_id
                        )
                        self.logger.info(
                            f"Updating section: {section_name} with description: {description}"
                        )
                        self.tr_api.update_section(
                            section["id"], section_name, description=description
                        )
                except Exception as e:
                    self.logger.error(f"Error updating section '{existing_section_path}': {e}")
                    raise

            existing_section_pathes = []
            for path in sorted_formatted_local_pathes:
                if path in [
                    s["formatted_path"] for s in existing_sections_with_formatted_path
                ]:
                    existing_section_pathes.append(path)
            self.logger.info("Existing sections:\n%s", existing_section_pathes)

            for path in existing_section_pathes:
                update_section(path)

        #write robot tests to file:
        #with open('robot_tests.json', 'w') as json_file:
        #    json.dump(robot_tests, json_file, indent=4)
        
        formatted_pathes = [test["formatted_path"] for test in robot_tests['tests']]
        # Process each path and add intermediate paths
        for path in formatted_pathes:
            add_intermediate_paths(path, formatted_pathes)

        # Remove duplicates and sort by length
        sorted_formatted_local_pathes = sorted(list(set(formatted_pathes)), key=len)
        existing_sections_with_formatted_path = self.tr_api.get_sections_with_formatted_path(
            project_id, suite_id
        )

        create_missing_sections()
        update_existing_sections()

    def add_tests_to_testrail(self, project_id, suite_id, existing_tr_tests, robot_tests):


        # If the test with the particular name exists locally but NOT in the TestRail, then it will be added to the tests_to_add list
        
        tests_to_add = []
        for test in robot_tests['tests']:
            if test["title"] not in [t["title"] for t in existing_tr_tests]:
                tests_to_add.append(test)

        tr_sections = self.get_sections_with_formatted_path(project_id, suite_id)

        def add_test(test):
            section_id = next(
                (
                    s["id"]
                    for s in tr_sections
                    if s["formatted_path"] == test["formatted_path"]
                ),
                None,
            )
            preconditions = f'**[Tags]**\n{str(test["tags"])}'

            self.tr_api.add_test_case(
                section_id = section_id,
                title = test["title"],
                steps=test["rich_text_steps"],
                refs=test["refs"],
                priority_id=self._get_priority_id(test),
                custom_automation_type=self._get_custom_automation_type(test),
                type_id=self._get_type_id(test),
                estimate=test['estimate'],
                milestone_id=test['milestone_id'],
                preconditions=preconditions,
            )
            self.logger.info(f"Test added: {test['title']}")


        #with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        #    executor.map(add_test, tests_to_add)

        #adding tests not in parallel
        for test in tests_to_add:
            add_test(test)

    def create_csv_file_for_tests(self, tests):
        with open("test_cases.csv", "w", newline="", encoding="utf-8") as csvfile:
            headers = [
                "Title",
                "Automation Type",
                "Section",
                "Steps",
                "Section Description",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            robot_tests = tests
            writer.writeheader()
            for test in robot_tests:
                row = {
                    "Title": test["title"],
                    "Automation Type": self._get_custom_automation_type(test),
                    "Section": test["formatted_path"],
                    "Steps": test["rich_text_steps"],
                    "Section Description": test["suite_documentation"],
                }
                writer.writerow(row)
            self.logger.info("\nCSV file created successfully: test_cases.csv")



    def update_tests_in_testrail(self, project_id, suite_id, existing_tr_tests, robot_tests):
        # If the test with the particular name exists locally AND in the TestRail, then it will be added to the tests_to_update list
        tests_to_update = [
            test
            for test in robot_tests['tests']
            if test["title"] in [t["title"] for t in existing_tr_tests]
        ]

        tr_sections = self.get_sections_with_formatted_path(project_id, suite_id)

        def update_test(test):
            section_id = next(
                (
                    s["id"]
                    for s in tr_sections
                    if s["formatted_path"] == test["formatted_path"]
                ),
                None,
            )
            case_id = next(
                (c["id"] for c in existing_tr_tests if c["title"] == test["title"]), None
            )
            preconditions = f'**[Tags]**\n{str(test["tags"])}'

            self.tr_api.update_test_case(
                case_id,
                section_id = section_id,
                title = test["title"],
                steps=test["rich_text_steps"],
                refs=test["refs"],
                priority_id=self._get_priority_id(test),
                custom_automation_type=self._get_custom_automation_type(test),
                type_id=self._get_type_id(test),
                estimate=test['estimate'],
                milestone_id=test['milestone_id'],
                preconditions=preconditions,
            )
        
        if self.max_workers:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.logger.info(f"Updating tests in TestRail\nThe following number of tests will be updated: {len(tests_to_update)}")
                executor.map(update_test, tests_to_update)
        else:
            for test in tests_to_update:
                update_test(test)


    def move_orphan_tests_to_orphan_folder(self, project_id, suite_id, robot_tests):
        # Define the name of the orphan folder
        orphan_folder_name = self.config.get_orphan_test_section_name()
        orphan_description = self.config.get_orphan_test_section_description()

        existing_tr_tests = self.tr_api.get_cases(project_id, suite_id)["cases"]
        robot_tests_titles = [t["title"] for t in robot_tests['tests']]
        orphan_tests = []
        for test in existing_tr_tests:
            if test["title"] not in robot_tests_titles:
                orphan_tests.append(test)

        orphan_section = self.tr_api.get_section_by_name(project_id, suite_id, orphan_folder_name)
        if not orphan_tests and not orphan_section:
            pass
        elif orphan_tests and not orphan_section:
            self.tr_api.add_section(
                project_id, suite_id, orphan_folder_name, description=orphan_description
            )
        elif not orphan_tests and orphan_section:
            self.logger.info(
                f'{orphan_folder_name} section is empty: {orphan_section["id"]} and there are no orphan tests. Deleting the section.'
            )
            self.tr_api.delete_section(orphan_section["id"])
        else:
            self.tr_api.update_section(orphan_section["id"], orphan_folder_name, orphan_description)

        # Extract orphan test IDs
        orphan_tests_ids = [
            str(test["id"]) for test in orphan_tests
        ]  # Convert IDs to strings for joining
        formatted_tests_ids = ",".join(orphan_tests_ids)
        test_ids_with_prefix = [f"C{test_id}" for test_id in orphan_tests_ids]

        if orphan_tests:
            self.logger.warning(f"ORPHAN tests: {test_ids_with_prefix}")
            orphan_section = self.tr_api.get_section_by_name(project_id, suite_id, orphan_folder_name)
            self.tr_api.move_cases_to_section(suite_id, orphan_section["id"], formatted_tests_ids)

    
    def get_sections_with_formatted_path(self, project_id, suite_id):
        sections = self.tr_api.get_sections(project_id, suite_id)["sections"]
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
    
    def set_test_results(self, project_id, suite_id, test_run_id, output_file):
        tr_test_cases = self.tr_api.get_cases(project_id, suite_id)
        robot_tests = parse_robot_output_xml(output_file)
        robot_tests = add_additional_info_to_parsed_robot_tests(robot_tests)

        results = []
        for test in robot_tests['tests']:
            case_id = self._get_tr_case_id_by_title(test["title"], tr_test_cases)
            status_id = self._get_testrail_status_by_robot_status(test['test_status'])
            self.logger.info(f"Test case: {test['title']} | Status: {status_id}")
            
            formatted_elapsed = f"{str(round(test.get('elapsedtime', 0)/1000))}s"
            if formatted_elapsed == '0s':
                formatted_elapsed = 0
            #milestone_id = self.config.get_test_run_milestone_id()

            assignedto_id = None
            if self.config.get_test_run_assignedto_email():
                user = self.tr_api.get_user_by_email(self.config.get_test_run_assignedto_email())
                assignedto_id = user['id']

            status_id = self._get_testrail_status_by_robot_status(test['test_status'])
            comment = test.get('status_message') or None
            elapsed = formatted_elapsed or None
            version = test.get('version') or None
            defects = test.get('defects') or None
            assignedto_id = assignedto_id or None
            #milestone_id = milestone_id
            results.append({"case_id": case_id, "status_id": status_id, "comment": comment, "elapsed": elapsed, "version": version, "defects": defects})
        
        self.tr_api.add_results_for_cases(test_run_id, {"results": results})
            

    def _get_tr_case_id_by_title(self, title, test_cases):
        for case in test_cases["cases"]:
            if case["title"] == title:
                return case["id"]
        return None
    