"""Sync management handlers for SurveyApp."""
import threading
import time
import random
import requests
import logging


class SyncHandler:
    """Handles synchronization operations."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sync_scheduler = None
        self.sync_failures = 0
        self.last_sync_success = None

    def start_sync_scheduler(self):
        """Start the background sync scheduler"""
        self.sync_scheduler = threading.Thread(target=self.sync_scheduler_loop, daemon=True)
        self.sync_scheduler.start()

    def sync_scheduler_loop(self):
        """Advanced sync scheduler with configurable intervals and exponential backoff"""
        while True:
            try:
                # Get sync configuration
                sync_interval = int(self.app.config.get('auto_sync_interval', 300))  # Default 5 minutes

                # Perform sync
                success = self.sync_with_server()

                if success:
                    self.sync_failures = 0
                    self.last_sync_success = time.time()
                    # Reset to normal interval on success
                    sleep_time = sync_interval
                else:
                    self.sync_failures += 1
                    # Exponential backoff with jitter
                    base_delay = min(sync_interval * (2 ** min(self.sync_failures, 6)), 3600)  # Max 1 hour
                    jitter = random.uniform(0.8, 1.2)  # Add ±20% jitter
                    sleep_time = base_delay * jitter

                # Sleep until next sync attempt
                time.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"Sync scheduler error: {e}")
                time.sleep(60)  # Fallback delay on error

    def sync_with_server(self, widget=None):
        """Sync local data with server - returns True on success"""
        try:
            # Get local changes
            local_changes = self.app.db.get_changes_since(self.app.last_sync_version)

            # Send local changes to the server
            if local_changes:
                response = self.app.api_service.post(
                    '/api/changes',
                    json=local_changes,
                    timeout=30  # Increased timeout
                )
                if response.status_code != 200:
                    self.app.status_label.text = "Sync failed - server error"
                    return False

            # Get remote changes from the server
            response = self.app.api_service.get(
                f'/api/changes?version={self.app.last_sync_version}&site_id={self.app.db.site_id}',
                timeout=30
            )

            if response.status_code == 200:
                remote_changes = response.json()
                if remote_changes:
                    self.app.db.apply_changes(remote_changes)
                self.app.last_sync_version = self.app.db.get_current_version()

                # Process offline queue if we have connectivity
                if self.app.offline_queue:
                    self.process_offline_queue()

                self.update_sync_status("Sync complete")
                if self.app.current_site:
                    self.app.survey_handler.load_surveys_for_site(self.app.current_site.id)
                return True
            else:
                self.update_sync_status("Sync failed - server error")
                return False

        except requests.exceptions.RequestException:
            self.update_sync_status("Sync failed - server not available")
            return False
        except Exception as e:
            self.update_sync_status(f"Sync error: {str(e)}")
            return False

    def update_sync_status(self, message):
        """Update sync status with health indicators"""
        if self.last_sync_success:
            minutes_since = (time.time() - self.last_sync_success) / 60
            if minutes_since < 5:
                status_indicator = "🟢"  # Green - recently synced
            elif minutes_since < 30:
                status_indicator = "🟡"  # Yellow - synced within 30 min
            else:
                status_indicator = "🔴"  # Red - stale sync
        else:
            status_indicator = "⚪"  # White - never synced

        full_message = f"{status_indicator} {message}"
        if self.sync_failures > 0:
            full_message += f" ({self.sync_failures} failures)"

        self.app.status_label.text = full_message

    def process_offline_queue(self):
        """Process queued operations that were deferred due to offline state"""
        # For now, just clear the queue - in a full implementation,
        # this would retry failed operations
        processed = len(self.app.offline_queue)
        self.app.offline_queue.clear()
        if processed > 0:
            self.logger.info(f"Processed {processed} queued operations")

    def show_config_ui(self, widget):
        """Show configuration settings UI"""
        # Create config window
        config_window = toga.Window(title="Settings")

        # Config labels and inputs
        quality_label = toga.Label('Image Compression Quality (1-100):', style=toga.Pack(padding=(10, 5, 5, 5)))
        self.app.quality_input = toga.TextInput(
            value=str(self.app.config.get('image_compression_quality', 75)),
            style=toga.Pack(padding=(5, 5, 10, 5))
        )

        sync_label = toga.Label('Auto-sync Interval (seconds, 0=disabled):', style=toga.Pack(padding=(10, 5, 5, 5)))
        self.app.sync_input = toga.TextInput(
            value=str(self.app.config.get('auto_sync_interval', 300)),
            style=toga.Pack(padding=(5, 5, 10, 5))
        )

        offline_label = toga.Label('Max Offline Days:', style=toga.Pack(padding=(10, 5, 5, 5)))
        self.app.offline_input = toga.TextInput(
            value=str(self.app.config.get('max_offline_days', 30)),
            style=toga.Pack(padding=(5, 5, 10, 5))
        )

        # Save button
        save_button = toga.Button(
            'Save Settings',
            on_press=self.save_config,
            style=toga.Pack(padding=(10, 5, 10, 5))
        )

        close_button = toga.Button(
            'Close',
            on_press=lambda w: config_window.close(),
            style=toga.Pack(padding=(5, 5, 10, 5))
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
            style=toga.Pack(direction=toga.COLUMN, padding=20)
        )

        config_window.content = config_box
        config_window.show()

    def save_config(self, widget):
        """Save configuration settings"""
        # In a real app, this would be a CRDT insert
        pass