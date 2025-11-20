"""CompanyCam integration handler for SurveyApp."""
import toga
import asyncio
import logging


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

    def handle_oauth_callback(self, auth_code):
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

            # 1. Get survey details and create/find project
            survey = self.app.current_survey
            project_name = f"{survey.get('title', 'Survey')}"
            existing_project = self.app.companycam_service.find_project_by_name(project_name)

            if existing_project:
                project_id = existing_project['id']
                self.app.status_label.text = f"Using existing CompanyCam project: {existing_project['name']}"
            else:
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

            # 2. Create Checklist from a template
            self.app.status_label.text = "Creating checklist..."
            templates = self.app.companycam_service.list_checklist_templates()
            if not templates:
                self.app.status_label.text = "No checklist templates found in CompanyCam."
                return

            template_id = None
            default_template_name = self.app.config.get('default_companycam_template_name')
            if default_template_name:
                for template in templates:
                    if template['name'] == default_template_name:
                        template_id = template['id']
                        break

            if not template_id:
                self.logger.warning(f"Default checklist template '{default_template_name}' not found. Using the first available template.")
                template_id = templates[0]['id']

            checklist_data = self.app.companycam_service.create_project_checklist(project_id, template_id)
            if not checklist_data:
                self.app.status_label.text = "Failed to create checklist."
                return
            checklist_id = checklist_data['id']
            self.app.status_label.text = "Checklist created. Mapping questions..."

            # 3. Map Questions and Answers to Checklist Items
            checklist_details = self.app.companycam_service.get_project_checklist(project_id, checklist_id)
            if checklist_details and 'items' in checklist_details:
                survey_responses = self.app.db_service.get_responses(survey_id=survey['id'])
                for response in survey_responses:
                    for item in checklist_details['items']:
                        if response.question.strip().lower() == item['title'].strip().lower():
                            self.app.companycam_service.update_checklist_item(checklist_id, item['id'], response['answer'])
                            self.logger.info(f"Mapped question: {response['question']}")
                            break

            # 4. Upload Photos with Mapped Tags
            photos = self.app.db.get_photos(survey_id=survey['id'])
            total_photos = len(photos.get('photos', []))
            if total_photos == 0:
                self.app.status_label.text = "Sync complete (no photos to upload)."
                return

            self.app.status_label.text = f"Uploading {total_photos} photos..."
            uploaded_count = 0
            failed_count = 0

            for photo in photos['photos']:
                try:
                    if photo.image_data:
                        # Map tags
                        app_tags = self.app.db.get_tags_for_photo(photo.id)
                        companycam_tag_ids = []
                        if app_tags:
                            for app_tag in app_tags:
                                matched_tag = self.app.tag_mapper.find_best_match(app_tag)
                                if matched_tag:
                                    companycam_tag_ids.append(matched_tag['id'])

                        # Add section as a tag
                        section = self.app.db.get_section_for_photo(photo.id)
                        if section:
                            section_tag_name = f"#section-{section.lower().replace(' ', '-')}"
                            matched_tag = self.app.tag_mapper.find_best_match(section_tag_name)
                            if matched_tag:
                                companycam_tag_ids.append(matched_tag['id'])
                            else:
                                # Create the tag if it doesn't exist
                                new_tag = self.app.companycam_service.create_tag(section_tag_name)
                                if new_tag:
                                    companycam_tag_ids.append(new_tag['id'])

                        filename = f"survey_photo_{photo.id}.jpg"
                        result = self.app.companycam_service.upload_photo(
                            project_id=project_id,
                            image_data=photo.image_data,
                            filename=filename,
                            description=photo.description or "",
                            latitude=photo.latitude if photo.latitude else None,
                            longitude=photo.longitude if photo.longitude else None,
                            tag_ids=companycam_tag_ids
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

            if failed_count == 0:
                self.app.status_label.text = f"Successfully synced {uploaded_count} photos to CompanyCam!"
            else:
                self.app.status_label.text = f"Sync complete. Uploaded: {uploaded_count}, Failed: {failed_count}"

        except Exception as e:
            self.logger.error(f"Sync failed: {e}")
            self.app.status_label.text = f"An error occurred during sync: {e}"

    def _get_survey_address(self):
        """Get address for the current survey."""
        if self.app.current_site:
            return self.app.current_site.address or ""
        return ""

    def _update_sync_button_visibility(self):
        """Update visibility of sync button based on connection status."""
        # This would be called when UI needs to be refreshed
        pass

    def handle_oauth_url(self, url):
        """Handle OAuth callback URL (for custom URL scheme handling)."""
        try:
            if 'code=' in url:
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
