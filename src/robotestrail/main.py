if __name__ == "__main__" and __package__ is None:
    import sys
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    __package__ = "robotestrail"


from robotestrail.config import initialize_config, read_config
from robotestrail.logging_config import setup_logging
import argparse


# Initialize logging
logger = setup_logging()

def main():

    parser = argparse.ArgumentParser(description='RoboTestRail - A tool to synchronize Robot Framework tests with TestRail')
    parser.add_argument('--sync', '-s', action='store_true', help='Sync Robot Framework tests with TestRail by name')
    parser.add_argument('--sync_by_id', '-sbid', action='store_true', help='Sync Robot Framework tests with TestRail by test case IDs')
    parser.add_argument('--results', '-r', action='store_true', help='Upload test results to TestRail')
    parser.add_argument('--results_by_id', '-rbid', action='store_true', help='Upload test results to TestRail by test case IDs')
    parser.add_argument('--csv', action='store_true', help='Generate a CSV file withe the text cases. This CSV file can be imported to TestRail.')
    parser.add_argument('--milestones', '-m', action='store_true', help='Show TestRail milestones for the project specified in the config file')
    parser.add_argument('--check', '-c', action='store_true', help='Check the config file, Robot Framework tests, and the TestRail connection')
    parser.add_argument('--create_config', '-cc', action='store_true', help='Create a new config file with the default values')
    parser.add_argument('--config_path', '-config', type=str, required=True, help='Path to the YAML config file')
    
    args = parser.parse_args()
    config = read_config(args.config_path)
    initialize_config(config)
    
    # Initialize the TestRail API

    from robotestrail.handlers import sync_robot_tests_to_testrail, add_new_test_results, show_milestones, check, generate_csv, create_config, sync_robot_tests_to_testrail_by_ids, set_results_by_testrail_ids
    if args.sync:
        sync_robot_tests_to_testrail()
    elif args.results:
        add_new_test_results()
    elif args.milestones:
        show_milestones(args.config_path)
    elif args.csv:
        generate_csv()
    elif args.sync_by_id:
        sync_robot_tests_to_testrail_by_ids(args.config_path)
    elif args.results_by_id:
        set_results_by_testrail_ids(args.config_path)
    elif args.check:
        check()
    elif args.check:
        create_config()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
