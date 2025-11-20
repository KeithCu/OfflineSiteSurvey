"""Configuration Manager for Survey App."""
import os


class ConfigManager:
    """Manages application configuration settings."""

    # Default configuration values
    DEFAULTS = {
        # API settings
        'api_timeout': 5.0,
        'api_base_url': 'http://localhost:5000',

        # Auto-save settings
        'auto_save_delay': 2.0,  # seconds
        'auto_save_min_interval': 30.0,  # seconds
        'draft_retention_time': 300.0,  # 5 minutes

        # Sync settings
        'sync_batch_size': 100,
        'sync_retry_attempts': 3,
        'sync_retry_delay': 1.0,

        # UI settings
        'max_visible_photos': 40,
        'photo_thumbnail_size': (150, 150),

        # Storage settings
        'max_draft_age_days': 7,
        'cleanup_interval_hours': 24,

        # GPS settings
        'gps_timeout': 10.0,
        'gps_accuracy_threshold': 50.0,  # meters

        # CompanyCam settings
        'companycam_client_id': '',
        'companycam_client_secret': '',
        'companycam_access_token': '',
        'companycam_refresh_token': '',
        'companycam_user_id': '',
        'default_companycam_template_name': '',
    }

    def __init__(self):
        self._config = self.DEFAULTS.copy()
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'SURVEY_API_TIMEOUT': ('api_timeout', float),
            'SURVEY_API_BASE_URL': ('api_base_url', str),
            'SURVEY_AUTO_SAVE_DELAY': ('auto_save_delay', float),
            'SURVEY_AUTO_SAVE_MIN_INTERVAL': ('auto_save_min_interval', float),
            'SURVEY_DRAFT_RETENTION': ('draft_retention_time', float),
            'SURVEY_SYNC_BATCH_SIZE': ('sync_batch_size', int),
            'SURVEY_SYNC_RETRY_ATTEMPTS': ('sync_retry_attempts', int),
            'SURVEY_SYNC_RETRY_DELAY': ('sync_retry_delay', float),
            'SURVEY_MAX_VISIBLE_PHOTOS': ('max_visible_photos', int),
            'SURVEY_GPS_TIMEOUT': ('gps_timeout', float),
            'SURVEY_GPS_ACCURACY_THRESHOLD': ('gps_accuracy_threshold', float),
            'COMPANYCAM_CLIENT_ID': ('companycam_client_id', str),
            'COMPANYCAM_CLIENT_SECRET': ('companycam_client_secret', str),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    self._config[config_key] = converter(value)
                except (ValueError, TypeError):
                    # Log warning but keep default
                    pass

    def get(self, key, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self._config[key] = value

    def get_all(self):
        """Get all configuration values."""
        return self._config.copy()

    # Convenience methods for commonly accessed settings
    @property
    def api_timeout(self):
        return self.get('api_timeout')

    @property
    def auto_save_delay(self):
        return self.get('auto_save_delay')

    @property
    def auto_save_min_interval(self):
        return self.get('auto_save_min_interval')

    @property
    def draft_retention_time(self):
        return self.get('draft_retention_time')

    @property
    def api_base_url(self):
        return self.get('api_base_url')

    @property
    def sync_batch_size(self):
        return self.get('sync_batch_size')

    @property
    def gps_timeout(self):
        return self.get('gps_timeout')

    # CompanyCam properties
    @property
    def companycam_client_id(self):
        return self.get('companycam_client_id')

    @property
    def companycam_access_token(self):
        return self.get('companycam_access_token')

    @property
    def companycam_refresh_token(self):
        return self.get('companycam_refresh_token')

    @property
    def companycam_user_id(self):
        return self.get('companycam_user_id')

    @property
    def companycam_client_secret(self):
        return self.get('companycam_client_secret')
