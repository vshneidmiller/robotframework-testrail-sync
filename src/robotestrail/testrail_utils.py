import os
from collections import Counter
import concurrent.futures

from robotestrail.logging_config import setup_logging
from robotestrail.robot_framework_utils import parse_robot_output_xml, get_rich_text_steps
from robotestrail.testrail_api import (
    tr_add_result_for_case,
    tr_add_section,
    tr_add_test_case,
    tr_get_projects,
    tr_get_test_plans,
    tr_get_test_suites,
    tr_get_sections,
    tr_get_test_cases,
    tr_update_section,
    tr_update_test_case,
    tr_move_cases_to_section,
    tr_delete_section,
    tr_add_test_plan,
    get_testrail_status_by_robot_status
)

from robotestrail.config import (
    MAX_WORKERS,
    ROOT_TEST_SECTION_NAME,
    ROOT_TEST_SECTION_DISCLAIMER,
    ORPHAN_TEST_SECTION_NAME,
    ORPHAN_TEST_SECTION_DESCRIPTION,
    TEST_PLAN_NAME,
    TEST_PLAN_DESCRIPTION,
    SOURCE_CONTROL_NAME,
    SOURCE_CONTROL_LINK,
    TESTRAIL_DEFAULT_TC_PRIORITY_ID,
    TESTRAIL_DEFAULT_TC_TYPE_ID,
)

# Initialize the logger for this module
logger = setup_logging()


# Handlers
def get_project_by_name(name):
    projects = tr_get_projects()["projects"]
    for project in projects:
        if project["name"] == name:
            return project
    return None


def get_tr_case_id_by_title(title, test_cases):
    for case in test_cases["cases"]:
        if case["title"] == title:
            return case["id"]
    return None


def get_tr_test_plan_by_name(project_id, name):
    test_plans = tr_get_test_plans(project_id)["plans"]
    for test_plan in test_plans:
        if test_plan["name"] == name:
            return test_plan
    return None


def get_test_suite_by_name(project_id, name):
    suites = tr_get_test_suites(project_id)
    for suite in suites:
        if suite["name"] == name:
            return suite
    return None


def get_section_by_name(project_id, suite_id, name):
    sections = tr_get_sections(project_id, suite_id)["sections"]
    for section in sections:
        if section["name"] == name:
            return section
    return None


def get_section_by_name_and_parent_id(project_id, suite_id, name, parent_id):
    sections = tr_get_sections(project_id, suite_id)["sections"]
    for section in sections:
        if section["name"] == name and section["parent_id"] == parent_id:
            return section
    return None


