from robotestrail.config_manager import ConfigManager
from robotestrail.test_sync_manager import TestSyncManager


def sync_robot_tests_to_testrail_by_ids(config_path):
    config = ConfigManager(config_path)
    test_syncer_by_id = TestSyncManager(config)
    test_syncer_by_id.sync_tests_by_id()


def set_results_by_testrail_ids(config_path):
    config = ConfigManager(config_path)
    test_syncer_by_id = TestSyncManager(config)
    test_syncer_by_id.set_results_by_id()


def sync_robot_test_by_name(config_path):
    config = ConfigManager(config_path)
    test_syncer_by_name = TestSyncManager(config)
    test_syncer_by_name.sync_robot_test_by_name()


def add_new_test_results_by_name(config_path):
    config = ConfigManager(config_path)
    test_syncer_by_name = TestSyncManager(config)
    test_syncer_by_name.add_new_test_results_by_name()


def generate_csv(config_path):
    config = ConfigManager(config_path)
    test_syncer = TestSyncManager(config)
    test_syncer.generate_csv()


def show_info(config_path):
    config = ConfigManager(config_path)
    test_syncer = TestSyncManager(config)
    test_syncer.show_info()


def check(config_path):
    config = ConfigManager(config_path)
    test_syncer = TestSyncManager(config)
    test_syncer.check()
