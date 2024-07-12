import csv
from robotestrail.logging_config import *
from robotestrail.robot_framework_utils import (
    run_dryrun_and_get_tests_with_additional_info,
)


class CsvGenerator:
    def __init__(self, config):
        self.logger = setup_logging()
        self.config = config

    def generate_csv(self):
        self.logger.info("Generating CSV file with test cases")
        path_to_tests = self.config.get_robot_tests_folder_path()
        robot_tests = run_dryrun_and_get_tests_with_additional_info(
            path_to_tests, "dry_run_output.xml"
        )
        self.create_csv_file_for_tests(robot_tests["tests"])

    def create_csv_file_for_tests(self, tests):
        with open("test_cases.csv", "w", newline="", encoding="utf-8") as csvfile:
            headers = [
                "Title",
                #"Automation Type",
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
                    # "Automation Type": self._get_custom_automation_type(test),
                    "Section": test["formatted_path"],
                    "Steps": test["rich_text_steps"],
                    "Section Description": test["suite_documentation"],
                }
                writer.writerow(row)
            self.logger.info("\nCSV file created successfully: test_cases.csv")