def add_folders_to_testrail(project_id, suite_id, robot_tests):
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
                f"{SOURCE_CONTROL_LINK}/{str(formatted_path).replace(' > ', os.sep)}"
            )
        else:
            source_control_link = f"{SOURCE_CONTROL_LINK}/{str(formatted_path).replace(' > ', os.sep)}.robot"
        return source_control_link

    def get_parent_id_by_formatted_path(formatted_path):
        sections = tr_get_sections(project_id, suite_id)["sections"]
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

    def create_sections_in_parallel(sections):
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for missing_path in sections:
                parent_id = get_parent_id_by_formatted_path(
                    missing_path.rsplit(" > ", 1)[0]
                )
                source_control_link = get_github_link_to_folder_file(
                    missing_path, sorted_formatted_local_pathes
                )
                description = (
                    f"Link to the {SOURCE_CONTROL_NAME}:\n{source_control_link}"
                )
                section_name = missing_path.split(">")[-1].strip()
                futures.append(
                    executor.submit(
                        tr_add_section,
                        project_id,
                        suite_id,
                        section_name,
                        parent_id=parent_id,
                        description=description,
                    )
                )

            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error creating section: {e}")

    def create_missing_sections():
        missing_sections_pathes = []
        for path in sorted_formatted_local_pathes:
            if path not in [
                s["formatted_path"] for s in existing_sections_with_formatted_path
            ]:
                missing_sections_pathes.append(path)
        logger.info("Missing sections:\n%s", missing_sections_pathes)

        levels = [[] for _ in range(6)]
        for path in missing_sections_pathes:
            levels[min(path.count(" > "), 5)].append(path)

        for i, level in enumerate(levels):
            if level:
                logger.info(f"Creating sections for level {i}:\n{level}")
                create_sections_in_parallel(level)

    def update_existing_sections():
        def update_section(existing_section_path):
            try:
                parent_id = get_parent_id_by_formatted_path(
                    existing_section_path.rsplit(" > ", 1)[0]
                )
                source_control_link = get_github_link_to_folder_file(
                    existing_section_path, sorted_formatted_local_pathes
                )
                description = (
                    f"Link to the {SOURCE_CONTROL_NAME}:\n{source_control_link}"
                )
                section_name = existing_section_path.split(">")[-1].strip()
                if existing_section_path == ROOT_TEST_SECTION_NAME:
                    root_description = (
                        f"{ROOT_TEST_SECTION_DISCLAIMER}\n\n{description}"
                    )
                    section = get_section_by_name(
                        project_id, suite_id, ROOT_TEST_SECTION_NAME
                    )
                    logger.info(
                        f"Updating root section: {section_name} with description: {root_description}"
                    )
                    tr_update_section(
                        section["id"], section_name, description=root_description
                    )
                else:
                    section = get_section_by_name_and_parent_id(
                        project_id, suite_id, section_name, parent_id
                    )
                    logger.info(
                        f"Updating section: {section_name} with description: {description}"
                    )
                    tr_update_section(
                        section["id"], section_name, description=description
                    )
            except Exception as e:
                logger.error(f"Error updating section '{existing_section_path}': {e}")
                raise

        existing_section_pathes = []
        for path in sorted_formatted_local_pathes:
            if path in [
                s["formatted_path"] for s in existing_sections_with_formatted_path
            ]:
                existing_section_pathes.append(path)
        logger.info("Existing sections:\n%s", existing_section_pathes)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(update_section, path)
                for path in existing_section_pathes
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error updating section: {e}")

    formatted_pathes = [test["formatted_path"] for test in robot_tests]
    # Process each path and add intermediate paths
    for path in formatted_pathes:
        add_intermediate_paths(path, formatted_pathes)

    # Remove duplicates and sort by length
    sorted_formatted_local_pathes = sorted(list(set(formatted_pathes)), key=len)
    existing_sections_with_formatted_path = get_sections_with_formatted_path(
        project_id, suite_id
    )

    create_missing_sections()
    update_existing_sections()


def parse_robot_test_tags(tags):
    priority_id = TESTRAIL_DEFAULT_TC_PRIORITY_ID
    type_id = TESTRAIL_DEFAULT_TC_TYPE_ID
    estimate = None
    milestone_id = None
    refs = []

    for tag in tags:
        tag = str(tag)
        if tag.startswith("priority_id"):
            priority_id = int(tag.split(":")[1])
        elif tag.startswith("type_id"):
            type_id = int(tag.split(":")[1])
        elif tag.startswith("estimate"):
            estimate = tag.split(":")[1]
        elif tag.startswith("milestone_id"):
            milestone_id = int(tag.split(":")[1])
        elif tag.startswith("refs"):
            refs.append(tag.split(":")[1])
        elif tag.startswith("jira"):
            jira_ticket_link = tag.split(":")[1]
            refs.append(jira_ticket_link)

    refs = ", ".join(refs) if refs else None

    return priority_id, type_id, estimate, milestone_id, refs


