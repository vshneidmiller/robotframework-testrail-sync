if __name__ == "__main__" and __package__ is None:
    import sys
    from os import path

    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    __package__ = "robotestrail"


from robotestrail.logging_config import setup_logging
import argparse


# Initialize logging
logger = setup_logging()


def main():

    parser = argparse.ArgumentParser(
        description="RoboTestRail - A tool to synchronize Robot Framework tests with TestRail"
    )
    parser.add_argument(
        "--sync",
        "-s",
        action="store_true",
        help="Sync Robot Framework tests with TestRail by name",
    )
    parser.add_argument(
        "--sync_by_id",
        "-sbid",
        action="store_true",
        help="Sync Robot Framework tests with TestRail by test case IDs",
    )
    parser.add_argument(
        "--results", "-r", action="store_true", help="Upload test results to TestRail"
    )
    parser.add_argument(
        "--results_by_id",
        "-rbid",
        action="store_true",
        help="Upload test results to TestRail by test case IDs",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Generate a CSV file withe the text cases. This CSV file can be imported to TestRail.",
    )
    parser.add_argument(
        "--info",
        "-i",
        action="store_true",
        help="Show TestRail information like milestones, users, fields, etc",
    )
    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        help="Check the config file, Robot Framework tests, and the TestRail connection",
    )
    parser.add_argument(
        "--create_config",
        "-cc",
        action="store_true",
        help="Create a new config file with the default values",
    )
    parser.add_argument(
        "--config_path",
        "-config",
        type=str,
        required=True,
        help="Path to the YAML config file",
    )

    args = parser.parse_args()

    from robotestrail.handlers import (
        show_info,
        check,
        generate_csv,
        sync_robot_tests_to_testrail_by_ids,
        set_results_by_testrail_ids,
        sync_robot_test_by_name,
        add_new_test_results_by_name,
    )

    if args.sync:
        sync_robot_test_by_name(args.config_path)
    elif args.results:
        add_new_test_results_by_name(args.config_path)
    elif args.info:
        show_info(args.config_path)
    elif args.csv:
        generate_csv(args.config_path)
    elif args.sync_by_id:
        sync_robot_tests_to_testrail_by_ids(args.config_path)
    elif args.results_by_id:
        set_results_by_testrail_ids(args.config_path)
    elif args.check:
        check(args.config_path)
    # elif args.check:
    #    create_config()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
