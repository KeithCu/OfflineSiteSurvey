"""Sync management handlers for SurveyApp."""
import threading
import time
import random
import requests
import logging
import os


class SyncHandler:
    """Handles synchronization operations."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sync_scheduler = None
        self.sync_failures = 0
        self.last_sync_success = None
        self._sync_lock = threading.Lock()  # Prevent concurrent sync operations

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
        # Prevent concurrent sync operations
        if not self._sync_lock.acquire(blocking=False):
            self.logger.info("Sync already in progress, skipping")
            return True  # Consider this a success to avoid error status

        try:
            # 1. Sync Pending Photos first
            photos_synced = self.sync_pending_photos()
            if not photos_synced:
                self.logger.warning("Some photos failed to sync")

            # 2. Get local changes (CRDT)
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
                    # If CRDT sync fails, we consider the whole sync a failure
                    return False

            # 3. Get remote changes from the server
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
        finally:
            self._sync_lock.release()

    def sync_pending_photos(self):
        """Upload pending photos to server."""
        pending_photos = self.app.db.get_pending_upload_photos()
        all_success = True
        
        for photo in pending_photos:
            try:
                # Get local path using the db helper or fallback to file_path
                photo_path = self.app.db.get_photo_path(photo.id)
                
                if not photo_path or not os.path.exists(photo_path):
                    self.logger.warning(f"Photo file not found for {photo.id}, skipping upload")
                    # Mark as failed? Or just leave pending? 
                    # Leaving pending so we retry later if file appears (unlikely) or user fixes it
                    continue
                
                # Prepare metadata
                data = {
                    'id': photo.id,
                    'description': photo.description,
                    'category': photo.category,
                    'latitude': photo.latitude,
                    'longitude': photo.longitude,
                    'tags': photo.tags,
                    'question_id': photo.question_id
                }
                
                # Upload
                response = self.app.api_service.upload_photo(
                    f'/api/surveys/{photo.survey_id}/photos',
                    photo_path,
                    data=data
                )
                
                if response.status_code in [200, 201]:
                    # Mark as uploaded
                    # Note: Server might return cloud_url/thumbnail_url if it uploads synchronously,
                    # but our backend queues it.
                    # We mark it as uploaded locally so we don't resend binary.
                    # The CRDT sync will eventually bring back the cloud URLs.
                    self.app.db.mark_photo_uploaded(photo.id)
                    self.logger.info(f"Uploaded photo {photo.id}")
                else:
                    self.logger.error(f"Failed to upload photo {photo.id}: {response.status_code}")
                    all_success = False
                    
            except Exception as e:
                self.logger.error(f"Exception uploading photo {photo.id}: {e}")
                all_success = False
                
        return all_success

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
        if not self.app.offline_queue:
            return

        self.logger.info(f"Processing {len(self.app.offline_queue)} offline operations")
        
        # Create a copy of the queue to iterate
        queue_copy = list(self.app.offline_queue)
        self.app.offline_queue.clear()
        
        failed_ops = []
        
        for op in queue_copy:
            try:
                method = op.get('method')
                endpoint = op.get('endpoint')
                kwargs = op.get('kwargs', {})
                
                if method == 'POST':
                    self.app.api_service.post(endpoint, **kwargs)
                elif method == 'PUT':
                    self.app.api_service.put(endpoint, **kwargs)
                elif method == 'DELETE':
                    self.app.api_service.delete(endpoint, **kwargs)
                # GET requests are usually not queued
                
            except Exception as e:
                self.logger.error(f"Failed to process offline operation {op}: {e}")
                failed_ops.append(op)
        
        # Re-queue failed operations
        if failed_ops:
            self.app.offline_queue.extend(failed_ops)
            
        if len(failed_ops) < len(queue_copy):
            self.logger.info(f"Successfully processed {len(queue_copy) - len(failed_ops)} offline operations")

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

        # CompanyCam section
        companycam_label = toga.Label('CompanyCam Integration:', style=toga.Pack(padding=(20, 5, 10, 5), font_weight='bold'))

        # Connection status
        connection_status = "Connected" if self.app.companycam_service.is_connected() else "Not Connected"
        status_label = toga.Label(f'Status: {connection_status}', style=toga.Pack(padding=(5, 5, 5, 5)))

        connect_button = toga.Button(
            'Connect to CompanyCam',
            on_press=self.app.companycam_handler.connect_to_companycam,
            style=toga.Pack(padding=(5, 5, 5, 5))
        )

        disconnect_button = toga.Button(
            'Disconnect',
            on_press=self.app.companycam_handler.disconnect_from_companycam,
            style=toga.Pack(padding=(5, 5, 5, 5))
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
                companycam_label,
                status_label,
                connect_button,
                disconnect_button,
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
