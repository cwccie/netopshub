"""Tests for configuration manager."""

import pytest
from netopshub.config.manager import ConfigManager


class TestConfigManager:
    def test_backup_config(self, config_manager):
        snapshot = config_manager.backup_config("dev1", "hostname router-1\n!", hostname="router-1")
        assert snapshot.device_id == "dev1"
        assert snapshot.config_hash != ""
        assert config_manager.device_count == 1

    def test_get_latest(self, config_manager):
        config_manager.backup_config("dev1", "config v1")
        config_manager.backup_config("dev1", "config v2")
        latest = config_manager.get_latest("dev1")
        assert latest is not None
        assert latest.config_text == "config v2"

    def test_no_duplicate_backup(self, config_manager):
        config_manager.backup_config("dev1", "same config")
        config_manager.backup_config("dev1", "same config")
        assert config_manager.total_snapshots == 1

    def test_diff(self, config_manager):
        config_manager.backup_config("dev1", "line 1\nline 2\n")
        config_manager.backup_config("dev1", "line 1\nline 3\n")
        diff = config_manager.diff("dev1")
        assert diff is not None
        assert diff.lines_added > 0

    def test_history(self, config_manager):
        config_manager.backup_config("dev1", "v1")
        config_manager.backup_config("dev1", "v2")
        config_manager.backup_config("dev1", "v3")
        history = config_manager.get_history("dev1")
        assert len(history) == 3

    def test_golden_config(self, config_manager):
        config_manager.set_golden_config("dev1", "golden config")
        config_manager.backup_config("dev1", "current config")
        result = config_manager.compare_to_golden("dev1")
        assert result is not None
        assert "golden" in result or "current" in result

    def test_search_configs(self, config_manager):
        config_manager.backup_config("dev1", "hostname router-1\ninterface Gi0/0\n ip address 10.0.0.1")
        results = config_manager.search_configs("10.0.0.1")
        assert len(results) > 0
