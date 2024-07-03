import yaml
from robotestrail.logging_config import setup_logging

class ConfigManager:
    def __init__(self, config_file):
        self.logger = setup_logging()
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_file, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def get_config(self):
        return self.config

    def get_robot_tests_folder_path(self):
        return self.config['paths']['tests_folder']
    
    def get_robot_output_xml_file_path(self):
        return self.config['paths']['output_xml_file']

    def get_default_type_id(self):
        return self.config['testrail_defaults']['type_id']
    
    def get_default_priority_id(self):
        return self.config['testrail_defaults']['priority_id']
    
    def get_project_name(self):
        return self.config['project']['name']
    
    def get_max_workers(self):
        return self.config['testrail']['max_workers']

    def get_default_custom_automation_type(self):
        return self.config['testrail_defaults']['custom_automation_type_id']
    
    def get_test_plan_name(self):
        return self.config['test_plan']['name']
    
    def get_test_run_name(self):
        return self.config['test_run']['name']
    
    def get_test_suite(self):
        return self.config['project']['suite_name']
    