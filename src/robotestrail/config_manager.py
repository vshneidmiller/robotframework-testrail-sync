import yaml
from robotestrail.logging_config import setup_logging


class ConfigManager:
    def __init__(self, config_file):
        self.logger = setup_logging()
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_file, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def get_config(self):
        return self.config

    def get_robot_tests_folder_path(self):
        return self.config["paths"]["tests_folder"]

    def get_robot_output_xml_file_path(self):
        return self.config["paths"]["output_xml_file"]

    def get_default_type_id(self):
        return self.config.get("testrail_defaults", {}).get("type_id", None)

    def get_default_type(self):
        return self.config["testrail_defaults"]["type"]

    def get_default_priority_id(self):
        return self.config.get("testrail_defaults", {}).get("priority_id", None)

    def get_default_priority(self):
        return self.config.get("testrail_defaults", {}).get("priority", None)

    def get_project_name(self):
        return self.config["project"]["name"]

    def get_max_workers(self):
        return self.config["testrail"]["max_workers"]

    def get_default_custom_automation_type(self):
        return self.config.get("testrail_defaults", {}).get(
            "custom_automation_type", None
        )

    def get_default_custom_automation_type_id(self):
        return self.config.get("testrail_defaults", {}).get(
            "custom_automation_type_id", None
        )

    def get_default_automatedby(self):
        return self.config.get("testrail_defaults", {}).get("automatedby", None)

    def get_default_automatedby_id(self):
        return self.config.get("testrail_defaults", {}).get("automatedby_id", None)

    # test plan
    def get_test_plan_name(self):
        return self.config["test_plan"]["name"]

    def get_test_plan_description(self):
        return self.config["test_plan"]["description"]

    def get_test_plan_milestone_id(self):
        return self.config["test_plan"]["milestone_id"]

    def get_test_plan_milestone_name(self):
        return self.config["test_plan"]["milestone_name"]

    # test run
    def get_test_run_name(self):
        return self.config["test_run"]["name"]

    def get_test_run_description(self):
        return self.config.get("test_run", {}).get("description", None)

    def get_test_run_milestone_id(self):
        return self.config.get("test_run", {}).get("milestone_id", None)

    def get_test_run_milestone_name(self):
        return self.config.get("test_run", {}).get("milestone_name", None)

    def get_test_run_assignedto_email(self):
        return self.config["test_run"]["assignedto_email"]

    def get_test_run_include_all(self):
        return self.config.get("test_run", {}).get("include_all", False)

    def get_test_run_refs(self):
        return self.config.get("test_run", {}).get("refs", None)

    def get_test_suite(self):
        return self.config.get("project", {}).get("suite_name", None)

    def get_root_test_section_name(self):
        return self.config["test_section"]["root_name"]

    def get_root_test_section_disclaimer(self):
        return self.config["test_section"]["root_disclaimer"]

    def get_orphan_test_section_name(self):
        return self.config["test_section"]["orphan_name"]

    def get_orphan_test_section_description(self):
        return self.config["test_section"]["orphan_description"]

    def get_source_control_name(self):
        return self.config.get("source_control", {}).get("name", None)

    def get_source_control_link(self):
        return self.config.get("source_control", {}).get("link", None)