def add_tests_to_testrail(project_id, suite_id, existing_tr_tests, robot_tests):
    # If the test with the particular name exists locally but NOT in the TestRail, then it will be added to the tests_to_add list
    tests_to_add = [
        test
        for test in robot_tests
        if test["title"] not in [t["title"] for t in existing_tr_tests]
    ]

    tr_sections = get_sections_with_formatted_path(project_id, suite_id)
    # existing_tr_tests = tr_get_test_cases(project_id, suite_id)['cases']

    def add_test(test):
        section_id = next(
            (
                s["id"]
                for s in tr_sections
                if s["formatted_path"] == test["formatted_path"]
            ),
            None,
        )
        steps = get_rich_text_steps(test["steps"])
        preconditions = f'**[Tags]**\n{str(test["tags"])}'
        priority_id, type_id, estimate, milestone_id, refs = parse_robot_test_tags(
            test["tags"]
        )
        tr_add_test_case(
            section_id,
            test["title"],
            steps,
            1,
            refs=refs,
            priority_id=priority_id,
            type_id=type_id,
            estimate=estimate,
            milestone_id=milestone_id,
            preconditions=preconditions,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(add_test, tests_to_add)


def update_tests_in_testrail(project_id, suite_id, existing_tr_tests, robot_tests):
    # If the test with the particular name exists locally AND in the TestRail, then it will be added to the tests_to_update list
    tests_to_update = [
        test
        for test in robot_tests
        if test["title"] in [t["title"] for t in existing_tr_tests]
    ]

    tr_sections = get_sections_with_formatted_path(project_id, suite_id)

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
        steps = get_rich_text_steps(test["steps"])
        preconditions = f'**[Tags]**\n{str(test["tags"])}'

        priority_id, type_id, estimate, milestone_id, refs = parse_robot_test_tags(
            test["tags"]
        )
        tr_update_test_case(
            case_id,
            section_id,
            test["title"],
            steps,
            1,
            preconditions,
            refs=refs,
            priority_id=priority_id,
            type_id=type_id,
            estimate=estimate,
            milestone_id=milestone_id,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(update_test, tests_to_update)


def move_orphan_tests_to_orphan_folder(project_id, suite_id, robot_tests):
    # Define the name of the orphan folder
    orphan_folder_name = ORPHAN_TEST_SECTION_NAME
    orphan_description = ORPHAN_TEST_SECTION_DESCRIPTION

    existing_tr_tests = tr_get_test_cases(project_id, suite_id)["cases"]
    robot_tests_titles = [t["title"] for t in robot_tests]
    orphan_tests = []
    for test in existing_tr_tests:
        if test["title"] not in robot_tests_titles:
            orphan_tests.append(test)

    orphan_section = get_section_by_name(project_id, suite_id, orphan_folder_name)
    if not orphan_tests and not orphan_section:
        pass
    elif orphan_tests and not orphan_section:
        tr_add_section(
            project_id, suite_id, orphan_folder_name, description=orphan_description
        )
    elif not orphan_tests and orphan_section:
        logger.info(
            f'{ORPHAN_TEST_SECTION_NAME} section is empty: {orphan_section["id"]} and there are no orphan tests. Deleting the section.'
        )
        tr_delete_section(orphan_section["id"])
    else:
        tr_update_section(orphan_section["id"], orphan_folder_name, orphan_description)

    # Extract orphan test IDs
    orphan_tests_ids = [
        str(test["id"]) for test in orphan_tests
    ]  # Convert IDs to strings for joining
    formatted_tests_ids = ",".join(orphan_tests_ids)
    test_ids_with_prefix = [f"C{test_id}" for test_id in orphan_tests_ids]

    if orphan_tests:
        logger.warning(f"ORPHAN tests: {test_ids_with_prefix}")
        orphan_section = get_section_by_name(project_id, suite_id, orphan_folder_name)
        tr_move_cases_to_section(suite_id, orphan_section["id"], formatted_tests_ids)


def get_sections_with_formatted_path(project_id, suite_id):
    sections = tr_get_sections(project_id, suite_id)["sections"]
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


def add_or_set_test_plan(project_id):
    test_plan = get_tr_test_plan_by_name(project_id, TEST_PLAN_NAME)
    if not test_plan:
        test_plan = tr_add_test_plan(project_id, TEST_PLAN_NAME, TEST_PLAN_DESCRIPTION)
    logger.info(f"Test plan ID: {test_plan['id']}")
    return test_plan


def process_test_result(test_result, tr_test_cases, test_run_id):
    try:
        test_case_id = get_tr_case_id_by_title(test_result["title"], tr_test_cases)
        status_id = get_testrail_status_by_robot_status(test_result["test_status"])
        logger.info(f"Test case: {test_result['title']} | Status: {status_id}")
        comment = ""
        if test_result['status_message']:
            comment = test_result['status_message']
        tr_add_result_for_case(test_run_id, test_case_id, status_id, comment)
    except Exception as e:
        logger.exception(
            f"Error processing test result for {test_result['title']}: {e}"
        )


def set_test_results(project_id, suite_id, test_run, output_file):
    tr_test_cases = tr_get_test_cases(project_id, suite_id)
    test_results = parse_robot_output_xml(output_file)
    test_run_id = test_run["id"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(
                process_test_result, test_result, tr_test_cases, test_run_id
            )
            for test_result in test_results
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.exception(f"Error in future: {e}")
