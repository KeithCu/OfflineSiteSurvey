"""Configuration management UI views."""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN


class ConfigView:
    """View class for configuration/settings UI.
    
    Handles all UI construction for configuration-related windows and dialogs.
    Separates UI concerns from business logic (which is in SyncHandler).
    """
    
    def __init__(self, handler):
        """Initialize the config view.
        
        Args:
            handler: SyncHandler instance that handles business logic
        """
        self.handler = handler
        self.app = handler.app
    
    def create_config_window(self):
        """Create and return the configuration settings window.
        
        Returns:
            toga.Window: Configured config window
        """
        config_window = toga.Window(title="Settings")
        
        # Config labels and inputs
        quality_label = toga.Label('Image Compression Quality (1-100):', style=Pack(padding=(10, 5, 5, 5)))
        self.app.quality_input = toga.TextInput(
            value=str(self.app.config.get('image_compression_quality', 75)),
            style=Pack(padding=(5, 5, 10, 5))
        )
        
        sync_label = toga.Label('Auto-sync Interval (seconds, 0=disabled):', style=Pack(padding=(10, 5, 5, 5)))
        self.app.sync_input = toga.TextInput(
            value=str(self.app.config.get('auto_sync_interval', 300)),
            style=Pack(padding=(5, 5, 10, 5))
        )
        
        offline_label = toga.Label('Max Offline Days:', style=Pack(padding=(10, 5, 5, 5)))
        self.app.offline_input = toga.TextInput(
            value=str(self.app.config.get('max_offline_days', 30)),
            style=Pack(padding=(5, 5, 10, 5))
        )
        
        # Save button
        save_button = toga.Button(
            'Save Settings',
            on_press=self.handler.save_config,
            style=Pack(padding=(10, 5, 10, 5))
        )
        
        close_button = toga.Button(
            'Close',
            on_press=lambda w: config_window.close(),
            style=Pack(padding=(5, 5, 10, 5))
        )
        
        # Create config box
        config_box = toga.Box(
            children=[
                quality_label,
                self.app.quality_input,
                sync_label,
                self.app.sync_input,
                offline_label,
                self.app.offline_input,
                save_button,
                close_button
            ],
            style=Pack(direction=COLUMN, padding=20)
        )
        
        config_window.content = config_box
        return config_window

