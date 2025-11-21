"""Configuration Manager for Survey App."""
import os
from pydantic_settings import BaseSettings


class ConfigManager(BaseSettings):
    """Manages application configuration settings using Pydantic BaseSettings."""

    # API settings
    api_timeout: float = 5.0
    api_base_url: str = 'http://localhost:5000'

    # Auto-save settings
    auto_save_delay: float = 2.0  # seconds
    auto_save_min_interval: float = 30.0  # seconds
    draft_retention_time: float = 300.0  # 5 minutes

    # Sync settings
    sync_batch_size: int = 100
    sync_retry_attempts: int = 3
    sync_retry_delay: float = 1.0

    # UI settings
    max_visible_photos: int = 40
    photo_thumbnail_size: tuple = (150, 150)

    # Storage settings
    max_draft_age_days: int = 7
    cleanup_interval_hours: int = 24

    # GPS settings
    gps_timeout: float = 10.0
    gps_accuracy_threshold: float = 50.0  # meters

    # Image processing settings
    image_compression_quality: int = 75  # JPEG quality (1-100)
    thumbnail_max_size: int = 200  # Maximum thumbnail dimension in pixels
    upload_retry_attempts: int = 3  # Number of upload retry attempts

    # CompanyCam settings (loaded manually from env without prefix)
    companycam_client_id: str = ''
    companycam_client_secret: str = ''
    companycam_access_token: str = ''
    companycam_refresh_token: str = ''
    companycam_user_id: str = ''
    default_companycam_template_name: str = ''

    class Config:
        env_prefix = 'SURVEY_'
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize config and load CompanyCam settings from env."""
        super().__init__(**kwargs)
        # Load CompanyCam settings manually (no SURVEY_ prefix)
        self.companycam_client_id = os.getenv('COMPANYCAM_CLIENT_ID', self.companycam_client_id)
        self.companycam_client_secret = os.getenv('COMPANYCAM_CLIENT_SECRET', self.companycam_client_secret)
        self.companycam_access_token = os.getenv('COMPANYCAM_ACCESS_TOKEN', self.companycam_access_token)
        self.companycam_refresh_token = os.getenv('COMPANYCAM_REFRESH_TOKEN', self.companycam_refresh_token)
        self.companycam_user_id = os.getenv('COMPANYCAM_USER_ID', self.companycam_user_id)

    def get(self, key, default=None):
        """Get a configuration value (backward compatibility)."""
        return getattr(self, key, default)

    def set(self, key, value):
        """Set a configuration value (backward compatibility)."""
        setattr(self, key, value)

    def get_all(self):
        """Get all configuration values as dictionary."""
        return self.model_dump()
