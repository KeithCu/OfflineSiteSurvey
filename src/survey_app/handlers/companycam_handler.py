"""CompanyCam integration handler for SurveyApp."""
import toga
import asyncio
import logging
from typing import Optional


class CompanyCamHandler:
    """Handles CompanyCam OAuth and synchronization operations."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect_to_companycam(self, widget):
        """Start CompanyCam OAuth connection flow."""
        try:
            if self.app.companycam_service.is_connected():
                self.app.status_label.text = "Already connected to CompanyCam"
                return

            self.app.companycam_service.start_oauth_flow()
            self.app.status_label.text = "Opening CompanyCam authorization page..."

        except Exception as e:
            self.logger.error(f"Failed to start OAuth flow: {e}")
            self.app.status_label.text = f"Failed to connect to CompanyCam: {e}"

    def handle_oauth_callback(self, auth_code: str) -> bool:
        """Handle OAuth callback from CompanyCam."""
        try:
            success = self.app.companycam_service.handle_oauth_callback(auth_code)
            if success:
                self.app.status_label.text = "Successfully connected to CompanyCam!"
                # Refresh UI to show sync button if applicable
                self._update_sync_button_visibility()
                return True
            else:
                self.app.status_label.text = "Failed to connect to CompanyCam"
                return False
        except Exception as e:
            self.logger.error(f"OAuth callback failed: {e}")
            self.app.status_label.text = f"Connection failed: {e}"
            return False

    def sync_survey_to_companycam(self, widget):
        """Sync the current completed survey to CompanyCam."""
        if not self.app.current_survey:
            self.app.status_label.text = "No survey selected"
            return

        if self.app.current_survey.get('status') != 'completed':
            self.app.status_label.text = "Survey must be completed before syncing"
            return

        if not self.app.companycam_service.is_connected():
            self.app.status_label.text = "Please connect to CompanyCam first"
            return

        # Start async sync process
        asyncio.create_task(self._perform_sync())

    async def _perform_sync(self):
        """Perform the actual sync operation asynchronously."""
        try:
            self.app.status_label.text = "Starting sync to CompanyCam..."

            # Get survey details
            survey = self.app.current_survey
            project_name = f"{survey.get('title', 'Survey')}"

            # Check if project already exists
            existing_project = self.app.companycam_service.find_project_by_name(project_name)

            if existing_project:
                project_id = existing_project['id']
                self.app.status_label.text = f"Using existing CompanyCam project: {existing_project['name']}"
            else:
                # Create new project
                project_data = self.app.companycam_service.create_project(
                    name=project_name,
                    description=survey.get('description', ''),
                    address=self._get_survey_address()
                )

                if not project_data:
                    self.app.status_label.text = "Failed to create CompanyCam project"
                    return

                project_id = project_data['id']
                self.app.status_label.text = f"Created CompanyCam project: {project_data['name']}"

            # Get photos for this survey
            photos = self.app.db.get_photos(survey_id=survey['id'])
            total_photos = len(photos.get('photos', []))

            if total_photos == 0:
                self.app.status_label.text = "No photos to sync"
                return

            self.app.status_label.text = f"Uploading {total_photos} photos to CompanyCam..."

            uploaded_count = 0
            failed_count = 0

            for photo in photos['photos']:
                try:
                    # Get photo data (assuming it's stored locally for now)
                    # In production, this would download from cloud storage if needed
                    if photo.image_data:
                        filename = f"survey_photo_{photo.id}.jpg"
                        result = self.app.companycam_service.upload_photo(
                            project_id=project_id,
                            image_data=photo.image_data,
                            filename=filename,
                            description=photo.description or "",
                            latitude=photo.latitude if photo.latitude else None,
                            longitude=photo.longitude if photo.longitude else None
                        )

                        if result:
                            uploaded_count += 1
                            self.app.status_label.text = f"Uploaded {uploaded_count}/{total_photos} photos..."
                        else:
                            failed_count += 1
                            self.logger.warning(f"Failed to upload photo {photo.id}")
                    else:
                        failed_count += 1
                        self.logger.warning(f"No image data for photo {photo.id}")

                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Error uploading photo {photo.id}: {e}")

            # Final status
            if failed_count == 0:
                self.app.status_label.text = f"Successfully synced {uploaded_count} photos to CompanyCam!"
            else:
                self.app.status_label.text = f"Synced {uploaded_count} photos, {failed_count} failed"

        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            self.app.status_label.text = f"Sync failed: {e}"

    def _get_survey_address(self) -> str:
        """Get address for the current survey."""
        if self.app.current_site:
            return self.app.current_site.address or ""
        return ""

    def _update_sync_button_visibility(self):
        """Update visibility of sync button based on connection status."""
        # This would be called when UI needs to be refreshed
        # For now, we'll handle this in the UI creation
        pass

    def handle_oauth_url(self, url: str) -> bool:
        """Handle OAuth callback URL (for custom URL scheme handling)."""
        try:
            # Parse the URL to extract the authorization code
            # URL format: mysurveyapp://auth?code=ABC123&state=survey_app_oauth
            if 'code=' in url:
                # Extract code from URL
                code_start = url.find('code=') + 5
                code_end = url.find('&', code_start)
                if code_end == -1:
                    code_end = len(url)
                auth_code = url[code_start:code_end]

                return self.handle_oauth_callback(auth_code)
            else:
                self.app.status_label.text = "Invalid OAuth callback URL"
                return False
        except Exception as e:
            self.logger.error(f"Failed to handle OAuth URL: {e}")
            self.app.status_label.text = f"OAuth URL handling failed: {e}"
            return False

    def disconnect_from_companycam(self, widget):
        """Disconnect from CompanyCam by clearing tokens."""
        self.app.config.set('companycam_access_token', '')
        self.app.config.set('companycam_refresh_token', '')
        self.app.config.set('companycam_user_id', '')
        self.app.status_label.text = "Disconnected from CompanyCam"
        self._update_sync_button_visibility()