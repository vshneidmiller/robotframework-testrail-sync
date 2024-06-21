import os
import csv
from robot import run
from robot.api import ExecutionResult, ResultVisitor
from robotestrail.logging_config import setup_logging

# Initialize the logger for this module
logger = setup_logging()

class TestSuiteVisitor(ResultVisitor):
    def __init__(self):
        self.test_cases = []

    def visit_suite(self, suite):
        self.current_suite_doc = suite.doc
        self.current_suite_id = suite.id
        self.current_suite_source = str(suite.source) if suite.source else None
        self.current_suite_starttime = suite.starttime
        self.current_suite_endtime = suite.endtime
        self.current_suite_status = suite.status

        for test in suite.tests:
            self.visit_test(test)
        for child_suite in suite.suites:
            self.visit_suite(child_suite)

    def visit_test(self, test):
        test_info = {
            "title": test.name,
            "tags": [str(tag) for tag in test.tags],
            "steps": self._parse_keywords(test.body),
            "formatted_path": self._get_test_path(test).lower(),
            "suite_documentation": self.current_suite_doc,
            "suite_id": self.current_suite_id,
            "suite_source": self.current_suite_source,
            "test_status": test.status,
            "test_documentation": test.doc,
            "status_message": self._get_status_message(test)
        }
        self.test_cases.append(test_info)

    def _parse_keywords(self, keywords):
        steps = []
        for kw in keywords:
            if kw.type == "KEYWORD":
                steps.append(
                    {
                        "step_name": kw.name.split(".", 1)[-1],
                        "args": [str(arg) for arg in kw.args],
                        "library": kw.libname,
                        "status": kw.status,
                        "starttime": kw.starttime,
                        "endtime": kw.endtime,
                    }
                )
        return steps

    def _get_test_path(self, test):
        path_elements = []
        suite = test.parent
        while suite:
            if suite.source:  # Using source to get the exact name including underscores
                suite_name = os.path.basename(suite.source).replace(".robot", "")
                path_elements.insert(0, suite_name)
            suite = suite.parent
        return " > ".join(path_elements)

    def _get_status_message(self, test):
        return test.message

def parse_robot_output_xml(output_file):
        result = ExecutionResult(output_file)
        visitor = TestSuiteVisitor()
        result.visit(visitor)
        return visitor.test_cases

def run_robot_dryrun(output_file, path_to_tests):
        run(
            path_to_tests,
            dryrun=True,
            output=output_file,
            log=None,
            report=None,
            stdout=None,
            stderr=None,
        )

def run_dryrun_and_get_tests(path_to_tests, output_file):
    run_robot_dryrun(output_file, path_to_tests)

    test_cases = parse_robot_output_xml(output_file)

    try:
        os.remove(output_file)
    except OSError as e:
        logger.error(f"Error: {output_file} : {e.strerror}")

    return test_cases


def get_rich_text_steps(steps):
    rich_text_steps = []

    for step in steps:
        # Assuming each step has a 'step_name' and 'args' fields
        step_name = step["step_name"]
        args = step["args"]

        # Formatting the step name as bold
        formatted_step = f"**{step_name}**"

        # Adding arguments if present
        if args:
            formatted_step += ": " + ", ".join(args)

        rich_text_steps.append(formatted_step)

    # Join steps with a newline for better readability
    return "\n".join(rich_text_steps)


def generate_csv(tests):
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
            steps = get_rich_text_steps(test["steps"])
            row = {
                "Title": test["title"],
                "Automation Type": "Automated",
                "Section": test["formatted_path"],
                "Steps": steps,
                "Section Description": test["suite_documentation"],
            }
            writer.writerow(row)
        print("\nCSV file created successfully: test_cases.csv")


def generate_csv_for_test_rail(path):
    tests = run_dryrun_and_get_tests(path, "dryrun_output.xml")
    generate_csv(tests)
