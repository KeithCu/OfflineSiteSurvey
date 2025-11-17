"""Tests for configuration manager."""
import os
import pytest
from src.survey_app.config_manager import ConfigManager


class TestConfigManager:
    """Test configuration manager."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ConfigManager()
        assert config.get('api_timeout') == 5.0
        assert config.get('auto_save_delay') == 2.0
        assert config.get('max_visible_photos') == 40

    def test_environment_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv('SURVEY_API_TIMEOUT', '10.0')
        monkeypatch.setenv('SURVEY_AUTO_SAVE_DELAY', '5.0')

        config = ConfigManager()
        assert config.get('api_timeout') == 10.0
        assert config.get('auto_save_delay') == 5.0

    def test_invalid_env_values(self, monkeypatch):
        """Test that invalid environment values keep defaults."""
        monkeypatch.setenv('SURVEY_API_TIMEOUT', 'invalid')

        config = ConfigManager()
        assert config.get('api_timeout') == 5.0  # Should keep default

    def test_get_with_default(self):
        """Test get method with default values."""
        config = ConfigManager()
        assert config.get('nonexistent_key', 'default') == 'default'
        assert config.get('api_timeout', 'ignored') == 5.0

    def test_set_value(self):
        """Test setting configuration values."""
        config = ConfigManager()
        config.set('custom_key', 'custom_value')
        assert config.get('custom_key') == 'custom_value'

    def test_convenience_properties(self):
        """Test convenience property accessors."""
        config = ConfigManager()
        assert config.api_timeout == 5.0
        assert config.auto_save_delay == 2.0
        assert config.api_base_url == 'http://localhost:5000'

    def test_get_all(self):
        """Test getting all configuration values."""
        config = ConfigManager()
        all_config = config.get_all()
        assert isinstance(all_config, dict)
        assert 'api_timeout' in all_config
        assert 'auto_save_delay' in all_config
