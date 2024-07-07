import os
import re
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
            "status_message": test.message,
            "elapsedtime": test.elapsedtime,
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


def parse_robot_output_xml(output_file):
    result = ExecutionResult(output_file)
    visitor = TestSuiteVisitor()
    result.visit(visitor)

    # write to json
    # with open('test_cases.json', 'w') as json_file:
    #    json.dump(visitor.test_cases, json_file, indent=4)

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


def add_additional_info_to_parsed_robot_tests(robot_tests):
    # add unique ID for each test case
    for i, test in enumerate(robot_tests):
        test["id"] = i

    # add rich text steps for each test case
    for test in robot_tests:
        test["rich_text_steps"] = get_rich_text_steps(test["steps"])

    # add formatted tags for each test case
    for test in robot_tests:
        test["formatted_tags"] = f'**[Tags]**\n{", ".join(test["tags"])}'

    # set estimate, priority_id, type_id, milestone_id, refs for each test case
    for test in robot_tests:
        refs = []
        defects = []
        estimate = None
        milestone_id = None
        for tag in test["tags"]:
            try:
                tag = str(tag)
                if tag.startswith("priority_id:"):
                    test["priority_id"] = int(tag.split(":")[1])
                if tag.startswith("priority:"):
                    test["priority"] = tag.split(":")[1]
                elif tag.startswith("type_id:"):
                    test["type_id"] = int(tag.split(":")[1])
                elif tag.startswith("type:"):
                    test["type"] = tag.split(":")[1]
                elif tag.startswith("estimate:"):
                    estimate = tag.split(":")[1]
                elif tag.startswith("automation_type_id:"):
                    test["custom_automation_type"] = int(tag.split(":")[1])
                elif tag.startswith("automation_type:"):
                    test["custom_automation_type"] = tag.split(":")[1]
                elif tag.startswith("automatedby_id:"):
                    test["custom_automatedby_id"] = int(tag.split(":")[1])
                elif tag.startswith("customer:"):
                    test["custom_customer"] = int(tag.split(":")[1])
                elif tag.startswith("milestone_id:"):
                    milestone_id = int(tag.split(":")[1])
                elif tag.startswith("refs:"):
                    refs.append(tag.split(":")[1])
                elif tag.startswith("jira:"):
                    refs.append(tag.split(":")[1])
                elif tag.startswith("defect:"):
                    defects.append(tag.split(":")[1])
                elif tag.startswith("bug:"):
                    defects.append(tag.split(":")[1])
            except Exception as e:
                logger.error(f"Unable to parse tag: '{tag}' ] Error: {e}")

        test["refs"] = ", ".join(refs) if refs else None
        test["defects"] = ", ".join(defects) if defects else None
        test["estimate"] = estimate
        test["milestone_id"] = milestone_id

    # add tr_id to each test case with tag in format C123456
    for test in robot_tests:
        tr_ids = []
        for tag in test["tags"]:
            if re.match(r"C\d{2,9}", tag):
                tr_ids.append(tag)
        test["tr_ids"] = tr_ids

    tests_with_multiple_tr_ids = []
    tests_with_one_tr_id = []
    tests_with_no_tr_id = []

    for test in robot_tests:
        if "tr_ids" not in test:
            tests_with_no_tr_id.append(test)

        if "tr_ids" in test:
            if len(test["tr_ids"]) == 1:
                tests_with_one_tr_id.append(test)
            elif len(test["tr_ids"]) > 1:
                tests_with_multiple_tr_ids.append(test)

    # add information about duplicate TR ids
    all_tr_ids = []
    for test in robot_tests:
        if test["tr_ids"]:
            for tr_id in test["tr_ids"]:
                all_tr_ids.append(tr_id)

    test_ids_of_tests_with_multiple_tr_ids = [
        t["id"] for t in tests_with_multiple_tr_ids
    ]
    all_robot_test_ids = [t["id"] for t in robot_tests]

    test_ids_of_tests_with_tr_ids = [t["id"] for t in robot_tests if "tr_id" in t]

    test_ids_of_tests_without_tr_ids = list(
        set(all_robot_test_ids) - set(test_ids_of_tests_with_tr_ids)
    )
    tests_without_tr_id = [t for t in robot_tests if not t["tr_ids"]]

    tests_with_additional_info = {
        "tests": robot_tests,
        "multiple_tr_ids": test_ids_of_tests_with_multiple_tr_ids,
        "no_tr_id": test_ids_of_tests_without_tr_ids,
        "tests_with_multiple_tr_ids": tests_with_multiple_tr_ids,
        "tests_without_tr_id": tests_without_tr_id,
        "tests_with_one_tr_id": tests_with_one_tr_id,
        "all_tr_ids": all_tr_ids,
    }
    return tests_with_additional_info


def run_dryrun_and_get_tests_with_additional_info(path_to_tests, output_file):
    robot_tests = run_dryrun_and_get_tests(path_to_tests, output_file)
    tests_with_additional_info = add_additional_info_to_parsed_robot_tests(robot_tests)
    return tests_with_additional_info


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
